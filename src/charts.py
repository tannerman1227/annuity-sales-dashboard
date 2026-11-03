"""Plotly figures. No Streamlit imports, so the chart layer stays testable."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.constants import CHANNELS, PRODUCTS
from src.formatting import format_count, format_premium
from src.theme import (
    BRICK,
    CHANNEL_COLORS,
    FONT,
    GOLD,
    INK,
    LINE,
    MAP_SCALE,
    NAVY,
    PAPER,
    PRODUCT_COLORS,
    SERIF,
    SLATE,
    TEAL,
)

PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _base(fig: go.Figure, height: int, title: str | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        title=dict(
            text=title or "",
            font=dict(family=SERIF, size=18, color=NAVY),
            x=0,
            xanchor="left",
            pad=dict(b=6),
        ),
        margin=dict(l=8, r=12, t=72 if title else 42, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=INK, size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family=FONT),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE, zeroline=False, color=SLATE)
    fig.update_yaxes(gridcolor=LINE, zeroline=False, color=SLATE)
    return fig


def _empty(title: str | None, height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text="No policies in this view",
        showarrow=False,
        font=dict(family=FONT, size=14, color=SLATE),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _base(fig, height, title)


def chart_cumulative_ytd(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty("Year to date vs prior year", 420)
    fig = go.Figure()
    colors = {"current": NAVY, "prior": GOLD}
    dashes = {"current": "solid", "prior": "dash"}
    for role in ("prior", "current"):
        sl = frame[frame["role"] == role]
        if sl.empty:
            continue
        year = int(sl["year"].iloc[0])
        ending = float(sl["cumulative_premium"].iloc[-1])
        fig.add_scatter(
            x=sl["month_label"],
            y=sl["cumulative_premium"],
            name=f"{year} · {format_premium(ending)}",
            mode="lines+markers",
            line=dict(color=colors[role], width=2.6 if role == "current" else 2.2, dash=dashes[role]),
            marker=dict(size=7),
            customdata=sl["monthly_premium"],
            hovertemplate=(
                "%{x}<br>Cumulative %{y:$,.0f}<br>Month %{customdata:$,.0f}<extra>" + str(year) + "</extra>"
            ),
        )
    fig.update_yaxes(tickformat="$.3s", title=None)
    fig.update_layout(hovermode="x unified")
    return _base(fig, 430)


def chart_monthly(frame: pd.DataFrame) -> go.Figure:
    if frame.empty or float(frame["premium"].sum()) == 0:
        return _empty("Monthly issued premium", 420)
    fig = go.Figure()
    fig.add_bar(
        x=frame["month"],
        y=frame["premium"],
        name="Premium",
        marker_color=NAVY,
        customdata=frame["policies"],
        hovertemplate="%{x|%b %Y}<br>Premium %{y:$,.0f}<br>Policies %{customdata:,}<extra></extra>",
    )
    yoy = frame["yoy_pct"] if "yoy_pct" in frame else None
    if yoy is not None and yoy.notna().any():
        fig.add_scatter(
            x=frame["month"],
            y=frame["yoy_pct"],
            name="YoY growth",
            mode="lines+markers",
            line=dict(color=GOLD, width=2.4),
            marker=dict(size=6),
            yaxis="y2",
            hovertemplate="%{x|%b %Y}<br>YoY %{y:+.1%}<extra></extra>",
        )
    span_days = (frame["month"].max() - frame["month"].min()).days if len(frame) else 0
    dtick = "M6" if span_days > 800 else "M3" if span_days > 400 else "M1"
    fig.update_xaxes(tickformat="%b %Y", dtick=dtick)
    fig.update_layout(barmode="relative", hovermode="x unified")
    built = _base(fig, 440)
    axis = dict(tickformat="$.3s", gridcolor=LINE, zeroline=False, color=SLATE)
    built.update_layout(yaxis=axis)
    if yoy is not None and yoy.notna().any():
        # Set this after the base layout. update_yaxes() would restyle every y axis,
        # and a percent series labeled with a dollar SI format reads as milli-dollars.
        built.update_layout(
            yaxis2=dict(
                overlaying="y",
                side="right",
                tickformat="+.0%",
                showgrid=False,
                zeroline=False,
                color=GOLD,
            )
        )
    return built


def chart_mom(frame: pd.DataFrame) -> go.Figure:
    if frame.empty or "mom_pct" not in frame or frame["mom_pct"].notna().sum() == 0:
        return _empty("Month over month", 300)
    plot = frame.dropna(subset=["mom_pct"])
    colors = [TEAL if value >= 0 else BRICK for value in plot["mom_pct"]]
    fig = go.Figure()
    fig.add_bar(
        x=plot["month"],
        y=plot["mom_pct"],
        marker_color=colors,
        name="MoM",
        hovertemplate="%{x|%b %Y}<br>%{y:+.1%}<extra></extra>",
    )
    span_days = (plot["month"].max() - plot["month"].min()).days if len(plot) else 0
    dtick = "M6" if span_days > 800 else "M3" if span_days > 400 else "M1"
    fig.update_xaxes(tickformat="%b %Y", dtick=dtick)
    fig.add_hline(y=0, line_color=LINE, line_width=1)
    fig.update_layout(showlegend=False)
    built = _base(fig, 320, "Month-over-month change")
    built.update_layout(yaxis=dict(tickformat="+.0%", gridcolor=LINE, zeroline=False, color=SLATE))
    return built


def chart_product_mix(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty("By product", 380)
    total = float(frame["premium"].sum())
    fig = go.Figure(
        data=[
            go.Pie(
                labels=frame["product"],
                values=frame["premium"],
                sort=False,
                hole=0.68,
                marker=dict(
                    colors=[PRODUCT_COLORS.get(product, NAVY) for product in frame["product"]],
                    line=dict(color=PAPER, width=2),
                ),
                textinfo="none",
                hovertemplate="%{label}<br>%{customdata}<br>%{percent}<extra></extra>",
                customdata=[format_premium(value) for value in frame["premium"]],
                direction="clockwise",
            )
        ]
    )
    fig.update_layout(
        annotations=[
            dict(
                text=format_premium(total),
                x=0.5,
                y=0.54,
                showarrow=False,
                font=dict(family=SERIF, size=22, color=NAVY),
            ),
            dict(
                text="premium",
                x=0.5,
                y=0.44,
                showarrow=False,
                font=dict(family=FONT, size=12, color=SLATE),
            ),
        ],
        showlegend=True,
    )
    fig = _base(fig, 380, "By product")
    fig.update_layout(margin=dict(l=8, r=8, t=56, b=8))
    return fig


def chart_bars(frame: pd.DataFrame, label: str, title: str, color: str = NAVY) -> go.Figure:
    if frame.empty:
        return _empty(title, 380)
    ordered = frame.sort_values("premium", ascending=True)
    fig = go.Figure()
    fig.add_bar(
        x=ordered["premium"],
        y=ordered[label].astype(str),
        orientation="h",
        marker_color=color,
        text=[format_premium(value) for value in ordered["premium"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x:$,.0f}<extra></extra>",
    )
    fig.update_xaxes(tickformat="$.3s")
    fig.update_layout(
        yaxis=dict(categoryorder="array", categoryarray=list(ordered[label].astype(str))),
        margin=dict(l=8, r=72, t=52, b=8),
    )
    built = _base(fig, 380, title)
    built.update_layout(margin=dict(l=8, r=72, t=52, b=8))
    return built


def chart_product_channel(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty("Product by channel", 400)
    present = [product for product in PRODUCTS if product in set(frame["product"])]
    fig = go.Figure()
    for channel in CHANNELS:
        subset = frame[frame["channel"] == channel]
        if subset.empty:
            continue
        aligned = subset.set_index("product")["premium"]
        amounts = []
        for product in present:
            value = aligned.get(product, 0.0)
            amounts.append(0.0 if pd.isna(value) else float(value))
        fig.add_bar(
            name=channel,
            x=present,
            y=amounts,
            marker_color=CHANNEL_COLORS[channel],
            hovertemplate="%{x}<br>" + channel + "<br>%{y:$,.0f}<extra></extra>",
        )
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickformat="$.3s")
    return _base(fig, 400, "Premium by product and channel")


def chart_map(frame: pd.DataFrame) -> go.Figure:
    if frame.empty or float(frame["premium"].sum()) == 0:
        return _empty("Issued premium by state", 480)
    fig = go.Figure(
        data=[
            go.Choropleth(
                locations=frame["state"],
                z=frame["premium"],
                locationmode="USA-states",
                colorscale=MAP_SCALE,
                marker_line_color=PAPER,
                marker_line_width=0.6,
                colorbar=dict(title="", tickformat="$.2s", len=0.75, thickness=12),
                customdata=list(
                    zip(
                        [format_premium(value) for value in frame["premium"]],
                        [format_count(value) for value in frame["policies"]],
                        [f"{share:.1%}" for share in frame["share"]],
                        frame["region"],
                        strict=True,
                    )
                ),
                hovertemplate=(
                    "<b>%{location}</b> · %{customdata[3]}<br>"
                    "Premium %{customdata[0]}<br>"
                    "Policies %{customdata[1]}<br>"
                    "Share %{customdata[2]}<extra></extra>"
                ),
            )
        ]
    )
    fig.update_geos(scope="usa", projection_type="albers usa", bgcolor="rgba(0,0,0,0)", showlakes=False)
    fig.update_layout(geo=dict(bgcolor="rgba(0,0,0,0)"))
    built = _base(fig, 500)
    built.update_layout(margin=dict(l=0, r=0, t=52, b=0))
    return built


def chart_distributors(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty("Top distributors", 460)
    fig = go.Figure()
    for channel in CHANNELS:
        subset = frame[frame["channel"] == channel]
        if subset.empty:
            continue
        fig.add_bar(
            name=channel,
            y=subset["distributor_name"],
            x=subset["premium"],
            orientation="h",
            marker_color=CHANNEL_COLORS[channel],
            text=[format_premium(value) for value in subset["premium"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:$,.0f}<extra>" + channel + "</extra>",
        )
    fig.update_layout(barmode="stack", yaxis=dict(categoryorder="total ascending"))
    fig.update_xaxes(tickformat="$.3s")
    built = _base(fig, 480)
    built.update_layout(margin=dict(l=8, r=78, t=56, b=8))
    return built


def chart_profile(frame: pd.DataFrame, label: str, title: str) -> go.Figure:
    return chart_bars(frame, label, title, color=NAVY)


def chart_forecast(history: pd.Series, forecast: pd.DataFrame) -> go.Figure:
    if history.empty and forecast.empty:
        return _empty("Six-month outlook", 440)
    fig = go.Figure()
    if not forecast.empty:
        months = list(forecast["month"])
        upper = list(forecast["upper"])
        lower = list(forecast["lower"])
        fig.add_scatter(
            x=months + months[::-1],
            y=upper + lower[::-1],
            fill="toself",
            fillcolor="rgba(166, 124, 61, 0.16)",
            line=dict(width=0),
            name="± 1 residual SD",
            hoverinfo="skip",
        )
    if not history.empty:
        tail = history.iloc[-36:]
        fig.add_scatter(
            x=tail.index,
            y=tail.to_numpy(),
            name="Actual",
            mode="lines",
            line=dict(color=NAVY, width=2.5),
            hovertemplate="%{x|%b %Y}<br>%{y:$,.0f}<extra>Actual</extra>",
        )
    if not forecast.empty and not history.empty:
        bridge_x = [history.index[-1], *forecast["month"]]
        bridge_y = [float(history.iloc[-1]), *forecast["forecast"]]
        fig.add_scatter(
            x=bridge_x,
            y=bridge_y,
            name="Outlook",
            mode="lines+markers",
            line=dict(color=GOLD, width=2.5, dash="dash"),
            marker=dict(size=7),
            hovertemplate="%{x|%b %Y}<br>%{y:$,.0f}<extra>Outlook</extra>",
        )
    elif not forecast.empty:
        fig.add_scatter(
            x=forecast["month"],
            y=forecast["forecast"],
            name="Outlook",
            mode="lines+markers",
            line=dict(color=GOLD, width=2.5, dash="dash"),
        )
    fig.update_yaxes(tickformat="$.3s")
    fig.update_xaxes(tickformat="%b %Y")
    return _base(fig, 460)


def growth_class(value) -> str:
    if value is None or pd.isna(value):
        return "flat"
    if float(value) > 0.0005:
        return "up"
    if float(value) < -0.0005:
        return "down"
    return "flat"


def format_delta(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    klass = growth_class(value)
    arrow = {"up": "▲ ", "down": "▼ ", "flat": ""}[klass]
    return f"{arrow}{abs(float(value)):.1%}"
