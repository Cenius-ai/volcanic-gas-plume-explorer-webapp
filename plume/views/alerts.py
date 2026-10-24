"""Eruption alert episodes with a level filter, live count and per-episode detail."""

from __future__ import annotations

from typing import Any

import streamlit as st

from lib import db, format as fmt, repository as repo, session, ui
from views import common

LEVEL_HELP = {
    "normal": "Background activity.",
    "advisory": "Minor unrest; the vent is watched more closely.",
    "watch": "Escalating unrest that could lead to an eruption.",
    "warning": "Eruption under way or imminent.",
}


def _select_all_levels() -> None:
    st.session_state["alert_levels"] = list(repo.LEVELS)


def _controls() -> dict[str, Any]:
    with st.sidebar:
        st.markdown(
            '<div class="plume-eyebrow" style="margin-top:14px">Alert filters</div>',
            unsafe_allow_html=True,
        )
        levels = st.multiselect(
            "Alert level",
            list(repo.LEVELS),
            default=list(repo.LEVELS),
            key="alert_levels",
        )
    return {"levels": levels}


def _fetch(levels: list[str]) -> list[dict[str, Any]]:
    with db.session() as conn:
        return repo.list_episodes(conn, levels)


def _truncate(text: str, limit: int = 90) -> str:
    clean = " ".join((text or "").split())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def render() -> None:
    _, filters = session.guard("Alert episodes", _controls)
    ui.topbar("Alert episodes")

    levels: list[str] = filters["levels"]
    ui.page_title(
        "Eruption alert episodes",
        "The curated catalogue of alert-level episodes for the Kawah Ratu complex. "
        "Read-only: episodes are published by the observatory, not edited here.",
    )

    episodes = common.fetch("the alert episode catalogue", lambda: _fetch(levels))

    if not levels:
        ui.empty_state(
            "No alert level selected",
            "The filter excludes every level, so no episode can match.",
            "Select at least one level in the sidebar to see episodes.",
        )
        st.button("Select all levels", on_click=_select_all_levels, key="alert_select_all")
        return

    if not episodes:
        ui.empty_state(
            "No episodes match these filters",
            f"None of the selected levels ({', '.join(levels)}) has an episode on record.",
            "Add another level in the sidebar to widen the search.",
        )
        return

    count_label = "1 episode" if len(episodes) == 1 else f"{len(episodes)} episodes"
    ui.section(count_label, f"levels: {', '.join(levels)}")

    rows = []
    for episode in episodes:
        rows.append(
            [
                ui.badge(episode["level"]),
                f'{ui.esc(episode["vent_code"])} · {ui.esc(episode["vent_name"])}',
                ui.esc(fmt.fmt_stamp(episode["started_at"])),
                ui.esc(fmt.fmt_stamp(episode["ended_at"])) if episode["ended_at"] else "Ongoing",
                f'<span class="num">{ui.esc(fmt.fmt_duration(episode["started_at"], episode["ended_at"]))}</span>',
                ui.esc(_truncate(episode["summary"])),
            ]
        )
    ui.data_table(
        [
            ("Level", "left"),
            ("Vent", "left"),
            ("Started", "left"),
            ("Ended", "left"),
            ("Duration", "left"),
            ("Summary", "dim"),
        ],
        rows,
    )

    ui.section("Episode detail", "expand an episode for the full summary")
    for episode in episodes:
        header = (
            f"{episode['level'].upper()} · {episode['vent_code']} · "
            f"{fmt.fmt_date(episode['started_at'])}"
        )
        with st.expander(header):
            ui.markdown(
                f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px">'
                f"{ui.badge(episode['level'])}"
                f'<span class="plume-meta">{ui.esc(LEVEL_HELP.get(episode["level"], ""))}</span></div>'
                f'<div class="plume-meta">Vent: <b>{ui.esc(episode["vent_code"])} · '
                f'{ui.esc(episode["vent_name"])}</b> · started {ui.esc(fmt.fmt_stamp(episode["started_at"]))}'
                f" · "
                f'{"ongoing" if not episode["ended_at"] else "ended " + ui.esc(fmt.fmt_stamp(episode["ended_at"]))}'
                f' · duration {ui.esc(fmt.fmt_duration(episode["started_at"], episode["ended_at"]))}</div>'
                f'<p style="margin-top:10px">{ui.esc(episode["summary"])}</p>'
            )
