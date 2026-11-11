from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.config import settings
from app.db.models import Recruiter
from app.graphql.context import client_ip_from_request
from app.services.auth import (
    authenticate,
    create_session_token,
    demo_recruiter,
    recruiter_from_session,
)
from app.services.usage_guard import hit_rate_limit


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


def _set_session_cookie(response: Response, recruiter: Recruiter) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(recruiter),
        max_age=settings.session_max_age_seconds,
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


@router.post("/login", response_model=RecruiterSession)
async def login(payload: LoginRequest, request: Request, response: Response) -> RecruiterSession:
    await _enforce_login_rate_limit(request)
    recruiter = await authenticate(payload.email, payload.password)
    if recruiter is None or (recruiter.is_demo and not settings.demo_mode):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    await recruiter.fetch_related("company")
    _set_session_cookie(response, recruiter)
    return _session_payload(recruiter)


@router.post("/demo", response_model=RecruiterSession)
async def demo_login(request: Request, response: Response) -> RecruiterSession:
    await _enforce_login_rate_limit(request)
    recruiter = await demo_recruiter()
    if recruiter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The demo account is not available. Run the seed script to create it.",
        )
    await recruiter.fetch_related("company")
    _set_session_cookie(response, recruiter)
    return _session_payload(recruiter)


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
