from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import strawberry

from app.enums import AIProcessingState
from app.graphql.inputs import (
    GenerateCandidateEvaluationInput,
    GenerateJobCriteriaInput,
    ProcessApplicationResumeInput,
    ScreenJobApplicantsInput,
)
from app.graphql.types import (
    AIProcessingPayload,
    BatchScreeningPayload,
    OperationError,
    OperationErrorCode,
    operation_error,
)
from app.services import AIProcessingService
from app.services.ai_processing import ProcessingRequest
from app.services.errors import (
    AIProcessingRequestError,
    ProcessingPrerequisiteError,
    ProcessingQueueError,
    ProcessingResourceNotFoundError,
)


logger = logging.getLogger(__name__)


def _parse_id(value: strawberry.ID) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ValueError
    return parsed


def _processing_error(
    error: AIProcessingRequestError,
    field: str,
) -> OperationError:
    if isinstance(error, ProcessingResourceNotFoundError):
        return operation_error(OperationErrorCode.NOT_FOUND, str(error), field)
    if isinstance(error, ProcessingPrerequisiteError):
        return operation_error(OperationErrorCode.VALIDATION_ERROR, str(error), field)
    if isinstance(error, ProcessingQueueError):
        return operation_error(OperationErrorCode.INTERNAL_ERROR, str(error))
    return operation_error(OperationErrorCode.INTERNAL_ERROR, "Unable to queue AI processing.")


async def _enqueue_resource(
    *,
    raw_id: strawberry.ID,
    field: str,
    enqueue: Callable[[int], Awaitable[ProcessingRequest]],
) -> AIProcessingPayload:
    try:
        resource_id = _parse_id(raw_id)
    except (TypeError, ValueError):
        return AIProcessingPayload(
            success=False,
            accepted=False,
            resource_id=None,
            state=AIProcessingState.NOT_STARTED,
            message="AI processing was not queued.",
            task_id=None,
            errors=[
                operation_error(
                    OperationErrorCode.VALIDATION_ERROR,
                    f"Invalid {field}.",
                    field,
                )
            ],
        )

    try:
        request = await enqueue(resource_id)
    except AIProcessingRequestError as exc:
        return AIProcessingPayload(
            success=False,
            accepted=False,
            resource_id=strawberry.ID(str(resource_id)),
            state=(
                AIProcessingState.FAILED
                if isinstance(exc, ProcessingQueueError)
                else AIProcessingState.NOT_STARTED
            ),
            message=str(exc),
            task_id=None,
            errors=[_processing_error(exc, field)],
        )
    except Exception:
        logger.exception("Unable to enqueue AI processing for %s=%s", field, resource_id)
        return AIProcessingPayload(
            success=False,
            accepted=False,
            resource_id=strawberry.ID(str(resource_id)),
            state=AIProcessingState.FAILED,
            message="Unable to queue AI processing.",
            task_id=None,
            errors=[
                operation_error(
                    OperationErrorCode.INTERNAL_ERROR,
                    "Unable to queue AI processing.",
                )
            ],
        )

    return AIProcessingPayload(
        success=True,
        accepted=request.accepted,
        resource_id=strawberry.ID(str(request.resource_id)),
        state=request.state,
        message=request.message,
        task_id=request.task_id,
        errors=[],
    )


@strawberry.type
class AIProcessingMutation:
    @strawberry.mutation
    async def generate_job_criteria(
        self,
        input: GenerateJobCriteriaInput,
    ) -> AIProcessingPayload:
        return await _enqueue_resource(
            raw_id=input.job_id,
            field="jobId",
            enqueue=AIProcessingService.generate_job_criteria,
        )

    @strawberry.mutation
    async def process_application_resume(
        self,
        input: ProcessApplicationResumeInput,
    ) -> AIProcessingPayload:
        return await _enqueue_resource(
            raw_id=input.application_id,
            field="applicationId",
            enqueue=AIProcessingService.process_application_resume,
        )

    @strawberry.mutation
    async def generate_candidate_evaluation(
        self,
        input: GenerateCandidateEvaluationInput,
    ) -> AIProcessingPayload:
        return await _enqueue_resource(
            raw_id=input.application_id,
            field="applicationId",
            enqueue=AIProcessingService.generate_candidate_evaluation,
        )

    @strawberry.mutation
    async def screen_job_applicants(
        self,
        input: ScreenJobApplicantsInput,
    ) -> BatchScreeningPayload:
        try:
            job_id = _parse_id(input.job_id)
        except (TypeError, ValueError):
            return BatchScreeningPayload(
                success=False,
                accepted=False,
                job_id=None,
                state=AIProcessingState.NOT_STARTED,
                message="Applicant screening was not queued.",
                queued_count=0,
                application_ids=[],
                failed_application_ids=[],
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid job ID.",
                        "jobId",
                    )
                ],
            )

        try:
            request = await AIProcessingService.screen_job_applicants(job_id)
        except AIProcessingRequestError as exc:
            return BatchScreeningPayload(
                success=False,
                accepted=False,
                job_id=strawberry.ID(str(job_id)),
                state=AIProcessingState.NOT_STARTED,
                message=str(exc),
                queued_count=0,
                application_ids=[],
                failed_application_ids=[],
                errors=[_processing_error(exc, "jobId")],
            )
        except Exception:
            logger.exception("Unable to screen applicants for job_id=%s", job_id)
            return BatchScreeningPayload(
                success=False,
                accepted=False,
                job_id=strawberry.ID(str(job_id)),
                state=AIProcessingState.FAILED,
                message="Unable to queue applicant screening.",
                queued_count=0,
                application_ids=[],
                failed_application_ids=[],
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to queue applicant screening.",
                    )
                ],
            )

        accepted = bool(request.accepted_application_ids)
        state = (
            AIProcessingState.PROCESSING
            if accepted
            else (
                AIProcessingState.FAILED
                if request.failed_application_ids
                else AIProcessingState.NOT_STARTED
            )
        )
        return BatchScreeningPayload(
            success=not request.failed_application_ids,
            accepted=accepted,
            job_id=strawberry.ID(str(job_id)),
            state=state,
            message=request.message,
            queued_count=len(request.accepted_application_ids),
            application_ids=[
                strawberry.ID(str(application_id))
                for application_id in request.accepted_application_ids
            ],
            failed_application_ids=[
                strawberry.ID(str(application_id))
                for application_id in request.failed_application_ids
            ],
            errors=[],
        )
