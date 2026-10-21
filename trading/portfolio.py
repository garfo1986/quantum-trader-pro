"""
Módulo de cálculo de rendimiento de cartera, estadísticas cuantitativas, curva de equity
y simulador contrafactual "¿Qué habría pasado?".
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np


class PortfolioAnalyzer:
    """Calcula métricas de rendimiento avanzadas para auditoría de trading."""

    @staticmethod
    def calculate_performance_metrics(
        initial_capital: float,
        current_equity: float,
        closed_trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calcula Win Rate, Profit Factor, Drawdown, Sharpe y medias de ganancia/pérdida."""
        total_pnl_usd = current_equity - initial_capital
        total_return_pct = (total_pnl_usd / initial_capital) * 100.0 if initial_capital > 0 else 0.0

        if not closed_trades:
            return {
                "initial_capital": initial_capital,
                "current_equity": current_equity,
                "total_pnl_usd": total_pnl_usd,
                "total_return_pct": total_return_pct,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_usd": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "equity_curve": pd.DataFrame({"trade": [0], "equity": [initial_capital]})
            }

        df_trades = pd.DataFrame(closed_trades)
        total_trades = len(df_trades)
        wins = df_trades[df_trades["pnl_usd"] > 0]
        losses = df_trades[df_trades["pnl_usd"] < 0]

        winning_count = len(wins)
        losing_count = len(losses)
        win_rate = (winning_count / total_trades) * 100.0 if total_trades > 0 else 0.0

        avg_win = float(wins["pnl_usd"].mean()) if winning_count > 0 else 0.0
        avg_loss = float(losses["pnl_usd"].mean()) if losing_count > 0 else 0.0

        gross_profit = float(wins["pnl_usd"].sum()) if winning_count > 0 else 0.0
        gross_loss = float(abs(losses["pnl_usd"].sum())) if losing_count > 0 else 0.0

        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        # Construcción de la Curva de Equity acumulada
        # Orden cronológico de cierre
        df_sorted = df_trades.sort_values(by="id").copy()
        equity_values = [initial_capital]
        running_equity = initial_capital

        for _, row in df_sorted.iterrows():
            running_equity += float(row["pnl_usd"])
            equity_values.append(running_equity)

        # Cálculo de Máximo Drawdown (de pico a valle)
        peak = equity_values[0]
        max_dd_usd = 0.0
        max_dd_pct = 0.0

        for eq in equity_values:
            if eq > peak:
                peak = eq
            dd_usd = peak - eq
            dd_pct = (dd_usd / peak) * 100.0 if peak > 0 else 0.0
            if dd_usd > max_dd_usd:
                max_dd_usd = dd_usd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        # Cálculo de Sharpe Ratio (solo si hay al menos 5 trades para significancia estadística)
        sharpe = 0.0
        if total_trades >= 5:
            returns = df_trades["pnl_pct"].values / 100.0
            std_dev = np.std(returns)
            if std_dev > 0:
                # Estimación Sharpe anualizada asumiendo ~252 periodos
                sharpe = float(np.mean(returns) / std_dev * np.sqrt(min(252, total_trades)))

        curve_df = pd.DataFrame({
            "trade_num": list(range(len(equity_values))),
            "equity": equity_values
        })

        return {
            "initial_capital": initial_capital,
            "current_equity": current_equity,
            "total_pnl_usd": total_pnl_usd,
            "total_return_pct": total_return_pct,
            "total_trades": total_trades,
            "winning_trades": winning_count,
            "losing_trades": losing_count,
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_usd": round(max_dd_usd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "sharpe_ratio": round(sharpe, 2),
            "equity_curve": curve_df
        }

    @staticmethod
    def simulate_what_if(trade: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Calcula qué habría pasado si una posición cerrada se hubiese mantenido abierta
        hasta el precio actual de mercado.
        """
        side = trade["side"]
        entry_price = float(trade["entry_price"])
        exit_price = float(trade["exit_price"])
        shares = float(trade["shares"])
        invested = float(trade["entry_amount"])
        realized_pnl = float(trade["pnl_usd"])
        realized_pct = float(trade["pnl_pct"])

        if side == "LONG":
            hypothetical_val = shares * current_price
            hypothetical_pnl = hypothetical_val - invested
        else:
            hypothetical_val = invested + ((entry_price - current_price) * shares)
            hypothetical_pnl = (entry_price - current_price) * shares

        hypothetical_pct = (hypothetical_pnl / invested) * 100.0 if invested > 0 else 0.0
        difference_usd = hypothetical_pnl - realized_pnl

        return {
            "symbol": trade["symbol"],
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "current_price": current_price,
            "invested": invested,
            "shares": shares,
            "realized_pnl_usd": realized_pnl,
            "realized_pnl_pct": realized_pct,
            "hypothetical_pnl_usd": hypothetical_pnl,
            "hypothetical_pnl_pct": hypothetical_pct,
            "difference_usd": difference_usd,
            "was_closing_better": realized_pnl > hypothetical_pnl
        }
