"""Session gate: one sign-in card, one guard, one sign-out.

Streamlit pages are individually addressable, so every page asks for the guard
before it renders anything. Authentication state also rides in a signed query
token so a browser reload (or a deep link inside the workspace) keeps the
analyst signed in.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import streamlit as st

from lib import auth, db, ui

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 20


def _load_user(email: str) -> dict[str, Any] | None:
    with db.session() as conn:
        row = conn.execute(
            "SELECT id, email, display_name FROM user_account WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()
    return dict(row) if row else None


def current_user() -> dict[str, Any] | None:
    """Session state first, then the signed query token, else no one."""
    state = st.session_state
    if state.get("plume_user"):
        return state["plume_user"]
    token = st.query_params.get("s")
    if isinstance(token, list):
        token = token[0] if token else None
    if token:
        email = auth.verify_token(token)
        if email:
            user = _load_user(email)
            if user:
                state["plume_user"] = user
                return user
    return None


def sign_in(user: dict[str, Any]) -> None:
    st.session_state["plume_user"] = user
    st.session_state.pop("login_error", None)
    st.session_state["failed_attempts"] = 0
    st.query_params["s"] = auth.issue_token(user["email"])


def sign_out() -> None:
    for key in ("plume_user", "login_error"):
        st.session_state.pop(key, None)
    st.query_params.clear()
    st.rerun()


def _locked_out() -> int:
    """Return remaining lockout seconds after repeated failures."""
    until = float(st.session_state.get("locked_until", 0.0))
    return max(int(until - time.time()), 0)


def _record_failure() -> None:
    attempts = int(st.session_state.get("failed_attempts", 0)) + 1
    st.session_state["failed_attempts"] = attempts
    if attempts >= MAX_FAILED_ATTEMPTS:
        st.session_state["locked_until"] = time.time() + LOCKOUT_SECONDS
        st.session_state["failed_attempts"] = 0


def _try_sign_in(email: str, password: str) -> bool:
    with db.session() as conn:
        user = auth.authenticate(conn, email, password)
    if user:
        sign_in(user)
        return True
    _record_failure()
    return False


def render_login_card() -> None:
    """The sign-in view: product identity, one form, the demo credential."""
    left, middle, right = st.columns([1, 1.25, 1])
    with middle:
        st.markdown('<div style="height:26px"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="plume-eyebrow">Observatory workspace</div>'
            '<h1 style="margin-top:6px">Volcanic Gas Plume Explorer</h1>'
            '<p class="plume-meta" style="margin-bottom:18px;max-width:46ch">'
            "Sulphur dioxide flux, tremor amplitude and fumarole observations for the "
            "Kawah Ratu complex. Sign in to open the shift workspace.</p>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown('<div class="plume-eyebrow">Sign in</div>', unsafe_allow_html=True)
            remaining = _locked_out()
            if remaining:
                ui.error_state(
                    f"Too many attempts. Try again in {remaining}s.",
                    "Failed sign-ins are throttled per session.",
                )

            show_password = st.checkbox("Show password", key="login_show_password")
            with st.form("sign_in_form", clear_on_submit=False):
                email = st.text_input(
                    "Email", key="login_email", placeholder="analyst@plume.app", autocomplete="username"
                )
                password = st.text_input(
                    "Password",
                    key="login_password",
                    type="default" if show_password else "password",
                    autocomplete="current-password",
                )
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

            if submitted:
                errors: dict[str, str] = {}
                email_error = auth.validate_email(email)
                if email_error:
                    errors["email"] = email_error
                if not password:
                    errors["password"] = "Enter your password."
                if errors:
                    for message in errors.values():
                        ui.error_state(message)
                elif remaining:
                    ui.error_state(f"Too many attempts. Try again in {remaining}s.")
                else:
                    with st.spinner("Checking credentials..."):
                        signed_in = _try_sign_in(email.strip(), password)
                    if signed_in:
                        st.rerun()
                    else:
                        ui.error_state(
                            "Email or password is incorrect.",
                            "One message for every failure - we do not say which field was wrong.",
                        )

            st.markdown(
                '<div style="margin-top:14px;border-top:1px solid var(--border);padding-top:12px">'
                '<div class="plume-eyebrow">Demo credential</div>'
                '<div class="plume-meta" style="font-family:var(--font-mono);color:var(--accent-strong);'
                'font-size:12.5px;margin-top:4px">Demo: cenius@cenius.ai / cenius</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Sign in as the demo analyst", key="demo_sign_in", use_container_width=True):
                if _try_sign_in(auth.DEMO_EMAIL, auth.DEMO_PASSWORD):
                    st.rerun()
                else:
                    ui.error_state("The demo account could not be opened. Run the seed script.")


def render_sidebar(user: dict[str, Any]) -> None:
    with st.sidebar:
        st.markdown(
            '<div class="plume-card" style="padding:12px 14px;margin-top:10px">'
            '<div class="plume-eyebrow">Signed in</div>'
            f'<div style="font-size:12.5px;margin-top:4px;overflow-wrap:anywhere">{ui.esc(user["email"])}</div>'
            f'<div class="plume-meta" style="font-size:11.5px">{ui.esc(user["display_name"])}</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Sign out", key="sign_out_button", use_container_width=True):
            sign_out()
        st.markdown(
            '<div class="plume-meta" style="font-size:11px;padding:2px 4px">'
            "Kawah Ratu observatory · UTC</div>",
            unsafe_allow_html=True,
        )


def guard(page_name: str, controls: Callable[[], Any] | None = None) -> tuple[dict[str, Any], Any]:
    """Return the signed-in analyst, or render the sign-in card and stop the page.

    ``controls`` renders the page's sidebar filters before the account block so
    the sidebar reads: navigation, filters, identity, sign out.
    """
    user = current_user()
    if user is None:
        ui.topbar("Sign in")
        render_login_card()
        st.stop()
    filters = controls() if controls is not None else None
    render_sidebar(user)
    return user, filters
