"""Plotly figures. Colours are hex only - canvas libraries cannot read oklch()/var()."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from lib.theme import CHART_SERIES

PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
ROLLING_SAMPLES_24H = 8  # tremor samples arrive every 3 hours
# Shape carries the series as well as colour: six vents on one axis stay legible.
SERIES_MARKERS = ("circle", "square", "diamond", "triangle-up", "cross", "x")

# One layout for every figure: transparent paper, hairline grid, readable ticks.
BASE_LAYOUT: dict = {
    "colorway": list(CHART_SERIES),
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, sans-serif", "size": 13, "color": "#efeff5"},
    "margin": {"l": 10, "r": 14, "t": 34, "b": 10},
    "hovermode": "x unified",
    "hoverlabel": {
        "bgcolor": "#16161d",
        "bordercolor": "#2d2d34",
        "font": {"family": "Inter, sans-serif", "size": 12, "color": "#efeff5"},
    },
    "legend": {
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "x": 0,
        "font": {"size": 11, "color": "#9d9da6"},
        "bgcolor": "rgba(0,0,0,0)",
    },
    "xaxis": {
        "gridcolor": "#25252c",
        "zeroline": False,
        "linecolor": "#2d2d34",
        "tickfont": {"size": 11, "color": "#9d9da6"},
        "title": {"font": {"size": 11, "color": "#9d9da6"}},
    },
    "yaxis": {
        "gridcolor": "#25252c",
        "zeroline": False,
        "linecolor": "#2d2d34",
        "tickfont": {"size": 11, "color": "#9d9da6"},
        "title": {"font": {"size": 11, "color": "#9d9da6"}},
    },
}


def _finish(fig: go.Figure, height: int, y_title: str, x_title: str = "UTC date") -> go.Figure:
    fig.update_layout(**BASE_LAYOUT)
    fig.update_layout(
        height=height,
        yaxis_title=y_title,
        xaxis_title=x_title,
        showlegend=True,
    )
    fig.update_xaxes(showgrid=True, ticks="outside")
    fig.update_yaxes(rangemode="tozero")
    return fig


def flux_figure(frame: pd.DataFrame, single_vent: bool) -> go.Figure:
    """SO2 flux in tonnes/day; the uncertainty band only makes sense for one vent."""
    fig = go.Figure()
    if frame.empty:
        return _finish(fig, 380, "SO2 flux (t/day)")

    if single_vent:
        series = frame.sort_values("observed_at")
        upper = series["so2_tonnes_per_day"] * (1 + series["uncertainty_pct"] / 100.0)
        lower = series["so2_tonnes_per_day"] * (1 - series["uncertainty_pct"] / 100.0)
        fig.add_trace(
            go.Scatter(
                x=series["observed_at"],
                y=upper,
                mode="lines",
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=series["observed_at"],
                y=lower,
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(152,132,243,0.16)",
                name="Measurement uncertainty",
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=series["observed_at"],
                y=series["so2_tonnes_per_day"],
                mode="lines+markers",
                name="SO2 flux",
                line=dict(color=CHART_SERIES[0], width=2.4),
                marker=dict(size=5, color=CHART_SERIES[0]),
                hovertemplate="%{y:.1f} t/day<extra></extra>",
            )
        )
    else:
        for index, (label, group) in enumerate(frame.groupby("vent_label", sort=False)):
            ordered = group.sort_values("observed_at")
            color = CHART_SERIES[index % len(CHART_SERIES)]
            fig.add_trace(
                go.Scatter(
                    x=ordered["observed_at"],
                    y=ordered["so2_tonnes_per_day"],
                    mode="lines+markers",
                    name=label,
                    line=dict(color=color, width=2),
                    marker=dict(
                        size=5,
                        color=color,
                        symbol=SERIES_MARKERS[index % len(SERIES_MARKERS)],
                    ),
                    hovertemplate="%{y:.1f} t/day<extra>" + label + "</extra>",
                )
            )
    return _finish(fig, 400, "SO2 flux (t/day)")


def tremor_figure(frame: pd.DataFrame, rolling_label: str = "24h rolling mean") -> go.Figure:
    """Raw RSAM amplitude plus a 24-hour rolling mean per station."""
    fig = go.Figure()
    if frame.empty:
        return _finish(fig, 400, "Amplitude (µm/s)")

    for index, (station, group) in enumerate(frame.groupby("station_code", sort=True)):
        ordered = group.sort_values("recorded_at").copy()
        color = CHART_SERIES[index % len(CHART_SERIES)]
        rolling = (
            ordered.set_index("recorded_at")["amplitude_um"]
            .rolling(window=ROLLING_SAMPLES_24H, min_periods=3)
            .mean()
        )
        fig.add_trace(
            go.Scatter(
                x=ordered["recorded_at"],
                y=ordered["amplitude_um"],
                mode="lines",
                name=f"{station} raw",
                line=dict(color=color, width=1),
                opacity=0.38,
                showlegend=False,
                hovertemplate="%{y:.2f} µm/s<extra>" + station + " raw</extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=rolling.index,
                y=rolling.to_numpy(),
                mode="lines",
                name=f"{station} · {rolling_label}",
                line=dict(color=color, width=2.4),
                hovertemplate="%{y:.2f} µm/s<extra>" + station + " mean</extra>",
            )
        )
    return _finish(fig, 420, "RSAM amplitude (µm/s)")


def sparkline(x: pd.Series, y: pd.Series, height: int = 52) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            line=dict(color=CHART_SERIES[0], width=1.8),
            hoverinfo="skip",
            fill="tozeroy",
            fillcolor="rgba(152,132,243,0.10)",
        )
    )
    fig.update_layout(**BASE_LAYOUT)
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
