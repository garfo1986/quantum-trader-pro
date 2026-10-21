"""
Motor de Backtesting cuantitativo sin Look-Ahead Bias.
Simula operaciones históricas vela por vela incorporando comisiones, spread y slippage,
y compara la estrategia del sistema contra la referencia pasiva Buy & Hold.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from signals.signal_engine import SignalEngine


class BacktestEngine:
    """Ejecuta simulaciones históricas estrictamente causales."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_rate: float = 0.001,
        spread_rate: float = 0.0002,
        slippage_rate: float = 0.0005,
        allow_short: bool = True
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.spread_rate = spread_rate
        self.slippage_rate = slippage_rate
        self.allow_short = allow_short
        self.signal_engine = SignalEngine()

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Ejecuta el backtest vela a vela.
        Devuelve métricas completas y la serie de equity curve comparativa.
        """
        if len(df) < 60:
            return {"success": False, "error": "Se requieren al menos 60 velas históricas para ejecutar el backtest."}

        cash = self.initial_capital
        position_side: Optional[str] = None  # 'LONG', 'SHORT', None
        position_shares = 0.0
        position_entry_price = 0.0
        position_entry_amount = 0.0
        position_entry_date = None

        trades = []
        strategy_equity = []
        bh_equity = []
        dates = []

        first_close = float(df["close"].iloc[50])  # Inicio tras periodo de calentamiento de indicadores
        bh_shares = (self.initial_capital * (1.0 - self.commission_rate)) / first_close

        # Recorrer a partir de la vela 50 (warmup)
        for i in range(50, len(df)):
            current_date = df.index[i]
            dates.append(str(current_date))
            sub_df = df.iloc[: i + 1]

            curr_close = float(sub_df["close"].iloc[-1])
            sig = self.signal_engine.evaluate_latest(sub_df)
            sig_type = sig["type"]

            # 1. Evaluar si cerramos posición existente
            if position_side == "LONG" and ("SELL" in sig_type):
                # Cerrar LONG
                exit_price = curr_close * (1.0 - (self.spread_rate / 2.0) - self.slippage_rate)
                gross_amount = position_shares * exit_price
                exit_comm = gross_amount * self.commission_rate
                net_pnl = (gross_amount - position_entry_amount) - (exit_comm + (position_entry_amount * self.commission_rate))
                pnl_pct = (net_pnl / position_entry_amount) * 100.0 if position_entry_amount > 0 else 0.0

                cash += gross_amount - exit_comm
                trades.append({
                    "side": "LONG",
                    "entry_date": position_entry_date,
                    "exit_date": str(current_date),
                    "entry_price": position_entry_price,
                    "exit_price": exit_price,
                    "pnl_usd": net_pnl,
                    "pnl_pct": pnl_pct,
                    "reason": sig_type
                })
                position_side = None
                position_shares = 0.0

            elif position_side == "SHORT" and ("BUY" in sig_type):
                # Cerrar SHORT
                exit_price = curr_close * (1.0 + (self.spread_rate / 2.0) + self.slippage_rate)
                gross_buyback = position_shares * exit_price
                exit_comm = gross_buyback * self.commission_rate
                net_pnl = (position_entry_price - exit_price) * position_shares - (exit_comm + (position_entry_amount * self.commission_rate))
                pnl_pct = (net_pnl / position_entry_amount) * 100.0 if position_entry_amount > 0 else 0.0

                cash += max(0.0, position_entry_amount + net_pnl)
                trades.append({
                    "side": "SHORT",
                    "entry_date": position_entry_date,
                    "exit_date": str(current_date),
                    "entry_price": position_entry_price,
                    "exit_price": exit_price,
                    "pnl_usd": net_pnl,
                    "pnl_pct": pnl_pct,
                    "reason": sig_type
                })
                position_side = None
                position_shares = 0.0

            # 2. Evaluar apertura de nueva posición si estamos en liquidez
            if position_side is None and cash > 50.0:
                if "BUY" in sig_type:
                    # Abrir LONG
                    invest_amt = cash * 0.95  # Dejar pequeño colchón de liquidez
                    entry_price = curr_close * (1.0 + (self.spread_rate / 2.0) + self.slippage_rate)
                    comm = invest_amt * self.commission_rate
                    position_shares = (invest_amt - comm) / entry_price
                    position_entry_price = entry_price
                    position_entry_amount = invest_amt
                    position_entry_date = str(current_date)
                    position_side = "LONG"
                    cash -= invest_amt

                elif "SELL" in sig_type and self.allow_short:
                    # Abrir SHORT
                    invest_amt = cash * 0.95
                    entry_price = curr_close * (1.0 - (self.spread_rate / 2.0) - self.slippage_rate)
                    comm = invest_amt * self.commission_rate
                    position_shares = (invest_amt - comm) / entry_price
                    position_entry_price = entry_price
                    position_entry_amount = invest_amt
                    position_entry_date = str(current_date)
                    position_side = "SHORT"
                    cash -= invest_amt

            # 3. Calcular Equity del paso
            if position_side == "LONG":
                curr_pos_val = position_shares * curr_close
            elif position_side == "SHORT":
                curr_pos_val = position_entry_amount + ((position_entry_price - curr_close) * position_shares)
            else:
                curr_pos_val = 0.0

            step_strat_equity = cash + curr_pos_val
            strategy_equity.append(step_strat_equity)

            # Buy & Hold equity
            step_bh_equity = bh_shares * curr_close
            bh_equity.append(step_bh_equity)

        # Cerrar posición final si quedara abierta al terminar el dataset
        if position_side is not None:
            final_close = float(df["close"].iloc[-1])
            if position_side == "LONG":
                pnl = (final_close - position_entry_price) * position_shares
            else:
                pnl = (position_entry_price - final_close) * position_shares
            trades.append({
                "side": position_side,
                "entry_date": position_entry_date,
                "exit_date": str(df.index[-1]),
                "entry_price": position_entry_price,
                "exit_price": final_close,
                "pnl_usd": pnl,
                "pnl_pct": (pnl / position_entry_amount) * 100.0 if position_entry_amount > 0 else 0.0,
                "reason": "FIN_HISTÓRICO"
            })

        # Métricas de la estrategia
        final_strat_equity = strategy_equity[-1] if strategy_equity else self.initial_capital
        strat_return_pct = ((final_strat_equity - self.initial_capital) / self.initial_capital) * 100.0

        # Drawdown de la estrategia
        strat_peak = self.initial_capital
        strat_max_dd_pct = 0.0
        for eq in strategy_equity:
            if eq > strat_peak:
                strat_peak = eq
            dd = ((strat_peak - eq) / strat_peak) * 100.0 if strat_peak > 0 else 0.0
            if dd > strat_max_dd_pct:
                strat_max_dd_pct = dd

        # Métricas Buy & Hold
        final_bh_equity = bh_equity[-1] if bh_equity else self.initial_capital
        bh_return_pct = ((final_bh_equity - self.initial_capital) / self.initial_capital) * 100.0

        bh_peak = self.initial_capital
        bh_max_dd_pct = 0.0
        for eq in bh_equity:
            if eq > bh_peak:
                bh_peak = eq
            dd = ((bh_peak - eq) / bh_peak) * 100.0 if bh_peak > 0 else 0.0
            if dd > bh_max_dd_pct:
                bh_max_dd_pct = dd

        # Estadísticas de trades
        total_trades = len(trades)
        wins = [t for t in trades if t["pnl_usd"] > 0]
        losses = [t for t in trades if t["pnl_usd"] < 0]
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum(t["pnl_usd"] for t in wins)
        gross_loss = abs(sum(t["pnl_usd"] for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        equity_df = pd.DataFrame({
            "date": dates,
            "Estrategia Sistema": strategy_equity,
            "Buy & Hold": bh_equity
        })

        return {
            "success": True,
            "initial_capital": self.initial_capital,
            "strategy": {
                "final_equity": round(final_strat_equity, 2),
                "total_return_pct": round(strat_return_pct, 2),
                "max_drawdown_pct": round(strat_max_dd_pct, 2),
                "total_trades": total_trades,
                "winning_trades": len(wins),
                "losing_trades": len(losses),
                "win_rate": round(win_rate, 2),
                "profit_factor": round(profit_factor, 2)
            },
            "buy_and_hold": {
                "final_equity": round(final_bh_equity, 2),
                "total_return_pct": round(bh_return_pct, 2),
                "max_drawdown_pct": round(bh_max_dd_pct, 2)
            },
            "trades": trades,
            "equity_curve": equity_df
        }
