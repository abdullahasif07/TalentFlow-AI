from __future__ import annotations

import strawberry
from strawberry.scalars import JSON

from app.db.models import Company, Job
from app.enums import JobStatus
from app.graphql.types import JobType


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


@strawberry.type
class JobMutation:
    @strawberry.mutation
    async def create_job(self, input: CreateJobInput) -> JobType:
        company_id = int(input.company_id)
        if not await Company.exists(id=company_id):
            raise ValueError(f"Company {company_id} does not exist")

        job = await Job.create(
            company_id=company_id,
            title=input.title,
            description=input.description,
            required_skills=input.required_skills,
            preferred_skills=input.preferred_skills,
            experience_requirement=input.experience_requirement,
            evaluation_criteria=input.evaluation_criteria or {},
            status=input.status,
        )
        return JobType.from_model(job)
