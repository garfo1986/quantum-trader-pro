"""
Detección automática de soportes, resistencias, pivotes locales, tendencia y rupturas.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd


def find_swing_extrema(df: pd.DataFrame, window: int = 5) -> Tuple[List[float], List[float]]:
    """
    Encuentra pivotes locales de máximos y mínimos.
    Utiliza una ventana deslizante simétrica para análisis de estructura.
    """
    if len(df) < window * 2 + 1:
        return [], []

    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    swing_highs = []
    swing_lows = []

    for i in range(window, n - window):
        # Máximo local si es el mayor en la ventana [i - window, i + window]
        is_max = True
        for j in range(i - window, i + window + 1):
            if j != i and highs[j] >= highs[i]:
                is_max = False
                break
        if is_max:
            swing_highs.append(float(highs[i]))

        # Mínimo local si es el menor en la ventana
        is_min = True
        for j in range(i - window, i + window + 1):
            if j != i and lows[j] <= lows[i]:
                is_min = False
                break
        if is_min:
            swing_lows.append(float(lows[i]))

    return swing_highs, swing_lows


def cluster_levels(prices: List[float], current_price: float, tolerance_pct: float = 0.015) -> List[Dict[str, Any]]:
    """
    Agrupa precios cercanos para evitar líneas duplicadas y obtener niveles significativos.
    Separa en Soportes (por debajo del precio) y Resistencias (por encima del precio).
    """
    if not prices:
        return []

    sorted_prices = sorted(prices)
    clusters: List[List[float]] = []

    for p in sorted_prices:
        if not clusters:
            clusters.append([p])
        else:
            # Si está dentro del rango de tolerancia porcentual del cluster actual
            cluster_avg = np.mean(clusters[-1])
            if abs(p - cluster_avg) / cluster_avg <= tolerance_pct:
                clusters[-1].append(p)
            else:
                clusters.append([p])

    # Calcular nivel medio y fuerza de cada cluster (número de toques)
    levels = []
    for cl in clusters:
        avg_price = float(np.mean(cl))
        touches = len(cl)
        is_support = avg_price < current_price
        level_type = "Soporte" if is_support else "Resistencia"
        distance_pct = ((avg_price - current_price) / current_price) * 100.0

        levels.append({
            "price": round(avg_price, 4),
            "type": level_type,
            "touches": touches,
            "distance_pct": round(distance_pct, 2)
        })

    # Filtrar para devolver los más relevantes (hasta 3 soportes más cercanos y 3 resistencias más cercanas)
    supports = sorted([l for l in levels if l["type"] == "Soporte"], key=lambda x: abs(x["distance_pct"]))[:3]
    resistances = sorted([l for l in levels if l["type"] == "Resistencia"], key=lambda x: abs(x["distance_pct"]))[:3]

    return supports + resistances


def detect_trend(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Determina la tendencia actual del mercado combinando medias móviles y ADX.
    """
    if len(df) < 50:
        return {
            "direction": "INSUFICIENTE_DATA",
            "label": "Datos insuficientes para tendencia",
            "strength": "Baja",
            "score": 0
        }

    last_row = df.iloc[-1]
    close = last_row["close"]
    ema_20 = last_row.get("ema_20", close)
    ema_50 = last_row.get("ema_50", close)
    ema_200 = last_row.get("ema_200", close)
    adx = last_row.get("adx", 20)
    plus_di = last_row.get("plus_di", 0)
    minus_di = last_row.get("minus_di", 0)

    score = 0

    # Puntos por alineación de medias
    if close > ema_20:
        score += 15
    else:
        score -= 15

    if ema_20 > ema_50:
        score += 25
    else:
        score -= 25

    if not pd.isna(ema_200) and ema_200 > 0:
        if close > ema_200:
            score += 30
        else:
            score -= 30

    # Confirmación direccional DI
    if plus_di > minus_di:
        score += 15
    elif minus_di > plus_di:
        score -= 15

    # Fuerza según ADX
    if adx >= 30:
        strength = "Muy Fuerte"
    elif adx >= 20:
        strength = "Moderada"
    else:
        strength = "Débil / Rango"

    if score >= 40:
        label = "Alcista Fuerte 🟢🟢"
        direction = "BULLISH_STRONG"
    elif score > 10:
        label = "Alcista Moderada 🟢"
        direction = "BULLISH_MODERATE"
    elif score <= -40:
        label = "Bajista Fuerte 🔴🔴"
        direction = "BEARISH_STRONG"
    elif score < -10:
        label = "Bajista Moderada 🔴"
        direction = "BEARISH_MODERATE"
    else:
        label = "Lateral / Sin Tendencia Clara ⚪"
        direction = "NEUTRAL"

    return {
        "direction": direction,
        "label": label,
        "strength": strength,
        "score": score,
        "adx": round(float(adx), 2) if not pd.isna(adx) else 0.0
    }


def detect_breakouts(df: pd.DataFrame, key_levels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evalúa si la vela más reciente rompió un soporte o resistencia relevante con volumen.
    """
    if len(df) < 2 or not key_levels:
        return []

    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    curr_close = last_row["close"]
    prev_close = prev_row["close"]
    rvol = last_row.get("rvol", 1.0)
    events = []

    for lvl in key_levels:
        price = lvl["price"]
        l_type = lvl["type"]

        # Ruptura alcista de resistencia
        if l_type == "Resistencia" and prev_close <= price and curr_close > price:
            vol_confirmed = rvol > 1.2 if not pd.isna(rvol) else False
            events.append({
                "type": "RUPTURA_RESISTENCIA",
                "price": price,
                "message": f"Ruptura alcista de resistencia en ${price:,.2f}" + (" con alto volumen (RVOL > 1.2)!" if vol_confirmed else "."),
                "volume_confirmed": vol_confirmed
            })

        # Ruptura bajista de soporte
        elif l_type == "Soporte" and prev_close >= price and curr_close < price:
            vol_confirmed = rvol > 1.2 if not pd.isna(rvol) else False
            events.append({
                "type": "RUPTURA_SOPORTE",
                "price": price,
                "message": f"Ruptura bajista de soporte en ${price:,.2f}" + (" con alto volumen (RVOL > 1.2)!" if vol_confirmed else "."),
                "volume_confirmed": vol_confirmed
            })

    return events
