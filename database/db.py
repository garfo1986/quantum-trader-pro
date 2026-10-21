"""
Capa de persistencia local SQLite para QuantumTrader Pro.
Almacena cuentas simuladas, posiciones abiertas, historial de trades y señales.
100% local en tu equipo, sin requerir servidores ni bases de datos de pago.
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from config import DB_FILE, PAPER_TRADING_DEFAULTS


def get_db_connection() -> sqlite3.Connection:
    """Retorna una conexión a la base de datos SQLite local."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializa el esquema de tablas si no existen."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabla de Cuenta / Saldo
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS account (
        id INTEGER PRIMARY KEY,
        balance REAL NOT NULL,
        initial_capital REAL NOT NULL,
        currency TEXT DEFAULT 'USD',
        updated_at TEXT NOT NULL
    )
    """)

    # Tabla de Posiciones Abiertas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,          -- 'LONG' o 'SHORT'
        shares REAL NOT NULL,
        entry_price REAL NOT NULL,
        entry_amount REAL NOT NULL,
        stop_loss REAL,
        take_profit REAL,
        commission_paid REAL DEFAULT 0.0,
        slippage_paid REAL DEFAULT 0.0,
        opened_at TEXT NOT NULL,
        is_open INTEGER DEFAULT 1
    )
    """)

    # Tabla de Historial de Operaciones Cerradas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        position_id INTEGER,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        shares REAL NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL NOT NULL,
        entry_amount REAL NOT NULL,
        exit_amount REAL NOT NULL,
        pnl_usd REAL NOT NULL,
        pnl_pct REAL NOT NULL,
        commission_total REAL NOT NULL,
        opened_at TEXT NOT NULL,
        closed_at TEXT NOT NULL,
        exit_reason TEXT NOT NULL     -- 'MANUAL', 'STOP_LOSS', 'TAKE_PROFIT'
    )
    """)

    # Tabla de Registro de Señales Históricas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS signals_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        signal_type TEXT NOT NULL,
        score INTEGER NOT NULL,
        reason TEXT NOT NULL,
        price REAL NOT NULL
    )
    """)

    # Tabla de Pronósticos Probabilísticos y Evaluación Posterior
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        horizon TEXT NOT NULL,         -- '15m', '1h', '4h', '24h', '1w'
        generated_at TEXT NOT NULL,
        initial_price REAL NOT NULL,
        prob_bullish REAL NOT NULL,
        prob_neutral REAL NOT NULL,
        prob_bearish REAL NOT NULL,
        predicted_direction TEXT NOT NULL,
        final_price REAL,
        actual_direction TEXT,
        is_correct INTEGER,
        evaluated_at TEXT
    )
    """)

    # Inicializar cuenta con $10,000 por defecto si está vacía
    cursor.execute("SELECT COUNT(*) FROM account")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        cursor.execute(
            "INSERT INTO account (id, balance, initial_capital, updated_at) VALUES (1, ?, ?, ?)",
            (PAPER_TRADING_DEFAULTS["initial_capital"], PAPER_TRADING_DEFAULTS["initial_capital"], now_str)
        )

    conn.commit()
    conn.close()


def get_account_balance() -> Dict[str, float]:
    """Obtiene el saldo disponible y capital inicial de la cuenta."""
    conn = get_db_connection()
    row = conn.execute("SELECT balance, initial_capital FROM account WHERE id = 1").fetchone()
    conn.close()
    if row:
        return {"balance": float(row["balance"]), "initial_capital": float(row["initial_capital"])}
    return {"balance": 10000.0, "initial_capital": 10000.0}


def update_account_balance(new_balance: float):
    """Actualiza el balance en efectivo disponible."""
    conn = get_db_connection()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    conn.execute("UPDATE account SET balance = ?, updated_at = ? WHERE id = 1", (new_balance, now_str))
    conn.commit()
    conn.close()


def reset_account(initial_capital: float = 10000.0):
    """Reinicia la cuenta, cerrando todas las posiciones y restaurando el saldo."""
    conn = get_db_connection()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    conn.execute("UPDATE account SET balance = ?, initial_capital = ?, updated_at = ? WHERE id = 1",
                 (initial_capital, initial_capital, now_str))
    conn.execute("DELETE FROM positions")
    conn.execute("DELETE FROM trades_history")
    conn.commit()
    conn.close()


def save_open_position(
    symbol: str, side: str, shares: float, entry_price: float, entry_amount: float,
    stop_loss: Optional[float], take_profit: Optional[float],
    commission: float, slippage: float, opened_at: str
) -> int:
    """Guarda una nueva posición abierta."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO positions (symbol, side, shares, entry_price, entry_amount, stop_loss, take_profit, commission_paid, slippage_paid, opened_at, is_open)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (symbol, side, shares, entry_price, entry_amount, stop_loss, take_profit, commission, slippage, opened_at))
    pos_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pos_id


def get_open_positions() -> List[Dict[str, Any]]:
    """Obtiene todas las posiciones abiertas actualmente."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM positions WHERE is_open = 1 ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def close_position_in_db(
    pos_id: int, exit_price: float, exit_amount: float, pnl_usd: float,
    pnl_pct: float, commission_total: float, closed_at: str, exit_reason: str
):
    """Cierra una posición y la transfiere al historial."""
    conn = get_db_connection()
    cursor = conn.cursor()
    pos = cursor.execute("SELECT * FROM positions WHERE id = ?", (pos_id,)).fetchone()
    if pos:
        # Registrar en historial
        cursor.execute("""
            INSERT INTO trades_history (
                position_id, symbol, side, shares, entry_price, exit_price,
                entry_amount, exit_amount, pnl_usd, pnl_pct, commission_total,
                opened_at, closed_at, exit_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pos_id, pos["symbol"], pos["side"], pos["shares"], pos["entry_price"],
            exit_price, pos["entry_amount"], exit_amount, pnl_usd, pnl_pct,
            commission_total, pos["opened_at"], closed_at, exit_reason
        ))
        # Marcar como cerrada
        cursor.execute("UPDATE positions SET is_open = 0 WHERE id = ?", (pos_id,))
        conn.commit()
    conn.close()


def get_closed_trades() -> List[Dict[str, Any]]:
    """Obtiene el historial de todas las operaciones cerradas."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM trades_history ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Inicialización automática al importar
init_db()
