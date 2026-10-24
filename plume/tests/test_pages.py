"""End-to-end page smoke tests driven through Streamlit's own test runtime.

Each test boots a real page script against a freshly seeded database, so a
broken sign-in gate, a crashing query or a lost form submit fails here before
it reaches a browser.
"""

from __future__ import annotations

from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

import seed_data  # noqa: F401  (imported for the seeded fixture environment)
from lib import db
from tests.conftest import DEMO_USER, PLUME_DIR

PAGES = (
    "pages/1_Overview.py",
    "pages/2_Flux_by_Vent.py",
    "pages/3_Tremor_Trends.py",
    "pages/4_Fumarole_Notes.py",
    "pages/5_Alert_Episodes.py",
)


def _app(path: str = "streamlit_app.py") -> AppTest:
    return AppTest.from_file(str(PLUME_DIR / path), default_timeout=120)


def _button(at: AppTest, label: str) -> Any:
    for button in at.button:
        if button.label == label:
            return button
    raise AssertionError(f"button {label!r} not rendered (have {[b.label for b in at.button]})")


def _button_for_key(at: AppTest, key: str) -> Any:
    for button in at.button:
        if button.key == key:
            return button
    raise AssertionError(f"no button with key {key!r}")


def _text(at: AppTest) -> str:
    return "\n".join(block.value for block in at.markdown)


def test_sign_in_card_is_the_public_screen(seeded_env):
    at = _app()
    at.run()
    assert not at.exception
    body = _text(at)
    assert "Volcanic Gas Plume Explorer" in body
    assert "Demo: cenius@cenius.ai / cenius" in body
    assert [field.label for field in at.text_input] == ["Email", "Password"]


def test_wrong_credentials_show_one_message_and_no_content(seeded_env):
    at = _app()
    at.run()
    at.text_input(key="login_email").set_value("analyst@plume.app")
    at.text_input(key="login_password").set_value("wrong-password")
    _button(at, "Sign in").click().run()

    assert not at.exception
    body = _text(at)
    assert body.count("Email or password is incorrect.") == 1
    assert "# Shift handover" not in body
    assert "plume_user" not in at.session_state.filtered_state


def test_demo_credentials_open_the_workspace(seeded_env):
    at = _app()
    at.run()
    at.text_input(key="login_email").set_value("cenius@cenius.ai")
    at.text_input(key="login_password").set_value("cenius")
    _button(at, "Sign in").click().run()

    assert not at.exception
    user = at.session_state.filtered_state.get("plume_user")
    assert user is not None and user["email"] == "cenius@cenius.ai"
    body = _text(at)
    assert "# Shift handover" in body
    assert "Current alert level" in body


def test_one_click_demo_sign_in(seeded_env):
    at = _app()
    at.run()
    _button(at, "Sign in as the demo analyst").click().run()
    assert not at.exception
    assert at.session_state.filtered_state.get("plume_user")["email"] == "cenius@cenius.ai"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_for_the_signed_in_analyst(seeded_env, page):
    at = _app(page)
    at.session_state["plume_user"] = DEMO_USER
    at.run()
    assert not at.exception, [error.message for error in at.exception]
    body = _text(at)
    assert "Plume" in body
    assert "Traceback" not in body


def test_fumarole_note_is_saved_and_persists(seeded_env):
    at = _app("pages/4_Fumarole_Notes.py")
    at.session_state["plume_user"] = DEMO_USER
    at.run()

    at.text_input(key="note_name").set_value("F9 - Hammer Test Vent")
    at.number_input(key="note_temp").set_value(221.5)
    at.text_area(key="note_text").set_value("Thermocouple stable across three probes.")
    _button(at, "Save observation").click().run()

    assert not at.exception, [error.message for error in at.exception]
    with db.session() as conn:
        row = conn.execute(
            "SELECT fumarole_name, temperature_c, author_email FROM fumarole_note "
            "ORDER BY observed_at DESC, id DESC LIMIT 1"
        ).fetchone()
    assert row["fumarole_name"] == "F9 - Hammer Test Vent"
    assert row["temperature_c"] == 221.5
    assert row["author_email"] == "cenius@cenius.ai"

    # A reload re-reads the row from SQLite: the note is still at the top.
    reloaded = _app("pages/4_Fumarole_Notes.py")
    reloaded.session_state["plume_user"] = DEMO_USER
    reloaded.run()
    assert "F9 - Hammer Test Vent" in _text(reloaded)


def test_fumarole_form_blocks_an_empty_name(seeded_env):
    at = _app("pages/4_Fumarole_Notes.py")
    at.session_state["plume_user"] = DEMO_USER
    at.run()

    at.text_input(key="note_name").set_value("")
    at.number_input(key="note_temp").set_value(240.0)
    _button(at, "Save observation").click().run()

    assert not at.exception
    body = _text(at)
    assert "Fumarole name is required." in body
    assert "nothing was written to the log" in body.lower()
    with db.session() as conn:
        count = conn.execute("SELECT COUNT(*) c FROM fumarole_note").fetchone()["c"]
    assert count == len(seed_data.FUMAROLE_SEED)


def test_alert_page_empty_filter_state(seeded_env):
    at = _app("pages/5_Alert_Episodes.py")
    at.session_state["plume_user"] = DEMO_USER
    at.session_state["alert_levels"] = []
    at.run()
    assert not at.exception
    body = _text(at)
    assert "No alert level selected" in body
    assert "Select at least one level" in body


def test_alert_page_level_filter_narrows_the_count(seeded_env):
    at = _app("pages/5_Alert_Episodes.py")
    at.session_state["plume_user"] = DEMO_USER
    at.run()
    assert "4 episodes" in _text(at)

    at.session_state["alert_levels"] = ["warning"]
    at.run()
    assert not at.exception
    body = _text(at)
    assert "1 episode" in body


def test_sign_out_returns_to_the_sign_in_card(seeded_env):
    at = _app()
    at.run()
    _button(at, "Sign in as the demo analyst").click().run()
    assert at.session_state.filtered_state.get("plume_user") is not None

    _button(at, "Sign out").click().run()
    assert not at.exception
    assert "plume_user" not in at.session_state.filtered_state
    assert "Demo: cenius@cenius.ai / cenius" in _text(at)


def test_a_deep_page_link_without_a_session_shows_the_wall(seeded_env):
    at = _app("pages/2_Flux_by_Vent.py")
    at.run()
    assert not at.exception
    body = _text(at)
    assert "Demo: cenius@cenius.ai / cenius" in body
    assert "SO2 flux per crater vent" not in body


def test_owner_can_delete_their_own_note(seeded_env):
    with db.session() as conn:
        row = conn.execute(
            "SELECT id FROM fumarole_note WHERE author_email = ? ORDER BY observed_at DESC LIMIT 1",
            ("cenius@cenius.ai",),
        ).fetchone()
    note_id = row["id"]

    at = _app("pages/4_Fumarole_Notes.py")
    at.session_state["plume_user"] = DEMO_USER
    at.run()

    at.checkbox(key=f"confirm_delete_{note_id}").check().run()
    _button_for_key(at, f"delete_note_{note_id}").click().run()
    assert not at.exception, [error.message for error in at.exception]

    with db.session() as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) c FROM fumarole_note WHERE id = ?", (note_id,)
        ).fetchone()["c"]
    assert remaining == 0


def test_tremor_page_asks_for_a_station_when_none_is_selected(seeded_env):
    at = _app("pages/3_Tremor_Trends.py")
    at.session_state["plume_user"] = DEMO_USER
    at.session_state["tremor_stations"] = []
    at.run()
    assert not at.exception
    body = _text(at)
    assert "No station selected" in body
    assert "Pick at least one station" in body
