"""Tremor amplitude trends: per-station raw series, 24-hour rolling mean, change strip."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from lib import charts, db, format as fmt, repository as repo, session, ui
from views import common


def _controls() -> dict[str, Any]:
    try:
        with db.session() as conn:
            stations = repo.station_codes(conn)
    except Exception:  # storage problems are reported by the page body
        stations = []
    with st.sidebar:
        st.markdown(
            '<div class="plume-eyebrow" style="margin-top:14px">Tremor filters</div>',
            unsafe_allow_html=True,
        )
        chosen = st.multiselect("Stations", stations, default=stations, key="tremor_stations")
        window = st.radio("Date window", list(common.WINDOWS), index=0, key="tremor_window")
    return {"stations": stations, "chosen": chosen, "window": window}


def _fetch(chosen: list[str], start, end, prev_start, prev_end) -> dict[str, Any]:
    with db.session() as conn:
        return {
            "frame": repo.tremor_frame(conn, chosen, start, end),
            "previous": repo.tremor_frame(conn, chosen, prev_start, prev_end),
            "latest": repo.latest_tremor_per_station(conn),
        }


def _mean(frame: pd.DataFrame) -> float | None:
    if frame.empty:
        return None
    value = frame["amplitude_um"].mean()
    return None if pd.isna(value) else float(value)


def render() -> None:
    _, filters = session.guard("Tremor trends", _controls)
    ui.topbar("Tremor trends")

    days = common.WINDOWS[filters["window"]]
    start, end = common.window_bounds(days)
    prev_start, prev_end = start - (end - start), start
    chosen: list[str] = filters["chosen"]

    ui.page_title(
        "Tremor amplitude trends",
        "RSAM amplitude per station in micrometres per second, sampled every three hours. "
        "The heavy line is the 24-hour rolling mean; the thin line is the raw sample.",
    )

    if not chosen:
        ui.empty_state(
            "No station selected",
            "Pick at least one station in the sidebar to draw a tremor series.",
            "All four stations are selected by default.",
        )
        return

    data = common.fetch("the tremor series", lambda: _fetch(chosen, start, end, prev_start, prev_end))
    frame: pd.DataFrame = data["frame"]
    previous: pd.DataFrame = data["previous"]

    if frame.empty:
        ui.empty_state(
            f"No tremor samples in the last {days} days",
            "The selected stations reported nothing in this window.",
            "Widen the date window in the sidebar or select another station.",
        )
        return

    peak = frame.loc[frame["amplitude_um"].idxmax()]
    cards = [
        ui.card(
            ui.kpi(
                "Window peak",
                fmt.fmt_amount(float(peak["amplitude_um"]), 2),
                "µm/s",
                flag=f"{peak['station_code']} STATION",
                tone="accent",
                meta=fmt.fmt_stamp(peak["recorded_at"]),
            ),
            0,
        ),
        ui.card(
            ui.kpi(
                "Window mean",
                fmt.fmt_amount(_mean(frame), 2),
                "µm/s",
                flag=f"{len(chosen)} STATIONS",
                tone="neutral",
                meta=f"{fmt.fmt_date(start)} to {fmt.fmt_date(end)}",
            ),
            1,
        ),
        ui.card(
            ui.kpi(
                "Samples",
                f"{len(frame):,}",
                "",
                flag="3-HOURLY CADENCE",
                tone="neutral",
                meta="Raw RSAM samples behind the chart",
            ),
            2,
        ),
    ]
    ui.markdown(ui.grid(cards))

    st.plotly_chart(charts.tremor_figure(frame), use_container_width=True, config=charts.PLOT_CONFIG)

    ui.section("Station summary", f"latest amplitude and change against the previous {days} days")
    summary_cards = []
    for index, station in enumerate(chosen):
        station_now = frame[frame["station_code"] == station]
        if station_now.empty:
            continue
        station_previous = previous[previous["station_code"] == station]
        latest_row = station_now.sort_values("recorded_at").iloc[-1]
        now_mean = _mean(station_now)
        prior_mean = _mean(station_previous)
        change = common.pct_change(now_mean or 0.0, prior_mean or 0.0)
        flag = "NO PRIOR WINDOW" if change is None else f"{'▲' if change >= 0 else '▼'} {abs(change):.0f}% VS PREV WINDOW"
        summary_cards.append(
            ui.card(
                ui.kpi(
                    f"{station} station",
                    fmt.fmt_amount(float(latest_row["amplitude_um"]), 2),
                    "µm/s",
                    flag=flag,
                    tone="neutral" if change is None or change < 0 else "accent",
                    meta=(
                        f"mean {fmt.fmt_amount(now_mean, 2)} µm/s · dominant "
                        f"{float(latest_row['dominant_freq_hz']):.1f} Hz · "
                        f"{fmt.fmt_stamp(latest_row['recorded_at'])}"
                    ),
                ),
                index,
            )
        )
    ui.markdown(ui.grid(summary_cards))
