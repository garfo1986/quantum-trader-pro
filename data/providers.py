"""
Capa de proveedores de datos de mercado.
Diseñada con arquitectura abstracta para permitir incorporar múltiples fuentes gratuitas.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf
from typing import Optional, Dict, Any

from config import TIMEFRAME_CONFIG


@dataclass
class MarketDataResult:
    """Contenedor de datos de mercado con metadatos transparentes de fuente y latencia."""
    symbol: str
    df: pd.DataFrame
    source: str
    timestamp: str
    delay_note: str
    last_price: float
    prev_close: float
    change_usd: float
    change_pct: float
    currency: str
    is_success: bool = True
    error_message: Optional[str] = None


class BaseDataProvider(ABC):
    """Interfaz abstracta para proveedores de datos de mercado."""

    @abstractmethod
    def fetch_data(self, symbol: str, timeframe: str = "1D") -> MarketDataResult:
        """Obtiene datos OHLCV históricos y metadatos de cotización."""
        pass

    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """Obtiene la cotización más reciente."""
        pass


class YFinanceProvider(BaseDataProvider):
    """
    Proveedor gratuito basado en yfinance.
    Proporciona acciones, ETFs, cripto, materias primas y divisas sin requerir API keys de pago.
    """

    def __init__(self):
        self.provider_name = "Yahoo Finance (Acceso Público Gratuito)"

    def _estimate_delay(self, symbol: str) -> str:
        """Determina la estimación transparente de latencia según el tipo de instrumento."""
        s = symbol.upper()
        if "-USD" in s or "-EUR" in s or s in ["BTC", "ETH", "SOL"]:
            return "Cripto: Datos de agregadores públicos (latencia aprox. < 1-2 min)."
        elif "=X" in s:
            return "Forex: Precios interbancarios públicos (posible retraso de 2-5 min)."
        elif "=F" in s:
            return "Futuros: Contratos de materias primas (retraso típico de 10-15 min)."
        elif s.startswith("^"):
            return "Índices: Datos diferidos 15 minutos en sesión de mercado."
        else:
            return "Acciones / ETFs: Retraso estándar de 15 minutos en sesión bursátil."

    def fetch_data(self, symbol: str, timeframe: str = "1D") -> MarketDataResult:
        tf_cfg = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1D"])
        interval = tf_cfg["interval"]
        period = tf_cfg["default_period"]
        resample_rule = tf_cfg.get("resample")
        delay_note = self._estimate_delay(symbol)

        try:
            ticker = yf.Ticker(symbol)
            # Descarga de datos
            df = ticker.history(interval=interval, period=period, auto_adjust=False)

            if df is None or df.empty:
                # Intento de reintento con símbolo normalizado
                return MarketDataResult(
                    symbol=symbol,
                    df=pd.DataFrame(),
                    source=self.provider_name,
                    timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    delay_note=delay_note,
                    last_price=0.0,
                    prev_close=0.0,
                    change_usd=0.0,
                    change_pct=0.0,
                    currency="USD",
                    is_success=False,
                    error_message=f"No se encontraron datos para el símbolo '{symbol}' en el timeframe '{timeframe}'."
                )

            # Normalizar nombres de columnas
            df = df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })

            # Asegurar columnas esenciales
            cols = ["open", "high", "low", "close", "volume"]
            df = df[[c for c in cols if c in df.columns]].copy()

            # Resampling si es necesario (ej: 4h construido a partir de 1h)
            if resample_rule and len(df) > 0:
                df = df.resample(resample_rule).agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum"
                }).dropna()

            # Limpiar filas con NaN en precios de cierre
            df = df.dropna(subset=["close"])

            if df.empty:
                return MarketDataResult(
                    symbol=symbol,
                    df=pd.DataFrame(),
                    source=self.provider_name,
                    timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    delay_note=delay_note,
                    last_price=0.0,
                    prev_close=0.0,
                    change_usd=0.0,
                    change_pct=0.0,
                    currency="USD",
                    is_success=False,
                    error_message=f"Los datos descargados para '{symbol}' resultaron vacíos tras la limpieza."
                )

            last_row = df.iloc[-1]
            last_price = float(last_row["close"])

            # Cálculo de variación
            if len(df) >= 2:
                prev_close = float(df.iloc[-2]["close"])
                change_usd = last_price - prev_close
                change_pct = (change_usd / prev_close) * 100 if prev_close != 0 else 0.0
            else:
                prev_close = last_price
                change_usd = 0.0
                change_pct = 0.0

            # Timestamp de la última vela
            last_dt = df.index[-1]
            if hasattr(last_dt, "strftime"):
                timestamp_str = last_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = str(last_dt)

            # Moneda estimada
            currency = "USD"
            if "=X" in symbol:
                currency = symbol[:3]
            elif symbol.endswith("COP=X"):
                currency = "COP"

            return MarketDataResult(
                symbol=symbol,
                df=df,
                source=self.provider_name,
                timestamp=timestamp_str,
                delay_note=delay_note,
                last_price=last_price,
                prev_close=prev_close,
                change_usd=change_usd,
                change_pct=change_pct,
                currency=currency,
                is_success=True,
                error_message=None
            )

        except Exception as e:
            return MarketDataResult(
                symbol=symbol,
                df=pd.DataFrame(),
                source=self.provider_name,
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                delay_note=delay_note,
                last_price=0.0,
                prev_close=0.0,
                change_usd=0.0,
                change_pct=0.0,
                currency="USD",
                is_success=False,
                error_message=f"Error al conectar con la fuente gratuita: {str(e)}"
            )

    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """Obtiene cotización rápida sin descargar todo el histórico."""
        try:
            ticker = yf.Ticker(symbol)
            fast_info = getattr(ticker, "fast_info", None)
            if fast_info and hasattr(fast_info, "last_price") and fast_info.last_price is not None:
                last = float(fast_info.last_price)
                prev = float(fast_info.previous_close) if hasattr(fast_info, "previous_close") and fast_info.previous_close else last
                chg = last - prev
                pct = (chg / prev) * 100 if prev != 0 else 0.0
                return {
                    "price": last,
                    "change": chg,
                    "change_pct": pct,
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "source": self.provider_name,
                    "delay_note": self._estimate_delay(symbol),
                    "success": True
                }
            
            # Si fast_info no tiene los datos, recurrir a history de 1 día
            df = ticker.history(period="2d", interval="1d")
            if not df.empty:
                last = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else last
                chg = last - prev
                pct = (chg / prev) * 100 if prev != 0 else 0.0
                return {
                    "price": last,
                    "change": chg,
                    "change_pct": pct,
                    "timestamp": str(df.index[-1]),
                    "source": self.provider_name,
                    "delay_note": self._estimate_delay(symbol),
                    "success": True
                }
        except Exception as e:
            return {"success": False, "error": str(e), "price": 0.0}

        return {"success": False, "error": "No data", "price": 0.0}
