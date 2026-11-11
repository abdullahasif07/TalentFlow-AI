from __future__ import annotations

import hashlib
import logging

import strawberry

from app.config import settings
from app.db.models import AIEvaluation, Job
from app.graphql.context import RECRUITER_ONLY, job_visible_to
from app.schemas import CandidateComparison
from app.services.usage_guard import cache_get, cache_set, ensure_ai_budget_available

from app.graphql.inputs import CompareCandidatesInput
from app.graphql.types import (
    CandidateComparisonResult,
    OperationError,
    OperationErrorCode,
    operation_error,
)
from app.services import CandidateComparisonService
from app.services.errors import (
    AIUsageLimitError,
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
    @strawberry.mutation(permission_classes=RECRUITER_ONLY)
    async def compare_candidates(
        self,
        info: strawberry.Info,
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

        if not await job_visible_to(info, job_id):
            return CandidateComparisonResult.failure(
                [operation_error(OperationErrorCode.NOT_FOUND, "Job record not found.", "jobId")]
            )

        try:
            cache_key = await _comparison_cache_key(job_id, application_ids)
            cached = await cache_get(cache_key) if cache_key else None
            if cached:
                try:
                    return CandidateComparisonResult.success_result(
                        CandidateComparison.model_validate_json(cached)
                    )
                except ValueError:
                    logger.warning("Ignoring an unreadable cached comparison %s", cache_key)
            await ensure_ai_budget_available()
            comparison = await CandidateComparisonService().compare(
                job_id=job_id,
                application_ids=application_ids,
            )
            if cache_key:
                await cache_set(
                    cache_key,
                    comparison.model_dump_json(),
                    ttl_seconds=settings.comparison_cache_seconds,
                )
        except AIUsageLimitError as exc:
            return CandidateComparisonResult.failure(
                [operation_error(OperationErrorCode.RATE_LIMITED, str(exc))]
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


async def _comparison_cache_key(job_id: int, application_ids: list[int]) -> str | None:
    """Key a comparison on its inputs so any re-evaluation or job edit misses the cache."""

    job = await Job.get_or_none(id=job_id)
    if job is None:
        return None
    evaluations = await AIEvaluation.filter(application_id__in=application_ids).only(
        "application_id", "updated_at"
    )
    if len(evaluations) != len(application_ids):
        return None
    fingerprint = "|".join(
        [job.updated_at.isoformat()]
        + sorted(f"{item.application_id}:{item.updated_at.isoformat()}" for item in evaluations)
    )
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:24]
    ordered_ids = "-".join(str(application_id) for application_id in application_ids)
    return f"comparison:{job_id}:{ordered_ids}:{digest}"
