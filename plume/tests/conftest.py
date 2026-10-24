"""Shared fixtures: every test runs against its own throwaway SQLite file."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

PLUME_DIR = Path(__file__).resolve().parent.parent
if str(PLUME_DIR) not in sys.path:
    sys.path.insert(0, str(PLUME_DIR))

import seed_data  # noqa: E402
from lib import db  # noqa: E402

# A fixed reference date keeps every assertion independent of the wall clock.
SEED_NOW = datetime(2026, 5, 1, 9, 0, 0)

DEMO_USER = {"id": 1, "email": "cenius@cenius.ai", "display_name": "Cenius Demo Analyst"}


@pytest.fixture()
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUME_DB_PATH", str(tmp_path / "plume_test.db"))
    connection = db.connect()
    seed_data.seed(connection, now=SEED_NOW)
    yield connection
    connection.close()


@pytest.fixture()
def seeded_env(tmp_path, monkeypatch):
    """Seed a temp database and point the whole app (pages included) at it."""
    monkeypatch.setenv("PLUME_DB_PATH", str(tmp_path / "plume_test.db"))
    connection = db.connect()
    seed_data.seed(connection, now=SEED_NOW)
    connection.close()
    return tmp_path / "plume_test.db"
