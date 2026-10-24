"""Deterministic, idempotent seed for the Volcanic Gas Plume Explorer.

Run it directly (``python3 plume/seed_data.py``) or let the app call
``ensure_seeded()`` on its boot path. Re-running never duplicates a row and
never raises a unique-constraint error: static catalogue rows use
``INSERT OR IGNORE`` on their natural keys, and the instrument series is
regenerated only when the stored reference date differs from ``REFERENCE_DATE``.

Every timestamp is derived from the fixed ``REFERENCE_DATE`` constant below, so
the 90-day series is identical on every machine and the charts are complete the
moment the app opens - no "wait a few days for data" empty state.
"""

from __future__ import annotations

import hashlib
import math
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import auth, db  # noqa: E402
from lib.repository import METHODS, to_db_time  # noqa: E402

SERIES_DAYS = 90
FLUX_STEP_DAYS = 2
TREMOR_STEP_HOURS = 3
ANCHOR_KEY = db.SERIES_ANCHOR_KEY

# Constant reference date the whole seeded series is anchored to (UTC, on the
# 3-hour tremor grid). Fixed on purpose: deterministic timestamps everywhere.
REFERENCE_DATE = datetime(2026, 10, 24, 9, 0, 0)

DEMO_EMAIL = auth.DEMO_EMAIL
DEMO_PASSWORD = auth.DEMO_PASSWORD
DUTY_EMAIL = "analyst@plume.app"
DUTY_PASSWORD = "plume-analyst"

OBSERVERS = ("A. Reyes", "M. Tanaka", "L. Okonkwo", "S. Halim", "R. Ferreira")

VENTS = [
    ("B1", "North Vent", 1142, -6.1215, 105.4231, "active",
     "Open vent on the north rim; steady low-pressure degassing with a visible plume."),
    ("B2", "Sulphur Shelf", 1108, -6.1231, 105.4202, "resting",
     "Sintered shelf with weak diffuse emission and scattered sulphur crusts."),
    ("K1", "Kawah Domas", 985, -6.1310, 105.4188, "active",
     "Fumarole field on the southwest floor; mud pools and warm ground."),
    ("[redacted]", "Kawah Ratu", 1220, -6.1190, 105.4250, "active",
     "Central crater vent driving the current degassing episode."),
    ("S1", "South Crater Fissure", 1054, -6.1342, 105.4211, "active",
     "Fissure swarm on the south flank; intermittent puffing observed."),
    ("S2", "Twin Ponds", 1012, -6.1288, 105.4305, "resting",
     "Two acid ponds with diffuse bubbling and low SO2 output."),
]

# Baselines in tonnes/day, chosen so the six vents never look like copies.
FLUX_BASE = {"B1": 148.0, "B2": 92.0, "K1": 61.0, "[redacted]": 214.0, "S1": 38.0, "S2": 77.0}

STATIONS = [
    ("MAL", "Malabar Ridge", 4.2),
    ("LMB", "Lembang Bench", 2.6),
    ("KRA", "Kawah Ratu Rim", 6.8),
    ("TNG", "Tangkuban Flank", 3.4),
]

FUMAROLE_SEED = [
    ("F2 - Sulphur Shelf", "B2", 213.5, 26,
     "Crust cracking across the shelf; strong sulphur odour, no visible plume change."),
    ("F1 - North Fissure", "B1", 168.0, 9,
     "Steady roaring gas jet. Thermocouple reading stable within 2 C across three probes."),
    ("F4 - Ratu Terrace", "[redacted]", 312.4, 4,
     "Temperature up 18 C since last week, consistent with the elevated SO2 flux."),
    ("F3 - Domas Pool", "K1", 96.5, 51,
     "Pool edge steaming gently; water clear with light sulphur film."),
    ("F6 - Malabar Crack", None, 121.8, 74,
     "New hairline crack on the walking route - logged for the trail team to flag."),
    ("F5 - Twin Ponds Seep", "S2", 88.2, 118,
     "Bubbling rate unchanged. Ground around the seep is warm but dry."),
]

EPISODE_SEED = [
    ("[redacted]", "warning", 6, None,
     "Continuous ash venting from Kawah Ratu with incandescent ejecta at night. "
     "SO2 flux running near three times the 90-day baseline and tremor amplitude "
     "2.4x background. Exclusion zone extended to 2.5 km from the summit."),
    ("B1", "watch", 38, 26,
     "Elevated degassing at North Vent: repeated UV-camera transects returned "
     "220-260 t/d against a baseline near 150 t/d. Plume drifted north over the "
     "deserted upper trail. No ash observed."),
    ("S1", "advisory", 61, 58,
     "Short-lived puffing sequence on the south fissure, felt as a light tremor "
     "at the Lembang bench station. Gas ratios returned to background within a day."),
    ("B2", "normal", 84, 78,
     "Routine survey of the sulphur shelf after a small rockfall closed the west "
     "approach. No change in fumarole temperatures or plume height recorded."),
]


def _unit(*parts: object) -> float:
    """Deterministic pseudo-random value in [0, 1) for the given parts."""
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _anchor(now: datetime | None = None) -> datetime:
    """End of the seeded window: always the constant reference date unless a caller overrides it."""
    if now is None:
        return REFERENCE_DATE
    moment = now.replace(tzinfo=None, minute=0, second=0, microsecond=0)
    return moment.replace(hour=(moment.hour // TREMOR_STEP_HOURS) * TREMOR_STEP_HOURS)


def _seed_vents(conn: sqlite3.Connection) -> None:
    for code, name, elevation, lat, lon, status, notes in VENTS:
        conn.execute(
            "INSERT OR IGNORE INTO vent (code, name, elevation_m, latitude, longitude, status, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, name, elevation, lat, lon, status, notes),
        )


def _seed_users(conn: sqlite3.Connection, anchor: datetime) -> None:
    created_at = to_db_time(anchor - timedelta(days=120))
    auth.upsert_user(conn, DEMO_EMAIL, DEMO_PASSWORD, "Cenius Demo Analyst", created_at)
    auth.upsert_user(conn, DUTY_EMAIL, DUTY_PASSWORD, "Dr. Anika Reyes", created_at)


def _seed_flux(conn: sqlite3.Connection, anchor: datetime) -> None:
    conn.execute("DELETE FROM flux_reading")
    vent_ids = {row["code"]: row["id"] for row in conn.execute("SELECT id, code FROM vent")}
    rows = []
    steps = (SERIES_DAYS // FLUX_STEP_DAYS)
    for index, code in enumerate(FLUX_BASE):
        base = FLUX_BASE[code]
        phase = _unit(code, "phase") * math.tau
        for step in range(steps + 1):
            observed_at = anchor - timedelta(days=FLUX_STEP_DAYS * step, hours=index % 4)
            swing = 0.25 * math.sin(math.tau * step / 26 + phase)
            drift = 0.15 * math.sin(math.tau * step / SERIES_DAYS + phase / 2)
            jitter = 0.12 * (_unit(code, step, "flux") - 0.5) * 2
            value = base * (1 + swing + drift + jitter)
            if code == "[redacted]" and step < 4:  # the ongoing episode shows in the series
                value *= 1.35
            uncertainty = 8.0 + 11.0 * _unit(code, step, "unc")
            rows.append(
                (
                    vent_ids[code],
                    to_db_time(observed_at),
                    round(value, 1),
                    round(uncertainty, 1),
                    METHODS[(index + step) % len(METHODS)],
                    OBSERVERS[step % len(OBSERVERS)],
                )
            )
    conn.executemany(
        "INSERT OR IGNORE INTO flux_reading "
        "(vent_id, observed_at, so2_tonnes_per_day, uncertainty_pct, method, observer) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def _seed_tremor(conn: sqlite3.Connection, anchor: datetime) -> None:
    conn.execute("DELETE FROM tremor_sample")
    rows = []
    steps = (SERIES_DAYS * 24) // TREMOR_STEP_HOURS
    for code, _label, base in STATIONS:
        for step in range(steps + 1):
            recorded_at = anchor - timedelta(hours=TREMOR_STEP_HOURS * step)
            hour_of_day = recorded_at.hour
            daily = 0.18 * math.sin(math.tau * (hour_of_day - 8) / 24)
            jitter = 0.10 * (_unit(code, step, "amp") - 0.5) * 2
            spike = 1.9 if _unit(code, step, "spike") > 0.965 else 1.0
            amplitude = base * (1 + daily + jitter) * spike
            if code == "KRA" and step < 16:  # borehole station tracks the warning
                amplitude *= 1.4
            frequency = 0.8 + 2.4 * _unit(code, step, "freq")
            rows.append(
                (
                    code,
                    to_db_time(recorded_at),
                    round(max(amplitude, 0.05), 2),
                    round(frequency, 2),
                )
            )
    conn.executemany(
        "INSERT OR IGNORE INTO tremor_sample (station_code, recorded_at, amplitude_um, dominant_freq_hz) "
        "VALUES (?, ?, ?, ?)",
        rows,
    )


def _seed_notes(conn: sqlite3.Connection, anchor: datetime) -> None:
    vent_ids = {row["code"]: row["id"] for row in conn.execute("SELECT id, code FROM vent")}
    for index, (name, vent_code, temperature, hours_ago, text) in enumerate(FUMAROLE_SEED):
        observed_at = anchor - timedelta(hours=hours_ago)
        author = DEMO_EMAIL if index % 2 == 0 else DUTY_EMAIL
        exists = conn.execute(
            "SELECT id FROM fumarole_note WHERE fumarole_name = ? AND observed_at = ?",
            (name, to_db_time(observed_at)),
        ).fetchone()
        if exists is not None:
            continue
        conn.execute(
            "INSERT INTO fumarole_note "
            "(vent_id, fumarole_name, temperature_c, observed_at, note_text, author_email, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                vent_ids.get(vent_code),
                name,
                temperature,
                to_db_time(observed_at),
                text,
                author,
                to_db_time(anchor),
            ),
        )


def _seed_episodes(conn: sqlite3.Connection, anchor: datetime) -> None:
    vent_ids = {row["code"]: row["id"] for row in conn.execute("SELECT id, code FROM vent")}
    for vent_code, level, started_days, ended_days, summary in EPISODE_SEED:
        started_at = to_db_time(anchor - timedelta(days=started_days))
        exists = conn.execute(
            "SELECT id FROM alert_episode WHERE vent_id = ? AND level = ? AND started_at = ?",
            (vent_ids[vent_code], level, started_at),
        ).fetchone()
        if exists is not None:
            continue
        ended_at = None if ended_days is None else to_db_time(anchor - timedelta(days=ended_days))
        conn.execute(
            "INSERT INTO alert_episode (vent_id, level, started_at, ended_at, summary, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (vent_ids[vent_code], level, started_at, ended_at, summary, started_at),
        )


def seed(conn: sqlite3.Connection, now: datetime | None = None) -> None:
    """Create the schema and fill it. Safe to call on every boot."""
    db.init_schema(conn)
    anchor = _anchor(now)
    _seed_vents(conn)
    _seed_users(conn, anchor)
    _seed_episodes(conn, anchor)
    _seed_notes(conn, anchor)

    if db.get_meta(conn, ANCHOR_KEY) != to_db_time(anchor):
        _seed_flux(conn, anchor)
        _seed_tremor(conn, anchor)
        db.set_meta(conn, ANCHOR_KEY, to_db_time(anchor))
    conn.commit()


def ensure_seeded() -> None:
    """Boot-path guard: the app never renders against a missing or empty database."""
    conn = db.connect()
    try:
        seed(conn)
    finally:
        conn.close()


def main() -> int:
    conn = db.connect()
    try:
        seed(conn)
        counts = {
            "vents": conn.execute("SELECT COUNT(*) c FROM vent").fetchone()["c"],
            "flux readings": conn.execute("SELECT COUNT(*) c FROM flux_reading").fetchone()["c"],
            "tremor samples": conn.execute("SELECT COUNT(*) c FROM tremor_sample").fetchone()["c"],
            "fumarole notes": conn.execute("SELECT COUNT(*) c FROM fumarole_note").fetchone()["c"],
            "alert episodes": conn.execute("SELECT COUNT(*) c FROM alert_episode").fetchone()["c"],
            "users": conn.execute("SELECT COUNT(*) c FROM user_account").fetchone()["c"],
        }
    finally:
        conn.close()
    print(f"Seeded database at {db.db_path()} (series anchored to {REFERENCE_DATE:%Y-%m-%d %H:%M} UTC)")
    for label, count in counts.items():
        print(f"  {label}: {count}")
    print(f"Demo sign-in: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
