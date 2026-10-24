"""Credentials for the observatory workspace.

Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a per-user random salt
(stdlib only, no native build). Verification is constant time. The demo
account is created through this very module by the seed script, so the hash
login verifies is always the hash the seed wrote.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from typing import Any

ITERATIONS = 210_000
SALT_BYTES = 16
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
TOKEN_TTL_SECONDS = 12 * 60 * 60

# The platform demo account: seeded through hash_password(), never a bypass.
DEMO_EMAIL = "cenius@cenius.ai"
DEMO_PASSWORD = "cenius"
SESSION_SECRET = os.environ.get("PLUME_SESSION_SECRET", "cenius-dev-9f2c4b7e61d84a05")


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return ``(hash_hex, salt_hex)`` for the password."""
    salt_hex = salt or secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERATIONS)
    return digest.hex(), salt_hex


def verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    """Constant-time comparison of a candidate password against the stored hash."""
    try:
        candidate, _ = hash_password(password, salt_hex)
    except ValueError:
        return False
    return hmac.compare_digest(candidate, stored_hash)


def validate_email(value: str) -> str | None:
    """Return an inline error message, or None when the address is acceptable."""
    candidate = (value or "").strip()
    if not candidate:
        return "Enter your email address."
    if len(candidate) > 254 or not EMAIL_PATTERN.match(candidate):
        return "Enter a valid email address, for example analyst@plume.app."
    return None


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> dict[str, Any] | None:
    """Resolve the account for these credentials, or None. Never reveals which part failed."""
    row = conn.execute(
        "SELECT id, email, display_name, password_hash, salt FROM user_account WHERE email = ? COLLATE NOCASE",
        ((email or "").strip(),),
    ).fetchone()
    if row is None or not password:
        return None
    if not verify_password(password, row["password_hash"], row["salt"]):
        return None
    return {"id": row["id"], "email": row["email"], "display_name": row["display_name"]}


def upsert_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
    display_name: str,
    created_at: str,
) -> int:
    """Create the account once; re-running never rewrites an existing hash."""
    existing = conn.execute("SELECT id FROM user_account WHERE email = ?", (email,)).fetchone()
    if existing is not None:
        return int(existing["id"])
    password_hash, salt = hash_password(password)
    cursor = conn.execute(
        "INSERT INTO user_account (email, display_name, password_hash, salt, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (email, display_name, password_hash, salt, created_at),
    )
    return int(cursor.lastrowid)


def _sign(payload: str) -> str:
    return hmac.new(SESSION_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_token(email: str) -> str:
    """Signed, expiring session token so a browser reload keeps the analyst signed in."""
    issued_at = int(time.time())
    payload = f"{email}|{issued_at}"
    return f"{payload}|{_sign(payload)}"


def verify_token(token: str) -> str | None:
    """Return the email carried by a valid unexpired token, else None."""
    try:
        email, issued_at, signature = (token or "").rsplit("|", 2)
    except ValueError:
        return None
    if not email or not issued_at.isdigit():
        return None
    if not hmac.compare_digest(_sign(f"{email}|{issued_at}"), signature):
        return None
    if time.time() - int(issued_at) > TOKEN_TTL_SECONDS:
        return None
    return email
