from __future__ import annotations

import logging

import strawberry

from app.graphql.context import RECRUITER_ONLY

from app.db.models import Company, Job
from app.enums import AIProcessingState
from app.graphql.context import require_recruiter
from app.services.ai_processing import AIProcessingService
from app.services.errors import AIProcessingRequestError
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
    @strawberry.mutation(permission_classes=RECRUITER_ONLY)
    async def create_job(
        self, info: strawberry.Info, input: CreateJobInput
    ) -> CreateJobPayload:
        recruiter = require_recruiter(info)
        company_id = recruiter.company_id
        if input.company_id is not None and str(input.company_id) != str(company_id):
            return CreateJobPayload(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Jobs can only be created for your own company.",
                        "companyId",
                    )
                ],
            )
        required_skills = _clean_skills(input.required_skills)
        preferred_skills = _clean_skills(input.preferred_skills)
        if required_skills is None or preferred_skills is None:
            return CreateJobPayload(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Skills must be a list of up to 30 short text values.",
                        "requiredSkills" if required_skills is None else "preferredSkills",
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
                required_skills=required_skills,
                preferred_skills=preferred_skills,
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

        if job.criteria_processing_state == AIProcessingState.NOT_STARTED:
            # New jobs get an AI scoring rubric automatically so applicants can be
            # evaluated without a separate manual step.
            try:
                await AIProcessingService.generate_job_criteria(job.id)
                await job.refresh_from_db()
            except AIProcessingRequestError as exc:
                logger.warning("Criteria generation was not queued for job %s: %s", job.id, exc)
            except Exception:
                logger.exception("Unable to queue criteria generation for job %s", job.id)
        return CreateJobPayload(success=True, job=JobType.from_model(job), errors=[])


def _clean_skills(value: object) -> list[str] | None:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 30:
        return None
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        skill = item.strip()
        if len(skill) > 100:
            return None
        if skill and skill.casefold() not in {existing.casefold() for existing in cleaned}:
            cleaned.append(skill)
    return cleaned
