"""
Auditor de predicciones probabilísticas.
Registra pronósticos antes de conocer el futuro y evalúa posteriormente el acierto o fallo objetivo.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import sqlite3
from database.db import get_db_connection


class PredictionTracker:
    """Registra y evalúa la fiabilidad estadística de los pronósticos guardados."""

    @staticmethod
    def log_prediction(
        symbol: str,
        timeframe: str,
        horizon: str,
        initial_price: float,
        prob_bullish: float,
        prob_neutral: float,
        prob_bearish: float,
        predicted_direction: str
    ) -> int:
        """Guarda un pronóstico antes de conocer el resultado futuro."""
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        cursor.execute("""
            INSERT INTO predictions_log (
                symbol, timeframe, horizon, generated_at, initial_price,
                prob_bullish, prob_neutral, prob_bearish, predicted_direction,
                is_correct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, (
            symbol, timeframe, horizon, now_str, initial_price,
            prob_bullish, prob_neutral, prob_bearish, predicted_direction
        ))
        pred_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return pred_id

    @staticmethod
    def evaluate_pending_predictions(symbol: str, current_price: float) -> int:
        """
        Evalúa predicciones pendientes para el activo especificado.
        Determina la dirección real y si la predicción fue un acierto o fallo.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, initial_price, predicted_direction FROM predictions_log
            WHERE symbol = ? AND is_correct IS NULL
        """, (symbol,)).fetchall()

        evaluated_count = 0
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        for r in rows:
            p_id = r["id"]
            init_price = float(r["initial_price"])
            pred_dir = r["predicted_direction"].upper()

            # Variación porcentual desde la predicción
            change_pct = ((current_price - init_price) / init_price) * 100.0

            if change_pct > 0.5:
                actual_dir = "ALCISTA"
            elif change_pct < -0.5:
                actual_dir = "BAJISTA"
            else:
                actual_dir = "LATERAL"

            is_correct = 1 if pred_dir in actual_dir else 0

            cursor.execute("""
                UPDATE predictions_log
                SET final_price = ?, actual_direction = ?, is_correct = ?, evaluated_at = ?
                WHERE id = ?
            """, (current_price, actual_dir, is_correct, now_str, p_id))
            evaluated_count += 1

        conn.commit()
        conn.close()
        return evaluated_count

    @staticmethod
    def get_prediction_audit_history(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene el historial de predicciones y su tasa de acierto."""
        conn = get_db_connection()
        if symbol:
            rows = conn.execute("""
                SELECT * FROM predictions_log WHERE symbol = ? ORDER BY id DESC LIMIT 50
            """, (symbol,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM predictions_log ORDER BY id DESC LIMIT 50").fetchall()
        conn.close()
        return [dict(r) for r in rows]
