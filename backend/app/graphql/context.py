from __future__ import annotations

import hmac
from typing import Any

from fastapi import Request, Response
from strawberry.fastapi import BaseContext
from strawberry.permission import BasePermission
from strawberry.types import Info

from app.db.models import Recruiter
from app.services.auth import recruiter_from_session


class GraphQLContext(BaseContext):
    """Per-request context: the signed-in recruiter, if any, and the client address."""

    def __init__(
        self,
        *,
        recruiter: Recruiter | None = None,
        client_ip: str | None = None,
    ) -> None:
        super().__init__()
        self.recruiter = recruiter
        self.client_ip = client_ip


PROXY_SECRET_HEADER = "x-tf-proxy-secret"
PROXY_CLIENT_IP_HEADER = "x-tf-client-ip"


def has_valid_proxy_secret(request: Request) -> bool:
    """True when a proxy secret is configured and the request carries it."""

    from app.config import settings

    expected = settings.proxy_shared_secret
    if expected is None or not expected.get_secret_value():
        return False
    supplied = request.headers.get(PROXY_SECRET_HEADER, "")
    return hmac.compare_digest(
        supplied.encode("utf-8"), expected.get_secret_value().encode("utf-8")
    )


def client_ip_from_request(request: Request | None) -> str:
    if request is None:
        return "unknown"
    # Behind the frontend proxy every request comes from the proxy's own address, so
    # use the visitor address it forwards, but only when the shared secret proves the
    # header was set by the proxy and not by the caller.
    if has_valid_proxy_secret(request):
        forwarded = request.headers.get(PROXY_CLIENT_IP_HEADER, "").strip()
        if forwarded:
            return forwarded[:64]
    if request.client is None:
        return "unknown"
    return request.client.host or "unknown"


async def get_graphql_context(request: Request, response: Response) -> GraphQLContext:
    from app.config import settings

    recruiter = await recruiter_from_session(request.cookies.get(settings.session_cookie_name))
    return GraphQLContext(recruiter=recruiter, client_ip=client_ip_from_request(request))


def current_recruiter(info: Info) -> Recruiter | None:
    return getattr(info.context, "recruiter", None)


def require_recruiter(info: Info) -> Recruiter:
    recruiter = current_recruiter(info)
    if recruiter is None:  # Guarded by IsAuthenticated; this is a safety net.
        raise PermissionError("Authentication required.")
    return recruiter


def request_client_ip(info: Info) -> str:
    return getattr(info.context, "client_ip", None) or "unknown"


class IsAuthenticated(BasePermission):
    """Allow only signed-in recruiters. Applied to every non-public field."""

    message = "Sign in as a recruiter to use this operation."
    error_extensions = {"code": "UNAUTHENTICATED"}

    def has_permission(self, source: Any, info: Info, **kwargs: Any) -> bool:
        return current_recruiter(info) is not None


RECRUITER_ONLY = [IsAuthenticated]


async def job_visible_to(info: Info, job_id: int) -> bool:
    """Recruiters only see jobs that belong to their own company."""

    from app.db.models import Job

    recruiter = require_recruiter(info)
    return await Job.exists(id=job_id, company_id=recruiter.company_id)


async def application_visible_to(info: Info, application_id: int) -> bool:
    from app.db.models import Application

    recruiter = require_recruiter(info)
    return await Application.exists(id=application_id, job__company_id=recruiter.company_id)


async def outreach_visible_to(info: Info, outreach_id: int) -> bool:
    from app.db.models import OutreachEmail

    recruiter = require_recruiter(info)
    return await OutreachEmail.exists(
        id=outreach_id, application__job__company_id=recruiter.company_id
    )
