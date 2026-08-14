from __future__ import annotations

from datetime import datetime
from typing import Any

import strawberry
from strawberry.scalars import JSON

from app.db.models import Job
from app.enums import AIProcessingState, JobStatus
from app.graphql.types.common import OperationError


@strawberry.type
class JobSummary:
    id: strawberry.ID
    title: str
    status: JobStatus
    criteria_processing_state: AIProcessingState

    @classmethod
    def from_model(cls, job: Job) -> "JobSummary":
        return cls(
            id=strawberry.ID(str(job.id)),
            title=job.title,
            status=job.status,
            criteria_processing_state=job.criteria_processing_state,
        )


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
    criteria_processing_state: AIProcessingState
    status: JobStatus
    applicant_count: int
    shortlisted_count: int
    contacted_count: int
    interview_count: int
    hired_count: int
    recommended_candidate_count: int
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
            criteria_processing_state=job.criteria_processing_state,
            status=job.status,
            applicant_count=getattr(job, "applicant_count", 0),
            shortlisted_count=getattr(job, "shortlisted_count", 0),
            contacted_count=getattr(job, "contacted_count", 0),
            interview_count=getattr(job, "interview_count", 0),
            hired_count=getattr(job, "hired_count", 0),
            recommended_candidate_count=getattr(
                job, "recommended_candidate_count", 0
            ),
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


@strawberry.type
class JobsResult:
    success: bool
    items: list[JobType]
    total_count: int
    errors: list[OperationError]


@strawberry.type
class JobResult:
    success: bool
    job: JobType | None
    errors: list[OperationError]


@strawberry.type
class CreateJobPayload:
    success: bool
    job: JobType | None
    errors: list[OperationError]
