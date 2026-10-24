"""The single data-access layer used by every page and every query.

Pages never touch SQL directly: they call these helpers with an open
connection, which keeps the session-guarded read model in one place and makes
the same functions testable outside Streamlit.

Every statement below is a module-level constant. Optional filters are passed
as bound parameters (``?1 IS NULL OR ...``) and id/station/level lists are
passed as a bound JSON array read with ``json_each`` - no value, identifier or
fragment is ever interpolated into SQL text.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Iterable

import pandas as pd

LEVELS: tuple[str, ...] = ("normal", "advisory", "watch", "warning")
METHODS: tuple[str, ...] = ("walking FTIR", "UV camera", "COSPEC")
DB_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

VENTS_SQL = (
    "SELECT id, code, name, elevation_m, latitude, longitude, status, notes "
    "FROM vent ORDER BY elevation_m DESC"
)

FLUX_SQL = (
    "SELECT r.id, r.vent_id, v.code || ' - ' || v.name AS vent_label, r.observed_at, "
    "r.so2_tonnes_per_day, r.uncertainty_pct, r.method, r.observer "
    "FROM flux_reading r JOIN vent v ON v.id = r.vent_id "
    "WHERE (?1 IS NULL OR r.vent_id IN (SELECT value FROM json_each(?1))) "
    "AND (?2 IS NULL OR r.observed_at >= ?2) "
    "AND (?3 IS NULL OR r.observed_at <= ?3) "
    "ORDER BY r.observed_at ASC, r.vent_id ASC"
)

LATEST_FLUX_SQL = (
    "SELECT v.id AS vent_id, v.code AS vent_code, v.name AS vent_name, v.status, "
    "r.observed_at, r.so2_tonnes_per_day, r.uncertainty_pct, r.method, r.observer "
    "FROM vent v JOIN flux_reading r ON r.id = ("
    "SELECT id FROM flux_reading WHERE vent_id = v.id ORDER BY observed_at DESC LIMIT 1) "
    "ORDER BY v.elevation_m DESC"
)

PREVIOUS_FLUX_SQL = (
    "SELECT so2_tonnes_per_day FROM flux_reading WHERE vent_id = ? "
    "ORDER BY observed_at DESC LIMIT 2"
)

STATIONS_SQL = (
    "SELECT station_code, MAX(recorded_at) AS newest FROM tremor_sample "
    "GROUP BY station_code ORDER BY station_code"
)

TREMOR_SQL = (
    "SELECT id, station_code, recorded_at, amplitude_um, dominant_freq_hz "
    "FROM tremor_sample "
    "WHERE (?1 IS NULL OR station_code IN (SELECT value FROM json_each(?1))) "
    "AND (?2 IS NULL OR recorded_at >= ?2) "
    "AND (?3 IS NULL OR recorded_at <= ?3) "
    "ORDER BY recorded_at ASC, station_code ASC"
)

LATEST_TREMOR_SQL = (
    "SELECT station_code, recorded_at, amplitude_um, dominant_freq_hz FROM tremor_sample t "
    "WHERE recorded_at = ("
    "SELECT MAX(recorded_at) FROM tremor_sample WHERE station_code = t.station_code) "
    "ORDER BY station_code"
)

NOTES_SQL = (
    "SELECT n.id, n.fumarole_name, n.temperature_c, n.observed_at, n.note_text, "
    "n.author_email, n.created_at, v.code AS vent_code, v.name AS vent_name "
    "FROM fumarole_note n LEFT JOIN vent v ON v.id = n.vent_id "
    "ORDER BY n.observed_at DESC, n.id DESC LIMIT ?"
)

INSERT_NOTE_SQL = (
    "INSERT INTO fumarole_note "
    "(vent_id, fumarole_name, temperature_c, observed_at, note_text, author_email, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)

DELETE_NOTE_SQL = "DELETE FROM fumarole_note WHERE id = ? AND author_email = ?"

EPISODES_SQL = (
    "SELECT e.id, e.level, e.started_at, e.ended_at, e.summary, e.created_at, "
    "v.id AS vent_id, v.code AS vent_code, v.name AS vent_name "
    "FROM alert_episode e JOIN vent v ON v.id = e.vent_id "
    "WHERE (?1 IS NULL OR e.level IN (SELECT value FROM json_each(?1))) "
    "ORDER BY e.started_at DESC, e.id DESC"
)

CURRENT_EPISODE_SQL = (
    "SELECT e.id, e.level, e.started_at, e.ended_at, e.summary, "
    "v.id AS vent_id, v.code AS vent_code, v.name AS vent_name "
    "FROM alert_episode e JOIN vent v ON v.id = e.vent_id "
    "ORDER BY e.started_at DESC, e.id DESC LIMIT 1"
)


def to_db_time(moment: datetime) -> str:
    """Store UTC timestamps as sortable ISO-8601 text (no timezone suffix)."""
    return moment.replace(tzinfo=None, microsecond=0).strftime(DB_TIME_FORMAT)


def from_db_time(text: str) -> datetime:
    return datetime.strptime(text, DB_TIME_FORMAT)


def vent_label(vent: dict[str, Any] | sqlite3.Row) -> str:
    return f"{vent['code']} - {vent['name']}"


def _id_param(values: Iterable[Any] | None) -> str | None:
    """Bound JSON array for an IN-list, or None when the filter is inactive."""
    items = list(values or [])
    return json.dumps(items) if items else None


# --------------------------------------------------------------------------- vents


def list_vents(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(VENTS_SQL).fetchall()]


# --------------------------------------------------------------------------- flux


def flux_frame(
    conn: sqlite3.Connection,
    vent_ids: Iterable[int] | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> pd.DataFrame:
    """SO2 flux readings for one vent or several, inside a start/end window."""
    params = (
        _id_param(vent_ids),
        to_db_time(start) if start is not None else None,
        to_db_time(end) if end is not None else None,
    )
    frame = pd.read_sql_query(FLUX_SQL, conn, params=params)
    if not frame.empty:
        frame["observed_at"] = pd.to_datetime(frame["observed_at"])
    return frame


def latest_flux_per_vent(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Newest reading plus the one before it, per vent (for the change arrow)."""
    latest = [dict(row) for row in conn.execute(LATEST_FLUX_SQL).fetchall()]
    for reading in latest:
        recent = conn.execute(
            PREVIOUS_FLUX_SQL, (reading["vent_id"],)
        ).fetchall()
        reading["previous_so2"] = float(recent[1]["so2_tonnes_per_day"]) if len(recent) > 1 else None
        reading["observed_at_dt"] = from_db_time(reading["observed_at"])
    return latest


# ------------------------------------------------------------------------- tremor


def station_codes(conn: sqlite3.Connection) -> list[str]:
    return [row["station_code"] for row in conn.execute(STATIONS_SQL).fetchall()]


def tremor_frame(
    conn: sqlite3.Connection,
    stations: Iterable[str] | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> pd.DataFrame:
    params = (
        _id_param(stations),
        to_db_time(start) if start is not None else None,
        to_db_time(end) if end is not None else None,
    )
    frame = pd.read_sql_query(TREMOR_SQL, conn, params=params)
    if not frame.empty:
        frame["recorded_at"] = pd.to_datetime(frame["recorded_at"])
    return frame


def latest_tremor_per_station(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(LATEST_TREMOR_SQL).fetchall()]


# ------------------------------------------------------------------ fumarole notes


def list_notes(conn: sqlite3.Connection, limit: int = 60) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(NOTES_SQL, (int(limit),)).fetchall()]


def create_note(
    conn: sqlite3.Connection,
    *,
    vent_id: int | None,
    fumarole_name: str,
    temperature_c: float,
    observed_at: datetime,
    note_text: str,
    author_email: str,
    created_at: datetime,
) -> int:
    cursor = conn.execute(
        INSERT_NOTE_SQL,
        (
            vent_id,
            fumarole_name.strip(),
            float(temperature_c),
            to_db_time(observed_at),
            note_text.strip(),
            author_email,
            to_db_time(created_at),
        ),
    )
    return int(cursor.lastrowid)


def delete_note(conn: sqlite3.Connection, note_id: int, author_email: str) -> bool:
    """Owner-scoped delete: another analyst's note id simply matches nothing."""
    cursor = conn.execute(DELETE_NOTE_SQL, (note_id, author_email))
    return cursor.rowcount > 0


# ------------------------------------------------------------------------- alerts


def list_episodes(conn: sqlite3.Connection, levels: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Episodes for the selected levels; ``None`` means every level."""
    selected = [level for level in levels or [] if level in LEVELS]
    if levels is not None and not selected:
        return []
    param = _id_param(selected)
    return [dict(row) for row in conn.execute(EPISODES_SQL, (param,)).fetchall()]


def current_episode(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(CURRENT_EPISODE_SQL).fetchone()
    return dict(row) if row else None
