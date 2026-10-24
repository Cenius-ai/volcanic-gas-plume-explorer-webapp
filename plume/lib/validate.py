"""Field-level validation for fumarole observations.

Runs in the page before a row is written, and again in the tests, so every
message the analyst sees is produced by one implementation.
"""

from __future__ import annotations

from datetime import datetime

MIN_TEMPERATURE_C = 0.0
MAX_TEMPERATURE_C = 1200.0
MAX_NAME_LENGTH = 80
MAX_NOTE_LENGTH = 1000


def validate_note(
    fumarole_name: str,
    temperature_c: float,
    observed_at: datetime,
    note_text: str = "",
    now: datetime | None = None,
) -> dict[str, str]:
    """Return ``{field: message}`` for every invalid field (empty when valid)."""
    errors: dict[str, str] = {}
    name = (fumarole_name or "").strip()
    if not name:
        errors["fumarole_name"] = "Fumarole name is required."
    elif len(name) > MAX_NAME_LENGTH:
        errors["fumarole_name"] = f"Keep the fumarole name under {MAX_NAME_LENGTH} characters."

    try:
        temperature = float(temperature_c)
    except (TypeError, ValueError):
        errors["temperature_c"] = "Temperature must be a number."
    else:
        if not MIN_TEMPERATURE_C <= temperature <= MAX_TEMPERATURE_C:
            errors["temperature_c"] = "Temperature must be between 0 and 1200 C"

    reference = (now or datetime.utcnow()).replace(tzinfo=None, microsecond=0)
    if observed_at is None:
        errors["observed_at"] = "Observation time is required."
    elif observed_at.replace(tzinfo=None, microsecond=0) > reference:
        # Compare at whole-second resolution: the form starts on "now" and the
        # clock keeps moving while the analyst types.
        errors["observed_at"] = "Observation time cannot be in the future"

    if len((note_text or "").strip()) > MAX_NOTE_LENGTH:
        errors["note_text"] = f"Keep the note under {MAX_NOTE_LENGTH} characters."
    return errors
