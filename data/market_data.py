"""
Gestor unificado de datos de mercado con soporte para múltiples proveedores y caché.
"""

from typing import Dict, Any, Optional
import pandas as pd
from data.providers import BaseDataProvider, YFinanceProvider, MarketDataResult
from config import WATCHLIST


class MarketDataManager:
    """Gestiona las peticiones de datos de mercado para la interfaz y módulos analíticos."""

    def __init__(self, provider: Optional[BaseDataProvider] = None):
        self.provider: BaseDataProvider = provider if provider else YFinanceProvider()

    def get_market_data(self, symbol: str, timeframe: str = "1D") -> MarketDataResult:
        """Obtiene velas y metadatos limpios para el activo y temporalidad indicados."""
        symbol = symbol.strip().upper()
        return self.provider.fetch_data(symbol, timeframe)

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Obtiene la cotización instantánea del activo."""
        symbol = symbol.strip().upper()
        return self.provider.get_latest_quote(symbol)

    @staticmethod
    def get_symbol_name(symbol: str) -> str:
        """Busca el nombre amigable en la watchlist o devuelve el símbolo."""
        symbol_clean = symbol.strip().upper()
        for category, symbols in WATCHLIST.items():
            if symbol_clean in symbols:
                return f"{symbols[symbol_clean]} ({symbol_clean})"
        return symbol_clean
