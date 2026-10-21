"""
Test suite de integración para verificar todos los módulos de QuantumTrader Pro.
"""

import pytest
import pandas as pd
import numpy as np

from forecasting.heuristics import generate_heuristic_forecasts
from forecasting.ml_model import TimeSeriesMarketML
from forecasting.tracker import PredictionTracker
from backtesting.backtest import BacktestEngine
from news.sentiment import analyze_financial_sentiment
from ai.ollama_client import OllamaClient
from indicators.technical import enrich_with_all_indicators


def get_mock_df():
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    np.random.seed(123)
    close = 100.0 + np.cumsum(np.random.normal(0.2, 1.5, 120))
    high = close + np.random.uniform(0.5, 2.0, 120)
    low = close - np.random.uniform(0.5, 2.0, 120)
    open_p = low + np.random.uniform(0.1, 1.5, 120)
    volume = np.random.uniform(1000, 50000, 120)

    df = pd.DataFrame({
        "open": open_p, "high": high, "low": low, "close": close, "volume": volume
    }, index=dates)
    return enrich_with_all_indicators(df)


def test_heuristics_sum_to_100():
    df = get_mock_df()
    forecasts = generate_heuristic_forecasts(df)
    for h, data in forecasts.items():
        total = data["alcista"] + data["lateral"] + data["bajista"]
        assert pytest.approx(total, 0.1) == 100.0


def test_ml_model_temporal_split():
    df = get_mock_df()
    ml = TimeSeriesMarketML(forward_bars=3, threshold_pct=0.005)
    res = ml.train_and_evaluate(df)
    assert res["success"]
    assert "test_accuracy" in res
    assert "baseline_accuracy" in res
    assert "walk_forward_cv_accuracy" in res
    probs = res["probabilities"]
    assert pytest.approx(probs["alcista"] + probs["lateral"] + probs["bajista"], 0.1) == 100.0


def test_backtest_execution():
    df = get_mock_df()
    engine = BacktestEngine(initial_capital=10000.0, commission_rate=0.001)
    res = engine.run(df)
    assert res["success"]
    assert "strategy" in res
    assert "buy_and_hold" in res
    assert len(res["equity_curve"]) > 50


def test_sentiment_analysis():
    bull_res = analyze_financial_sentiment("Bitcoin surges to record high with massive profits")
    assert bull_res["label"] == "POSITIVO 🟢"
    assert bull_res["score"] > 0

    bear_res = analyze_financial_sentiment("Stock market crash causes historic losses and bankruptcy risk")
    assert bear_res["label"] == "NEGATIVO 🔴"
    assert bear_res["score"] < 0

    neutral_res = analyze_financial_sentiment("Company reported standard quarterly meeting")
    assert neutral_res["label"] == "NEUTRAL ⚪"


def test_ollama_graceful_fallback():
    client = OllamaClient(base_url="http://localhost:99999")  # Puerto inexistente
    info = client.check_availability()
    assert not info["available"]
    assert "message" in info
