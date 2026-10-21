"""
Modelo de Machine Learning con Scikit-Learn para pronósticos probabilísticos.
Utiliza estricta separación temporal (TimeSeriesSplit) para evitar Data Leakage y Look-Ahead Bias.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, brier_score_loss


class TimeSeriesMarketML:
    """
    Entrena un clasificador probabilístico sobre características estacionarias
    respetando el orden temporal de las series de precios.
    """

    def __init__(self, forward_bars: int = 5, threshold_pct: float = 0.01):
        self.forward_bars = forward_bars
        self.threshold_pct = threshold_pct
        self.model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        self.is_trained = False
        self.feature_cols = []

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrae características técnicas estacionarias (retornos, distancias relativas)."""
        data = df.copy()

        # Retornos pasados
        data["ret_1"] = data["close"].pct_change(1)
        data["ret_3"] = data["close"].pct_change(3)
        data["ret_5"] = data["close"].pct_change(5)

        # Distancias relativas a medias (estacionarias)
        if "ema_20" in data.columns:
            data["dist_ema20"] = (data["close"] - data["ema_20"]) / data["ema_20"]
        if "ema_50" in data.columns:
            data["dist_ema50"] = (data["close"] - data["ema_50"]) / data["ema_50"]

        # Volatilidad relativa
        if "atr" in data.columns:
            data["atr_pct"] = data["atr"] / data["close"]

        # Osciladores
        if "rsi" in data.columns:
            data["rsi_norm"] = data["rsi"] / 100.0

        if "macd_hist" in data.columns:
            data["macd_hist_norm"] = data["macd_hist"] / data["close"]

        if "rvol" in data.columns:
            data["rvol_clean"] = data["rvol"].fillna(1.0)

        # Retorno futuro objetivo (Target)
        future_return = data["close"].shift(-self.forward_bars) / data["close"] - 1.0

        # Clasificación: 1 = Alcista, 0 = Lateral, -1 = Bajista
        conditions = [
            (future_return > self.threshold_pct),
            (future_return < -self.threshold_pct)
        ]
        choices = [1, -1]
        data["target"] = np.select(conditions, choices, default=0)

        return data

    def train_and_evaluate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Entrena el modelo con separación temporal (Walk-Forward / TimeSeriesSplit).
        Compara la exactitud contra un modelo base (estrategia ingenua).
        """
        if len(df) < 80:
            return {"success": False, "error": "Se requieren al menos 80 velas históricas para entrenar el modelo ML."}

        prepared = self.prepare_features(df)

        candidate_features = [
            "ret_1", "ret_3", "ret_5", "dist_ema20", "dist_ema50",
            "atr_pct", "rsi_norm", "macd_hist_norm", "rvol_clean"
        ]
        self.feature_cols = [c for c in candidate_features if c in prepared.columns]

        # Descartar las últimas forward_bars filas (ya que su target no ha ocurrido aún) y filas con NaN
        clean_data = prepared.dropna(subset=self.feature_cols + ["target"]).iloc[:-self.forward_bars]

        if len(clean_data) < 50:
            return {"success": False, "error": "Datos insuficientes tras la limpieza de características."}

        X = clean_data[self.feature_cols].values
        y = clean_data["target"].values

        # División temporal estricta: 75% entrenamiento inicial, 25% test final (SIN SHUFFLE)
        split_idx = int(len(clean_data) * 0.75)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Entrenar modelo
        self.model.fit(X_train, y_train)
        self.is_trained = True

        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)

        acc = float(accuracy_score(y_test, y_pred))

        # Modelo base: predecir siempre la clase mayoritaria en el conjunto de entrenamiento
        majority_class = int(pd.Series(y_train).mode()[0])
        baseline_acc = float(accuracy_score(y_test, [majority_class] * len(y_test)))

        # Validación cruzada de series temporales (Walk-Forward TimeSeriesSplit)
        tscv = TimeSeriesSplit(n_splits=3)
        cv_scores = []
        for train_idx, val_idx in tscv.split(X):
            m = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            m.fit(X[train_idx], y[train_idx])
            cv_scores.append(float(accuracy_score(y[val_idx], m.predict(X[val_idx]))))

        avg_cv_acc = float(np.mean(cv_scores))

        # Predicción sobre la vela más reciente
        last_row_features = prepared[self.feature_cols].iloc[[-1]].fillna(0).values
        latest_proba = self.model.predict_proba(last_row_features)[0]
        classes = self.model.classes_

        # Mapear probabilidades a [-1: Bajista, 0: Lateral, 1: Alcista]
        proba_map = {cls: prob for cls, prob in zip(classes, latest_proba)}
        p_bear = float(proba_map.get(-1, 0.0)) * 100.0
        p_neutral = float(proba_map.get(0, 0.0)) * 100.0
        p_bull = float(proba_map.get(1, 0.0)) * 100.0

        # Asegurar suma 100%
        tot = p_bear + p_neutral + p_bull
        if tot > 0:
            p_bear = round((p_bear / tot) * 100.0, 1)
            p_neutral = round((p_neutral / tot) * 100.0, 1)
            p_bull = round(100.0 - (p_bear + p_neutral), 1)

        # Importancia de características
        importances = {
            col: round(float(imp), 3)
            for col, imp in zip(self.feature_cols, self.model.feature_importances_)
        }

        return {
            "success": True,
            "test_accuracy": round(acc * 100.0, 2),
            "baseline_accuracy": round(baseline_acc * 100.0, 2),
            "walk_forward_cv_accuracy": round(avg_cv_acc * 100.0, 2),
            "beats_baseline": acc >= baseline_acc,
            "probabilities": {
                "alcista": p_bull,
                "lateral": p_neutral,
                "bajista": p_bear
            },
            "feature_importance": importances,
            "train_samples": len(X_train),
            "test_samples": len(X_test)
        }
