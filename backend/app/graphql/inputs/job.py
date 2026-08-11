from __future__ import annotations

import strawberry
from strawberry.scalars import JSON

from app.enums import JobStatus


@strawberry.input
class JobsQueryInput:
    company_id: strawberry.ID | None = None
    status: JobStatus | None = None


@strawberry.input
class JobQueryInput:
    id: strawberry.ID


@strawberry.input
class CreateJobInput:
    company_id: strawberry.ID
    title: str
    description: str
    required_skills: JSON
    preferred_skills: JSON
    experience_requirement: str | None = None
    evaluation_criteria: JSON | None = None
    status: JobStatus = JobStatus.DRAFT

