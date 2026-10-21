"""
Motor de señales multi-factor transparente y configurable.
Sin look-ahead bias: cada señal se evalúa exclusivamente con datos disponibles en su momento.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd


class SignalEngine:
    """
    Evalúa múltiples factores técnicos para determinar el sesgo del mercado:
    - Tendencia (EMA 20, 50, 200)
    - Momento y Osciladores (RSI, MACD, ROC)
    - Volumen (RVOL)
    - Volatilidad (ATR, Bandas de Bollinger)
    - Acción del precio y niveles
    """

    def __init__(self, strong_threshold: int = 50, normal_threshold: int = 20):
        self.strong_threshold = strong_threshold
        self.normal_threshold = normal_threshold

    def evaluate_latest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Evalúa únicamente la última vela disponible del DataFrame.
        """
        if len(df) < 30:
            return {
                "type": "HOLD",
                "score": 0,
                "bullish_factors": [],
                "bearish_factors": ["Datos históricos insuficientes para evaluación técnica segura"],
                "reason": "Se requieren al menos 30 velas para calcular los indicadores necesarios.",
                "price": float(df["close"].iloc[-1]) if not df.empty else 0.0,
                "timestamp": str(df.index[-1]) if not df.empty else ""
            }

        last = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0
        bullish = []
        bearish = []

        close = float(last["close"])
        timestamp = str(df.index[-1])

        # 1. FACTOR: Tendencia y Medias Móviles (Hasta ±30 pts)
        ema_20 = last.get("ema_20", np.nan)
        ema_50 = last.get("ema_50", np.nan)
        ema_200 = last.get("ema_200", np.nan)

        if not pd.isna(ema_20) and not pd.isna(ema_50):
            if ema_20 > ema_50:
                score += 15
                bullish.append("Cruce alcista: EMA 20 por encima de EMA 50")
            else:
                score -= 15
                bearish.append("Cruce bajista: EMA 20 por debajo de EMA 50")

        if not pd.isna(ema_200) and ema_200 > 0:
            if close > ema_200:
                score += 15
                bullish.append(f"Régimen alcista mayor: Precio (${close:,.2f}) > EMA 200 (${ema_200:,.2f})")
            else:
                score -= 15
                bearish.append(f"Régimen bajista mayor: Precio (${close:,.2f}) < EMA 200 (${ema_200:,.2f})")

        # 2. FACTOR: RSI y Zonas de Sobrecompra/Sobreventa (Hasta ±25 pts)
        rsi = last.get("rsi", np.nan)
        prev_rsi = prev.get("rsi", np.nan)

        if not pd.isna(rsi):
            if rsi < 30:
                # Zona de sobreventa con posible rebote
                score += 20
                bullish.append(f"RSI en sobreventa extrema ({rsi:.1f} < 30) - alta probabilidad de rebote")
            elif 30 <= rsi <= 45 and not pd.isna(prev_rsi) and rsi > prev_rsi:
                score += 10
                bullish.append(f"RSI saliendo de zona baja con pendiente positiva ({rsi:.1f})")
            elif rsi > 70:
                # Sobrecompra con posible agotamiento
                score -= 20
                bearish.append(f"RSI en sobrecompra extrema ({rsi:.1f} > 70) - riesgo de corrección")
            elif 55 <= rsi <= 70 and not pd.isna(prev_rsi) and rsi < prev_rsi:
                score -= 10
                bearish.append(f"RSI perdiendo impulso en zona alta ({rsi:.1f})")

        # 3. FACTOR: MACD y Momentum (Hasta ±25 pts)
        macd = last.get("macd", np.nan)
        macd_signal = last.get("macd_signal", np.nan)
        macd_hist = last.get("macd_hist", np.nan)
        prev_macd_hist = prev.get("macd_hist", np.nan)

        if not pd.isna(macd) and not pd.isna(macd_signal):
            if macd > macd_signal:
                score += 15
                bullish.append("MACD por encima de su línea de señal (impulso comprador)")
            else:
                score -= 15
                bearish.append("MACD por debajo de su línea de señal (impulso vendedor)")

            if not pd.isna(macd_hist) and not pd.isna(prev_macd_hist):
                if macd_hist > 0 and macd_hist > prev_macd_hist:
                    score += 10
                    bullish.append("Histograma MACD en expansión alcista")
                elif macd_hist < 0 and macd_hist < prev_macd_hist:
                    score -= 10
                    bearish.append("Histograma MACD en expansión bajista")

        # 4. FACTOR: Bandas de Bollinger y Volatilidad (Hasta ±15 pts)
        bb_upper = last.get("bb_upper", np.nan)
        bb_lower = last.get("bb_lower", np.nan)

        if not pd.isna(bb_lower) and close <= bb_lower * 1.002:
            score += 10
            bullish.append("Precio testeando o rebotando en Banda Inferior de Bollinger")
        elif not pd.isna(bb_upper) and close >= bb_upper * 0.998:
            score -= 10
            bearish.append("Precio alcanzando Banda Superior de Bollinger (resistencia dinámica)")

        # 5. FACTOR: Volumen Relativo (Multiplicador / Confirmación)
        rvol = last.get("rvol", np.nan)
        if not pd.isna(rvol) and rvol >= 1.3:
            if score > 0:
                score += 10
                bullish.append(f"Confirmación de volumen: RVOL alto ({rvol:.2f}x de la media)")
            elif score < 0:
                score -= 10
                bearish.append(f"Presión de volumen vendedor: RVOL alto ({rvol:.2f}x de la media)")

        # Acotar score a [-100, +100]
        final_score = int(max(-100, min(100, score)))

        # Clasificación final
        if final_score >= self.strong_threshold:
            sig_type = "STRONG BUY"
            reason = f"Confluencia alcista fuerte (Score: {final_score}/100) respaldada por medias y osciladores."
        elif final_score >= self.normal_threshold:
            sig_type = "BUY"
            reason = f"Predominio de señales alcistas (Score: {final_score}/100)."
        elif final_score <= -self.strong_threshold:
            sig_type = "STRONG SELL"
            reason = f"Confluencia bajista severa (Score: {final_score}/100). Alto riesgo de caída continua."
        elif final_score <= -self.normal_threshold:
            sig_type = "SELL"
            reason = f"Predominio de factores de venta (Score: {final_score}/100)."
        else:
            sig_type = "HOLD"
            reason = f"Mercado en equilibrio o indecisión técnica (Score: {final_score}/100). Esperar confirmación."

        return {
            "type": sig_type,
            "score": final_score,
            "bullish_factors": bullish,
            "bearish_factors": bearish,
            "reason": reason,
            "price": close,
            "timestamp": timestamp
        }

    def generate_history(self, df: pd.DataFrame, step: int = 1) -> List[Dict[str, Any]]:
        """
        Genera la serie histórica de señales vela a vela (sin mirar hacia el futuro).
        Se usa para pintar las flechas históricas en el gráfico y evaluar el rendimiento.
        """
        signals = []
        if len(df) < 50:
            return signals

        # Recorrer histórico para detectar cambios relevantes de señal
        last_emitted_type = None
        for i in range(50, len(df), step):
            sub_df = df.iloc[: i + 1]
            sig = self.evaluate_latest(sub_df)
            stype = sig["type"]

            # Registrar si es BUY o SELL (evitar saturar el gráfico con señales idénticas consecutivas)
            if "BUY" in stype and last_emitted_type != "BUY":
                signals.append(sig)
                last_emitted_type = "BUY"
            elif "SELL" in stype and last_emitted_type != "SELL":
                signals.append(sig)
                last_emitted_type = "SELL"
            elif stype == "HOLD":
                last_emitted_type = "HOLD"

        return signals
