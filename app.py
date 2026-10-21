"""
QuantumTrader Pro - Terminal Completa de Análisis de Mercados & Paper Trading (100% Gratuito).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config import (
    APP_TITLE, APP_ICON, WATCHLIST, TIMEFRAME_CONFIG, THEME_COLORS,
    PAPER_TRADING_DEFAULTS
)
from data.market_data import MarketDataManager
from indicators.technical import enrich_with_all_indicators
from indicators.levels import find_swing_extrema, cluster_levels, detect_trend, detect_breakouts
from signals.signal_engine import SignalEngine
from trading.engine import PaperTradingEngine
from trading.portfolio import PortfolioAnalyzer
from forecasting.heuristics import generate_heuristic_forecasts
from forecasting.ml_model import TimeSeriesMarketML
from forecasting.tracker import PredictionTracker
from backtesting.backtest import BacktestEngine
from news.news_feed import FreeNewsFeed
from ai.ollama_client import OllamaClient
from database.db import reset_account, get_account_balance, get_open_positions, get_closed_trades
from ui.charts import create_candlestick_chart
from ui.components import render_market_header
from ui.training_mode import render_training_module

# Configuración de página
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS de Terminal Oscuro
st.markdown(f"""
<style>
    .stApp {{
        background-color: {THEME_COLORS['background']};
        color: {THEME_COLORS['text_primary']};
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background-color: {THEME_COLORS['card_bg']};
        border-radius: 8px;
        padding: 6px;
        border: 1px solid {THEME_COLORS['border']};
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 38px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 6px;
        color: {THEME_COLORS['text_secondary']};
        font-weight: 600;
        font-size: 13px;
        border: none;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {THEME_COLORS['accent']} !important;
        color: #ffffff !important;
    }}
    div[data-testid="stMetricValue"] {{
        font-size: 20px;
        font-weight: 700;
        color: #ffffff;
    }}
    div[data-testid="stSidebar"] {{
        background-color: {THEME_COLORS['card_bg']};
        border-right: 1px solid {THEME_COLORS['border']};
    }}
    .custom-card {{
        background-color: {THEME_COLORS['card_bg']};
        border: 1px solid {THEME_COLORS['border']};
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }}
</style>
""", unsafe_allow_html=True)

# Inicialización del estado global
if "market_manager" not in st.session_state:
    st.session_state.market_manager = MarketDataManager()
if "signal_engine" not in st.session_state:
    st.session_state.signal_engine = SignalEngine()
if "trading_engine" not in st.session_state:
    st.session_state.trading_engine = PaperTradingEngine()
if "ollama_client" not in st.session_state:
    st.session_state.ollama_client = OllamaClient()

# --- BARRA LATERAL (CONTROLES Y PARÁMETROS) ---
with st.sidebar:
    st.markdown(f"### {APP_ICON} QuantumTrader Pro")
    st.caption("Terminal de Mercados & Paper Trading (Coste APIs = $0)")
    st.divider()

    st.markdown("#### 🎯 Selector de Activo")
    category = st.selectbox("Categoría de Mercado:", list(WATCHLIST.keys()), index=0)
    symbols_in_cat = WATCHLIST[category]
    selected_preset = st.selectbox(
        "Activo Predeterminado:",
        list(symbols_in_cat.keys()),
        format_func=lambda x: f"{x} - {symbols_in_cat[x]}",
        index=0
    )
    custom_symbol = st.text_input("O escribe cualquier símbolo:", value="", placeholder="Ej: TSLA, SOL-USD, GC=F")
    symbol = custom_symbol.strip().upper() if custom_symbol.strip() else selected_preset

    st.divider()

    st.markdown("#### ⏱️ Temporalidad")
    timeframe = st.selectbox("Intervalo de Velas:", list(TIMEFRAME_CONFIG.keys()), index=6)
    tf_info = TIMEFRAME_CONFIG[timeframe]
    st.caption(f"ℹ️ {tf_info['note']}")

    st.divider()

    st.markdown("#### 📐 Indicadores Gráficos")
    show_ema_9 = st.checkbox("EMA 9 (Cian)", value=False)
    show_ema_20 = st.checkbox("EMA 20 (Amarillo)", value=True)
    show_ema_50 = st.checkbox("EMA 50 (Naranja)", value=True)
    show_ema_200 = st.checkbox("EMA 200 (Magenta)", value=False)
    show_sma_50 = st.checkbox("SMA 50 (Púrpura)", value=False)
    show_sma_200 = st.checkbox("SMA 200 (Azul)", value=False)
    show_bollinger = st.checkbox("Bandas de Bollinger", value=False)
    show_vwap = st.checkbox("VWAP", value=False)
    show_levels = st.checkbox("Soportes y Resistencias", value=True)
    show_signals_chart = st.checkbox("Señales BUY / SELL en Gráfico", value=True)
    show_trades_chart = st.checkbox("Mis Operaciones en Gráfico", value=True)

    active_indicators = {
        "ema_9": show_ema_9, "ema_20": show_ema_20, "ema_50": show_ema_50,
        "ema_200": show_ema_200, "sma_50": show_sma_50, "sma_200": show_sma_200,
        "bollinger": show_bollinger, "vwap": show_vwap
    }

    st.divider()
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.rerun()


# --- OBTENCIÓN Y PREPARACIÓN DE DATOS ---
with st.spinner(f"Cargando datos de {symbol}..."):
    result = st.session_state.market_manager.get_market_data(symbol, timeframe)

if not result.is_success:
    st.error(f"❌ Error al consultar **{symbol}**: {result.error_message}")
    st.stop()

# Enriquecimiento de datos
df = enrich_with_all_indicators(result.df.copy())
swing_highs, swing_lows = find_swing_extrema(df, window=5)
key_levels = cluster_levels(swing_highs + swing_lows, result.last_price, tolerance_pct=0.015)
trend_info = detect_trend(df)
breakouts = detect_breakouts(df, key_levels)
latest_signal = st.session_state.signal_engine.evaluate_latest(df)
historical_signals = st.session_state.signal_engine.generate_history(df) if show_signals_chart else []

# Comprobar Stop-Loss / Take-Profit automáticos si hay posiciones de este activo
last_row = df.iloc[-1]
triggered_stops = st.session_state.trading_engine.check_and_trigger_stops(
    symbol=symbol,
    high_price=float(last_row["high"]),
    low_price=float(last_row["low"]),
    close_price=float(last_row["close"])
)

# Evaluar predicciones pendientes
PredictionTracker.evaluate_pending_predictions(symbol, result.last_price)

# Obtener operaciones del usuario para pintar en el gráfico si está activo
user_open_pos = get_open_positions()
user_closed_trades = get_closed_trades()
user_trades_for_chart = []
if show_trades_chart:
    for p in user_open_pos:
        if p["symbol"] == symbol:
            user_trades_for_chart.append({
                "side": p["side"], "entry_price": p["entry_price"],
                "timestamp": p["opened_at"][:19], "amount_usd": p["entry_amount"],
                "shares": p["shares"], "status": "ABIERTA"
            })
    for t in user_closed_trades:
        if t["symbol"] == symbol:
            user_trades_for_chart.append({
                "side": t["side"], "entry_price": t["entry_price"],
                "timestamp": t["opened_at"][:19], "amount_usd": t["entry_amount"],
                "shares": t["shares"], "status": f"CERRADA ({t['exit_reason']})"
            })


# --- PESTAÑAS PRINCIPALES ---
tab_market, tab_signals, tab_trading, tab_forecast, tab_backtest, tab_training, tab_news, tab_history, tab_config = st.tabs([
    "📊 Mercado",
    "⚡ Señales",
    "💼 Paper Trading",
    "🎯 Pronósticos",
    "🧪 Backtest",
    "🕹️ Modo Entrenamiento",
    "📰 Noticias",
    "📜 Rendimiento & Historial",
    "⚙️ Configuración"
])

# ==========================================
# 1. MERCADO
# ==========================================
with tab_market:
    render_market_header(result)

    if triggered_stops:
        for trig in triggered_stops:
            st.warning(f"🛑 **Orden Automática Ejecutada**: Posición #{trig['position_id']} en {symbol} cerrada por {trig['reason']} a ${trig['exit_price']:,.2f} (P&L: ${trig['pnl_usd']:+,.2f})")

    fig = create_candlestick_chart(
        df=df,
        symbol=symbol,
        active_indicators=active_indicators,
        signals=historical_signals,
        user_trades=user_trades_for_chart,
        support_resistance_levels=key_levels if show_levels else []
    )
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})

    st.markdown("#### 🔍 Resumen Cuantitativo")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    rsi_val = last_row.get("rsi", float("nan"))
    atr_val = last_row.get("atr", float("nan"))
    volat_val = last_row.get("volatility", float("nan"))
    rvol_val = last_row.get("rvol", float("nan"))

    with c1:
        st.metric("Señal Sistema", latest_signal["type"])
    with c2:
        st.metric("Score Multi-Factor", f"{latest_signal['score']}/100")
    with c3:
        st.metric("RSI (14)", f"{rsi_val:.1f}" if not pd.isna(rsi_val) else "N/A")
    with c4:
        st.metric("Tendencia", trend_info["label"])
    with c5:
        st.metric("ATR (Rango Medio)", f"${atr_val:,.2f}" if not pd.isna(atr_val) else "N/A")
    with c6:
        st.metric("Volumen Relativo", f"{rvol_val:.2f}x" if not pd.isna(rvol_val) else "N/A")

    if breakouts:
        for b in breakouts:
            if b["type"] == "RUPTURA_RESISTENCIA":
                st.success(f"🚀 **Alerta Técnica**: {b['message']}")
            else:
                st.warning(f"⚠️ **Alerta Técnica**: {b['message']}")


# ==========================================
# 2. SEÑALES
# ==========================================
with tab_signals:
    st.markdown(f"### ⚡ Motor Multi-Factor: Confluencia Algorítmica ({symbol})")
    col_s1, col_s2 = st.columns([1, 2])

    with col_s1:
        st.markdown(
            f"""
            <div class="custom-card" style="text-align: center;">
                <div style="color: {THEME_COLORS['text_secondary']};">SEÑAL ACTUAL</div>
                <div style="font-size: 32px; font-weight: 800; margin: 10px 0; color: {
                    THEME_COLORS['bullish'] if 'BUY' in latest_signal['type']
                    else (THEME_COLORS['bearish'] if 'SELL' in latest_signal['type'] else '#ffffff')
                };">
                    {latest_signal['type']}
                </div>
                <div style="color: {THEME_COLORS['text_secondary']};">Score Confluencia</div>
                <div style="font-size: 36px; font-weight: 700; color: #ffffff;">
                    {latest_signal['score']} <span style="font-size: 16px; color: {THEME_COLORS['text_secondary']};">/ 100</span>
                </div>
                <p style="margin-top: 10px; font-size: 13px; color: {THEME_COLORS['text_primary']};">
                    {latest_signal['reason']}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("#### 📍 Niveles Clave Detectados")
        if key_levels:
            for lvl in key_levels:
                color = THEME_COLORS["bullish"] if lvl["type"] == "Soporte" else THEME_COLORS["bearish"]
                st.markdown(
                    f"- <span style='color: {color}; font-weight: 600;'>{lvl['type']}</span>: "
                    f"**${lvl['price']:,.2f}** ({lvl['distance_pct']:+.2f}%, {lvl['touches']} toques)",
                    unsafe_allow_html=True
                )
        else:
            st.info("No se detectaron niveles clave consolidados en este rango.")

    with col_s2:
        st.markdown("#### ✅ Factores Alcistas")
        if latest_signal["bullish_factors"]:
            for f in latest_signal["bullish_factors"]:
                st.success(f"🟢 {f}")
        else:
            st.write("Ningún factor alcista destacado.")

        st.markdown("#### ❌ Factores Bajistas")
        if latest_signal["bearish_factors"]:
            for f in latest_signal["bearish_factors"]:
                st.error(f"🔴 {f}")
        else:
            st.write("Ningún factor bajista destacado.")

        # IA Local Ollama opcional
        ollama_status = st.session_state.ollama_client.check_availability()
        if ollama_status["available"] and ollama_status["models"]:
            st.divider()
            selected_model = st.selectbox("Modelo Ollama Local para Explicación:", ollama_status["models"], key="ollama_sig_model")
            if st.button("🧠 Explicar Señal con IA Local"):
                with st.spinner("Generando explicación técnica cualitativa con Ollama local..."):
                    ai_exp = st.session_state.ollama_client.explain_signal(symbol, latest_signal, selected_model)
                    st.info(ai_exp)


# ==========================================
# 3. PAPER TRADING
# ==========================================
with tab_trading:
    st.markdown("### 💼 Simulador de Paper Trading (Dinero Ficticio)")
    st.caption("Prueba tus estrategias con saldo simulado sin ningún riesgo de capital real.")

    # Estado de la cartera simulada
    portfolio_state = st.session_state.trading_engine.get_portfolio_state({symbol: result.last_price})

    p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
    with p_col1:
        st.metric("Efectivo (Cash)", f"${portfolio_state['cash']:,.2f}")
    with p_col2:
        st.metric("Valor Posiciones", f"${portfolio_state['positions_value']:,.2f}")
    with p_col3:
        st.metric("Patrimonio Total", f"${portfolio_state['total_equity']:,.2f}")
    with p_col4:
        pnl_color = THEME_COLORS["bullish"] if portfolio_state["total_pnl_usd"] >= 0 else THEME_COLORS["bearish"]
        st.metric("P&L Total", f"${portfolio_state['total_pnl_usd']:+,.2f}")
    with p_col5:
        st.metric("Rentabilidad %", f"{portfolio_state['total_pnl_pct']:+.2f}%")

    st.divider()

    # Panel de Ejecución de Órdenes
    ord_c1, ord_c2 = st.columns([1, 1])

    with ord_c1:
        st.markdown("#### 🛒 Panel de Órdenes")
        trade_side = st.radio("Dirección de la Operación:", ["LONG (Comprar para ganar con subida)", "SHORT (Vender para ganar con caída)"], horizontal=True)
        is_long = "LONG" in trade_side
        side_code = "LONG" if is_long else "SHORT"

        order_type_mode = st.radio("Modo de Importe:", ["Invertir en Dólares ($ USD)", "Indicar Número de Unidades"], horizontal=True)

        if "Dólares" in order_type_mode:
            order_usd = st.number_input("Monto a Invertir ($ USD):", min_value=10.0, max_value=float(portfolio_state["cash"]), value=min(1000.0, float(portfolio_state["cash"])), step=100.0)
            order_shares = None
        else:
            order_shares = st.number_input("Número de Unidades:", min_value=0.0001, value=1.0, step=0.1)
            order_usd = None

        col_sl, col_tp = st.columns(2)
        with col_sl:
            use_sl = st.checkbox("Configurar Stop Loss", value=False)
            sl_price = st.number_input("Precio Stop Loss ($):", min_value=0.0, value=result.last_price * 0.95 if is_long else result.last_price * 1.05) if use_sl else None
        with col_tp:
            use_tp = st.checkbox("Configurar Take Profit", value=False)
            tp_price = st.number_input("Precio Take Profit ($):", min_value=0.0, value=result.last_price * 1.10 if is_long else result.last_price * 0.90) if use_tp else None

        if st.button(f"🚀 EJECUTAR ORDEN {side_code} en {symbol} a ${result.last_price:,.4f}", type="primary", use_container_width=True):
            exec_res = st.session_state.trading_engine.open_position(
                symbol=symbol,
                side=side_code,
                current_price=result.last_price,
                amount_usd=order_usd,
                shares=order_shares,
                stop_loss=sl_price,
                take_profit=tp_price
            )
            if exec_res["success"]:
                st.success(f"✅ Posición #{exec_res['position_id']} abierta exitosamente: {side_code} {exec_res['shares']:.4f} {symbol} a ${exec_res['entry_price']:,.4f} (Comisión: ${exec_res['commission']:,.2f})")
                st.rerun()
            else:
                st.error(f"❌ Error al abrir orden: {exec_res['error']}")

    with ord_c2:
        st.markdown("#### 📋 Posiciones Abiertas Actualmente")
        open_positions = portfolio_state["open_positions"]

        if not open_positions:
            st.info("No tienes posiciones abiertas en este momento.")
        else:
            for p in open_positions:
                with st.container():
                    st.markdown(
                        f"""
                        <div class="custom-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-weight: 700; font-size: 16px;">#{p['id']} {p['symbol']}</span>
                                    <span style="margin-left: 8px; font-weight: 600; color: {'#089981' if p['side'] == 'LONG' else '#f23645'};">[{p['side']}]</span>
                                </div>
                                <div style="font-weight: 700; color: {'#089981' if p['unrealized_pnl_usd'] >= 0 else '#f23645'};">
                                    ${p['unrealized_pnl_usd']:+,.2f} ({p['unrealized_pnl_pct']:+.2f}%)
                                </div>
                            </div>
                            <div style="font-size: 12px; color: {THEME_COLORS['text_secondary']}; margin-top: 6px;">
                                Entrada: ${p['entry_price']:,.4f} | Actual: ${p['current_price']:,.4f} | Cantidad: {p['shares']:.4f} | Invertido: ${p['entry_amount']:,.2f}
                            </div>
                            <div style="font-size: 12px; color: {THEME_COLORS['text_secondary']};">
                                Stop Loss: {f"${p['stop_loss']:,.2f}" if p['stop_loss'] else 'Sin definir'} | Take Profit: {f"${p['take_profit']:,.2f}" if p['take_profit'] else 'Sin definir'}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button(f"Cerrar Posición #{p['id']}", key=f"close_btn_{p['id']}"):
                        close_res = st.session_state.trading_engine.close_position(
                            pos_id=p["id"],
                            current_price=result.last_price if p["symbol"] == symbol else p["current_price"],
                            reason="MANUAL"
                        )
                        if close_res["success"]:
                            st.success(f"Posición #{p['id']} cerrada. P&L: ${close_res['pnl_usd']:+,.2f}")
                            st.rerun()

            st.divider()
            if st.button("🚨 CERRAR TODAS LAS POSICIONES", use_container_width=True):
                for p in open_positions:
                    st.session_state.trading_engine.close_position(p["id"], p["current_price"], reason="CERRAR_TODO")
                st.rerun()


# ==========================================
# 4. PRONÓSTICOS
# ==========================================
with tab_forecast:
    st.markdown("### 🎯 Pronósticos Probabilísticos del Mercado")
    st.caption("Estimaciones probabilísticas auditables. Las probabilidades suman exactamente 100%.")

    forecast_tab1, forecast_tab2, forecast_tab3 = st.tabs([
        "🔮 Estimación Heurística (Multi-Horizonte)",
        "🤖 Modelo Machine Learning (Scikit-Learn)",
        "📜 Auditoría Histórica de Pronósticos"
    ])

    with forecast_tab1:
        st.info("ℹ️ **Nota de Rigor**: 'Estimación heurística no calibrada'. No asumas que el programa 'sabe' el futuro.")
        forecasts = generate_heuristic_forecasts(df)

        cols = st.columns(5)
        for c, (h_name, f_data) in zip(cols, forecasts.items()):
            with c:
                st.markdown(
                    f"""
                    <div class="custom-card" style="text-align: center;">
                        <div style="font-weight: 700; font-size: 15px; margin-bottom: 6px;">{h_name}</div>
                        <div style="font-size: 13px; color: {THEME_COLORS['text_secondary']};">{f_data['sesgo']}</div>
                        <hr style="border-color: {THEME_COLORS['border']}; margin: 8px 0;">
                        <div style="font-size: 13px; color: {THEME_COLORS['bullish']}; font-weight: 600;">Alcista: {f_data['alcista']}%</div>
                        <div style="font-size: 13px; color: {THEME_COLORS['neutral']}; font-weight: 600;">Lateral: {f_data['lateral']}%</div>
                        <div style="font-size: 13px; color: {THEME_COLORS['bearish']}; font-weight: 600;">Bajista: {f_data['bajista']}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"Guardar {h_name}", key=f"save_pred_{h_name}"):
                    PredictionTracker.log_prediction(
                        symbol=symbol,
                        timeframe=timeframe,
                        horizon=h_name,
                        initial_price=result.last_price,
                        prob_bullish=f_data["alcista"],
                        prob_neutral=f_data["lateral"],
                        prob_bearish=f_data["bajista"],
                        predicted_direction="ALCISTA" if f_data["alcista"] > f_data["bajista"] else "BAJISTA"
                    )
                    st.success("Pronóstico registrado para auditoría futura.")

    with forecast_tab2:
        st.markdown("#### 🤖 Clasificador Random Forest con Separación Temporal Estricta")
        st.caption("Entrenado exclusivamente con el histórico causal (sin Look-Ahead Bias ni Data Leakage).")

        f_bars = st.slider("Horizonte de predicción (número de velas futuras objetivo):", 1, 10, 5)
        thr = st.slider("Umbral de movimiento porcentual para clasificar tendencia (%):", 0.2, 3.0, 1.0) / 100.0

        if st.button("🚀 Entrenar y Evaluar Modelo Scikit-Learn"):
            ml_model = TimeSeriesMarketML(forward_bars=f_bars, threshold_pct=thr)
            with st.spinner("Entrenando con Walk-Forward Validation..."):
                ml_res = ml_model.train_and_evaluate(df)

            if ml_res["success"]:
                r_c1, r_c2, r_c3 = st.columns(3)
                with r_c1:
                    st.metric("Exactitud en Test", f"{ml_res['test_accuracy']}%")
                with r_c2:
                    st.metric("Estrategia Base (Mayoritaria)", f"{ml_res['baseline_accuracy']}%")
                with r_c3:
                    st.metric("Walk-Forward Cross-Val", f"{ml_res['walk_forward_cv_accuracy']}%")

                probs = ml_res["probabilities"]
                st.markdown(f"**Probabilidad Calibrada para la Próxima Vela:**")
                st.progress(probs["alcista"] / 100.0, text=f"Alcista: {probs['alcista']}%")
                st.progress(probs["lateral"] / 100.0, text=f"Lateral: {probs['lateral']}%")
                st.progress(probs["bajista"] / 100.0, text=f"Bajista: {probs['bajista']}%")

                st.markdown("##### Importancia de Características Técnicas:")
                st.bar_chart(ml_res["feature_importance"])
            else:
                st.error(ml_res["error"])

    with forecast_tab3:
        st.markdown("#### 📜 Registro de Aciertos y Fallos de Pronósticos Pasados")
        audit_records = PredictionTracker.get_prediction_audit_history(symbol)
        if audit_records:
            a_df = pd.DataFrame(audit_records)[[
                "horizon", "generated_at", "initial_price", "final_price",
                "predicted_direction", "actual_direction", "is_correct"
            ]]
            a_df["Resultado"] = a_df["is_correct"].apply(lambda x: "ACIERTO 🟢" if x == 1 else ("FALLO 🔴" if x == 0 else "PENDIENTE ⏳"))
            st.dataframe(a_df, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no has guardado pronósticos para este activo.")


# ==========================================
# 5. BACKTEST
# ==========================================
with tab_backtest:
    st.markdown(f"### 🧪 Módulo de Backtesting Histórico: {symbol}")
    st.caption("Simulación cuantitativa rigurosa sin información futura, con comisiones y slippage.")

    bk_c1, bk_c2, bk_c3, bk_c4 = st.columns(4)
    with bk_c1:
        bk_capital = st.number_input("Capital Inicial ($ USD):", value=10000.0, step=1000.0)
    with bk_c2:
        bk_comm = st.number_input("Comisión (%):", value=0.1, step=0.01) / 100.0
    with bk_c3:
        bk_spread = st.number_input("Spread (%):", value=0.02, step=0.01) / 100.0
    with bk_c4:
        bk_slip = st.number_input("Slippage (%):", value=0.05, step=0.01) / 100.0

    allow_shorts_bk = st.checkbox("Permitir Operaciones en Corto (SHORT)", value=True)

    if st.button("🚀 Ejecutar Backtest Ahora", type="primary"):
        with st.spinner("Simulando estrategia histórica vela por vela..."):
            engine = BacktestEngine(
                initial_capital=bk_capital,
                commission_rate=bk_comm,
                spread_rate=bk_spread,
                slippage_rate=bk_slip,
                allow_short=allow_shorts_bk
            )
            bk_res = engine.run(df)

        if bk_res["success"]:
            strat = bk_res["strategy"]
            bh = bk_res["buy_and_hold"]

            st.markdown("#### 📊 Comparativa: Mi Estrategia vs Buy & Hold")
            comp_col1, comp_col2, comp_col3, comp_col4, comp_col5 = st.columns(5)
            with comp_col1:
                st.metric("Retorno Estrategia", f"{strat['total_return_pct']:+.2f}%", f"${strat['final_equity']:,.2f}")
            with comp_col2:
                st.metric("Retorno Buy & Hold", f"{bh['total_return_pct']:+.2f}%", f"${bh['final_equity']:,.2f}")
            with comp_col3:
                st.metric("Max Drawdown Estrategia", f"{strat['max_drawdown_pct']:.2f}%")
            with comp_col4:
                st.metric("Win Rate", f"{strat['win_rate']:.1f}%", f"{strat['total_trades']} operaciones")
            with comp_col5:
                st.metric("Profit Factor", f"{strat['profit_factor']:.2f}")

            # Gráfico de Equity Curve Comparativa
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(x=bk_res["equity_curve"]["date"], y=bk_res["equity_curve"]["Estrategia Sistema"], name="Estrategia Sistema (Señales)", line=dict(color="#089981", width=2)))
            fig_eq.add_trace(go.Scatter(x=bk_res["equity_curve"]["date"], y=bk_res["equity_curve"]["Buy & Hold"], name="Buy & Hold (Referencia)", line=dict(color="#787b86", width=1.5, dash="dash")))
            fig_eq.update_layout(template="plotly_dark", title="Curva de Capital (Equity Curve)", height=450, hovermode="x unified", paper_bgcolor=THEME_COLORS["card_bg"], plot_bgcolor=THEME_COLORS["background"])
            st.plotly_chart(fig_eq, use_container_width=True)

            if bk_res["trades"]:
                st.markdown("#### 📜 Registro de Operaciones del Backtest")
                st.dataframe(pd.DataFrame(bk_res["trades"]), use_container_width=True)
        else:
            st.error(bk_res["error"])


# ==========================================
# 6. MODO ENTRENAMIENTO
# ==========================================
with tab_training:
    render_training_module(df, symbol)


# ==========================================
# 7. NOTICIAS
# ==========================================
with tab_news:
    st.markdown(f"### 📰 Noticias Financieras & Análisis de Sentimiento ({symbol})")
    st.caption("Fuentes públicas RSS gratuitas y comunicados oficiales. Coste de APIs = $0.")

    news_items = FreeNewsFeed.get_news_for_symbol(symbol, limit=8)
    macro_items = FreeNewsFeed.get_macro_official_news(limit=4)

    # Resumen con Ollama opcional
    ollama_status = st.session_state.ollama_client.check_availability()
    if ollama_status["available"] and ollama_status["models"]:
        o_col1, o_col2 = st.columns([2, 1])
        with o_col1:
            n_model = st.selectbox("Modelo Ollama para Resumen:", ollama_status["models"], key="news_ollama_model")
        with o_col2:
            st.write("")
            st.write("")
            if st.button("🧠 Resumir Titulares con IA Local"):
                with st.spinner("Resumiendo noticias..."):
                    summary = st.session_state.ollama_client.summarize_news(news_items + macro_items, n_model)
                    st.info(summary)

    st.markdown(f"#### 🌐 Titulares de {symbol}")
    if news_items:
        for n in news_items:
            sent = n["sentiment"]
            st.markdown(
                f"""
                <div class="custom-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 11px; color: {THEME_COLORS['text_secondary']};">{n['date']} | {n['source']}</span>
                        <span style="font-size: 11px; font-weight: 700;">{sent['label']} (Score: {sent['score']})</span>
                    </div>
                    <div style="margin-top: 6px;">
                        <a href="{n['url']}" target="_blank" style="color: #ffffff; text-decoration: none; font-weight: 600; font-size: 15px;">
                            {n['title']}
                        </a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info(f"No se encontraron noticias RSS recientes para {symbol}.")

    st.markdown("#### 🏛️ Comunicados Oficiales (Federal Reserve & SEC)")
    if macro_items:
        for m in macro_items:
            st.markdown(f"- **{m['source']}** ({m['date']}): [{m['title']}]({m['url']}) | Sentimiento: {m['sentiment']['label']}")


# ==========================================
# 8. RENDIMIENTO & HISTORIAL
# ==========================================
with tab_history:
    st.markdown("### 📜 Métricas de Rendimiento Cuantitativo & Auditoría")
    account = get_account_balance()
    closed_trades = get_closed_trades()

    metrics = PortfolioAnalyzer.calculate_performance_metrics(
        initial_capital=account["initial_capital"],
        current_equity=portfolio_state["total_equity"],
        closed_trades=closed_trades
    )

    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns(6)
    with h_col1:
        st.metric("Capital Inicial", f"${metrics['initial_capital']:,.2f}")
    with h_col2:
        st.metric("Patrimonio Actual", f"${metrics['current_equity']:,.2f}")
    with h_col3:
        st.metric("P&L Neto", f"${metrics['total_pnl_usd']:+,.2f}")
    with h_col4:
        st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    with h_col5:
        st.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
    with h_col6:
        st.metric("Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%")

    # Curva de Equity de la Cartera
    if len(metrics["equity_curve"]) > 1:
        fig_user_eq = go.Figure()
        fig_user_eq.add_trace(go.Scatter(
            x=metrics["equity_curve"]["trade_num"],
            y=metrics["equity_curve"]["equity"],
            mode="lines+markers",
            line=dict(color="#089981", width=2),
            name="Patrimonio de Cartera"
        ))
        fig_user_eq.update_layout(template="plotly_dark", title="Evolución del Patrimonio de tu Cartera", height=380, paper_bgcolor=THEME_COLORS["card_bg"], plot_bgcolor=THEME_COLORS["background"])
        st.plotly_chart(fig_user_eq, use_container_width=True)

    st.divider()
    st.markdown("#### 🔍 Simulador Contrafactual: '¿Qué habría pasado?'")
    st.caption("Evalúa qué habría ocurrido si hubieses mantenido una operación cerrada hasta el precio actual.")

    if closed_trades:
        selected_trade_id = st.selectbox(
            "Selecciona una operación cerrada:",
            [t["id"] for t in closed_trades],
            format_func=lambda x: f"Trade #{x}: {next(t['symbol'] for t in closed_trades if t['id'] == x)} [{next(t['side'] for t in closed_trades if t['id'] == x)}] (Cerrado a ${next(t['exit_price'] for t in closed_trades if t['id'] == x):,.2f})"
        )
        trade_data = next(t for t in closed_trades if t["id"] == selected_trade_id)
        current_asset_price = result.last_price if trade_data["symbol"] == symbol else trade_data["exit_price"]
        what_if = PortfolioAnalyzer.simulate_what_if(trade_data, current_asset_price)

        wi_c1, wi_c2, wi_c3 = st.columns(3)
        with wi_c1:
            st.metric("P&L Realizado", f"${what_if['realized_pnl_usd']:+,.2f} ({what_if['realized_pnl_pct']:+.2f}%)")
        with wi_c2:
            st.metric("P&L Si Siguiera Abierta", f"${what_if['hypothetical_pnl_usd']:+,.2f} ({what_if['hypothetical_pnl_pct']:+.2f}%)")
        with wi_c3:
            st.metric("Diferencia de Decisión", f"${what_if['difference_usd']:+,.2f}")

        if what_if["was_closing_better"]:
            st.success("🎯 **Decisión Correcta**: Cerrar la posición fue mejor que haberla mantenido abierta.")
        else:
            st.warning("⏳ **Cierre Anticipado**: Si hubieses mantenido la operación, tendrías un mejor resultado.")

        st.markdown("#### 📜 Registro Completo de Operaciones Cerradas")
        st.dataframe(pd.DataFrame(closed_trades), use_container_width=True)
    else:
        st.info("Aún no tienes operaciones cerradas en el historial.")


# ==========================================
# 9. CONFIGURACIÓN
# ==========================================
with tab_config:
    st.markdown("### ⚙️ Configuración del Sistema")

    conf_c1, conf_c2 = st.columns(2)

    with conf_c1:
        st.markdown("#### 💰 Saldo y Parámetros de Simulación")
        if st.button("🔄 Reiniciar Cartera a $10,000 USD (Borrar Todo el Historial)"):
            reset_account(10000.0)
            st.success("Cuenta reiniciada a $10,000 USD.")
            st.rerun()

        st.markdown("#### 💸 Configuración de Costes Realistas")
        new_comm = st.slider("Comisión por Operación (%):", 0.0, 1.0, 0.1, step=0.01) / 100.0
        new_spread = st.slider("Spread Estimado (%):", 0.0, 0.5, 0.02, step=0.01) / 100.0
        new_slip = st.slider("Slippage Estimado (%):", 0.0, 0.5, 0.05, step=0.01) / 100.0
        st.caption("Puedes establecer los costes en 0.0% o simular condiciones de mercado reales.")

    with conf_c2:
        st.markdown("#### 🧠 Estado de IA Local (Ollama)")
        ollama_info = st.session_state.ollama_client.check_availability()
        if ollama_info["available"]:
            st.success(f"🟢 **Ollama Activo**: {ollama_info['count']} modelo(s) detectado(s).")
            st.write(f"Modelos disponibles: `{', '.join(ollama_info['models'])}`")
        else:
            st.warning(f"⚪ **Ollama no detectado**: {ollama_info.get('message')}")
            st.info("💡 Para activar la IA local opcional, descarga Ollama desde `https://ollama.ai` y ejecuta un modelo (ej: `ollama run llama3`).")

        st.markdown("#### 🛡️ Política de Coste $0 y Transparencia")
        st.markdown("""
        - **APIs de Pago**: 0 (Cero). No se requiere ninguna clave de OpenAI, AlphaVantage, Bloomberg ni Polygon.
        - **Retraso de Datos**: Acciones 15m diferido, Cripto y Forex tiempo casi real mediante feeds libres.
        - **Privacidad**: Todos los datos y bases de datos permanecen en tu ordenador local (`quantum_trader.db`).
        """)
