# ⚡ QuantumTrader Pro

Terminal profesional de análisis técnico de mercados financieros, pronósticos probabilísticos y paper trading simulado con dinero ficticio.

**100% GRATUITO: Coste de APIs = $0.00**
- Sin suscripciones.
- Sin tarjetas de crédito ni tokens de pago.
- Base de datos local SQLite.
- Integración opcional con IA local (Ollama).

---

## 🚀 Instalación y Ejecución Rápida

### Opción 1: En Windows (Doble clic)
Haz doble clic en el archivo `run_app.bat`. Se abrirá automáticamente el terminal y tu navegador web predeterminado.

### Opción 2: Desde la terminal (Windows, macOS, Linux)

1. **Abrir la terminal / PowerShell** en la carpeta `trading`:
   ```bash
   cd "d:/trabajo/Proyecto Yeimy/trading"
   ```

2. **Crear y activar un entorno virtual (opcional pero recomendado):**
   - En Windows:
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - En macOS / Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar los requerimientos gratuitos:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación:**
   ```bash
   streamlit run app.py
   ```

5. El navegador se abrirá en `http://localhost:8501`.

---

## 📁 Estructura del Proyecto

```
trading/
├── app.py                  # Dashboard y orquestador principal Streamlit
├── config.py               # Watchlist, timeframes y paleta de colores oscura
├── requirements.txt        # Dependencias 100% de código abierto
├── run_app.bat             # Lanzador rápido para Windows
├── data/
│   ├── providers.py        # Capa de proveedores y abstracción (Yahoo Finance gratuito)
│   └── market_data.py      # Gestor de cotizaciones y metadatos
├── ui/
│   ├── charts.py           # Gráfico interactivo Plotly OHLCV + Volumen + Overlays
│   └── components.py       # Encabezado de mercado y badges de latencia transparente
├── indicators/             # (Fase 2) RSI, MACD, ATR, Bollinger, ADX, VWAP, Soportes/Resistencias
├── signals/                # (Fase 2) Motor de señales multi-factor (BUY / HOLD / SELL)
├── trading/                # (Fase 3) Motor de Paper Trading, Long/Short, Stops y Take Profit
├── database/               # (Fase 3-4) SQLite local para operaciones y registros
├── forecasting/            # (Fase 5) Pronósticos probabilísticos y Machine Learning
├── backtesting/            # (Fase 5) Backtest histórico contra Buy & Hold
├── news/                   # (Fase 6) RSS y comunicados oficiales gratuitos
├── ai/                     # (Fase 7) Cliente local Ollama opcional
└── tests/                  # (Fases 3+) Tests unitarios de P&L, comisiones y consistencia matemática
```
