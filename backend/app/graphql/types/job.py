from __future__ import annotations

from datetime import datetime
from typing import Any

import strawberry
from strawberry.scalars import JSON

from app.db.models import Job
from app.enums import JobStatus


@strawberry.type
class JobSummary:
    id: strawberry.ID
    title: str
    status: JobStatus

    @classmethod
    def from_model(cls, job: Job) -> "JobSummary":
        return cls(id=strawberry.ID(str(job.id)), title=job.title, status=job.status)


@strawberry.type
class JobType:
    id: strawberry.ID
    company_id: strawberry.ID
    title: str
    description: str
    required_skills: JSON
    preferred_skills: JSON
    experience_requirement: str | None
    evaluation_criteria: JSON
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, job: Job) -> "JobType":
        return cls(
            id=strawberry.ID(str(job.id)),
            company_id=strawberry.ID(str(job.company_id)),
            title=job.title,
            description=job.description,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
            experience_requirement=job.experience_requirement,
            evaluation_criteria=job.evaluation_criteria,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
