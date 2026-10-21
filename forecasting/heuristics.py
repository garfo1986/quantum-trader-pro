"""
Generador de pronósticos probabilísticos heurísticos (15m, 1h, 4h, 24h, 1 semana).
Identificado obligatoriamente como 'Estimación heurística no calibrada'.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np


def generate_heuristic_forecasts(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Calcula probabilidades estimadas para 5 horizontes temporales:
    - 15 minutos
    - 1 hora
    - 4 horas
    - 24 horas
    - 1 semana

    Garantiza matemáticamente:
    Prob_Alcista + Prob_Lateral + Prob_Bajista = 100.0%
    """
    if len(df) < 30:
        horizons = ["15m", "1h", "4h", "24h", "1w"]
        return {
            h: {
                "horizon": h,
                "alcista": 33.33,
                "lateral": 33.34,
                "bajista": 33.33,
                "sesgo": "Indecisión (Datos insuficientes)",
                "label": "Estimación heurística no calibrada"
            }
            for h in horizons
        }

    last = df.iloc[-1]
    close = float(last["close"])
    rsi = float(last.get("rsi", 50.0))
    macd_hist = float(last.get("macd_hist", 0.0))
    adx = float(last.get("adx", 20.0))
    ema_20 = float(last.get("ema_20", close))
    ema_50 = float(last.get("ema_50", close))
    ema_200 = float(last.get("ema_200", close))

    # Puntuación base direccional (-1.0 a +1.0)
    score = 0.0

    # Sesgo de medias
    if close > ema_20:
        score += 0.25
    else:
        score -= 0.25

    if ema_20 > ema_50:
        score += 0.35
    else:
        score -= 0.35

    if ema_200 > 0 and close > ema_200:
        score += 0.40
    elif ema_200 > 0:
        score -= 0.40

    # Modificador RSI (oscilador)
    if rsi > 70:
        score -= 0.30  # Riesgo de corrección
    elif rsi < 30:
        score += 0.30  # Probabilidad de rebote

    # Modificador MACD
    if macd_hist > 0:
        score += 0.20
    else:
        score -= 0.20

    # Normalizar score a [-1.0, 1.0]
    norm_score = max(-1.0, min(1.0, score / 1.5))

    # Ponderaciones según horizonte:
    # A corto plazo (15m, 1h) la probabilidad lateral es mayor por ruido de mercado.
    # A medio plazo (24h, 1w) la tendencia dominante tiene mayor peso.
    horizon_weights = {
        "15 minutos": {"trend_weight": 0.20, "base_lateral": 50.0},
        "1 hora": {"trend_weight": 0.28, "base_lateral": 42.0},
        "4 horas": {"trend_weight": 0.38, "base_lateral": 35.0},
        "24 horas": {"trend_weight": 0.45, "base_lateral": 30.0},
        "1 semana": {"trend_weight": 0.50, "base_lateral": 25.0}
    }

    results = {}
    for h_name, params in horizon_weights.items():
        base_lateral = params["base_lateral"]
        remaining = 100.0 - base_lateral  # Ej: 70%

        # Desplazar según tendencia
        # Si norm_score es 1.0 -> alcista = remaining * 0.85, bajista = remaining * 0.15
        shift = norm_score * (remaining * params["trend_weight"])
        alcista = max(5.0, (remaining / 2.0) + shift)
        bajista = max(5.0, (remaining / 2.0) - shift)
        lateral = max(10.0, 100.0 - (alcista + bajista))

        # Normalización estricta para que la suma sea exactamente 100.0%
        total = alcista + lateral + bajista
        alcista_pct = round((alcista / total) * 100.0, 1)
        lateral_pct = round((lateral / total) * 100.0, 1)
        bajista_pct = round(100.0 - (alcista_pct + lateral_pct), 1)

        if alcista_pct > bajista_pct + 10:
            bias = "Alcista 🟢"
        elif bajista_pct > alcista_pct + 10:
            bias = "Bajista 🔴"
        else:
            bias = "Lateral / Neutral ⚪"

        results[h_name] = {
            "horizon": h_name,
            "alcista": alcista_pct,
            "lateral": lateral_pct,
            "bajista": bajista_pct,
            "sesgo": bias,
            "label": "Estimación heurística no calibrada",
            "score": round(norm_score, 2)
        }

    return results
