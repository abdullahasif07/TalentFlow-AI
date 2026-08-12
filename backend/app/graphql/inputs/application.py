from __future__ import annotations

from decimal import Decimal

import strawberry
from strawberry.file_uploads import Upload

from app.enums import ApplicationSort, ApplicationStatus
from app.graphql.inputs.common import OffsetPaginationInput


@strawberry.input
class ApplicationFiltersInput:
    status: ApplicationStatus | None = None
    minimum_fit_score: Decimal | None = None
    candidate_search: str | None = None


@strawberry.input
class ApplicationsQueryInput:
    job_id: strawberry.ID
    status: ApplicationStatus | None = None
    filters: ApplicationFiltersInput | None = None
    sort: ApplicationSort = ApplicationSort.NEWEST
    pagination: OffsetPaginationInput | None = None


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
    recruiter_id: strawberry.ID | None = None
    automated: bool = False


@strawberry.input
class BulkUpdateApplicationStatusInput:
    application_ids: list[strawberry.ID]
    status: ApplicationStatus
    changed_by: str
    recruiter_id: strawberry.ID | None = None
    automated: bool = False


@strawberry.input
class AddApplicationNoteInput:
    application_id: strawberry.ID
    content: str
    recruiter_id: strawberry.ID | None = None
