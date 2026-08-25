from __future__ import annotations

import logging

import strawberry

from app.graphql.inputs import CompareCandidatesInput
from app.graphql.types import (
    CandidateComparisonResult,
    OperationError,
    OperationErrorCode,
    operation_error,
)
from app.services import CandidateComparisonService
from app.services.errors import (
    CandidateComparisonDataAccessError,
    CandidateComparisonError,
    CandidateComparisonProviderError,
    ComparisonApplicationNotFoundError,
    ComparisonJobMismatchError,
    ComparisonJobNotFoundError,
    IncompleteCandidateComparisonDataError,
    InvalidCandidateComparisonInputError,
    InvalidCandidateComparisonOutputError,
    MissingCandidateEvaluationError,
    MissingComparisonJobCriteriaError,
)


logger = logging.getLogger(__name__)


def _comparison_error(error: CandidateComparisonError) -> OperationError:
    if isinstance(error, ComparisonJobNotFoundError):
        return operation_error(OperationErrorCode.NOT_FOUND, str(error), "jobId")
    if isinstance(error, ComparisonApplicationNotFoundError):
        return operation_error(
            OperationErrorCode.NOT_FOUND,
            str(error),
            "applicationIds",
        )
    if isinstance(error, ComparisonJobMismatchError):
        return operation_error(
            OperationErrorCode.CONFLICT,
            str(error),
            "applicationIds",
        )
    if isinstance(error, MissingComparisonJobCriteriaError):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR,
            str(error),
            "jobId",
        )
    if isinstance(
        error,
        (
            MissingCandidateEvaluationError,
            IncompleteCandidateComparisonDataError,
        ),
    ):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR,
            str(error),
            "applicationIds",
        )
    if isinstance(error, InvalidCandidateComparisonInputError):
        return operation_error(
            OperationErrorCode.VALIDATION_ERROR,
            str(error),
            "applicationIds",
        )
    if isinstance(
        error,
        (
            CandidateComparisonProviderError,
            CandidateComparisonDataAccessError,
            InvalidCandidateComparisonOutputError,
        ),
    ):
        return operation_error(OperationErrorCode.INTERNAL_ERROR, str(error))
    return operation_error(
        OperationErrorCode.INTERNAL_ERROR,
        "Unable to compare candidates. Please try again.",
    )


def _parse_input(input: CompareCandidatesInput) -> tuple[int, list[int]]:
    try:
        job_id = int(input.job_id)
    except (TypeError, ValueError):
        raise InvalidCandidateComparisonInputError(
            "Job ID must be a positive integer."
        ) from None

    try:
        application_ids = [
            int(application_id) for application_id in input.application_ids
        ]
    except (TypeError, ValueError):
        raise InvalidCandidateComparisonInputError(
            "Application IDs must be positive integers."
        ) from None

    if job_id < 1:
        raise InvalidCandidateComparisonInputError("Job ID must be a positive integer.")
    if any(application_id < 1 for application_id in application_ids):
        raise InvalidCandidateComparisonInputError(
            "Application IDs must be positive integers."
        )
    if not 2 <= len(application_ids) <= 5:
        raise InvalidCandidateComparisonInputError(
            "Candidate comparison requires between 2 and 5 applications."
        )
    if len(application_ids) != len(set(application_ids)):
        raise InvalidCandidateComparisonInputError(
            "Application IDs must be unique. Remove duplicate selections."
        )
    return job_id, application_ids


@strawberry.type
class CandidateComparisonMutation:
    @strawberry.mutation
    async def compare_candidates(
        self,
        input: CompareCandidatesInput,
    ) -> CandidateComparisonResult:
        try:
            job_id, application_ids = _parse_input(input)
        except InvalidCandidateComparisonInputError as exc:
            field = "jobId" if str(exc).startswith("Job ID") else "applicationIds"
            return CandidateComparisonResult.failure(
                [
                    operation_error(
                        OperationErrorCode.VALIDATION_ERROR,
                        str(exc),
                        field,
                    )
                ]
            )

        try:
            comparison = await CandidateComparisonService().compare(
                job_id=job_id,
                application_ids=application_ids,
            )
        except CandidateComparisonError as exc:
            return CandidateComparisonResult.failure([_comparison_error(exc)])
        except Exception:
            logger.exception(
                "Unable to compare applications job_id=%s application_ids=%s",
                job_id,
                application_ids,
            )
            return CandidateComparisonResult.failure(
                [
                    operation_error(
                        OperationErrorCode.INTERNAL_ERROR,
                        "Unable to compare candidates. Please try again.",
                    )
                ]
            )

        return CandidateComparisonResult.success_result(comparison)
