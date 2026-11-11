from __future__ import annotations

import logging

import strawberry

from app.graphql.context import RECRUITER_ONLY, require_recruiter

from app.db.models import Job
from app.graphql.inputs import JobQueryInput, JobsQueryInput, PublicJobQueryInput
from app.graphql.types import (
    JobResult,
    JobsResult,
    JobType,
    OperationErrorCode,
    PublicJobResult,
    PublicJobsResult,
    PublicJobType,
    operation_error,
)
from app.services import PublicJobQueryService, RecruiterJobQueryService


logger = logging.getLogger(__name__)


@strawberry.type
class JobQuery:
    @strawberry.field
    async def public_job(self, input: PublicJobQueryInput) -> PublicJobResult:
        try:
            job_id = int(input.id)
            if job_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            return PublicJobResult(
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
            record = await PublicJobQueryService.get_open_job(job_id)
        except Exception:
            logger.exception("Unable to query public job %s", job_id)
            return PublicJobResult(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to load this job.",
                    )
                ],
            )
        if record is None:
            return PublicJobResult(
                success=False,
                job=None,
                errors=[
                    operation_error(
                        OperationErrorCode.NOT_FOUND,
                        "This job is not available.",
                        "id",
                    )
                ],
            )
        return PublicJobResult(
            success=True,
            job=PublicJobType.from_model(record),
            errors=[],
        )

    @strawberry.field
    async def public_jobs(self) -> PublicJobsResult:
        """Open roles for the public landing page; exposes only applicant-safe fields."""

        try:
            records = await PublicJobQueryService.list_open_jobs()
        except Exception:
            logger.exception("Unable to query public jobs")
            return PublicJobsResult(
                success=False,
                items=[],
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to load open roles.",
                    )
                ],
            )
        return PublicJobsResult(
            success=True,
            items=[PublicJobType.from_model(record) for record in records],
            errors=[],
        )

    @strawberry.field(permission_classes=RECRUITER_ONLY)
    async def jobs(
        self, info: strawberry.Info, input: JobsQueryInput | None = None
    ) -> JobsResult:
        recruiter = require_recruiter(info)
        try:
            query = Job.filter(company_id=recruiter.company_id)
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

    @strawberry.field(permission_classes=RECRUITER_ONLY)
    async def job(self, info: strawberry.Info, input: JobQueryInput) -> JobResult:
        recruiter = require_recruiter(info)
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
            query = RecruiterJobQueryService.with_statistics(
                Job.filter(id=job_id, company_id=recruiter.company_id)
            )
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
