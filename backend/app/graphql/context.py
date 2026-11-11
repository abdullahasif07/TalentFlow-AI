from __future__ import annotations

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


def client_ip_from_request(request: Request | None) -> str:
    if request is None or request.client is None:
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
