from __future__ import annotations

from app.config import settings
from app.db.models import Recruiter
from app.services.security import (
    hash_password,
    sign_value,
    unsign_value,
    verify_password,
)


SESSION_PURPOSE = "recruiter-session"
# Verifying against a real hash when the email is unknown keeps response times similar,
# so login timing does not reveal which emails have accounts.
_DUMMY_HASH = hash_password("timing-equalizer")


async def authenticate(email: str, password: str) -> Recruiter | None:
    normalized = email.strip().casefold()
    if not normalized or not password:
        return None
    recruiter = await Recruiter.get_or_none(email=normalized)
    if recruiter is None or not recruiter.password_hash:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, recruiter.password_hash):
        return None
    return recruiter


async def demo_recruiter() -> Recruiter | None:
    if not settings.demo_mode:
        return None
    return await Recruiter.get_or_none(
        email=settings.demo_recruiter_email.strip().casefold(), is_demo=True
    )


def create_session_token(recruiter: Recruiter) -> str:
    return sign_value(recruiter.id, purpose=SESSION_PURPOSE)


async def recruiter_from_session(token: str | None) -> Recruiter | None:
    value = unsign_value(
        token,
        purpose=SESSION_PURPOSE,
        max_age_seconds=settings.session_max_age_seconds,
    )
    if value is None:
        return None
    try:
        recruiter_id = int(value)
    except ValueError:
        return None
    recruiter = await Recruiter.get_or_none(id=recruiter_id).select_related("company")
    if recruiter is None or not recruiter.password_hash:
        return None
    if recruiter.is_demo and not settings.demo_mode:
        return None
    return recruiter
