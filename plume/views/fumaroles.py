"""Fumarole temperature notes: validated entry, persisted list, owner-only delete."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import streamlit as st

from lib import db, repository as repo, session, ui, validate
from views import common

FLASH_KEY = "note_flash"
ERROR_KEY = "note_errors"
SUBMIT_KEY = "note_last_submit"
NO_LINK = "No vent link"


def _field_error(message: str) -> None:
    ui.markdown(
        '<div class="plume-error" style="margin:-6px 0 10px;font-size:12.5px;padding:8px 10px">'
        f"{ui.esc(message)}</div>"
    )


def _fetch() -> dict[str, Any]:
    with db.session() as conn:
        return {"vents": repo.list_vents(conn), "notes": repo.list_notes(conn)}


def _save(user: dict[str, Any], payload: dict[str, Any]) -> int | None:
    """Persist the observation and return its id (None when the same submit repeats)."""
    fingerprint = "|".join(str(payload[key]) for key in ("name", "temp", "observed_at", "text"))
    previous = st.session_state.get(SUBMIT_KEY)
    now_ts = time.time()
    if previous and previous[0] == fingerprint and now_ts - previous[1] < 3:
        return None
    with db.session() as conn:
        note_id = repo.create_note(
            conn,
            vent_id=payload["vent_id"],
            fumarole_name=payload["name"],
            temperature_c=payload["temp"],
            observed_at=payload["observed_at"],
            note_text=payload["text"],
            author_email=user["email"],
            created_at=datetime.utcnow(),
        )
    st.session_state[SUBMIT_KEY] = (fingerprint, now_ts)
    return note_id


def _form(vents: list[dict[str, Any]], user: dict[str, Any]) -> None:
    errors: dict[str, str] = st.session_state.get(ERROR_KEY) or {}
    labels = [NO_LINK] + [repo.vent_label(vent) for vent in vents]
    now = ui.utc_now()

    with st.form("fumarole_note_form", clear_on_submit=False):
        ui.markdown('<div class="plume-eyebrow">Record an observation</div>', unsafe_allow_html=True)
        name = st.text_input(
            "Fumarole name", key="note_name", placeholder="F2 - Sulphur Shelf", max_chars=80
        )
        if "fumarole_name" in errors:
            _field_error(errors["fumarole_name"])

        vent_choice = st.selectbox("Linked crater vent (optional)", labels, index=0, key="note_vent")

        temperature = st.number_input(
            "Temperature (°C)",
            min_value=validate.MIN_TEMPERATURE_C,
            max_value=validate.MAX_TEMPERATURE_C,
            value=210.0,
            step=0.5,
            format="%.1f",
            key="note_temp",
        )
        if "temperature_c" in errors:
            _field_error(errors["temperature_c"])

        observed_date = st.date_input(
            "Observation date (UTC)", value=now.date(), max_value=now.date(), key="note_date"
        )
        observed_time = st.time_input(
            "Observation time (UTC)",
            value=now.time().replace(second=0, microsecond=0),
            key="note_time",
        )
        if "observed_at" in errors:
            _field_error(errors["observed_at"])

        note_text = st.text_area(
            "Observation note",
            key="note_text",
            height=120,
            max_chars=validate.MAX_NOTE_LENGTH,
            placeholder="What did you see, hear or smell at the vent?",
        )
        if "note_text" in errors:
            _field_error(errors["note_text"])

        ui.markdown(
            '<div class="plume-meta" style="font-size:11.5px;margin-bottom:8px">'
            f"Name required · temperature between {validate.MIN_TEMPERATURE_C:.0f} and "
            f"{validate.MAX_TEMPERATURE_C:.0f} °C · observation time cannot be in the future · "
            f"note up to {validate.MAX_NOTE_LENGTH} characters.</div>",
            unsafe_allow_html=True,
        )
        submitted = st.form_submit_button("Save observation", type="primary", use_container_width=True)

    if not submitted:
        return

    observed_at = datetime.combine(observed_date, observed_time)
    found = validate.validate_note(name, float(temperature), observed_at, note_text)
    if found:
        st.session_state[ERROR_KEY] = found
        st.rerun()

    vent_id = None
    if vent_choice != NO_LINK:
        matched = next((v for v in vents if repo.vent_label(v) == vent_choice), None)
        vent_id = matched["id"] if matched else None

    with st.spinner("Saving observation..."):
        note_id = _save(
            user,
            {
                "name": name,
                "temp": float(temperature),
                "observed_at": observed_at,
                "text": note_text,
                "vent_id": vent_id,
            },
        )
    st.session_state[ERROR_KEY] = {}
    st.session_state[FLASH_KEY] = (
        ("success", f"Saved {name.strip()} at {temperature:.1f} °C.") if note_id else
        ("error", "That observation was just saved - it is already in the list.")
    )
    st.rerun()


def _delete(note_id: int, user: dict[str, Any]) -> None:
    with db.session() as conn:
        removed = repo.delete_note(conn, note_id, user["email"])
    st.session_state[FLASH_KEY] = (
        ("success", "Observation deleted.") if removed else
        ("error", "That observation is not yours to delete.")
    )
    st.rerun()


def _list(notes: list[dict[str, Any]], user: dict[str, Any]) -> None:
    if not notes:
        ui.empty_state(
            "No observations recorded yet",
            "No fumarole temperature reading is on file for this observatory.",
            "Use the form to record the first observation.",
        )
        return

    own = sum(1 for note in notes if note["author_email"] == user["email"])
    ui.section("Recorded observations", f"{len(notes)} notes · {own} yours")

    for note in notes:
        owned = note["author_email"] == user["email"]
        ui.markdown(ui.note_card(note, owned))
        if owned:
            confirm_col, action_col = st.columns([2.1, 1])
            with confirm_col:
                confirmed = st.checkbox(
                    "Confirm delete", key=f"confirm_delete_{note['id']}", label_visibility="visible"
                )
            with action_col:
                if st.button(
                    "Delete note",
                    key=f"delete_note_{note['id']}",
                    disabled=not confirmed,
                    use_container_width=True,
                ):
                    _delete(int(note["id"]), user)


def render() -> None:
    user, _ = session.guard("Fumarole notes")
    ui.topbar("Fumarole notes")
    data = common.fetch("the fumarole observation log", _fetch)

    ui.page_title(
        "Fumarole temperature notes",
        "Free-text observations from the field, with the measured temperature and the vent "
        "they belong to. You can delete your own notes; the duty scientist's stay on record.",
    )

    flash = st.session_state.pop(FLASH_KEY, None)
    if flash:
        tone, message = flash
        if tone == "success":
            st.success(message)
        else:
            ui.error_state(message)
    elif st.session_state.get(ERROR_KEY):
        ui.error_state("Fix the highlighted fields and save again.", "Nothing was written to the log.")

    form_col, list_col = st.columns([1, 1.25], gap="large")
    with form_col:
        _form(data["vents"], user)
    with list_col:
        _list(data["notes"], user)
