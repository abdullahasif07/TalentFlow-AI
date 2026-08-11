from __future__ import annotations

import strawberry
from strawberry.file_uploads import Upload

from app.enums import ApplicationStatus


@strawberry.input
class ApplicationsQueryInput:
    job_id: strawberry.ID
    status: ApplicationStatus | None = None


@strawberry.input
class ApplicationQueryInput:
    id: strawberry.ID


@strawberry.input
class SubmitApplicationInput:
    job_id: strawberry.ID
    full_name: str
    email: str
    cover_letter: str
    resume: Upload
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


@strawberry.input
class UpdateApplicationStatusInput:
    application_id: strawberry.ID
    status: ApplicationStatus
    changed_by: str

