"""SQLite storage for the Volcanic Gas Plume Explorer.

One relative database file (``plume/plume.db``) opened through a thin
repository layer. Every page and every query goes through here so the
session guard, the schema and the query helpers live in exactly one place.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = APP_DIR / "plume.db"

# Key in app_meta holding the dataset reference date the seeded series ends on.
SERIES_ANCHOR_KEY = "series_anchor"

SCHEMA = """
CREATE TABLE IF NOT EXISTS vent (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    elevation_m INTEGER,
    latitude    REAL,
    longitude   REAL,
    status      TEXT NOT NULL CHECK (status IN ('active', 'resting')),
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS flux_reading (
    id                 INTEGER PRIMARY KEY,
    vent_id            INTEGER NOT NULL REFERENCES vent(id) ON DELETE CASCADE,
    observed_at        TEXT NOT NULL,
    so2_tonnes_per_day REAL NOT NULL CHECK (so2_tonnes_per_day >= 0),
    uncertainty_pct    REAL NOT NULL CHECK (uncertainty_pct >= 0),
    method             TEXT NOT NULL CHECK (method IN ('walking FTIR', 'UV camera', 'COSPEC')),
    observer           TEXT NOT NULL,
    UNIQUE (vent_id, observed_at)
);
CREATE INDEX IF NOT EXISTS ix_flux_vent_time ON flux_reading (vent_id, observed_at);

CREATE TABLE IF NOT EXISTS tremor_sample (
    id               INTEGER PRIMARY KEY,
    station_code     TEXT NOT NULL,
    recorded_at      TEXT NOT NULL,
    amplitude_um     REAL NOT NULL CHECK (amplitude_um >= 0),
    dominant_freq_hz REAL NOT NULL,
    UNIQUE (station_code, recorded_at)
);
CREATE INDEX IF NOT EXISTS ix_tremor_station_time ON tremor_sample (station_code, recorded_at);

CREATE TABLE IF NOT EXISTS user_account (
    id            INTEGER PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fumarole_note (
    id             INTEGER PRIMARY KEY,
    vent_id        INTEGER REFERENCES vent(id) ON DELETE SET NULL,
    fumarole_name  TEXT NOT NULL,
    temperature_c  REAL NOT NULL CHECK (temperature_c >= 0 AND temperature_c <= 1200),
    observed_at    TEXT NOT NULL,
    note_text      TEXT,
    author_email   TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_note_observed ON fumarole_note (observed_at DESC);

CREATE TABLE IF NOT EXISTS alert_episode (
    id         INTEGER PRIMARY KEY,
    vent_id    INTEGER NOT NULL REFERENCES vent(id) ON DELETE CASCADE,
    level      TEXT NOT NULL CHECK (level IN ('normal', 'advisory', 'watch', 'warning')),
    started_at TEXT NOT NULL,
    ended_at   TEXT,
    summary    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_episode_level ON alert_episode (level, started_at DESC);

CREATE TABLE IF NOT EXISTS app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def db_path() -> Path:
    """Database file location (env override keeps tests off the real file)."""
    override = os.environ.get("PLUME_DB_PATH", "").strip()
    return Path(override).expanduser() if override else DEFAULT_DB_PATH


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open a connection with row access by name and FKs enforced."""
    target = Path(path) if path is not None else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session():
    """Short-lived connection per Streamlit run: commit on success, roll back on error."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
