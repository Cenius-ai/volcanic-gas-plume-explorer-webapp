"""The seed must fill every screen and stay identical when re-run."""

from __future__ import annotations

from datetime import datetime, timedelta

import seed_data
from lib import auth, repository as repo
from tests.conftest import SEED_NOW

TABLES = ("vent", "flux_reading", "tremor_sample", "fumarole_note", "alert_episode", "user_account")


def _counts(conn) -> dict[str, int]:
    return {table: conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"] for table in TABLES}


def test_seed_is_idempotent(conn):
    before = _counts(conn)
    seed_data.seed(conn, now=SEED_NOW)
    seed_data.seed(conn, now=SEED_NOW)
    assert _counts(conn) == before


def test_seed_fills_every_screen(conn):
    counts = _counts(conn)
    assert counts["vent"] == 6
    assert counts["flux_reading"] == 6 * 46
    assert counts["tremor_sample"] == 4 * 721
    assert counts["fumarole_note"] >= 5
    assert counts["alert_episode"] == 4
    assert counts["user_account"] >= 2

    levels = {row["level"] for row in conn.execute("SELECT level FROM alert_episode")}
    assert levels == {"normal", "advisory", "watch", "warning"}
    assert {row["station_code"] for row in conn.execute("SELECT station_code FROM tremor_sample")} == {
        "KRA",
        "LMB",
        "MAL",
        "TNG",
    }


def test_seed_series_is_anchored_and_moves_with_the_clock(conn):
    first_latest = conn.execute("SELECT MAX(observed_at) AS t FROM flux_reading").fetchone()["t"]
    assert first_latest == SEED_NOW.strftime("%Y-%m-%d %H:%M:%S")

    later = SEED_NOW + timedelta(days=3)
    seed_data.seed(conn, now=later)
    refreshed = conn.execute("SELECT MAX(observed_at) AS t FROM flux_reading").fetchone()["t"]
    assert refreshed == later.strftime("%Y-%m-%d %H:%M:%S")
    assert _counts(conn)["flux_reading"] == 6 * 46


def test_seed_keeps_a_single_demo_account(conn):
    rows = conn.execute(
        "SELECT email FROM user_account WHERE email = ?", (auth.DEMO_EMAIL,)
    ).fetchall()
    assert len(rows) == 1
    assert auth.authenticate(conn, auth.DEMO_EMAIL, auth.DEMO_PASSWORD) is not None


def test_seeded_readings_are_varied_not_flat(conn):
    frame = repo.flux_frame(conn)
    per_vent = frame.groupby("vent_id")["so2_tonnes_per_day"].agg(["min", "max"])
    assert (per_vent["max"] - per_vent["min"]).min() > 5.0
    assert frame["so2_tonnes_per_day"].nunique() > 100


def test_seed_anchors_to_the_constant_reference_date(conn):
    """The series ends on seed_data.REFERENCE_DATE, not on the wall clock."""
    assert seed_data.REFERENCE_DATE == datetime(2026, 10, 24, 9, 0, 0)

    seed_data.seed(conn)  # no explicit date: the constant reference date wins

    stamp = seed_data.REFERENCE_DATE.strftime("%Y-%m-%d %H:%M:%S")
    stored = conn.execute(
        "SELECT value FROM app_meta WHERE key = 'series_anchor'"
    ).fetchone()["value"]
    assert stored == stamp
    assert conn.execute("SELECT MAX(observed_at) t FROM flux_reading").fetchone()["t"] == stamp
    assert conn.execute("SELECT MAX(recorded_at) t FROM tremor_sample").fetchone()["t"] == stamp
    assert _counts(conn)["flux_reading"] == 6 * 46
