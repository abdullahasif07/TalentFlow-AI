from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import strawberry

from app.db.models import Application
from app.enums import ApplicationStatus
from app.graphql.types.job import JobSummary


@strawberry.type
class CandidateSummary:
    id: strawberry.ID
    name: str
    email: str


@strawberry.type
class ApplicationType:
    id: strawberry.ID
    candidate_id: strawberry.ID
    job_id: strawberry.ID
    candidate: CandidateSummary
    job: JobSummary
    resume_url: str | None
    cover_letter: str | None
    status: ApplicationStatus
    fit_score: Decimal | None
    applied_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, application: Application) -> "ApplicationType":
        return cls(
            id=strawberry.ID(str(application.id)),
            candidate_id=strawberry.ID(str(application.candidate_id)),
            job_id=strawberry.ID(str(application.job_id)),
            candidate=CandidateSummary(
                id=strawberry.ID(str(application.candidate.id)),
                name=application.candidate.name,
                email=application.candidate.email,
            ),
            job=JobSummary.from_model(application.job),
            resume_url=application.resume_url,
            cover_letter=application.cover_letter,
            status=application.status,
            fit_score=application.fit_score,
            applied_at=application.applied_at,
            updated_at=application.updated_at,
        )
