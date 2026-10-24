"""The repository layer: flux windows, tremor windows, note ownership, level filter."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from lib import charts, repository as repo, validate
from tests.conftest import SEED_NOW


def test_flux_window_filters_by_date_and_vent(conn):
    vents = repo.list_vents(conn)
    assert len(vents) == 6
    target = next(vent for vent in vents if vent["code"] == "B1")

    frame = repo.flux_frame(conn, [target["id"]], SEED_NOW - timedelta(days=30), SEED_NOW)
    assert not frame.empty
    assert frame["vent_id"].unique().tolist() == [target["id"]]
    assert frame["observed_at"].min() >= pd.Timestamp(SEED_NOW - timedelta(days=30))
    assert frame["observed_at"].max() <= pd.Timestamp(SEED_NOW)
    assert frame["vent_label"].iloc[0].startswith("B1 - ")

    inside = repo.flux_frame(conn, [target["id"]], SEED_NOW - timedelta(days=7), SEED_NOW)
    assert len(inside) < len(frame)


def test_flux_window_for_every_vent(conn):
    frame = repo.flux_frame(conn, None, SEED_NOW - timedelta(days=90), SEED_NOW)
    assert frame["vent_label"].nunique() == 6


def test_latest_flux_per_vent_includes_a_previous_reading(conn):
    latest = repo.latest_flux_per_vent(conn)
    assert len(latest) == 6
    for reading in latest:
        assert reading["so2_tonnes_per_day"] > 0
        assert reading["method"] in repo.METHODS
        assert reading["previous_so2"] is not None


def test_tremor_window_and_station_filter(conn):
    codes = repo.station_codes(conn)
    assert codes == ["KRA", "LMB", "MAL", "TNG"]

    frame = repo.tremor_frame(conn, ["MAL", "TNG"], SEED_NOW - timedelta(days=3), SEED_NOW)
    assert set(frame["station_code"].unique()) == {"MAL", "TNG"}
    assert len(frame) == 2 * 25  # 3-hourly samples across three days, inclusive


def test_rolling_mean_is_a_24_hour_window(conn):
    frame = repo.tremor_frame(conn, ["KRA"], SEED_NOW - timedelta(days=10), SEED_NOW)
    series = frame.sort_values("recorded_at")["amplitude_um"].reset_index(drop=True)
    rolling = series.rolling(window=charts.ROLLING_SAMPLES_24H, min_periods=3).mean()
    expected = series.iloc[: charts.ROLLING_SAMPLES_24H].mean()
    assert rolling.iloc[charts.ROLLING_SAMPLES_24H - 1] == expected
    assert pd.isna(rolling.iloc[0])


def test_alert_level_filter_counts(conn):
    assert len(repo.list_episodes(conn, list(repo.LEVELS))) == 4
    assert len(repo.list_episodes(conn, ["warning"])) == 1
    assert repo.list_episodes(conn, []) == []
    assert repo.list_episodes(conn, None) and len(repo.list_episodes(conn, None)) == 4


def test_current_episode_is_the_newest_one(conn):
    episode = repo.current_episode(conn)
    assert episode is not None
    assert episode["level"] == "warning"
    assert episode["ended_at"] is None


def test_note_create_orders_newest_first(conn):
    before = repo.list_notes(conn)
    note_id = repo.create_note(
        conn,
        vent_id=None,
        fumarole_name="F9 - Test Vent",
        temperature_c=221.5,
        observed_at=SEED_NOW,
        note_text="Smoke test observation.",
        author_email="cenius@cenius.ai",
        created_at=SEED_NOW,
    )
    after = repo.list_notes(conn)
    assert len(after) == len(before) + 1
    assert after[0]["id"] == note_id
    assert after[0]["fumarole_name"] == "F9 - Test Vent"


def test_note_delete_is_owner_scoped(conn):
    note_id = repo.create_note(
        conn,
        vent_id=None,
        fumarole_name="F9 - Owner Check",
        temperature_c=180.0,
        observed_at=SEED_NOW - timedelta(hours=1),
        note_text="",
        author_email="analyst@plume.app",
        created_at=SEED_NOW,
    )
    assert repo.delete_note(conn, note_id, "cenius@cenius.ai") is False
    assert any(note["id"] == note_id for note in repo.list_notes(conn))
    assert repo.delete_note(conn, note_id, "analyst@plume.app") is True
    assert not any(note["id"] == note_id for note in repo.list_notes(conn))


def test_validate_note_field_messages():
    now = SEED_NOW
    assert validate.validate_note("", 200, now, "", now=now)["fumarole_name"]
    assert validate.validate_note("F1", 5000, now, "", now=now)["temperature_c"] == (
        "Temperature must be between 0 and 1200 C"
    )
    future = now + timedelta(hours=2)
    assert validate.validate_note("F1", 200, future, "", now=now)["observed_at"] == (
        "Observation time cannot be in the future"
    )
    assert validate.validate_note("F1", 213.5, now, "clear plume", now=now) == {}
