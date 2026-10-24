"""Page bootstrap: one page config, one stylesheet, one Plotly template."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from lib import theme

FAVICON = str(Path(__file__).resolve().parent.parent / "static" / "favicon.png")


def bootstrap(page_title: str) -> None:
    """Must be the first Streamlit call in every page script."""
    st.set_page_config(
        page_title=f"{page_title} · Plume Explorer",
        page_icon=FAVICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    theme.inject()
