from __future__ import annotations

import logging

import strawberry

from app.graphql.inputs import (
    AddApplicationNoteInput,
    BulkUpdateApplicationStatusInput,
    SubmitApplicationInput,
    UpdateApplicationStatusInput,
)
from app.graphql.types import (
    AddApplicationNotePayload,
    ApplicationNoteType,
    ApplicationStatusUpdateFailure,
    ApplicationType,
    BulkUpdateApplicationStatusPayload,
    OperationError,
    OperationErrorCode,
    SubmitApplicationPayload,
    UpdateApplicationStatusPayload,
    operation_error,
)
from app.services import (
    ApplicationNoteService,
    ApplicationPipelineService,
    ApplicationService,
)
from app.services.errors import (
    ApplicationNotFoundError,
    ApplicationNoteError,
    ApplicationPipelineError,
    ApplicationSubmissionError,
    DuplicateApplicationError,
    InvalidApplicationInformationError,
    InvalidApplicationNoteError,
    InvalidCandidateInformationError,
    InvalidPipelineActorError,
    InvalidResumeTypeError,
    JobClosedError,
    JobNotFoundError,
    MissingResumeError,
    RecruiterCompanyMismatchError,
    RecruiterNotFoundError,
    ResumeTooLargeError,
)


logger = logging.getLogger(__name__)
MAX_BULK_APPLICATIONS = 100


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


def pipeline_error(error: ApplicationPipelineError) -> OperationError:
    if isinstance(error, (ApplicationNotFoundError, RecruiterNotFoundError)):
        field = "applicationId" if isinstance(error, ApplicationNotFoundError) else "recruiterId"
        return operation_error(OperationErrorCode.NOT_FOUND, str(error), field)
    if isinstance(error, RecruiterCompanyMismatchError):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR, str(error), "recruiterId"
        )
    if isinstance(error, InvalidPipelineActorError):
        return operation_error(OperationErrorCode.VALIDATION_ERROR, str(error), "changedBy")
    return operation_error(OperationErrorCode.VALIDATION_ERROR, str(error), "status")


def note_error(error: ApplicationNoteError | ApplicationPipelineError) -> OperationError:
    if isinstance(error, ApplicationNotFoundError):
        return operation_error(OperationErrorCode.NOT_FOUND, str(error), "applicationId")
    if isinstance(error, RecruiterNotFoundError):
        return operation_error(OperationErrorCode.NOT_FOUND, str(error), "recruiterId")
    if isinstance(error, RecruiterCompanyMismatchError):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR, str(error), "recruiterId"
        )
    if isinstance(error, InvalidApplicationNoteError):
        return operation_error(OperationErrorCode.VALIDATION_ERROR, str(error), "content")
    return operation_error(OperationErrorCode.VALIDATION_ERROR, str(error), "recruiterId")


def parse_optional_id(value: strawberry.ID | None) -> int | None:
    if value is None:
        return None
    parsed = int(value)
    if parsed < 1:
        raise ValueError
    return parsed


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

        try:
            recruiter_id = parse_optional_id(input.recruiter_id)
        except (TypeError, ValueError):
            return UpdateApplicationStatusPayload(
                success=False,
                application=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid recruiter ID.",
                        "recruiterId",
                    )
                ],
            )

        try:
            application = await ApplicationPipelineService.update_status(
                application_id=application_id,
                new_status=input.status,
                changed_by=input.changed_by,
                recruiter_id=recruiter_id,
                automated=input.automated,
            )
        except ApplicationPipelineError as exc:
            return UpdateApplicationStatusPayload(
                success=False,
                application=None,
                errors=[pipeline_error(exc)],
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
            application=ApplicationType.from_model(application),
            errors=[],
        )

    @strawberry.mutation
    async def bulk_update_application_status(
        self,
        input: BulkUpdateApplicationStatusInput,
    ) -> BulkUpdateApplicationStatusPayload:
        if not input.application_ids or len(input.application_ids) > MAX_BULK_APPLICATIONS:
            return BulkUpdateApplicationStatusPayload(
                success=False,
                applications=[],
                failures=[],
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        f"Provide between 1 and {MAX_BULK_APPLICATIONS} application IDs.",
                        "applicationIds",
                    )
                ],
            )
        try:
            recruiter_id = parse_optional_id(input.recruiter_id)
        except (TypeError, ValueError):
            return BulkUpdateApplicationStatusPayload(
                success=False,
                applications=[],
                failures=[],
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid recruiter ID.",
                        "recruiterId",
                    )
                ],
            )

        applications: list[ApplicationType] = []
        failures: list[ApplicationStatusUpdateFailure] = []
        seen_ids: set[str] = set()
        for raw_id in input.application_ids:
            display_id = str(raw_id)
            if display_id in seen_ids:
                continue
            seen_ids.add(display_id)
            try:
                application_id = int(raw_id)
                if application_id < 1:
                    raise ValueError
                application = await ApplicationPipelineService.update_status(
                    application_id=application_id,
                    new_status=input.status,
                    changed_by=input.changed_by,
                    recruiter_id=recruiter_id,
                    automated=input.automated,
                )
                applications.append(ApplicationType.from_model(application))
            except (TypeError, ValueError):
                failures.append(
                    ApplicationStatusUpdateFailure(
                        application_id=strawberry.ID(display_id),
                        errors=[
                            operation_error(
                                OperationErrorCode.VALIDATION_ERROR,
                                "Invalid application ID.",
                                "applicationIds",
                            )
                        ],
                    )
                )
            except ApplicationPipelineError as exc:
                failures.append(
                    ApplicationStatusUpdateFailure(
                        application_id=strawberry.ID(display_id),
                        errors=[pipeline_error(exc)],
                    )
                )
            except Exception:
                logger.exception("Unable to update application %s", display_id)
                failures.append(
                    ApplicationStatusUpdateFailure(
                        application_id=strawberry.ID(display_id),
                        errors=[
                            operation_error(
                                OperationErrorCode.INTERNAL_ERROR,
                                "Unable to update the application status.",
                            )
                        ],
                    )
                )

        return BulkUpdateApplicationStatusPayload(
            success=not failures,
            applications=applications,
            failures=failures,
            errors=[],
        )

    @strawberry.mutation
    async def add_application_note(
        self,
        input: AddApplicationNoteInput,
    ) -> AddApplicationNotePayload:
        try:
            application_id = int(input.application_id)
            if application_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            return AddApplicationNotePayload(
                success=False,
                note=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid application ID.",
                        "applicationId",
                    )
                ],
            )
        try:
            recruiter_id = parse_optional_id(input.recruiter_id)
        except (TypeError, ValueError):
            return AddApplicationNotePayload(
                success=False,
                note=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid recruiter ID.",
                        "recruiterId",
                    )
                ],
            )

        try:
            note = await ApplicationNoteService.add_note(
                application_id=application_id,
                content=input.content,
                recruiter_id=recruiter_id,
            )
        except (ApplicationNoteError, ApplicationPipelineError) as exc:
            return AddApplicationNotePayload(
                success=False,
                note=None,
                errors=[note_error(exc)],
            )
        except Exception:
            logger.exception("Unable to add a note to application %s", application_id)
            return AddApplicationNotePayload(
                success=False,
                note=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to add the application note.",
                    )
                ],
            )

        return AddApplicationNotePayload(
            success=True,
            note=ApplicationNoteType.from_model(note),
            errors=[],
        )
