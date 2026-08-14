from __future__ import annotations

import logging

import strawberry

from app.db.models import Company, Job
from app.enums import AIProcessingState
from app.graphql.inputs import CreateJobInput
from app.graphql.types import (
    CreateJobPayload,
    JobType,
    OperationErrorCode,
    operation_error,
)


logger = logging.getLogger(__name__)


@strawberry.type
class JobMutation:
    @strawberry.mutation
    async def create_job(self, input: CreateJobInput) -> CreateJobPayload:
        try:
            company_id = int(input.company_id)
        except (TypeError, ValueError):
            return CreateJobPayload(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid company ID.",
                        "companyId",
                    )
                ],
            )

        title = input.title.strip()
        description = input.description.strip()
        if not title or len(title) > 255:
            return CreateJobPayload(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Title must contain between 1 and 255 characters.",
                        "title",
                    )
                ],
            )
        if not description:
            return CreateJobPayload(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Description must not be empty.",
                        "description",
                    )
                ],
            )

        try:
            if not await Company.exists(id=company_id):
                return CreateJobPayload(
                    success=False,
                    job=None,
                    errors=[
                        operation_error(
                            OperationErrorCode.NOT_FOUND,
                            "Company not found.",
                            "companyId",
                        )
                    ],
                )
            job = await Job.create(
                company_id=company_id,
                title=title,
                description=description,
                required_skills=input.required_skills,
                preferred_skills=input.preferred_skills,
                experience_requirement=input.experience_requirement,
                evaluation_criteria=input.evaluation_criteria or {},
                criteria_processing_state=(
                    AIProcessingState.COMPLETED
                    if input.evaluation_criteria
                    else AIProcessingState.NOT_STARTED
                ),
                status=input.status,
            )
        except Exception:
            logger.exception("Unable to create job")
            return CreateJobPayload(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to create the job.",
                    )
                ],
            )
        return CreateJobPayload(success=True, job=JobType.from_model(job), errors=[])
