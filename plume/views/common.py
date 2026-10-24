"""Helpers shared by the feature pages."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Callable, TypeVar

import streamlit as st

from lib import db, repository, ui

LOGGER = logging.getLogger("plume")
T = TypeVar("T")

WINDOWS: dict[str, int] = {"14 days": 14, "30 days": 30, "60 days": 60, "90 days": 90}
DEFAULT_WINDOW = "30 days"


def data_anchor() -> datetime:
    """End of every query window: the dataset's constant reference date.

    The seed anchors all readings to ``seed_data.REFERENCE_DATE`` and records it
    in ``app_meta``; windows are measured back from there so charts stay complete
    however long after seeding the app is opened.
    """
    with db.session() as conn:
        raw = db.get_meta(conn, db.SERIES_ANCHOR_KEY)
    if raw:
        return repository.from_db_time(raw)
    return ui.utc_now().replace(microsecond=0)


def window_bounds(days: int, end: datetime | None = None) -> tuple[datetime, datetime]:
    finish = (end or data_anchor()).replace(microsecond=0)
    return finish - timedelta(days=days), finish


def fetch(source: str, query: Callable[[], T]) -> T:
    """Run a guarded read; on a storage error show a retry instead of a stack trace."""
    try:
        return query()
    except sqlite3.Error:
        LOGGER.exception("failed loading %s", source)
        ui.error_state(f"Couldn't load {source}.", "Nothing was changed - retry the same query.")
        if st.button("Retry", key=f"retry_{source}"):
            st.rerun()
        st.stop()


def change_flag(current: float | None, previous: float | None, suffix: str = "vs prev") -> tuple[str, str]:
    """(label, tone) for a percentage change, or a neutral 'no prior' chip."""
    if not previous or current is None:
        return ("NO PRIOR READING", "neutral")
    pct = (current - previous) / previous * 100.0
    arrow = "▲" if pct >= 0 else "▼"
    return (f"{arrow} {abs(pct):.0f}% {suffix}", "accent" if pct >= 0 else "neutral")


def pct_change(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return (current - previous) / previous * 100.0
