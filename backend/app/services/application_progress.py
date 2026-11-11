"""Applicant-safe progress for a submitted application.

Applicants receive a signed status token with their receipt. The token, rather than the
guessable application ID, unlocks this coarse progress view, which never exposes scores,
recommendations, notes, or pipeline status.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.db.models import Application, Resume
from app.enums import AIProcessingState
from app.services.security import sign_value, unsign_value


STATUS_TOKEN_PURPOSE = "application-status"
STATUS_TOKEN_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


class ApplicationProgressStage(str, Enum):
    RECEIVED = "RECEIVED"
    READING_RESUME = "READING_RESUME"
    SCORING = "SCORING"
    COMPLETE = "COMPLETE"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"


@dataclass(frozen=True)
class ApplicationProgress:
    stage: ApplicationProgressStage
    message: str
    job_title: str
    candidate_name: str
    finished: bool


def create_status_token(application_id: int) -> str:
    return sign_value(application_id, purpose=STATUS_TOKEN_PURPOSE)


def application_id_from_status_token(token: str) -> int | None:
    value = unsign_value(
        token,
        purpose=STATUS_TOKEN_PURPOSE,
        max_age_seconds=STATUS_TOKEN_MAX_AGE_SECONDS,
    )
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


async def get_application_progress(application_id: int) -> ApplicationProgress | None:
    application = await Application.get_or_none(id=application_id).select_related(
        "job", "candidate"
    )
    if application is None:
        return None
    resume = await Resume.get_or_none(candidate_id=application.candidate_id)
    resume_state = resume.processing_state if resume else AIProcessingState.NOT_STARTED
    evaluation_state = application.evaluation_processing_state
    criteria_state = application.job.criteria_processing_state
    has_criteria = isinstance(application.job.evaluation_criteria, dict) and bool(
        application.job.evaluation_criteria
    )

    def progress(stage: ApplicationProgressStage, message: str, finished: bool = False):
        return ApplicationProgress(
            stage=stage,
            message=message,
            job_title=application.job.title,
            candidate_name=application.candidate.name,
            finished=finished,
        )

    if resume_state == AIProcessingState.FAILED or evaluation_state == AIProcessingState.FAILED:
        return progress(
            ApplicationProgressStage.NEEDS_MANUAL_REVIEW,
            "Your application is saved. Automated screening could not finish, so a recruiter "
            "will review it manually.",
            finished=True,
        )
    if resume_state == AIProcessingState.NOT_STARTED:
        return progress(ApplicationProgressStage.RECEIVED, "Application received.")
    if resume_state == AIProcessingState.PROCESSING:
        return progress(
            ApplicationProgressStage.READING_RESUME,
            "Reading your resume and extracting your experience and skills.",
        )
    if evaluation_state == AIProcessingState.COMPLETED:
        return progress(
            ApplicationProgressStage.COMPLETE,
            "Screening is complete. Your application is with the hiring team.",
            finished=True,
        )
    if evaluation_state == AIProcessingState.PROCESSING or (
        not has_criteria and criteria_state == AIProcessingState.PROCESSING
    ):
        return progress(
            ApplicationProgressStage.SCORING,
            "Matching your experience against the role's requirements.",
        )
    return progress(
        ApplicationProgressStage.COMPLETE,
        "Your resume has been processed and your application is with the hiring team.",
        finished=True,
    )
