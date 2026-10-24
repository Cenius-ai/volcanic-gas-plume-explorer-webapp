"""Password hashing, credential checks and the signed reload token."""

from __future__ import annotations

from lib import auth


def test_hash_is_salted_pbkdf2_and_not_the_plaintext():
    first_hash, first_salt = auth.hash_password("cenius")
    second_hash, second_salt = auth.hash_password("cenius")
    assert first_hash != "cenius"
    assert len(first_hash) == 64
    assert first_salt != second_salt
    assert first_hash != second_hash  # same password, different salt


def test_verify_accepts_only_the_right_password():
    stored_hash, salt = auth.hash_password("plume-analyst")
    assert auth.verify_password("plume-analyst", stored_hash, salt) is True
    assert auth.verify_password("plume-analyst ", stored_hash, salt) is False
    assert auth.verify_password("", stored_hash, salt) is False


def test_authenticate_returns_the_account_for_the_seeded_demo_user(conn):
    user = auth.authenticate(conn, auth.DEMO_EMAIL, auth.DEMO_PASSWORD)
    assert user is not None
    assert user["email"] == auth.DEMO_EMAIL
    assert user["password_hash"] if "password_hash" in user else True


def test_authenticate_is_case_insensitive_on_email(conn):
    user = auth.authenticate(conn, auth.DEMO_EMAIL.upper(), auth.DEMO_PASSWORD)
    assert user is not None


def test_authenticate_rejects_wrong_password_and_unknown_email(conn):
    assert auth.authenticate(conn, auth.DEMO_EMAIL, "wrong-password") is None
    assert auth.authenticate(conn, "nobody@plume.app", auth.DEMO_PASSWORD) is None


def test_validate_email_messages():
    assert auth.validate_email("") is not None
    assert auth.validate_email("analyst") is not None
    assert auth.validate_email("analyst@plume") is not None
    assert auth.validate_email("analyst@plume.app") is None


def test_session_token_round_trip_and_tamper(monkeypatch):
    token = auth.issue_token(auth.DEMO_EMAIL)
    assert auth.verify_token(token) == auth.DEMO_EMAIL

    forged = token.rsplit("|", 1)[0] + "|" + "0" * 64
    assert auth.verify_token(forged) is None
    assert auth.verify_token("garbage") is None

    monkeypatch.setattr(auth, "TOKEN_TTL_SECONDS", -1)
    assert auth.verify_token(token) is None
