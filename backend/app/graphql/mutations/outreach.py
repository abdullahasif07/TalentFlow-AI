from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import strawberry

from app.db.models import OutreachEmail
from app.graphql.inputs import (
    ApproveOutreachInput,
    GenerateOutreachInput,
    SendOutreachInput,
    UpdateOutreachDraftInput,
)
from app.graphql.types import (
    OperationError,
    OperationErrorCode,
    OutreachEmailType,
    OutreachMutationPayload,
    operation_error,
)
from app.services import OutreachGenerationService, OutreachWorkflowService
from app.services.errors import (
    InvalidOutreachBodyError,
    InvalidOutreachContextError,
    InvalidOutreachInstructionError,
    InvalidOutreachOutputError,
    InvalidOutreachStatusTransitionError,
    InvalidOutreachSubjectError,
    MissingOutreachResumeDataError,
    OutreachApplicationNotFoundError,
    OutreachCandidateNotFoundError,
    OutreachCompanyNotFoundError,
    OutreachDeliveryError,
    OutreachGenerationError,
    OutreachGenerationProviderError,
    OutreachJobNotFoundError,
    OutreachNotFoundError,
    OutreachWorkflowError,
)


logger = logging.getLogger(__name__)


def _parse_id(value: strawberry.ID) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ValueError
    return parsed


def _generation_error(error: OutreachGenerationError) -> OperationError:
    if isinstance(
        error,
        (
            OutreachApplicationNotFoundError,
            OutreachCandidateNotFoundError,
            OutreachJobNotFoundError,
            OutreachCompanyNotFoundError,
        ),
    ):
        return operation_error(OperationErrorCode.NOT_FOUND, str(error), "applicationId")
    if isinstance(error, InvalidOutreachInstructionError):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR,
            str(error),
            "instruction",
        )
    if isinstance(
        error,
        (
            MissingOutreachResumeDataError,
            InvalidOutreachContextError,
            InvalidOutreachOutputError,
        ),
    ):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR,
            str(error),
            "applicationId",
        )
    if isinstance(error, OutreachGenerationProviderError):
        return operation_error(OperationErrorCode.INTERNAL_ERROR, str(error))
    return operation_error(
        OperationErrorCode.INTERNAL_ERROR,
        "Unable to generate outreach. Please try again.",
    )


def _workflow_error(error: OutreachWorkflowError) -> OperationError:
    if isinstance(error, OutreachNotFoundError):
        return operation_error(OperationErrorCode.NOT_FOUND, str(error), "outreachId")
    if isinstance(error, InvalidOutreachSubjectError):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR,
            str(error),
            "subject",
        )
    if isinstance(error, InvalidOutreachBodyError):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR,
            str(error),
            "body",
        )
    if isinstance(error, InvalidOutreachStatusTransitionError):
        return operation_error(OperationErrorCode.CONFLICT, str(error), "status")
    if isinstance(error, OutreachDeliveryError):
        return operation_error(OperationErrorCode.INTERNAL_ERROR, str(error))
    return operation_error(
        OperationErrorCode.INTERNAL_ERROR,
        "Unable to update outreach. Please try again.",
    )


async def _run_workflow_action(
    *,
    raw_id: strawberry.ID,
    action: Callable[[int], Awaitable[OutreachEmail]],
    log_action: str,
) -> OutreachMutationPayload:
    try:
        outreach_id = _parse_id(raw_id)
    except (TypeError, ValueError):
        return OutreachMutationPayload(
            success=False,
            outreach=None,
            errors=[
                operation_error(
                    OperationErrorCode.VALIDATION_ERROR,
                    "Invalid outreach ID.",
                    "outreachId",
                )
            ],
        )

    try:
        outreach = await action(outreach_id)
    except OutreachWorkflowError as exc:
        return OutreachMutationPayload(
            success=False,
            outreach=None,
            errors=[_workflow_error(exc)],
        )
    except Exception:
        logger.exception("Unable to %s outreach_id=%s", log_action, outreach_id)
        return OutreachMutationPayload(
            success=False,
            outreach=None,
            errors=[
                operation_error(
                    OperationErrorCode.INTERNAL_ERROR,
                    f"Unable to {log_action} outreach. Please try again.",
                )
            ],
        )

    return OutreachMutationPayload(
        success=True,
        outreach=OutreachEmailType.from_model(outreach),
        errors=[],
    )


@strawberry.type
class OutreachMutation:
    @strawberry.mutation
    async def generate_outreach(
        self,
        input: GenerateOutreachInput,
    ) -> OutreachMutationPayload:
        try:
            application_id = _parse_id(input.application_id)
        except (TypeError, ValueError):
            return OutreachMutationPayload(
                success=False,
                outreach=None,
                errors=[
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        "Invalid application ID.",
                        "applicationId",
                    )
                ],
            )

        try:
            outreach = await OutreachGenerationService().generate_and_save(
                application_id,
                instruction=input.instruction,
            )
        except OutreachGenerationError as exc:
            return OutreachMutationPayload(
                success=False,
                outreach=None,
                errors=[_generation_error(exc)],
            )
        except Exception:
            logger.exception("Unable to generate outreach for application_id=%s", application_id)
            return OutreachMutationPayload(
                success=False,
                outreach=None,
                errors=[
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to generate outreach. Please try again.",
                    )
                ],
            )

        return OutreachMutationPayload(
            success=True,
            outreach=OutreachEmailType.from_model(outreach),
            errors=[],
        )

    @strawberry.mutation
    async def update_outreach_draft(
        self,
        input: UpdateOutreachDraftInput,
    ) -> OutreachMutationPayload:
        async def update(outreach_id: int) -> OutreachEmail:
            return await OutreachWorkflowService.update_draft(
                outreach_id=outreach_id,
                subject=input.subject,
                body=input.body,
            )

        return await _run_workflow_action(
            raw_id=input.outreach_id,
            action=update,
            log_action="update",
        )

    @strawberry.mutation
    async def approve_outreach(
        self,
        input: ApproveOutreachInput,
    ) -> OutreachMutationPayload:
        return await _run_workflow_action(
            raw_id=input.outreach_id,
            action=OutreachWorkflowService.approve,
            log_action="approve",
        )

    @strawberry.mutation
    async def send_outreach(
        self,
        input: SendOutreachInput,
    ) -> OutreachMutationPayload:
        return await _run_workflow_action(
            raw_id=input.outreach_id,
            action=OutreachWorkflowService().send,
            log_action="send",
        )
