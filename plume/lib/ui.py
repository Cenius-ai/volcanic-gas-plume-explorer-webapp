"""Shared HTML building blocks: top bar, flag metrics, badges, tables, states.

Everything rendered from data is escaped here, so user-typed fumarole names and
notes can never become markup.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Iterable, Sequence

import streamlit as st

from lib.format import fmt_stamp

MAX_STAGGER_ITEMS = 8


def esc(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def topbar(section: str, status: str | None = None) -> None:
    """48px-class top strip: breadcrumb on the left, dataset status on the right."""
    label = status or f"OBSERVATORY · {utc_now():%H:%M} UTC"
    st.markdown(
        '<div class="plume-topbar">'
        f'<div class="plume-crumbs">Plume <b>/</b> {esc(section)}</div>'
        f'<span class="plume-status"><span class="plume-dot live"></span>{esc(label)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def page_title(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"# {esc(title)}", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="plume-meta" style="margin:-2px 0 6px;max-width:70ch">{esc(subtitle)}</p>',
                    unsafe_allow_html=True)


def section(title: str, aside: str | None = None) -> None:
    aside_html = f'<span class="plume-meta">{esc(aside)}</span>' if aside else ""
    st.markdown(
        f'<div class="plume-section"><h2>{esc(title)}</h2>{aside_html}</div>',
        unsafe_allow_html=True,
    )


def badge(level: str) -> str:
    safe = esc(level)
    return f'<span class="plume-badge badge-{safe}"><span class="plume-dot"></span>{safe}</span>'


def kpi(
    label: str,
    value: str,
    unit: str = "",
    flag: str | None = None,
    tone: str = "accent",
    meta: str = "",
) -> str:
    """A number with its unit and a leader-line flag callout - the product signature."""
    tone_class = {"accent": "", "neutral": " neutral", "down": " down"}.get(tone, "")
    unit_html = f"<small>{esc(unit)}</small>" if unit else ""
    flag_html = (
        f'<div class="plume-flag"><span class="plume-leader"></span>'
        f'<span class="plume-chip{tone_class}">{esc(flag)}</span></div>'
        if flag
        else ""
    )
    meta_html = f'<div class="plume-meta">{meta}</div>' if meta else ""
    return (
        f'<div class="plume-kpi"><div class="plume-kpi-label">{esc(label)}</div>'
        f'<div class="plume-kpi-value">{value}{unit_html}</div>{flag_html}{meta_html}</div>'
    )


def card(inner_html: str, index: int = 0, extra_class: str = "") -> str:
    delay = min(index, MAX_STAGGER_ITEMS - 1) * 55
    return (
        f'<div class="plume-card{(" " + extra_class) if extra_class else ""}" '
        f'style="animation-delay:{delay}ms">{inner_html}</div>'
    )


def grid(cards: Sequence[str], kind: str = "") -> str:
    return f'<div class="plume-grid{(" " + kind) if kind else ""}">{"".join(cards)}</div>'


def markdown(content: str, **kwargs) -> None:
    """Render HTML (escaped by the caller) through Streamlit's markdown sink."""
    kwargs.setdefault("unsafe_allow_html", True)
    st.markdown(content, **kwargs)


def empty_state(title: str, body: str, hint: str | None = None) -> None:
    hint_html = f'<div class="plume-meta" style="margin-top:6px">{esc(hint)}</div>' if hint else ""
    markdown(
        f'<div class="plume-empty"><strong>{esc(title)}</strong>'
        f'<div class="plume-meta">{esc(body)}</div>{hint_html}</div>'
    )


def error_state(message: str, hint: str = "Nothing was lost - try the same call again.") -> None:
    markdown(
        f'<div class="plume-error"><strong>{esc(message)}</strong>'
        f'<div style="margin-top:4px;font-size:12.5px;opacity:.9">{esc(hint)}</div></div>'
    )


def data_table(columns: Sequence[tuple[str, str]], rows: Iterable[Sequence[str]]) -> None:
    """columns: (label, align) where align is 'left' | 'num' | 'dim'."""
    head = "".join(
        f'<th class="{"num" if align == "num" else ""}">{esc(label)}</th>' for label, align in columns
    )
    body_rows = []
    for row in rows:
        cells = []
        for (_, align), cell in zip(columns, row):
            css = "num" if align == "num" else ("dim" if align == "dim" else "")
            cells.append(f'<td class="{css}">{cell}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    markdown(
        '<div class="plume-table-wrap"><table class="plume-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def note_card(note: dict, owned: bool) -> str:
    """HTML body of one fumarole note; text is escaped, ids stay numeric."""
    vent = f"{note['vent_code']} - {note['vent_name']}" if note.get("vent_code") else "Unlinked vent"
    owner_chip = (
        '<span class="plume-chip">Yours</span>'
        if owned
        else f'<span class="plume-chip neutral">{esc(note["author_email"])}</span>'
    )
    body = esc(note.get("note_text") or "No context recorded.")
    return (
        '<div class="plume-note">'
        '<div class="plume-note-head">'
        f'<div><div class="plume-note-temp">{note["temperature_c"]:,.1f}<small>°C</small></div>'
        f'<div class="plume-meta">{esc(note["fumarole_name"])} · {esc(vent)}</div></div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">{owner_chip}'
        f'<span class="plume-meta">{esc(fmt_stamp(note["observed_at"]))}</span></div>'
        "</div>"
        f'<div class="plume-note-body">{body}</div>'
        "</div>"
    )
