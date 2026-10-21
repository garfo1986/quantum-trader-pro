"""
Configuración global de la plataforma de Análisis de Mercados y Paper Trading.
"""

APP_TITLE = "QuantumTrader Pro | Terminal de Mercados & Paper Trading"
APP_ICON = "📈"
APP_VERSION = "1.0.0"

# Activos populares agrupados por categoría
WATCHLIST = {
    "Acciones": {
        "AAPL": "Apple Inc.",
        "NVDA": "NVIDIA Corporation",
        "MSFT": "Microsoft Corporation",
        "TSLA": "Tesla Inc.",
        "AMZN": "Amazon.com Inc.",
        "GOOGL": "Alphabet Inc.",
        "META": "Meta Platforms Inc."
    },
    "ETFs & Índices": {
        "SPY": "SPDR S&P 500 ETF Trust",
        "QQQ": "Invesco QQQ Trust (Nasdaq 100)",
        "DIA": "SPDR Dow Jones Industrial Average ETF",
        "IWM": "iShares Russell 2000 ETF",
        "^GSPC": "S&P 500 Index (Gratis delayed)",
        "^IXIC": "NASDAQ Composite (Gratis delayed)"
    },
    "Criptomonedas": {
        "BTC-USD": "Bitcoin / USD",
        "ETH-USD": "Ethereum / USD",
        "SOL-USD": "Solana / USD",
        "BNB-USD": "Binance Coin / USD",
        "XRP-USD": "XRP / USD"
    },
    "Materias Primas": {
        "GC=F": "Oro (Gold Futures)",
        "SI=F": "Plata (Silver Futures)",
        "CL=F": "Petróleo Crudo WTI",
        "NG=F": "Gas Natural"
    },
    "Forex": {
        "EURUSD=X": "EUR / USD",
        "GBPUSD=X": "GBP / USD",
        "USDJPY=X": "USD / JPY",
        "AUDUSD=X": "AUD / USD",
        "USDCOP=X": "USD / COP"
    }
}

# Configuración de temporalidades
TIMEFRAME_CONFIG = {
    "1m": {"interval": "1m", "default_period": "1d", "max_days": 7, "note": "Máximo 7 días en proveedor gratuito"},
    "5m": {"interval": "5m", "default_period": "5d", "max_days": 60, "note": "Máximo 60 días en proveedor gratuito"},
    "15m": {"interval": "15m", "default_period": "5d", "max_days": 60, "note": "Máximo 60 días en proveedor gratuito"},
    "30m": {"interval": "30m", "default_period": "1mo", "max_days": 60, "note": "Máximo 60 días en proveedor gratuito"},
    "1h": {"interval": "1h", "default_period": "1mo", "max_days": 730, "note": "Máximo 730 días (2 años)"},
    "4h": {"interval": "1h", "resample": "4h", "default_period": "3mo", "max_days": 730, "note": "Calculado agrupando velas de 1h"},
    "1D": {"interval": "1d", "default_period": "1y", "max_days": None, "note": "Histórico completo disponible"},
    "1W": {"interval": "1wk", "default_period": "5y", "max_days": None, "note": "Histórico semanal completo"}
}

# Configuración de colores del tema oscuro de Trading
THEME_COLORS = {
    "background": "#0e1117",
    "card_bg": "#1e222d",
    "border": "#2a2e39",
    "bullish": "#089981",       # Verde profesional trading
    "bearish": "#f23645",       # Rojo profesional trading
    "neutral": "#787b86",       # Gris secundario
    "accent": "#2962ff",        # Azul acción
    "warning": "#ff9800",
    "text_primary": "#d1d4dc",
    "text_secondary": "#787b86"
}

# Configuración por defecto de Paper Trading
PAPER_TRADING_DEFAULTS = {
    "initial_capital": 10000.0,
    "commission_rate": 0.001,   # 0.1% por defecto
    "spread_rate": 0.0002,      # 0.02%
    "slippage_rate": 0.0005     # 0.05%
}

# Configuración de base de datos
DB_FILE = "quantum_trader.db"
