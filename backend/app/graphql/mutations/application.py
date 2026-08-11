from __future__ import annotations

import logging

import strawberry
from tortoise.transactions import in_transaction

from app.db.models import Application, ApplicationStatusHistory
from app.graphql.inputs import SubmitApplicationInput, UpdateApplicationStatusInput
from app.graphql.types import (
    ApplicationType,
    OperationError,
    OperationErrorCode,
    SubmitApplicationPayload,
    UpdateApplicationStatusPayload,
    operation_error,
)
from app.services import ApplicationService
from app.services.errors import (
    ApplicationSubmissionError,
    DuplicateApplicationError,
    InvalidApplicationInformationError,
    InvalidCandidateInformationError,
    InvalidResumeTypeError,
    JobClosedError,
    JobNotFoundError,
    MissingResumeError,
    ResumeTooLargeError,
)


logger = logging.getLogger(__name__)


def application_submission_error(error: ApplicationSubmissionError) -> OperationError:
    if isinstance(error, JobNotFoundError):
        return operation_error(OperationErrorCode.NOT_FOUND, str(error), "jobId")
    if isinstance(error, JobClosedError):
        return operation_error(OperationErrorCode.JOB_CLOSED, str(error), "jobId")
    if isinstance(error, DuplicateApplicationError):
        return operation_error(OperationErrorCode.CONFLICT, str(error), "jobId")
    if isinstance(error, InvalidCandidateInformationError):
        return operation_error(OperationErrorCode.VALIDATION_ERROR, str(error), "candidate")
    if isinstance(error, InvalidApplicationInformationError):
        return operation_error(OperationErrorCode.VALIDATION_ERROR, str(error), "input")
    if isinstance(error, ResumeTooLargeError):
        return operation_error(OperationErrorCode.FILE_TOO_LARGE, str(error), "resume")
    if isinstance(error, (InvalidResumeTypeError, MissingResumeError)):
        return operation_error(OperationErrorCode.INVALID_FILE, str(error), "resume")
    return operation_error(
        OperationErrorCode.INTERNAL_ERROR,
        "Unable to submit the application. Please try again.",
    )


@strawberry.type
class ApplicationMutation:
    @strawberry.mutation
    async def submit_application(
        self, input: SubmitApplicationInput
    ) -> SubmitApplicationPayload:
        try:
            application = await ApplicationService().submit(
                job_id=str(input.job_id),
                full_name=input.full_name,
                email=input.email,
                phone=input.phone,
                linkedin_url=input.linkedin_url,
                github_url=input.github_url,
                portfolio_url=input.portfolio_url,
                cover_letter=input.cover_letter,
                resume=input.resume,
            )
        except ApplicationSubmissionError as exc:
            return SubmitApplicationPayload(
                success=False,
                application=None,
                errors=[application_submission_error(exc)],
            )
        except Exception:
            logger.exception("Unexpected application submission failure")
            return SubmitApplicationPayload(
                success=False,
                application=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to submit the application. Please try again.",
                    )
                ],
            )
        return SubmitApplicationPayload(
            success=True,
            application=ApplicationType.from_model(application),
            errors=[],
        )

    @strawberry.mutation
    async def update_application_status(
        self,
        input: UpdateApplicationStatusInput,
    ) -> UpdateApplicationStatusPayload:
        try:
            application_id = int(input.application_id)
        except (TypeError, ValueError):
            return UpdateApplicationStatusPayload(
                success=False,
                application=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid application ID.",
                        "applicationId",
                    )
                ],
            )

        changed_by = input.changed_by.strip()
        if not changed_by or len(changed_by) > 320:
            return UpdateApplicationStatusPayload(
                success=False,
                application=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Changed by must contain between 1 and 320 characters.",
                        "changedBy",
                    )
                ],
            )

        try:
            async with in_transaction() as connection:
                application = await Application.get_or_none(
                    id=application_id, using_db=connection
                )
                if application is None:
                    return UpdateApplicationStatusPayload(
                        success=False,
                        application=None,
                        errors=[
                            operation_error(
                                OperationErrorCode.NOT_FOUND,
                                "Application not found.",
                                "applicationId",
                            )
                        ],
                    )

                previous_status = application.status
                application.status = input.status
                await application.save(
                    using_db=connection,
                    update_fields=["status", "updated_at"],
                )
                await ApplicationStatusHistory.create(
                    application_id=application.id,
                    previous_status=previous_status,
                    new_status=input.status,
                    changed_by=changed_by,
                    using_db=connection,
                )

            refreshed = await Application.get(id=application.id).select_related(
                "candidate", "job"
            )
        except Exception:
            logger.exception("Unable to update application %s", application_id)
            return UpdateApplicationStatusPayload(
                success=False,
                application=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to update the application status.",
                    )
                ],
            )

        return UpdateApplicationStatusPayload(
            success=True,
            application=ApplicationType.from_model(refreshed),
            errors=[],
        )
