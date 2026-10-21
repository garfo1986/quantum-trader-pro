"""
Tests unitarios exhaustivos para el Motor de Paper Trading.
Verifica que las matemáticas de P&L, LONG, SHORT, comisiones y Stop-Loss sean 100% exactas.
"""

import pytest
import os
from database.db import reset_account, get_account_balance, get_open_positions, get_closed_trades
from trading.engine import PaperTradingEngine


@pytest.fixture(autouse=True)
def setup_teardown_db():
    """Reinicia la cuenta antes de cada test con $10,000 USD."""
    reset_account(10000.0)
    yield
    reset_account(10000.0)


def test_initial_balance():
    account = get_account_balance()
    assert account["balance"] == 10000.0
    assert account["initial_capital"] == 10000.0


def test_long_profitable_trade_with_zero_fees():
    """LONG: Comprar a 100, vender a 110. Ganancia = +10%."""
    engine = PaperTradingEngine(commission_rate=0.0, spread_rate=0.0, slippage_rate=0.0)
    
    # Comprar $1,000 a $100 -> 10 acciones
    res_open = engine.open_position(
        symbol="TEST",
        side="LONG",
        current_price=100.0,
        amount_usd=1000.0
    )
    assert res_open["success"]
    pos_id = res_open["position_id"]
    assert res_open["shares"] == 10.0
    assert res_open["entry_price"] == 100.0
    
    # Efectivo restante debe ser exactamente 9,000
    account = get_account_balance()
    assert account["balance"] == 9000.0

    # Cerrar a $110 -> 10 * 110 = $1,100 (+100 de ganancia)
    res_close = engine.close_position(pos_id=pos_id, current_price=110.0)
    assert res_close["success"]
    assert pytest.approx(res_close["pnl_usd"], 0.001) == 100.0
    assert pytest.approx(res_close["pnl_pct"], 0.001) == 10.0

    # Nuevo efectivo debe ser 10,100
    account_after = get_account_balance()
    assert pytest.approx(account_after["balance"], 0.001) == 10100.0


def test_long_losing_trade_with_commission():
    """LONG: Comprar a 100, vender a 90 con comisión del 0.1%."""
    comm_rate = 0.001
    engine = PaperTradingEngine(commission_rate=comm_rate, spread_rate=0.0, slippage_rate=0.0)

    # Invertir $1,000 a $100 -> 10 acciones. Comisión entrada = $1.00
    res_open = engine.open_position("TEST", "LONG", 100.0, amount_usd=1000.0)
    assert res_open["success"]
    assert res_open["commission"] == 1.0
    pos_id = res_open["position_id"]

    # Saldo después de apertura = 10,000 - 1,001 = 8,999
    assert pytest.approx(get_account_balance()["balance"], 0.001) == 8999.0

    # Vender a $90 -> Bruto = 900. Comisión salida = 900 * 0.001 = 0.90. Neto salida = 899.10
    res_close = engine.close_position(pos_id, current_price=90.0)
    assert res_close["success"]

    # P&L total = (900 - 1000) - (1.00 + 0.90) = -101.90
    expected_pnl = -101.90
    assert pytest.approx(res_close["pnl_usd"], 0.01) == expected_pnl

    # Saldo final = 8,999 + 899.10 = 9,898.10 (Pérdida neta de 101.90 respecto a 10,000)
    assert pytest.approx(get_account_balance()["balance"], 0.01) == 10000.0 + expected_pnl


def test_short_profitable_trade():
    """SHORT: Vender a 100, recomprar a 90. Ganancia = +10%."""
    engine = PaperTradingEngine(commission_rate=0.0, spread_rate=0.0, slippage_rate=0.0)

    # Abrir SHORT con $1,000 a $100 -> 10 acciones
    res_open = engine.open_position("TEST", "SHORT", 100.0, amount_usd=1000.0)
    assert res_open["success"]
    pos_id = res_open["position_id"]

    # Cerrar a $90 -> (100 - 90) * 10 = +$100 de ganancia
    res_close = engine.close_position(pos_id, current_price=90.0)
    assert res_close["success"]
    assert pytest.approx(res_close["pnl_usd"], 0.001) == 100.0
    assert pytest.approx(res_close["pnl_pct"], 0.001) == 10.0

    assert pytest.approx(get_account_balance()["balance"], 0.001) == 10100.0


def test_short_losing_trade():
    """SHORT: Vender a 100, el precio sube a 115. Pérdida = -$150."""
    engine = PaperTradingEngine(commission_rate=0.0, spread_rate=0.0, slippage_rate=0.0)

    res_open = engine.open_position("TEST", "SHORT", 100.0, amount_usd=1000.0)
    pos_id = res_open["position_id"]

    res_close = engine.close_position(pos_id, current_price=115.0)
    assert res_close["success"]
    assert pytest.approx(res_close["pnl_usd"], 0.001) == -150.0
    assert pytest.approx(res_close["pnl_pct"], 0.001) == -15.0

    assert pytest.approx(get_account_balance()["balance"], 0.001) == 9850.0


def test_stop_loss_conservative_same_candle_policy():
    """
    Si una vela tiene un rango tan amplio que toca tanto el Stop Loss como el Take Profit,
    la política CONSERVADORA documentada debe ejecutar el STOP LOSS.
    """
    engine = PaperTradingEngine(commission_rate=0.0, spread_rate=0.0, slippage_rate=0.0)

    # Abrir LONG a 100 con Stop Loss a 95 y Take Profit a 110
    res_open = engine.open_position(
        symbol="VOLATILE",
        side="LONG",
        current_price=100.0,
        amount_usd=1000.0,
        stop_loss=95.0,
        take_profit=110.0
    )
    assert res_open["success"]

    # Vela con Low = 92 (rompe SL) y High = 112 (rompe TP)
    closed = engine.check_and_trigger_stops(
        symbol="VOLATILE",
        high_price=112.0,
        low_price=92.0,
        close_price=105.0
    )

    assert len(closed) == 1
    assert "STOP_LOSS" in closed[0]["reason"]
    # P&L debe ser negativo (cerrado en 95)
    assert closed[0]["pnl_usd"] < 0
    assert pytest.approx(closed[0]["exit_price"], 0.001) == 95.0
