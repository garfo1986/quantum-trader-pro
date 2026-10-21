"""
Módulo de visualización gráfica financiera profesional con Plotly.
Gráfico de velas japonesas (OHLCV) con tema oscuro estilo TradingView,
indicadores superpuestos, soportes/resistencias y marcadores de señales.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config import THEME_COLORS


def create_candlestick_chart(
    df: pd.DataFrame,
    symbol: str,
    active_indicators: Optional[Dict[str, bool]] = None,
    signals: Optional[List[Dict[str, Any]]] = None,
    user_trades: Optional[List[Dict[str, Any]]] = None,
    support_resistance_levels: Optional[List[Dict[str, Any]]] = None
) -> go.Figure:
    """
    Crea un gráfico profesional interactivo con subplots:
    - Panel superior: Velas japonesas + Indicadores superpuestos + Niveles + Señales
    - Panel inferior: Barras de volumen coloreadas según el sentido de la vela
    """
    if active_indicators is None:
        active_indicators = {}
    if signals is None:
        signals = []
    if user_trades is None:
        user_trades = []
    if support_resistance_levels is None:
        support_resistance_levels = []

    # Configuración de subplots (80% velas, 20% volumen)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.78, 0.22],
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )

    # 1. Velas Japonesas
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=f"{symbol} Precio",
            increasing_line_color=THEME_COLORS["bullish"],
            decreasing_line_color=THEME_COLORS["bearish"],
            increasing_fillcolor=THEME_COLORS["bullish"],
            decreasing_fillcolor=THEME_COLORS["bearish"],
            hoverlabel=dict(bgcolor=THEME_COLORS["card_bg"], font_color=THEME_COLORS["text_primary"]),
            customdata=df[["volume"]],
            hovertemplate=(
                "<b>Fecha</b>: %{x}<br>"
                "<b>Apertura</b>: $%{open:,.4f}<br>"
                "<b>Máximo</b>: $%{high:,.4f}<br>"
                "<b>Mínimo</b>: $%{low:,.4f}<br>"
                "<b>Cierre</b>: $%{close:,.4f}<extra></extra>"
            )
        ),
        row=1, col=1
    )

    # 2. Volumen con colores alcistas/bajistas
    if "volume" in df.columns and not df["volume"].isna().all():
        vol_colors = [
            THEME_COLORS["bullish"] if c >= o else THEME_COLORS["bearish"]
            for o, c in zip(df["open"], df["close"])
        ]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["volume"],
                name="Volumen",
                marker_color=vol_colors,
                opacity=0.6,
                hovertemplate="<b>Volumen</b>: %{y:,.0f}<extra></extra>"
            ),
            row=2, col=1
        )

    # 3. Superposición de Indicadores (si existen en el DataFrame y están activos)
    indicator_styles = {
        "ema_9": {"name": "EMA 9", "color": "#00bcd4", "width": 1.2},
        "ema_20": {"name": "EMA 20", "color": "#ffeb3b", "width": 1.2},
        "ema_50": {"name": "EMA 50", "color": "#ff9800", "width": 1.5},
        "ema_200": {"name": "EMA 200", "color": "#e91e63", "width": 2.0},
        "sma_50": {"name": "SMA 50", "color": "#9c27b0", "width": 1.5},
        "sma_200": {"name": "SMA 200", "color": "#3f51b5", "width": 2.0},
        "vwap": {"name": "VWAP", "color": "#00e676", "width": 1.5},
    }

    for ind_key, style in indicator_styles.items():
        if active_indicators.get(ind_key, False) and ind_key in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[ind_key],
                    name=style["name"],
                    line=dict(color=style["color"], width=style["width"]),
                    hovertemplate=f"<b>{style['name']}</b>: %{{y:,.4f}}<extra></extra>"
                ),
                row=1, col=1
            )

    # Bandas de Bollinger
    if active_indicators.get("bollinger", False) and "bb_upper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["bb_upper"],
                name="BB Superior",
                line=dict(color="rgba(120, 123, 134, 0.4)", width=1, dash="dash"),
                hoverinfo="skip"
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["bb_lower"],
                name="BB Inferior",
                line=dict(color="rgba(120, 123, 134, 0.4)", width=1, dash="dash"),
                fill="tonexty",
                fillcolor="rgba(41, 98, 255, 0.05)",
                hoverinfo="skip"
            ),
            row=1, col=1
        )
        if "bb_middle" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["bb_middle"],
                    name="BB Media (SMA 20)",
                    line=dict(color="rgba(255, 152, 0, 0.6)", width=1),
                    hovertemplate="<b>BB Media</b>: %{y:,.4f}<extra></extra>"
                ),
                row=1, col=1
            )

    # 4. Soportes y Resistencias
    for lvl in support_resistance_levels:
        lvl_price = lvl.get("price")
        lvl_type = lvl.get("type", "Nivel")
        color = THEME_COLORS["bullish"] if "soporte" in lvl_type.lower() else THEME_COLORS["bearish"]
        fig.add_hline(
            y=lvl_price,
            line_dash="dot",
            line_color=color,
            line_width=1.2,
            annotation_text=f"{lvl_type} (${lvl_price:,.2f})",
            annotation_position="bottom right",
            annotation_font_color=color,
            annotation_font_size=10,
            row=1, col=1
        )

    # 5. Señales del Sistema (BUY: flecha verde abajo; SELL: flecha roja arriba)
    if signals:
        buy_signals = [s for s in signals if "BUY" in s.get("type", "")]
        sell_signals = [s for s in signals if "SELL" in s.get("type", "")]

        if buy_signals:
            fig.add_trace(
                go.Scatter(
                    x=[s["timestamp"] for s in buy_signals],
                    y=[s["price"] * 0.996 for s in buy_signals],  # Ligeramente debajo
                    mode="markers",
                    name="Señal Sistema: COMPRA",
                    marker=dict(
                        symbol="triangle-up",
                        size=14,
                        color=THEME_COLORS["bullish"],
                        line=dict(width=1.5, color="#ffffff")
                    ),
                    customdata=[[s.get("type"), s.get("score", 0), s.get("reason", "")] for s in buy_signals],
                    hovertemplate=(
                        "<b>SEÑAL DEL SISTEMA: %{customdata[0]}</b><br>"
                        "<b>Precio</b>: $%{y:,.4f}<br>"
                        "<b>Score</b>: %{customdata[1]}/100<br>"
                        "<b>Razón</b>: %{customdata[2]}<extra></extra>"
                    )
                ),
                row=1, col=1
            )

        if sell_signals:
            fig.add_trace(
                go.Scatter(
                    x=[s["timestamp"] for s in sell_signals],
                    y=[s["price"] * 1.004 for s in sell_signals],  # Ligeramente arriba
                    mode="markers",
                    name="Señal Sistema: VENTA",
                    marker=dict(
                        symbol="triangle-down",
                        size=14,
                        color=THEME_COLORS["bearish"],
                        line=dict(width=1.5, color="#ffffff")
                    ),
                    customdata=[[s.get("type"), s.get("score", 0), s.get("reason", "")] for s in sell_signals],
                    hovertemplate=(
                        "<b>SEÑAL DEL SISTEMA: %{customdata[0]}</b><br>"
                        "<b>Precio</b>: $%{y:,.4f}<br>"
                        "<b>Score</b>: %{customdata[1]}/100<br>"
                        "<b>Razón</b>: %{customdata[2]}<extra></extra>"
                    )
                ),
                row=1, col=1
            )

    # 6. Operaciones Manuales del Usuario (Distinción visual clara con diamantes/estrellas)
    if user_trades:
        user_longs = [t for t in user_trades if t.get("side", "").upper() == "LONG"]
        user_shorts = [t for t in user_trades if t.get("side", "").upper() == "SHORT"]

        if user_longs:
            fig.add_trace(
                go.Scatter(
                    x=[t["timestamp"] for t in user_longs],
                    y=[t["entry_price"] for t in user_longs],
                    mode="markers",
                    name="Tu Operación: LONG",
                    marker=dict(
                        symbol="diamond",
                        size=13,
                        color="#ffd700",  # Dorado
                        line=dict(width=2, color="#000000")
                    ),
                    customdata=[[t.get("amount_usd", 0), t.get("shares", 0), t.get("status", "")] for t in user_longs],
                    hovertemplate=(
                        "<b>TU OPERACIÓN: LONG</b><br>"
                        "<b>Precio Entrada</b>: $%{y:,.4f}<br>"
                        "<b>Invertido</b>: $%{customdata[0]:,.2f}<br>"
                        "<b>Cantidad</b>: %{customdata[1]:.4f}<br>"
                        "<b>Estado</b>: %{customdata[2]}<extra></extra>"
                    )
                ),
                row=1, col=1
            )

        if user_shorts:
            fig.add_trace(
                go.Scatter(
                    x=[t["timestamp"] for t in user_shorts],
                    y=[t["entry_price"] for t in user_shorts],
                    mode="markers",
                    name="Tu Operación: SHORT",
                    marker=dict(
                        symbol="diamond",
                        size=13,
                        color="#e040fb",  # Magenta brillante
                        line=dict(width=2, color="#000000")
                    ),
                    customdata=[[t.get("amount_usd", 0), t.get("shares", 0), t.get("status", "")] for t in user_shorts],
                    hovertemplate=(
                        "<b>TU OPERACIÓN: SHORT</b><br>"
                        "<b>Precio Entrada</b>: $%{y:,.4f}<br>"
                        "<b>Invertido</b>: $%{customdata[0]:,.2f}<br>"
                        "<b>Cantidad</b>: %{customdata[1]:.4f}<br>"
                        "<b>Estado</b>: %{customdata[2]}<extra></extra>"
                    )
                ),
                row=1, col=1
            )

    # Configuración de diseño estilo terminal TradingView
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=THEME_COLORS["card_bg"],
        plot_bgcolor=THEME_COLORS["background"],
        margin=dict(l=50, r=50, t=30, b=30),
        height=620,
        dragmode="pan",
        hovermode="x unified",
        xaxis=dict(
            gridcolor=THEME_COLORS["border"],
            showgrid=True,
            rangeslider=dict(visible=False),
            linecolor=THEME_COLORS["border"]
        ),
        yaxis=dict(
            gridcolor=THEME_COLORS["border"],
            showgrid=True,
            side="right",
            linecolor=THEME_COLORS["border"],
            tickformat=",.2f"
        ),
        yaxis2=dict(
            gridcolor=THEME_COLORS["border"],
            showgrid=False,
            side="right",
            linecolor=THEME_COLORS["border"],
            showticklabels=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(30, 34, 45, 0.7)",
            bordercolor=THEME_COLORS["border"],
            borderwidth=1,
            font=dict(size=11, color=THEME_COLORS["text_primary"])
        )
    )

    return fig
