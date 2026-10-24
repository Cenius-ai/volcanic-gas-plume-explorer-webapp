"""SO2 flux per crater vent: uncertainty band, all-vents overlay, weekly takeaway."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd
import streamlit as st

from lib import charts, db, format as fmt, repository as repo, session, ui
from lib.theme import CHART_SERIES
from views import common


def _controls() -> dict[str, Any]:
    try:
        with db.session() as conn:
            vents = repo.list_vents(conn)
    except Exception:  # the page body reports storage failures with a retry
        vents = []
    labels = ["All vents"] + [repo.vent_label(vent) for vent in vents]
    with st.sidebar:
        st.markdown(
            '<div class="plume-eyebrow" style="margin-top:14px">Flux filters</div>',
            unsafe_allow_html=True,
        )
        choice = st.selectbox("Crater vent", labels, index=0, key="flux_vent")
        window = st.radio("Date window", list(common.WINDOWS), index=1, key="flux_window")
    return {"choice": choice, "window": window, "vents": vents}


def _fetch(vent_ids: list[int], start, end) -> dict[str, Any]:
    with db.session() as conn:
        return {"frame": repo.flux_frame(conn, vent_ids, start, end)}


def _mean(frame: pd.DataFrame) -> float | None:
    if frame.empty:
        return None
    value = frame["so2_tonnes_per_day"].mean()
    return None if pd.isna(value) else float(value)


def _takeaway(frame: pd.DataFrame, label: str, end) -> str:
    recent_window = frame[frame["observed_at"] >= (end - timedelta(days=7))]
    prior_window = frame[
        (frame["observed_at"] >= (end - timedelta(days=14)))
        & (frame["observed_at"] < (end - timedelta(days=7)))
    ]
    recent, prior = _mean(recent_window), _mean(prior_window)
    if recent is None:
        return f"No readings for {label} in the last 7 days."
    if prior is None:
        return (
            f"{label} averaged {fmt.fmt_amount(recent)} t/day over the last 7 days. "
            "No readings exist for the prior week, so no comparison is possible."
        )
    delta = (recent - prior) / prior * 100.0
    direction = "higher than" if delta >= 0 else "lower than"
    return (
        f"{label} averaged {fmt.fmt_amount(recent)} t/day over the last 7 days, "
        f"{abs(delta):.0f}% {direction} the prior week ({fmt.fmt_amount(prior)} t/day)."
    )


def _headline(ordered: pd.DataFrame, single: bool) -> dict[str, Any]:
    """The single reading the KPI card and caption speak about."""
    if single:
        latest = ordered.iloc[-1]
        previous = float(ordered.iloc[-2]["so2_tonnes_per_day"]) if len(ordered) > 1 else None
        return {
            "label": "Latest reading",
            "row": latest,
            "previous": previous,
            "flag": None,
            "meta": f"{latest['method']} · {fmt.fmt_stamp(latest['observed_at'])}",
            "caption": (
                f"Latest traverse at {latest['vent_label']} · {latest['method']} · "
                f"{fmt.fmt_stamp(latest['observed_at'])} · uncertainty ±{latest['uncertainty_pct']:.1f}% · "
                f"observer {latest['observer']}"
            ),
        }

    per_vent = ordered.sort_values("observed_at").groupby("vent_label", sort=False).tail(1)
    hottest = per_vent.sort_values("so2_tonnes_per_day", ascending=False).iloc[0]
    newest = ordered["observed_at"].max()
    return {
        "label": "Highest vent now",
        "row": hottest,
        "previous": None,
        "flag": f"{len(per_vent)} VENTS REPORTING",
        "meta": f"{hottest['vent_label']} · {fmt.fmt_stamp(hottest['observed_at'])}",
        "caption": (
            f"Newest traverse in the window {fmt.fmt_stamp(newest)} · "
            f"{len(per_vent)} vents reporting · highest is {hottest['vent_label']} at "
            f"{fmt.fmt_amount(float(hottest['so2_tonnes_per_day']))} t/day"
        ),
    }


def render() -> None:
    _, filters = session.guard("SO2 flux by vent", _controls)
    ui.topbar("SO2 flux by vent")

    vents = filters["vents"]
    days = common.WINDOWS[filters["window"]]
    start, end = common.window_bounds(days)
    single = filters["choice"] != "All vents"
    selected = next((vent for vent in vents if repo.vent_label(vent) == filters["choice"]), None)
    if single and selected is None:
        single = False
    vent_ids = [selected["id"]] if single else [vent["id"] for vent in vents]
    label = repo.vent_label(selected) if single else "All crater vents"

    ui.page_title(
        "SO2 flux per crater vent",
        "Walking FTIR, UV camera and COSPEC traverses in tonnes of sulphur dioxide per day. "
        "The shaded band is the measurement uncertainty on the selected vent.",
    )

    data = common.fetch("the SO2 flux series", lambda: _fetch(vent_ids, start, end))
    frame: pd.DataFrame = data["frame"]

    if frame.empty:
        ui.empty_state(
            f"No readings for {label} in the last {days} days",
            "The selected window contains no SO2 traverses for this vent.",
            "Widen the date window in the sidebar or pick a different crater vent.",
        )
        return

    ordered = frame.sort_values("observed_at")
    headline = _headline(ordered, single)
    row = headline["row"]
    recent_mean = _mean(ordered[ordered["observed_at"] >= (end - timedelta(days=7))])
    flag, tone = common.change_flag(
        float(row["so2_tonnes_per_day"]), headline["previous"], "vs prev traverse"
    )
    if headline["flag"]:
        flag, tone = headline["flag"], "neutral"

    cards = [
        ui.card(
            ui.kpi(
                headline["label"],
                fmt.fmt_amount(float(row["so2_tonnes_per_day"])),
                "t/day",
                flag=flag,
                tone=tone,
                meta=headline["meta"],
            ),
            0,
        ),
        ui.card(
            ui.kpi(
                "7-day mean",
                fmt.fmt_amount(recent_mean),
                "t/day",
                flag=f"{len(ordered)} TRAVERSES IN WINDOW",
                tone="neutral",
                meta=f"{fmt.fmt_date(start)} to {fmt.fmt_date(end)}",
            ),
            1,
        ),
        ui.card(
            ui.kpi(
                "Uncertainty",
                f"±{float(row['uncertainty_pct']):.1f}",
                "%",
                flag="SHADED ON CHART" if single else "PER TRACE, NOT SHOWN",
                tone="neutral",
                meta="1-sigma uncertainty reported with each traverse",
            ),
            2,
        ),
        ui.card(
            ui.kpi(
                "Vents reporting",
                str(int(frame["vent_id"].nunique())),
                "",
                flag="OF 6 MONITORED",
                tone="neutral",
                meta="Crater vents with at least one traverse",
            ),
            3,
        ),
    ]
    ui.markdown(ui.grid(cards))

    st.plotly_chart(
        charts.flux_figure(ordered, single_vent=single),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
    )
    ui.markdown(
        f'<div class="plume-meta" style="margin-top:-6px">{ui.esc(headline["caption"])}</div>'
    )

    ui.markdown(
        '<div class="plume-card" style="margin-top:14px;border-left:3px solid var(--accent)">'
        '<div class="plume-eyebrow">Takeaway</div>'
        f'<div style="margin-top:5px;font-size:14px">{ui.esc(_takeaway(ordered, label, end))}</div>'
        "</div>"
    )

    with st.expander("How this chart is built"):
        ui.markdown(
            '<div class="plume-meta">Each point is one traverse; the shaded band is the '
            "reported 1-sigma uncertainty around the flux value. In <em>All vents</em> mode one "
            "line per crater vent is drawn with a legend and the band is dropped for legibility. "
            "The takeaway compares the mean of the last 7 days with the 7 days before it. Series "
            f"colours come from the committed chart palette "
            f"({', '.join(CHART_SERIES[:4])}).</div>"
        )
