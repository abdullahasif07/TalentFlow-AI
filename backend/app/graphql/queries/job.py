from __future__ import annotations

import logging

import strawberry

from app.db.models import Job
from app.graphql.inputs import JobQueryInput, JobsQueryInput
from app.graphql.types import (
    JobResult,
    JobsResult,
    JobType,
    OperationErrorCode,
    operation_error,
)
from app.services import RecruiterJobQueryService


logger = logging.getLogger(__name__)


@strawberry.type
class JobQuery:
    @strawberry.field
    async def jobs(self, input: JobsQueryInput | None = None) -> JobsResult:
        try:
            query = Job.all()
            if input and input.company_id is not None:
                try:
                    company_id = int(input.company_id)
                except (TypeError, ValueError):
                    return JobsResult(
                        success=False,
                        items=[],
                        total_count=0,
                        errors=[
                            operation_error(
                                OperationErrorCode.VALIDATION_ERROR,
                                "Invalid company ID.",
                                "companyId",
                            )
                        ],
                    )
                query = query.filter(company_id=company_id)
            if input and input.status is not None:
                query = query.filter(status=input.status)

            query = RecruiterJobQueryService.with_statistics(query)
            records = await query.order_by("-created_at")
            items = [JobType.from_model(record) for record in records]
            return JobsResult(success=True, items=items, total_count=len(items), errors=[])
        except Exception:
            logger.exception("Unable to query jobs")
            return JobsResult(
                success=False,
                items=[],
                total_count=0,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to load jobs.",
                    )
                ],
            )

    @strawberry.field
    async def job(self, input: JobQueryInput) -> JobResult:
        try:
            job_id = int(input.id)
        except (TypeError, ValueError):
            return JobResult(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid job ID.",
                        "id",
                    )
                ],
            )

        try:
            query = RecruiterJobQueryService.with_statistics(Job.filter(id=job_id))
            record = await query.first()
        except Exception:
            logger.exception("Unable to query job %s", job_id)
            return JobResult(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to load the job.",
                    )
                ],
            )
        if record is None:
            return JobResult(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.NOT_FOUND,
                        "Job not found.",
                        "id",
                    )
                ],
            )
        return JobResult(success=True, job=JobType.from_model(record), errors=[])
