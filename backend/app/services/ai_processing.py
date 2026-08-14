from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.db.models import AIEvaluation, Application, Job, Resume
from app.enums import AIProcessingState
from app.services.errors import (
    ProcessingPrerequisiteError,
    ProcessingQueueError,
    ProcessingResourceNotFoundError,
)


@dataclass(frozen=True)
class ProcessingRequest:
    accepted: bool
    resource_id: int
    state: AIProcessingState
    message: str
    task_id: str | None = None


@dataclass(frozen=True)
class BatchProcessingRequest:
    accepted_application_ids: list[int]
    failed_application_ids: list[int]
    message: str


class AIProcessingService:
    """Validates and enqueues AI work without performing AI logic."""

    @staticmethod
    async def generate_job_criteria(job_id: int) -> ProcessingRequest:
        job = await Job.get_or_none(id=job_id)
        if job is None:
            raise ProcessingResourceNotFoundError("Job not found.")
        if job.criteria_processing_state == AIProcessingState.PROCESSING:
            return ProcessingRequest(
                accepted=False,
                resource_id=job.id,
                state=AIProcessingState.PROCESSING,
                message="Job criteria generation is already processing.",
            )

        job.criteria_processing_state = AIProcessingState.PROCESSING
        await job.save(update_fields=["criteria_processing_state", "updated_at"])
        try:
            from app.worker.tasks import generate_job_criteria

            queued = await asyncio.to_thread(generate_job_criteria.delay, job.id)
        except Exception as exc:
            await Job.filter(id=job.id).update(
                criteria_processing_state=AIProcessingState.FAILED
            )
            raise ProcessingQueueError(
                "Unable to queue job criteria generation."
            ) from exc
        return ProcessingRequest(
            accepted=True,
            resource_id=job.id,
            state=AIProcessingState.PROCESSING,
            message="Job criteria generation was queued.",
            task_id=queued.id,
        )

    @staticmethod
    async def process_application_resume(application_id: int) -> ProcessingRequest:
        application = await Application.get_or_none(id=application_id)
        if application is None:
            raise ProcessingResourceNotFoundError("Application not found.")
        resume = await Resume.get_or_none(candidate_id=application.candidate_id)
        if resume is None:
            raise ProcessingResourceNotFoundError("Resume not found.")
        if resume.processing_state == AIProcessingState.PROCESSING:
            return ProcessingRequest(
                accepted=False,
                resource_id=application.id,
                state=AIProcessingState.PROCESSING,
                message="Resume processing is already in progress.",
            )

        resume.processing_state = AIProcessingState.PROCESSING
        await resume.save(update_fields=["processing_state", "updated_at"])
        try:
            from app.worker.tasks import process_resume

            queued = await asyncio.to_thread(process_resume.delay, application.id)
        except Exception as exc:
            await Resume.filter(id=resume.id).update(
                processing_state=AIProcessingState.FAILED
            )
            raise ProcessingQueueError("Unable to queue resume processing.") from exc
        return ProcessingRequest(
            accepted=True,
            resource_id=application.id,
            state=AIProcessingState.PROCESSING,
            message="Resume processing was queued.",
            task_id=queued.id,
        )

    @staticmethod
    async def generate_candidate_evaluation(
        application_id: int,
    ) -> ProcessingRequest:
        application = await Application.get_or_none(id=application_id).select_related(
            "job"
        )
        if application is None:
            raise ProcessingResourceNotFoundError("Application not found.")
        resume = await Resume.get_or_none(candidate_id=application.candidate_id)
        if resume is None or not isinstance(resume.parsed_data, dict) or not resume.parsed_data:
            raise ProcessingPrerequisiteError(
                "The application requires a parsed resume before evaluation."
            )
        if (
            not isinstance(application.job.evaluation_criteria, dict)
            or not application.job.evaluation_criteria
        ):
            raise ProcessingPrerequisiteError(
                "The job requires evaluation criteria before candidate evaluation."
            )
        if application.evaluation_processing_state == AIProcessingState.PROCESSING:
            return ProcessingRequest(
                accepted=False,
                resource_id=application.id,
                state=AIProcessingState.PROCESSING,
                message="Candidate evaluation is already processing.",
            )

        application.evaluation_processing_state = AIProcessingState.PROCESSING
        await application.save(
            update_fields=["evaluation_processing_state", "updated_at"]
        )
        try:
            from app.worker.tasks import evaluate_application

            queued = await asyncio.to_thread(evaluate_application.delay, application.id)
        except Exception as exc:
            await Application.filter(id=application.id).update(
                evaluation_processing_state=AIProcessingState.FAILED
            )
            raise ProcessingQueueError(
                "Unable to queue candidate evaluation."
            ) from exc
        return ProcessingRequest(
            accepted=True,
            resource_id=application.id,
            state=AIProcessingState.PROCESSING,
            message="Candidate evaluation was queued.",
            task_id=queued.id,
        )

    @staticmethod
    async def screen_job_applicants(job_id: int) -> BatchProcessingRequest:
        job = await Job.get_or_none(id=job_id)
        if job is None:
            raise ProcessingResourceNotFoundError("Job not found.")
        if not isinstance(job.evaluation_criteria, dict) or not job.evaluation_criteria:
            raise ProcessingPrerequisiteError(
                "The job requires evaluation criteria before applicant screening."
            )

        applications = await Application.filter(job_id=job.id).exclude(
            evaluation_processing_state__in=[
                AIProcessingState.PROCESSING,
                AIProcessingState.COMPLETED,
            ]
        )
        if not applications:
            return BatchProcessingRequest([], [], "No applicants are ready for screening.")

        application_ids = [application.id for application in applications]
        candidate_ids = [application.candidate_id for application in applications]
        evaluations, resumes = await asyncio.gather(
            AIEvaluation.filter(application_id__in=application_ids),
            Resume.filter(candidate_id__in=candidate_ids),
        )
        completed_ids = {evaluation.application_id for evaluation in evaluations}
        resumes_by_candidate = {resume.candidate_id: resume for resume in resumes}
        eligible_ids = [
            application.id
            for application in applications
            if application.id not in completed_ids
            and (resume := resumes_by_candidate.get(application.candidate_id)) is not None
            and isinstance(resume.parsed_data, dict)
            and bool(resume.parsed_data)
        ]
        if not eligible_ids:
            return BatchProcessingRequest([], [], "No applicants are ready for screening.")

        await Application.filter(id__in=eligible_ids).update(
            evaluation_processing_state=AIProcessingState.PROCESSING
        )
        accepted_ids: list[int] = []
        failed_ids: list[int] = []
        from app.worker.tasks import evaluate_application

        for application_id in eligible_ids:
            try:
                await asyncio.to_thread(evaluate_application.delay, application_id)
                accepted_ids.append(application_id)
            except Exception:
                failed_ids.append(application_id)
                await Application.filter(id=application_id).update(
                    evaluation_processing_state=AIProcessingState.FAILED
                )

        message = f"Queued {len(accepted_ids)} applicant evaluation(s)."
        if failed_ids:
            message += f" {len(failed_ids)} application(s) could not be queued."
        return BatchProcessingRequest(accepted_ids, failed_ids, message)
