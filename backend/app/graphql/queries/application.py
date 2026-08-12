from __future__ import annotations

import logging

import strawberry

from app.graphql.inputs import ApplicationQueryInput, ApplicationsQueryInput
from app.graphql.types import (
    ApplicationDetailType,
    ApplicationListItemType,
    ApplicationResult,
    ApplicationsResult,
    OffsetPageInfo,
    OperationErrorCode,
    operation_error,
)
from app.services import RecruiterApplicationQueryService
from app.services.errors import InvalidApplicationInformationError, JobNotFoundError


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
                page_info=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid job ID.",
                        "jobId",
                    )
                ],
            )

        pagination = input.pagination
        filters = input.filters
        try:
            page = await RecruiterApplicationQueryService.list_for_job(
                job_id=job_id,
                status=filters.status if filters and filters.status else input.status,
                minimum_fit_score=filters.minimum_fit_score if filters else None,
                candidate_search=filters.candidate_search if filters else None,
                sort=input.sort,
                limit=pagination.limit if pagination else 25,
                offset=pagination.offset if pagination else 0,
            )
            items = [
                ApplicationListItemType.from_models(
                    record.application,
                    record.resume,
                    record.evaluation,
                )
                for record in page.records
            ]
            return ApplicationsResult(
                success=True,
                items=items,
                total_count=page.total_count,
                page_info=OffsetPageInfo(
                    limit=page.limit,
                    offset=page.offset,
                    has_next_page=page.offset + len(items) < page.total_count,
                    has_previous_page=page.offset > 0,
                ),
                errors=[],
            )
        except JobNotFoundError as exc:
            return ApplicationsResult(
                success=False,
                items=[],
                total_count=0,
                page_info=None,
                errors=[
                    operation_error(OperationErrorCode.NOT_FOUND, str(exc), "jobId")
                ],
            )
        except InvalidApplicationInformationError as exc:
            return ApplicationsResult(
                success=False,
                items=[],
                total_count=0,
                page_info=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        str(exc),
                        "input",
                    )
                ],
            )
        except Exception:
            logger.exception("Unable to query applications for job %s", job_id)
            return ApplicationsResult(
                success=False,
                items=[],
                total_count=0,
                page_info=None,
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
            record = await RecruiterApplicationQueryService.get_detail(application_id)
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
            application=ApplicationDetailType.from_models(
                record.application,
                record.resume,
                record.evaluation,
                record.status_history,
                record.notes,
                record.outreach_emails,
            ),
            errors=[],
        )
