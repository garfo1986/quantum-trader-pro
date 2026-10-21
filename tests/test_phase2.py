"""
Test suite para verificar Indicadores Técnicos y Motor de Señales (Fase 2).
"""

import pytest
import pandas as pd
import numpy as np

from indicators.technical import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands,
    calculate_atr, calculate_adx, enrich_with_all_indicators
)
from indicators.levels import find_swing_extrema, cluster_levels, detect_trend
from signals.signal_engine import SignalEngine


def create_synthetic_data(n: int = 100) -> pd.DataFrame:
    """Genera datos OHLCV sintéticos consistentes para pruebas de cálculo."""
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.normal(0.5, 2.0, n))
    high = close + np.random.uniform(0.5, 2.0, n)
    low = close - np.random.uniform(0.5, 2.0, n)
    open_p = low + np.random.uniform(0.1, 1.5, n)
    volume = np.random.uniform(1000, 50000, n)

    return pd.DataFrame({
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=dates)


def test_rsi_bounds():
    df = create_synthetic_data(100)
    rsi = calculate_rsi(df["close"], 14)
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


def test_macd_computation():
    df = create_synthetic_data(100)
    macd = calculate_macd(df["close"])
    assert "macd" in macd and "signal" in macd and "hist" in macd
    assert len(macd["macd"].dropna()) > 50


def test_bollinger_bands():
    df = create_synthetic_data(100)
    bb = calculate_bollinger_bands(df["close"], 20, 2.0)
    valid_upper = bb["upper"].dropna()
    valid_lower = bb["lower"].dropna()
    valid_mid = bb["middle"].dropna()
    assert (valid_upper >= valid_mid).all()
    assert (valid_mid >= valid_lower).all()


def test_enrich_with_indicators():
    df = create_synthetic_data(100)
    enriched = enrich_with_all_indicators(df)
    expected_cols = ["ema_9", "ema_20", "ema_50", "ema_200", "rsi", "macd", "atr", "volatility", "adx"]
    for col in expected_cols:
        assert col in enriched.columns


def test_signal_engine_evaluation():
    df = create_synthetic_data(100)
    enriched = enrich_with_all_indicators(df)
    engine = SignalEngine()
    sig = engine.evaluate_latest(enriched)
    assert sig["type"] in ["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]
    assert -100 <= sig["score"] <= 100
    assert isinstance(sig["bullish_factors"], list)
    assert isinstance(sig["bearish_factors"], list)
    assert len(sig["reason"]) > 0


def test_levels_and_trend():
    df = create_synthetic_data(100)
    enriched = enrich_with_all_indicators(df)
    trend = detect_trend(enriched)
    assert "direction" in trend
    assert "label" in trend
    assert "strength" in trend

    highs, lows = find_swing_extrema(df)
    assert isinstance(highs, list)
    assert isinstance(lows, list)
