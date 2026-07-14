from __future__ import annotations

import secrets

import bcrypt

MIN_PASSWORD_LENGTH = 8


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # malformed hash -- treat as a failed verification, not a crash
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_temp_password() -> str:
    return secrets.token_urlsafe(12)
