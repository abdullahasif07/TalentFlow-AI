from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.config import settings
from app.db.models import Recruiter
from app.demo.sandbox import create_demo_sandbox, is_sandbox_recruiter
from app.graphql.context import client_ip_from_request
from app.services.auth import (
    authenticate,
    create_session_token,
    recruiter_from_session,
)
from app.services.usage_guard import hit_rate_limit


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class RecruiterSession(BaseModel):
    id: str
    name: str
    email: str
    role: str
    company_id: str
    company_name: str
    is_demo: bool


class AuthConfig(BaseModel):
    demo_mode: bool
    demo_email: str | None


def _session_payload(recruiter: Recruiter) -> RecruiterSession:
    return RecruiterSession(
        id=str(recruiter.id),
        name=recruiter.name,
        email=recruiter.email,
        role=recruiter.role,
        company_id=str(recruiter.company_id),
        company_name=recruiter.company.name,
        is_demo=recruiter.is_demo,
    )


def _set_session_cookie(
    response: Response, recruiter: Recruiter, *, max_age: int | None = None
) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(recruiter),
        max_age=max_age or settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


async def _enforce_login_rate_limit(request: Request) -> None:
    allowed = await hit_rate_limit(
        "login",
        client_ip_from_request(request),
        limit=settings.login_rate_limit_per_window,
        window_seconds=settings.login_rate_limit_window_seconds,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts. Please wait a few minutes and try again.",
        )


async def get_session_recruiter(request: Request) -> Recruiter:
    recruiter = await recruiter_from_session(request.cookies.get(settings.session_cookie_name))
    if recruiter is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in.")
    return recruiter


@router.get("/config", response_model=AuthConfig)
async def auth_config() -> AuthConfig:
    return AuthConfig(
        demo_mode=settings.demo_mode,
        demo_email=settings.demo_recruiter_email if settings.demo_mode else None,
    )


async def _start_sandbox_session(response: Response) -> RecruiterSession:
    try:
        recruiter = await create_demo_sandbox()
    except Exception:
        logger.exception("Unable to create a demo sandbox")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The demo is unavailable right now. Please try again in a moment.",
        ) from None
    await recruiter.fetch_related("company")
    # The sandbox is deleted after its TTL, so the cookie need not outlive it.
    _set_session_cookie(
        response,
        recruiter,
        max_age=min(settings.session_max_age_seconds, settings.demo_sandbox_ttl_hours * 3600),
    )
    return _session_payload(recruiter)


@router.post("/login", response_model=RecruiterSession)
async def login(payload: LoginRequest, request: Request, response: Response) -> RecruiterSession:
    await _enforce_login_rate_limit(request)
    recruiter = await authenticate(payload.email, payload.password)
    if recruiter is None or (recruiter.is_demo and not settings.demo_mode):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if recruiter.is_demo:
        # The shared demo login opens a private sandbox instead of the shared company.
        return await _start_sandbox_session(response)
    await recruiter.fetch_related("company")
    _set_session_cookie(response, recruiter)
    return _session_payload(recruiter)


@router.post("/demo", response_model=RecruiterSession)
async def demo_login(request: Request, response: Response) -> RecruiterSession:
    """Open the visitor's private demo workspace, creating one if they have none."""

    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="The demo is not enabled."
        )
    current = await recruiter_from_session(request.cookies.get(settings.session_cookie_name))
    if await is_sandbox_recruiter(current):
        await current.fetch_related("company")
        return _session_payload(current)

    await _enforce_login_rate_limit(request)
    return await _start_sandbox_session(response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=RecruiterSession)
async def me(recruiter: Recruiter = Depends(get_session_recruiter)) -> RecruiterSession:
    return _session_payload(recruiter)
