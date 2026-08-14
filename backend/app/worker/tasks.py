from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from celery.exceptions import Retry
from celery.utils.log import get_task_logger
from tortoise.exceptions import DBConnectionError, OperationalError

from app.config import settings
from app.db.models import Application, Job, Resume
from app.enums import AIProcessingState
from app.services.ai.client import LLMConfigurationError
from app.services.ai.candidate_evaluation import CandidateEvaluationService
from app.services.ai.job_criteria import JobCriteriaService
from app.services.ai.resume_parser import ResumeParsingService
from app.services.errors import (
    CandidateEvaluationError,
    CandidateEvaluationProviderError,
    EvaluationApplicationNotFoundError,
    JobCriteriaError,
    JobCriteriaProviderError,
    MissingJobEvaluationCriteriaError,
    MissingStructuredResumeDataError,
    ResumeExtractionError,
    ResumeParsingError,
    ResumeParsingProviderError,
    ResumeRecordNotFoundError,
)
from app.services.resume_extraction import ResumeExtractionService
from app.worker.celery_app import celery_app
from app.worker.runtime import run_async_db_operation


logger = get_task_logger(__name__)

TransientTaskError = (
    CandidateEvaluationProviderError,
    JobCriteriaProviderError,
    ResumeParsingProviderError,
    DBConnectionError,
    OperationalError,
    ConnectionError,
    TimeoutError,
)
PermanentTaskError = (
    CandidateEvaluationError,
    EvaluationApplicationNotFoundError,
    JobCriteriaError,
    MissingJobEvaluationCriteriaError,
    MissingStructuredResumeDataError,
    ResumeExtractionError,
    ResumeParsingError,
    ResumeRecordNotFoundError,
    LLMConfigurationError,
)


async def process_resume_workflow(application_id: int) -> dict[str, Any]:
    application = await Application.get_or_none(id=application_id)
    if application is None:
        raise EvaluationApplicationNotFoundError("Application record not found.")

    resume = await Resume.get_or_none(candidate_id=application.candidate_id)
    if resume is None:
        raise ResumeRecordNotFoundError("Resume record not found.")

    raw_text = await ResumeExtractionService().extract_and_save(resume.id)
    parsed_resume = await ResumeParsingService().parse_and_save(resume.id)
    return {
        "application_id": application.id,
        "resume_id": resume.id,
        "raw_text_length": len(raw_text),
        "parsed_field_count": len(parsed_resume.model_dump()),
        "status": "processed",
    }


async def generate_job_criteria_workflow(job_id: int) -> dict[str, Any]:
    criteria = await JobCriteriaService().generate_and_save(job_id)
    return {
        "job_id": job_id,
        "category_count": len(criteria.evaluation_categories),
        "status": "generated",
    }


async def evaluate_application_workflow(application_id: int) -> dict[str, Any]:
    evaluation = await CandidateEvaluationService().evaluate_and_save(application_id)
    return {
        "application_id": application_id,
        "overall_score": evaluation.overall_score,
        "status": "evaluated",
    }


def _execute_task(
    task: Any,
    *,
    operation: Callable[[], Awaitable[dict[str, Any]]],
    entity_name: str,
    entity_id: int,
) -> dict[str, Any]:
    try:
        result = run_async_db_operation(operation)
    except TransientTaskError as exc:
        retry_number = int(task.request.retries)
        countdown = min(
            settings.celery_retry_backoff_seconds * (2**retry_number),
            300,
        )
        logger.warning(
            "%s task failed temporarily for %s=%s; retrying in %ss: %s",
            task.name,
            entity_name,
            entity_id,
            countdown,
            exc,
        )
        raise task.retry(exc=exc, countdown=countdown) from exc
    except PermanentTaskError as exc:
        logger.error(
            "%s task rejected for %s=%s: %s",
            task.name,
            entity_name,
            entity_id,
            exc,
        )
        raise
    except Exception:
        logger.exception(
            "%s task failed unexpectedly for %s=%s",
            task.name,
            entity_name,
            entity_id,
        )
        raise

    logger.info(
        "%s task completed for %s=%s",
        task.name,
        entity_name,
        entity_id,
    )
    return result


def _execute_tracked_task(
    task: Any,
    *,
    operation: Callable[[], Awaitable[dict[str, Any]]],
    failure_operation: Callable[[], Awaitable[object]],
    entity_name: str,
    entity_id: int,
) -> dict[str, Any]:
    try:
        return _execute_task(
            task,
            operation=operation,
            entity_name=entity_name,
            entity_id=entity_id,
        )
    except Retry:
        raise
    except Exception:
        try:
            run_async_db_operation(failure_operation)
        except Exception:
            logger.exception(
                "Unable to persist FAILED state for %s=%s",
                entity_name,
                entity_id,
            )
        raise


async def _mark_resume_processing_failed(application_id: int) -> None:
    application = await Application.get_or_none(id=application_id)
    if application is not None:
        await Resume.filter(candidate_id=application.candidate_id).update(
            processing_state=AIProcessingState.FAILED
        )


async def _mark_job_criteria_failed(job_id: int) -> None:
    await Job.filter(id=job_id).update(
        criteria_processing_state=AIProcessingState.FAILED
    )


async def _mark_evaluation_failed(application_id: int) -> None:
    await Application.filter(id=application_id).update(
        evaluation_processing_state=AIProcessingState.FAILED
    )


@celery_app.task(
    bind=True,
    name="talentflow.process_resume",
    max_retries=settings.celery_task_max_retries,
)
def process_resume(task: Any, application_id: int) -> dict[str, Any]:
    return _execute_tracked_task(
        task,
        operation=lambda: process_resume_workflow(application_id),
        failure_operation=lambda: _mark_resume_processing_failed(application_id),
        entity_name="application_id",
        entity_id=application_id,
    )


@celery_app.task(
    bind=True,
    name="talentflow.generate_job_criteria",
    max_retries=settings.celery_task_max_retries,
)
def generate_job_criteria(task: Any, job_id: int) -> dict[str, Any]:
    return _execute_tracked_task(
        task,
        operation=lambda: generate_job_criteria_workflow(job_id),
        failure_operation=lambda: _mark_job_criteria_failed(job_id),
        entity_name="job_id",
        entity_id=job_id,
    )


@celery_app.task(
    bind=True,
    name="talentflow.evaluate_application",
    max_retries=settings.celery_task_max_retries,
)
def evaluate_application(task: Any, application_id: int) -> dict[str, Any]:
    return _execute_tracked_task(
        task,
        operation=lambda: evaluate_application_workflow(application_id),
        failure_operation=lambda: _mark_evaluation_failed(application_id),
        entity_name="application_id",
        entity_id=application_id,
    )
