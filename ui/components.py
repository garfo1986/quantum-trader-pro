"""
Componentes reutilizables de interfaz gráfica para QuantumTrader Pro.
"""

import streamlit as st
from config import THEME_COLORS
from data.providers import MarketDataResult


def render_market_header(data: MarketDataResult):
    """Renderiza la barra superior de información con precio, cambio, fuente y retraso."""
    is_positive = data.change_usd >= 0
    change_color = THEME_COLORS["bullish"] if is_positive else THEME_COLORS["bearish"]
    sign = "+" if is_positive else ""

    st.markdown(
        f"""
        <div style="
            background-color: {THEME_COLORS['card_bg']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
        ">
            <div>
                <span style="font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;">
                    {data.symbol}
                </span>
                <span style="margin-left: 12px; font-size: 28px; font-weight: 700; color: #ffffff;">
                    ${data.last_price:,.4f}
                </span>
                <span style="margin-left: 10px; font-size: 16px; font-weight: 600; color: {change_color};">
                    {sign}${data.change_usd:,.2f} ({sign}{data.change_pct:.2f}%)
                </span>
            </div>
            <div style="text-align: right; font-size: 12px; color: {THEME_COLORS['text_secondary']};">
                <div><b>Fuente:</b> {data.source}</div>
                <div><b>Última Vela:</b> {data.timestamp}</div>
                <div style="color: #f59e0b; margin-top: 2px;">⚠️ <b>Aviso:</b> {data.delay_note}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_delay_banner(delay_note: str):
    """Muestra una advertencia transparente sobre la latencia de datos gratuitos."""
    st.info(f"ℹ️ **Transparencia de Datos Gratuitos**: {delay_note}", icon="ℹ️")
