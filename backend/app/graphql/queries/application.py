from __future__ import annotations

import logging

import strawberry

from app.db.models import Application, Job
from app.graphql.inputs import ApplicationQueryInput, ApplicationsQueryInput
from app.graphql.types import (
    ApplicationResult,
    ApplicationsResult,
    ApplicationType,
    OperationErrorCode,
    operation_error,
)


logger = logging.getLogger(__name__)


@strawberry.type
class ApplicationQuery:
    @strawberry.field
    async def applications(self, input: ApplicationsQueryInput) -> ApplicationsResult:
        try:
            job_id = int(input.job_id)
        except (TypeError, ValueError):
            return ApplicationsResult(
                success=False,
                items=[],
                total_count=0,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid job ID.",
                        "jobId",
                    )
                ],
            )

        try:
            if not await Job.exists(id=job_id):
                return ApplicationsResult(
                    success=False,
                    items=[],
                    total_count=0,
                    errors=[
                        operation_error(
                            OperationErrorCode.NOT_FOUND,
                            "Job not found.",
                            "jobId",
                        )
                    ],
                )
            query = Application.filter(job_id=job_id)
            if input.status is not None:
                query = query.filter(status=input.status)
            records = await query.select_related("candidate", "job").order_by("-applied_at")
            items = [ApplicationType.from_model(record) for record in records]
            return ApplicationsResult(
                success=True,
                items=items,
                total_count=len(items),
                errors=[],
            )
        except Exception:
            logger.exception("Unable to query applications for job %s", job_id)
            return ApplicationsResult(
                success=False,
                items=[],
                total_count=0,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to load applications.",
                    )
                ],
            )

    @strawberry.field
    async def application(self, input: ApplicationQueryInput) -> ApplicationResult:
        try:
            application_id = int(input.id)
        except (TypeError, ValueError):
            return ApplicationResult(
                success=False,
                application=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid application ID.",
                        "id",
                    )
                ],
            )

        try:
            record = await Application.get_or_none(id=application_id).select_related(
                "candidate", "job"
            )
        except Exception:
            logger.exception("Unable to query application %s", application_id)
            return ApplicationResult(
                success=False,
                application=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to load the application.",
                    )
                ],
            )
        if record is None:
            return ApplicationResult(
                success=False,
                application=None,
                errors=[
                    operation_error(
                        OperationErrorCode.NOT_FOUND,
                        "Application not found.",
                        "id",
                    )
                ],
            )
        return ApplicationResult(
            success=True,
            application=ApplicationType.from_model(record),
            errors=[],
        )
