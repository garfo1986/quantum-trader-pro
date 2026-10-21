"""
Módulo del Modo Entrenamiento (Replay Histórico a ciegas).
Permite practicar trading vela a vela sin conocer el futuro.
Garantiza matemáticamente la imposibilidad de look-ahead bias.
"""

from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd
from ui.charts import create_candlestick_chart
from indicators.technical import enrich_with_all_indicators
from signals.signal_engine import SignalEngine
from config import THEME_COLORS


def init_training_state(df: pd.DataFrame):
    """Inicializa o reinicia la sesión de entrenamiento."""
    start_idx = min(60, len(df) - 10)  # Dejar espacio para calentar indicadores
    st.session_state.training_df = df
    st.session_state.training_idx = start_idx
    st.session_state.training_cash = 10000.0
    st.session_state.training_position = None
    st.session_state.training_trades = []
    st.session_state.training_active = True


def render_training_module(full_df: pd.DataFrame, symbol: str):
    """Renderiza la interfaz completa interactiva del Modo Entrenamiento."""
    st.markdown(f"### 🕹️ Modo Entrenamiento: Práctica Histórica a Ciegas ({symbol})")
    st.caption("El gráfico oculta todo lo ocurrido después de la fecha actual. Avanza vela a vela y practica tu estrategia.")

    if len(full_df) < 80:
        st.warning("Se requieren al menos 80 velas para activar el modo de práctica histórica.")
        return

    # Botón para iniciar / reiniciar sesión
    if "training_active" not in st.session_state or not st.session_state.training_active:
        col_init, _ = st.columns([1, 2])
        with col_init:
            st.info("Configura tu punto de partida histórico para comenzar el simulador.")
            if st.button("🚀 Iniciar Nueva Sesión de Entrenamiento ($10,000 USD)", use_container_width=True):
                init_training_state(full_df)
                st.rerun()
        return

    # Manejo de índices
    idx = st.session_state.training_idx
    if idx >= len(full_df) - 1:
        st.success("🎉 ¡Has completado todo el recorrido histórico disponible!")
        if st.button("Reiniciar Entrenamiento"):
            init_training_state(full_df)
            st.rerun()
        return

    # SUBSET ESTRICTO: Solo datos hasta la vela actual (Cero información del futuro)
    visible_df_raw = full_df.iloc[: idx + 1].copy()
    visible_df = enrich_with_all_indicators(visible_df_raw)

    current_bar = visible_df.iloc[-1]
    curr_price = float(current_bar["close"])
    curr_date = str(visible_df.index[-1])

    # Motor de señales sobre el subconjunto causal
    engine = SignalEngine()
    current_signal = engine.evaluate_latest(visible_df)

    # BARRA SUPERIOR DE ACCIONES Y SALDO
    stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)

    # Calcular P&L no realizado si hay posición abierta
    pos = st.session_state.training_position
    pos_pnl_usd = 0.0
    pos_val = 0.0

    if pos:
        if pos["side"] == "LONG":
            pos_val = pos["shares"] * curr_price
            pos_pnl_usd = pos_val - pos["entry_amount"]
        else:
            pos_val = pos["entry_amount"] + ((pos["entry_price"] - curr_price) * pos["shares"])
            pos_pnl_usd = (pos["entry_price"] - curr_price) * pos["shares"]

    total_equity = st.session_state.training_cash + pos_val

    with stat_c1:
        st.metric("Efectivo Libre", f"${st.session_state.training_cash:,.2f}")
    with stat_c2:
        st.metric("Patrimonio Total", f"${total_equity:,.2f}")
    with stat_c3:
        pnl_col = THEME_COLORS["bullish"] if pos_pnl_usd >= 0 else THEME_COLORS["bearish"]
        st.metric("P&L Flotante", f"${pos_pnl_usd:+,.2f}")
    with stat_c4:
        st.metric("Vela Actual", f"{idx + 1} / {len(full_df)}")

    # BOTONES DE OPERATIVA Y PASO
    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)

    with btn_col1:
        if st.button("🟢 COMPRAR (LONG)", use_container_width=True, disabled=(pos is not None)):
            # Invertir el 80% del efectivo disponible
            invest = st.session_state.training_cash * 0.80
            if invest > 50:
                shares = invest / curr_price
                st.session_state.training_cash -= invest
                st.session_state.training_position = {
                    "side": "LONG",
                    "entry_price": curr_price,
                    "entry_amount": invest,
                    "shares": shares,
                    "entry_date": curr_date
                }
                st.rerun()

    with btn_col2:
        if st.button("🔴 VENDER (SHORT)", use_container_width=True, disabled=(pos is not None)):
            invest = st.session_state.training_cash * 0.80
            if invest > 50:
                shares = invest / curr_price
                st.session_state.training_cash -= invest
                st.session_state.training_position = {
                    "side": "SHORT",
                    "entry_price": curr_price,
                    "entry_amount": invest,
                    "shares": shares,
                    "entry_date": curr_date
                }
                st.rerun()

    with btn_col3:
        if st.button("⚪ CERRAR POSICIÓN", use_container_width=True, disabled=(pos is None)):
            if pos:
                ret_cash = pos["entry_amount"] + pos_pnl_usd
                st.session_state.training_cash += ret_cash
                st.session_state.training_trades.append({
                    "side": pos["side"],
                    "entry_date": pos["entry_date"],
                    "exit_date": curr_date,
                    "entry_price": pos["entry_price"],
                    "exit_price": curr_price,
                    "pnl_usd": pos_pnl_usd,
                    "pnl_pct": (pos_pnl_usd / pos["entry_amount"]) * 100.0
                })
                st.session_state.training_position = None
                st.rerun()

    with btn_col4:
        if st.button("⏩ AVANZAR 1 VELA", type="primary", use_container_width=True):
            st.session_state.training_idx += 1
            st.rerun()

    with btn_col5:
        if st.button("⏹️ Reiniciar Sesión", use_container_width=True):
            init_training_state(full_df)
            st.rerun()

    # GRÁFICO REVELADO HASTA ESTE MOMENTO
    fig = create_candlestick_chart(
        df=visible_df.iloc[-100:],  # Mostrar hasta las últimas 100 velas visibles
        symbol=f"{symbol} (Fecha Revelada: {curr_date})"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Panel informativo de señal generada en esa fecha
    inf_c1, inf_c2 = st.columns([1, 2])
    with inf_c1:
        st.info(f"💡 **Señal del Sistema en esta vela**: {current_signal['type']} (Score: {current_signal['score']}/100)")
    with inf_c2:
        if pos:
            st.warning(f"📌 **Posición Abierta**: {pos['side']} {pos['shares']:.4f} unidades desde ${pos['entry_price']:,.2f} ({pos['entry_date']})")
        else:
            st.write("💤 Sin posición abierta actualmente.")

    # Historial de operaciones de la sesión
    if st.session_state.training_trades:
        st.markdown("#### 📜 Operaciones de esta Sesión de Práctica")
        t_df = pd.DataFrame(st.session_state.training_trades)
        st.dataframe(t_df, use_container_width=True)
