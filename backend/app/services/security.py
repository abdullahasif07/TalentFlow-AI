"""Password hashing and signed, expiring tokens built on the standard library."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from app.config import settings


_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not password or not encoded:
        return False
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(_b64decode(expected)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, _b64decode(expected))


def _signature(payload: str, purpose: str) -> str:
    key = settings.session_secret.get_secret_value().encode("utf-8")
    message = f"{purpose}:{payload}".encode("utf-8")
    return _b64encode(hmac.new(key, message, hashlib.sha256).digest())


def sign_value(value: str | int, *, purpose: str) -> str:
    """Return ``value.issued_at.signature``; the purpose binds a token to one use."""

    payload = f"{value}.{int(time.time())}"
    return f"{payload}.{_signature(payload, purpose)}"


def unsign_value(token: str | None, *, purpose: str, max_age_seconds: int) -> str | None:
    if not token or token.count(".") != 2:
        return None
    value, issued_at, signature = token.split(".")
    payload = f"{value}.{issued_at}"
    if not hmac.compare_digest(signature, _signature(payload, purpose)):
        return None
    try:
        age = time.time() - int(issued_at)
    except ValueError:
        return None
    if age < 0 or age > max_age_seconds:
        return None
    return value
