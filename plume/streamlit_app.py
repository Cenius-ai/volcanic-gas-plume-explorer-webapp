"""Volcanic Gas Plume Explorer - entry point.

Renders the sign-in card when there is no session, and the shift-handover
overview read through the same guarded data layer once the analyst is signed
in. The database is created and seeded on this boot path so a fresh clone
opens onto real content.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUME_DIR = Path(__file__).resolve().parent
if str(PLUME_DIR) not in sys.path:
    sys.path.insert(0, str(PLUME_DIR))

import streamlit as st  # noqa: E402

from lib import session, theme, ui  # noqa: E402
from lib.page_setup import FAVICON  # noqa: E402
from seed_data import ensure_seeded  # noqa: E402
from views import overview  # noqa: E402

st.set_page_config(
    page_title="Volcanic Gas Plume Explorer",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject()


@st.cache_resource(show_spinner=False)
def _boot() -> bool:
    """Create + seed the SQLite file once per process (idempotent)."""
    ensure_seeded()
    return True


_boot()

if session.current_user() is None:
    ui.topbar("Sign in")
    session.render_login_card()
else:
    overview.render()
