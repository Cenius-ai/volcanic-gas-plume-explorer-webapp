"""Shift-handover overview: current alert level, degassing snapshot, tremor strip."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import streamlit as st

from lib import charts, db, format as fmt, repository as repo, session, ui
from views import common


def _fetch() -> dict[str, Any]:
    now = common.data_anchor()
    with db.session() as conn:
        return {
            "flux": repo.latest_flux_per_vent(conn),
            "tremor": repo.latest_tremor_per_station(conn),
            "tremor_series": repo.tremor_frame(conn, None, now - timedelta(days=7), now),
            "episode": repo.current_episode(conn),
            "notes": repo.list_notes(conn, limit=1),
        }


def _banner(episode: dict[str, Any] | None) -> None:
    if episode is None:
        ui.empty_state(
            "No alert episodes on record",
            "This observatory has not logged an eruption episode yet.",
            "Episodes appear here as soon as the duty scientist publishes one.",
        )
        return
    state = "Ongoing" if not episode["ended_at"] else f"Ended {fmt.fmt_stamp(episode['ended_at'])}"
    ui.markdown(
        '<div class="plume-banner"><div>'
        '<div class="plume-eyebrow">Current alert level</div>'
        '<div style="display:flex;align-items:center;gap:10px;margin:6px 0 4px;flex-wrap:wrap">'
        f"{ui.badge(episode['level'])}"
        f'<h2 style="margin:0">{ui.esc(episode["vent_code"])} · {ui.esc(episode["vent_name"])}</h2></div>'
        f'<div class="plume-meta">{ui.esc(state)} · '
        f'{ui.esc(fmt.fmt_duration(episode["started_at"], episode["ended_at"]))} · '
        f'started {ui.esc(fmt.fmt_stamp(episode["started_at"]))}</div>'
        "</div>"
        '<div style="max-width:54ch"><div class="plume-meta">'
        f"{ui.esc(episode['summary'])}</div></div></div>"
    )


def _flux_cards(readings: list[dict[str, Any]]) -> None:
    if not readings:
        ui.empty_state(
            "No flux readings yet",
            "No crater vent has a SO2 measurement on file.",
            "Open SO2 flux by vent to widen the window or pick another vent.",
        )
        return
    cards = []
    for index, reading in enumerate(readings):
        flag, tone = common.change_flag(reading["so2_tonnes_per_day"], reading["previous_so2"])
        cards.append(
            ui.card(
                ui.kpi(
                    f"{reading['vent_code']} · {reading['vent_name']}",
                    fmt.fmt_amount(reading["so2_tonnes_per_day"]),
                    "t/day",
                    flag=flag,
                    tone=tone,
                    meta=(
                        f"{reading['method']} · {fmt.fmt_stamp(reading['observed_at'])} "
                        f"(±{reading['uncertainty_pct']:.0f}%)"
                    ),
                ),
                index,
            )
        )
    ui.markdown(ui.grid(cards))


def _tremor_strip(samples: list[dict[str, Any]], series) -> None:
    if not samples:
        ui.empty_state(
            "No tremor samples yet",
            "No station has reported an RSAM amplitude.",
            "Open Tremor trends to pick another station or window.",
        )
        return
    columns = st.columns(len(samples), gap="small")
    for column, sample in zip(columns, samples):
        with column:
            with st.container(border=True):
                ui.markdown(
                    ui.kpi(
                        f"{sample['station_code']} station",
                        fmt.fmt_amount(sample["amplitude_um"], 2),
                        "µm/s",
                        flag=f"{sample['dominant_freq_hz']:.1f} HZ DOMINANT",
                        tone="neutral",
                        meta=fmt.fmt_stamp(sample["recorded_at"]),
                    )
                )
                station_series = series[series["station_code"] == sample["station_code"]].sort_values(
                    "recorded_at"
                )
                if not station_series.empty:
                    st.plotly_chart(
                        charts.sparkline(station_series["recorded_at"], station_series["amplitude_um"]),
                        use_container_width=True,
                        config=charts.PLOT_CONFIG,
                    )
                    ui.markdown('<div class="plume-eyebrow">LAST 7 DAYS</div>')


def render() -> None:
    session.guard("Shift handover")
    ui.topbar("Shift handover")
    data = common.fetch("the observatory feed", _fetch)

    ui.page_title(
        "Shift handover",
        "The three things the next scientist needs: the current alert level, where the gas is "
        "degassing and how the plumbing is shaking.",
    )
    _banner(data["episode"])

    ui.section("Degassing snapshot", "latest SO2 flux per crater vent")
    _flux_cards(data["flux"])

    ui.section("Tremor now", "latest RSAM amplitude per station, with the last 7 days beneath")
    _tremor_strip(data["tremor"], data["tremor_series"])

    ui.section("Newest fumarole observation")
    notes = data["notes"]
    if notes:
        note = notes[0]
        ui.markdown(
            ui.card(
                ui.kpi(
                    note["fumarole_name"],
                    fmt.fmt_amount(note["temperature_c"]),
                    "°C",
                    flag=f"BY {note['author_email']}",
                    tone="neutral",
                    meta=(
                        f"{fmt.fmt_stamp(note['observed_at'])} · "
                        f"{note['note_text'] or 'No context recorded.'}"
                    ),
                )
            )
        )
    else:
        ui.empty_state(
            "No fumarole observations yet",
            "Nobody has logged a temperature reading yet.",
            "Open Fumarole notes to record the first observation.",
        )
