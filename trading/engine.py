"""
Motor de Paper Trading profesional con simulación de dinero ficticio.
Soporte completo para LONG y SHORT, Stop Loss, Take Profit y costes realistas.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import math

from database.db import (
    get_account_balance, update_account_balance,
    save_open_position, get_open_positions, close_position_in_db,
    get_closed_trades, reset_account
)


class PaperTradingEngine:
    """
    Simulador de broker de ejecución para Paper Trading.
    Garantiza cálculos matemáticos exactos para posiciones largas y cortas.
    """

    def __init__(
        self,
        commission_rate: float = 0.001,  # 0.1%
        spread_rate: float = 0.0002,     # 0.02%
        slippage_rate: float = 0.0005    # 0.05%
    ):
        self.commission_rate = commission_rate
        self.spread_rate = spread_rate
        self.slippage_rate = slippage_rate

    def open_position(
        self,
        symbol: str,
        side: str,
        current_price: float,
        amount_usd: Optional[float] = None,
        shares: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        custom_commission: Optional[float] = None,
        custom_spread: Optional[float] = None,
        custom_slippage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Abre una posición simulada LONG o SHORT.
        Permite especificar cantidad en dólares o número de acciones/criptos.
        """
        side = side.upper()
        if side not in ["LONG", "SHORT"]:
            return {"success": False, "error": f"Lado de orden inválido: {side}. Debe ser LONG o SHORT."}

        if current_price <= 0:
            return {"success": False, "error": "El precio actual debe ser mayor a 0."}

        comm_rate = self.commission_rate if custom_commission is None else custom_commission
        sprd_rate = self.spread_rate if custom_spread is None else custom_spread
        slip_rate = self.slippage_rate if custom_slippage is None else custom_slippage

        # Precio de ejecución realista (Slippage y Spread adversos)
        if side == "LONG":
            # Al comprar pagamos el Ask (más spread y slippage alcista)
            exec_price = current_price * (1.0 + (sprd_rate / 2.0) + slip_rate)
        else:
            # Al vender en corto recibimos el Bid (menos spread y slippage bajista)
            exec_price = current_price * (1.0 - (sprd_rate / 2.0) - slip_rate)

        # Determinar número de acciones o importe
        if amount_usd is not None and amount_usd > 0:
            invest_usd = float(amount_usd)
            shares_qty = invest_usd / exec_price
        elif shares is not None and shares > 0:
            shares_qty = float(shares)
            invest_usd = shares_qty * exec_price
        else:
            return {"success": False, "error": "Debes especificar un importe en USD o número de acciones."}

        # Comisión de apertura
        entry_commission = invest_usd * comm_rate
        total_required = invest_usd + entry_commission

        # Verificar saldo en cuenta
        account = get_account_balance()
        current_cash = account["balance"]

        if current_cash < total_required:
            return {
                "success": False,
                "error": f"Saldo insuficiente. Requieres ${total_required:,.2f} USD pero dispones de ${current_cash:,.2f} USD."
            }

        # Validaciones de Stop Loss y Take Profit
        if stop_loss is not None and stop_loss > 0:
            if side == "LONG" and stop_loss >= exec_price:
                return {"success": False, "error": "Para LONG, el Stop Loss debe ser MENOR que el precio de entrada."}
            if side == "SHORT" and stop_loss <= exec_price:
                return {"success": False, "error": "Para SHORT, el Stop Loss debe ser MAYOR que el precio de entrada."}

        if take_profit is not None and take_profit > 0:
            if side == "LONG" and take_profit <= exec_price:
                return {"success": False, "error": "Para LONG, el Take Profit debe ser MAYOR que el precio de entrada."}
            if side == "SHORT" and take_profit >= exec_price:
                return {"success": False, "error": "Para SHORT, el Take Profit debe ser MENOR que el precio de entrada."}

        # Descontar efectivo
        new_cash = current_cash - total_required
        update_account_balance(new_cash)

        # Guardar posición en SQLite
        opened_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        pos_id = save_open_position(
            symbol=symbol,
            side=side,
            shares=shares_qty,
            entry_price=exec_price,
            entry_amount=invest_usd,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission=entry_commission,
            slippage=abs(exec_price - current_price) * shares_qty,
            opened_at=opened_at
        )

        return {
            "success": True,
            "position_id": pos_id,
            "symbol": symbol,
            "side": side,
            "shares": shares_qty,
            "entry_price": exec_price,
            "entry_amount": invest_usd,
            "commission": entry_commission,
            "new_cash": new_cash,
            "opened_at": opened_at
        }

    def close_position(
        self,
        pos_id: int,
        current_price: float,
        reason: str = "MANUAL",
        custom_commission: Optional[float] = None,
        custom_spread: Optional[float] = None,
        custom_slippage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Cierra una posición abierta con cálculo estricto de P&L y comisiones.
        """
        positions = get_open_positions()
        pos = next((p for p in positions if p["id"] == pos_id), None)
        if not pos:
            return {"success": False, "error": f"Posición #{pos_id} no encontrada o ya cerrada."}

        comm_rate = self.commission_rate if custom_commission is None else custom_commission
        sprd_rate = self.spread_rate if custom_spread is None else custom_spread
        slip_rate = self.slippage_rate if custom_slippage is None else custom_slippage

        side = pos["side"]
        shares = pos["shares"]
        entry_price = pos["entry_price"]
        entry_amount = pos["entry_amount"]
        entry_comm = pos.get("commission_paid", 0.0)

        # Precio de salida con costes de spread y slippage
        if side == "LONG":
            # Al cerrar un LONG vendemos (Bid adverso)
            exit_price = current_price * (1.0 - (sprd_rate / 2.0) - slip_rate)
            gross_exit_amount = shares * exit_price
            exit_comm = gross_exit_amount * comm_rate
            net_return_to_cash = gross_exit_amount - exit_comm

            # Ganancia neta = Retorno neto - Coste inicial total (inversión + comisión entrada)
            pnl_usd = (gross_exit_amount - entry_amount) - (entry_comm + exit_comm)
            pnl_pct = (pnl_usd / entry_amount) * 100.0

        else:  # SHORT
            # Al cerrar un SHORT recompramos (Ask adverso)
            exit_price = current_price * (1.0 + (sprd_rate / 2.0) + slip_rate)
            gross_buyback_cost = shares * exit_price
            exit_comm = gross_buyback_cost * comm_rate

            # En short: P&L = (Precio entrada - Precio salida) * shares - comisiones
            pnl_usd = (entry_price - exit_price) * shares - (entry_comm + exit_comm)
            pnl_pct = (pnl_usd / entry_amount) * 100.0
            # Retorno a efectivo = capital reservado original + P&L neto
            net_return_to_cash = max(0.0, entry_amount + pnl_usd)

        total_commission = entry_comm + exit_comm

        # Actualizar efectivo
        account = get_account_balance()
        new_cash = account["balance"] + net_return_to_cash
        update_account_balance(new_cash)

        # Cerrar en DB
        closed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        close_position_in_db(
            pos_id=pos_id,
            exit_price=exit_price,
            exit_amount=shares * exit_price,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            commission_total=total_commission,
            closed_at=closed_at,
            exit_reason=reason
        )

        return {
            "success": True,
            "position_id": pos_id,
            "symbol": pos["symbol"],
            "side": side,
            "shares": shares,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct,
            "commission_total": total_commission,
            "new_cash": new_cash,
            "closed_at": closed_at,
            "reason": reason
        }

    def check_and_trigger_stops(
        self,
        symbol: str,
        high_price: float,
        low_price: float,
        close_price: float
    ) -> List[Dict[str, Any]]:
        """
        Comprueba Stop Loss y Take Profit para las posiciones del activo.
        Política Conservadora en la misma vela:
        Si tanto el SL como el TP se alcanzan dentro del rango [Low, High],
        se asume que el STOP LOSS ocurrió primero para evitar sobreestimar ganancias.
        """
        closed_events = []
        positions = [p for p in get_open_positions() if p["symbol"] == symbol]

        for pos in positions:
            sl = pos.get("stop_loss")
            tp = pos.get("take_profit")
            side = pos["side"]

            if side == "LONG":
                sl_hit = (sl is not None and sl > 0 and low_price <= sl)
                tp_hit = (tp is not None and tp > 0 and high_price >= tp)

                if sl_hit and tp_hit:
                    # POLÍTICA CONSERVADORA DOCUMENTADA: Stop Loss primero
                    res = self.close_position(pos["id"], sl, reason="STOP_LOSS (Conservador Misma Vela)")
                    closed_events.append(res)
                elif sl_hit:
                    res = self.close_position(pos["id"], sl, reason="STOP_LOSS")
                    closed_events.append(res)
                elif tp_hit:
                    res = self.close_position(pos["id"], tp, reason="TAKE_PROFIT")
                    closed_events.append(res)

            elif side == "SHORT":
                sl_hit = (sl is not None and sl > 0 and high_price >= sl)
                tp_hit = (tp is not None and tp > 0 and low_price <= tp)

                if sl_hit and tp_hit:
                    # POLÍTICA CONSERVADORA DOCUMENTADA: Stop Loss primero
                    res = self.close_position(pos["id"], sl, reason="STOP_LOSS (Conservador Misma Vela)")
                    closed_events.append(res)
                elif sl_hit:
                    res = self.close_position(pos["id"], sl, reason="STOP_LOSS")
                    closed_events.append(res)
                elif tp_hit:
                    res = self.close_position(pos["id"], tp, reason="TAKE_PROFIT")
                    closed_events.append(res)

        return closed_events

    def get_portfolio_state(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        Calcula el estado consolidado de la cartera ficticia (Cash, Posiciones, Equity y P&L flotante).
        """
        account = get_account_balance()
        cash = account["balance"]
        initial_capital = account["initial_capital"]

        open_pos = get_open_positions()
        positions_value = 0.0
        unrealized_pnl_usd = 0.0

        detailed_positions = []
        for p in open_pos:
            sym = p["symbol"]
            curr_price = current_prices.get(sym, p["entry_price"])
            shares = p["shares"]
            side = p["side"]
            entry_price = p["entry_price"]
            entry_amount = p["entry_amount"]
            entry_comm = p.get("commission_paid", 0.0)

            if side == "LONG":
                curr_val = shares * curr_price
                pnl = (curr_val - entry_amount) - entry_comm
            else:
                curr_val = entry_amount + ((entry_price - curr_price) * shares)
                pnl = ((entry_price - curr_price) * shares) - entry_comm

            pnl_pct = (pnl / entry_amount) * 100.0 if entry_amount > 0 else 0.0

            positions_value += curr_val
            unrealized_pnl_usd += pnl

            pos_copy = dict(p)
            pos_copy["current_price"] = curr_price
            pos_copy["current_value"] = curr_val
            pos_copy["unrealized_pnl_usd"] = pnl
            pos_copy["unrealized_pnl_pct"] = pnl_pct
            detailed_positions.append(pos_copy)

        total_equity = cash + positions_value
        total_pnl_usd = total_equity - initial_capital
        total_pnl_pct = (total_pnl_usd / initial_capital) * 100.0 if initial_capital > 0 else 0.0

        return {
            "cash": cash,
            "positions_value": positions_value,
            "total_equity": total_equity,
            "initial_capital": initial_capital,
            "total_pnl_usd": total_pnl_usd,
            "total_pnl_pct": total_pnl_pct,
            "unrealized_pnl_usd": unrealized_pnl_usd,
            "open_positions": detailed_positions,
            "open_positions_count": len(detailed_positions)
        }
