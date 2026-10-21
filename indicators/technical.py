"""
Cálculo de indicadores técnicos locales con pandas y numpy (100% gratuito y auditable).
No inventa indicadores si no hay suficientes datos históricos.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calcula la Media Móvil Exponencial (EMA)."""
    if len(series) < period:
        return pd.Series(index=series.index, dtype=float)
    return series.ewm(span=period, adjust=False).mean()


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calcula la Media Móvil Simple (SMA)."""
    if len(series) < period:
        return pd.Series(index=series.index, dtype=float)
    return series.rolling(window=period).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcula el Índice de Fuerza Relativa (RSI) usando el suavizado exponencial de Wilder.
    Valores estrictamente acotados entre 0 y 100.
    """
    if len(series) <= period:
        return pd.Series(index=series.index, dtype=float)

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Suavizado inicial simple seguido de suavizado de Wilder
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # Casos extremos: si no hubo pérdidas, RSI = 100; si no hubo ganancias, RSI = 0
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(avg_gain != 0, 0.0)
    return rsi


def calculate_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Dict[str, pd.Series]:
    """Calcula Línea MACD, Línea de Señal e Histograma."""
    if len(series) < slow:
        empty = pd.Series(index=series.index, dtype=float)
        return {"macd": empty, "signal": empty, "hist": empty}

    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    return {"macd": macd_line, "signal": signal_line, "hist": hist}


def calculate_bollinger_bands(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> Dict[str, pd.Series]:
    """Calcula Bandas de Bollinger (Media, Superior, Inferior, Ancho de Banda y %B)."""
    if len(series) < period:
        empty = pd.Series(index=series.index, dtype=float)
        return {
            "middle": empty,
            "upper": empty,
            "lower": empty,
            "bandwidth": empty,
            "percent_b": empty,
        }

    sma = calculate_sma(series, period)
    std = series.rolling(window=period).std()
    upper = sma + (num_std * std)
    lower = sma - (num_std * std)
    bandwidth = ((upper - lower) / sma) * 100.0
    percent_b = (series - lower) / (upper - lower).replace(0, np.nan)

    return {
        "middle": sma,
        "upper": upper,
        "lower": lower,
        "bandwidth": bandwidth,
        "percent_b": percent_b,
    }


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcula el Average True Range (ATR)."""
    if len(df) <= period or not {"high", "low", "close"}.issubset(df.columns):
        return pd.Series(index=df.index, dtype=float)

    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return atr


def calculate_adx(df: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
    """
    Calcula el Average Directional Index (ADX), +DI y -DI.
    Mide la fuerza de la tendencia independientemente de la dirección.
    """
    if len(df) <= period * 2 or not {"high", "low", "close"}.issubset(df.columns):
        empty = pd.Series(index=df.index, dtype=float)
        return {"adx": empty, "plus_di": empty, "minus_di": empty}

    high = df["high"]
    low = df["low"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = calculate_atr(df, period)

    plus_di = 100.0 * (
        pd.Series(plus_dm, index=df.index)
        .ewm(alpha=1.0 / period, adjust=False)
        .mean()
        / atr.replace(0, np.nan)
    )
    minus_di = 100.0 * (
        pd.Series(minus_dm, index=df.index)
        .ewm(alpha=1.0 / period, adjust=False)
        .mean()
        / atr.replace(0, np.nan)
    )

    dx = (100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).fillna(0)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    return {"adx": adx, "plus_di": plus_di, "minus_di": minus_di}


def calculate_relative_volume(volume: pd.Series, period: int = 20) -> pd.Series:
    """Calcula el volumen relativo respecto a su media móvil (RVOL)."""
    if len(volume) < period:
        return pd.Series(index=volume.index, dtype=float)
    avg_vol = volume.rolling(window=period).mean()
    return volume / avg_vol.replace(0, np.nan)


def calculate_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """Calcula volatilidad histórica anualizada basada en rendimientos logarítmicos."""
    if len(close) < period:
        return pd.Series(index=close.index, dtype=float)
    log_returns = np.log(close / close.shift(1))
    return log_returns.rolling(window=period).std() * np.sqrt(252) * 100.0


def calculate_momentum(close: pd.Series, period: int = 10) -> pd.Series:
    """Calcula el Momentum / Rate of Change porcentual."""
    if len(close) <= period:
        return pd.Series(index=close.index, dtype=float)
    return ((close - close.shift(period)) / close.shift(period)) * 100.0


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Calcula VWAP (Volume Weighted Average Price) acumulado."""
    if "volume" not in df.columns or df["volume"].isna().all():
        return pd.Series(index=df.index, dtype=float)
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol = df["volume"].cumsum()
    cum_tp_vol = (typical_price * df["volume"]).cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def enrich_with_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade todos los indicadores técnicos calculados de forma segura al DataFrame.
    """
    if df.empty or len(df) < 5:
        return df

    out = df.copy()

    # Medias Móviles
    out["ema_9"] = calculate_ema(out["close"], 9)
    out["ema_20"] = calculate_ema(out["close"], 20)
    out["ema_50"] = calculate_ema(out["close"], 50)
    out["ema_200"] = calculate_ema(out["close"], 200)
    out["sma_50"] = calculate_sma(out["close"], 50)
    out["sma_200"] = calculate_sma(out["close"], 200)

    # Osciladores y Volatilidad
    out["rsi"] = calculate_rsi(out["close"], 14)
    macd_res = calculate_macd(out["close"], 12, 26, 9)
    out["macd"] = macd_res["macd"]
    out["macd_signal"] = macd_res["signal"]
    out["macd_hist"] = macd_res["hist"]

    bb_res = calculate_bollinger_bands(out["close"], 20, 2.0)
    out["bb_middle"] = bb_res["middle"]
    out["bb_upper"] = bb_res["upper"]
    out["bb_lower"] = bb_res["lower"]
    out["bb_bandwidth"] = bb_res["bandwidth"]

    out["atr"] = calculate_atr(out, 14)
    out["volatility"] = calculate_volatility(out["close"], 20)
    out["momentum_10"] = calculate_momentum(out["close"], 10)

    # Indicadores avanzados cuando los datos lo permitan
    if "volume" in out.columns:
        out["rvol"] = calculate_relative_volume(out["volume"], 20)
        out["vwap"] = calculate_vwap(out)

    adx_res = calculate_adx(out, 14)
    out["adx"] = adx_res["adx"]
    out["plus_di"] = adx_res["plus_di"]
    out["minus_di"] = adx_res["minus_di"]

    return out
