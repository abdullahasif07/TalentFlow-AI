from __future__ import annotations

import logging

import strawberry

from app.graphql.context import RECRUITER_ONLY, application_visible_to, job_visible_to

from app.graphql.inputs import (
    ApplicationQueryInput,
    ApplicationsQueryInput,
    PublicApplicationStatusInput,
    RecommendedCandidatesInput,
)
from app.graphql.types import (
    ApplicationDetailType,
    ApplicationListItemType,
    ApplicationResult,
    ApplicationsResult,
    OffsetPageInfo,
    OperationErrorCode,
    PublicApplicationProgress,
    PublicApplicationStatusResult,
    RecommendedCandidateType,
    RecommendedCandidatesResult,
    operation_error,
)
from app.services import RecruiterApplicationQueryService
from app.services.application_progress import (
    application_id_from_status_token,
    get_application_progress,
)
from app.services.errors import InvalidApplicationInformationError, JobNotFoundError


logger = logging.getLogger(__name__)


@strawberry.type
class ApplicationQuery:
    @strawberry.field
    async def public_application_status(
        self, input: PublicApplicationStatusInput
    ) -> PublicApplicationStatusResult:
        """Coarse progress for an applicant, unlocked by their receipt's status token."""

        application_id = application_id_from_status_token(input.token.strip())
        if application_id is None:
            return PublicApplicationStatusResult(
                success=False,
                progress=None,
                errors=[
                    operation_error(
                        OperationErrorCode.NOT_FOUND,
                        "This application status link is invalid or has expired.",
                        "token",
                    )
                ],
            )
        try:
            progress = await get_application_progress(application_id)
        except Exception:
            logger.exception("Unable to load progress for application %s", application_id)
            return PublicApplicationStatusResult(
                success=False,
                progress=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to load the application status.",
                    )
                ],
            )
        if progress is None:
            return PublicApplicationStatusResult(
                success=False,
                progress=None,
                errors=[
                    operation_error(
                        OperationErrorCode.NOT_FOUND,
                        "This application status link is invalid or has expired.",
                        "token",
                    )
                ],
            )
        return PublicApplicationStatusResult(
            success=True,
            progress=PublicApplicationProgress.from_progress(progress),
            errors=[],
        )

    @strawberry.field(permission_classes=RECRUITER_ONLY)
    async def recommended_candidates(
        self,
        info: strawberry.Info,
        input: RecommendedCandidatesInput,
    ) -> RecommendedCandidatesResult:
        try:
            job_id = int(input.job_id)
            if job_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            return RecommendedCandidatesResult(
                success=False,
                items=[],
                total_count=0,
                limit=input.limit,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid job ID.",
                        "jobId",
                    )
                ],
            )

        try:
            if not await job_visible_to(info, job_id):
                raise JobNotFoundError("Job not found.")
            page = await RecruiterApplicationQueryService.list_recommended_for_job(
                job_id=job_id,
                limit=input.limit,
            )
        except JobNotFoundError as exc:
            return RecommendedCandidatesResult(
                success=False,
                items=[],
                total_count=0,
                limit=input.limit,
                errors=[
                    operation_error(OperationErrorCode.NOT_FOUND, str(exc), "jobId")
                ],
            )
        except InvalidApplicationInformationError as exc:
            return RecommendedCandidatesResult(
                success=False,
                items=[],
                total_count=0,
                limit=input.limit,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        str(exc),
                        "limit",
                    )
                ],
            )
        except Exception:
            logger.exception("Unable to load recommended candidates for job %s", job_id)
            return RecommendedCandidatesResult(
                success=False,
                items=[],
                total_count=0,
                limit=input.limit,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to load recommended candidates.",
                    )
                ],
            )

        return RecommendedCandidatesResult(
            success=True,
            items=[
                RecommendedCandidateType.from_models(
                    record.application,
                    record.evaluation,
                )
                for record in page.records
            ],
            total_count=page.total_count,
            limit=page.limit,
            errors=[],
        )

    @strawberry.field(permission_classes=RECRUITER_ONLY)
    async def applications(
        self, info: strawberry.Info, input: ApplicationsQueryInput
    ) -> ApplicationsResult:
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
            if not await job_visible_to(info, job_id):
                raise JobNotFoundError("Job not found.")
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

    @strawberry.field(permission_classes=RECRUITER_ONLY)
    async def application(
        self, info: strawberry.Info, input: ApplicationQueryInput
    ) -> ApplicationResult:
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
            record = (
                await RecruiterApplicationQueryService.get_detail(application_id)
                if await application_visible_to(info, application_id)
                else None
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
