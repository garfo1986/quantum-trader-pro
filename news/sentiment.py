"""
Analizador léxico local de sentimiento financiero.
100% gratuito y sin APIs de pago, basado en el vocabulario financiero Loughran-McDonald.
"""

from typing import Dict, Any
import re

# Diccionario léxico financiero simplificado (inglés y español)
BULLISH_TERMS = {
    "surge", "surges", "surging", "soar", "soars", "rally", "rallies", "gain", "gains",
    "profit", "profitable", "growth", "beat", "beats", "record", "bullish", "upgrade",
    "upgraded", "dividend", "acquisition", "expand", "expansion", "breakout", "positive",
    "high", "higher", "rebound", "sube", "subida", "ganancia", "ganancias", "crecimiento",
    "alcista", "beneficio", "máximo", "récord", "rebote", "recuperación"
}

BEARISH_TERMS = {
    "plunge", "plunges", "slump", "slumps", "drop", "drops", "crash", "crashes", "fall",
    "falls", "loss", "losses", "miss", "misses", "deficit", "bearish", "downgrade",
    "downgraded", "lawsuit", "sanction", "penalty", "debt", "risk", "warning", "negative",
    "low", "lower", "recession", "inflation", "cae", "caída", "pérdida", "pérdidas",
    "bajista", "desplome", "crisis", "recesión", "riesgo", "alerta", "mínimo"
}


def analyze_financial_sentiment(text: str) -> Dict[str, Any]:
    """
    Analiza la polaridad de sentimiento en titulares y resúmenes financieros.
    Retorna puntuación numérica [-1.0 a +1.0] y etiqueta cualitativa.
    """
    if not text:
        return {"score": 0.0, "label": "NEUTRAL ⚪", "bull_count": 0, "bear_count": 0}

    # Tokenizar palabras limpias
    words = re.findall(r"\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]+\b", text.lower())

    bull_count = sum(1 for w in words if w in BULLISH_TERMS)
    bear_count = sum(1 for w in words if w in BEARISH_TERMS)

    total_hits = bull_count + bear_count

    if total_hits == 0:
        return {"score": 0.0, "label": "NEUTRAL ⚪", "bull_count": 0, "bear_count": 0}

    score = (bull_count - bear_count) / float(total_hits)

    if score >= 0.25:
        label = "POSITIVO 🟢"
    elif score <= -0.25:
        label = "NEGATIVO 🔴"
    else:
        label = "NEUTRAL ⚪"

    return {
        "score": round(score, 2),
        "label": label,
        "bull_count": bull_count,
        "bear_count": bear_count
    }
