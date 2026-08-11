from __future__ import annotations

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.db.models import Application, ApplicationStatusHistory, Job, Resume
from app.enums import ApplicationStatus, JobStatus
from app.services.candidate import CandidateService
from app.services.errors import (
    ApplicationSubmissionError,
    DuplicateApplicationError,
    InvalidApplicationInformationError,
    JobClosedError,
    JobNotFoundError,
)
from app.services.resume_storage import ResumeStorageService, UploadedFile


class ApplicationService:
    max_cover_letter_length = 10_000

    def __init__(self, resume_storage: ResumeStorageService | None = None) -> None:
        self.resume_storage = resume_storage or ResumeStorageService()

    async def submit(
        self,
        *,
        job_id: str,
        full_name: str,
        email: str,
        phone: str | None,
        linkedin_url: str | None,
        github_url: str | None,
        portfolio_url: str | None,
        cover_letter: str,
        resume: UploadedFile | None,
    ) -> Application:
        try:
            parsed_job_id = int(job_id)
        except (TypeError, ValueError):
            raise InvalidApplicationInformationError("Invalid job ID.") from None
        if parsed_job_id < 1:
            raise InvalidApplicationInformationError("Invalid job ID.")

        normalized_cover_letter = cover_letter.strip()
        if not normalized_cover_letter:
            raise InvalidApplicationInformationError("Cover letter must not be empty.")
        if len(normalized_cover_letter) > self.max_cover_letter_length:
            raise InvalidApplicationInformationError(
                f"Cover letter must not exceed {self.max_cover_letter_length} characters."
            )

        candidate_data = CandidateService.validate(
            full_name=full_name,
            email=email,
            phone=phone,
            linkedin_url=linkedin_url,
            github_url=github_url,
            portfolio_url=portfolio_url,
        )

        stored_path: str | None = None
        try:
            async with in_transaction() as connection:
                job = await Job.get_or_none(id=parsed_job_id, using_db=connection)
                if job is None:
                    raise JobNotFoundError("Job not found.")
                if job.status != JobStatus.OPEN:
                    raise JobClosedError("This job is not accepting applications.")

                validated_resume = await self.resume_storage.validate(resume)
                candidate = await CandidateService.get_or_create(
                    candidate_data, connection=connection
                )
                duplicate_exists = await Application.filter(
                    candidate_id=candidate.id,
                    job_id=job.id,
                ).using_db(connection).exists()
                if duplicate_exists:
                    raise DuplicateApplicationError(
                        "This candidate has already applied to this job."
                    )

                stored_path = await self.resume_storage.store(candidate.id, validated_resume)
                await Resume.update_or_create(
                    candidate_id=candidate.id,
                    defaults={
                        "file_url": stored_path,
                        "raw_text": None,
                        "parsed_data": {},
                    },
                    using_db=connection,
                )
                application = await Application.create(
                    candidate_id=candidate.id,
                    job_id=job.id,
                    resume_url=stored_path,
                    cover_letter=normalized_cover_letter,
                    status=ApplicationStatus.APPLIED,
                    using_db=connection,
                )
                await ApplicationStatusHistory.create(
                    application_id=application.id,
                    previous_status=None,
                    new_status=ApplicationStatus.APPLIED,
                    changed_by=candidate.email,
                    using_db=connection,
                )
        except ApplicationSubmissionError:
            if stored_path:
                await self.resume_storage.delete(stored_path)
            raise
        except IntegrityError as exc:
            if stored_path:
                await self.resume_storage.delete(stored_path)
            candidate = await CandidateService.find_by_email(str(candidate_data.email))
            if candidate and await Application.exists(
                candidate_id=candidate.id, job_id=parsed_job_id
            ):
                raise DuplicateApplicationError(
                    "This candidate has already applied to this job."
                ) from None
            raise ApplicationSubmissionError(
                "Unable to submit the application. Please try again."
            ) from exc
        except Exception as exc:
            if stored_path:
                await self.resume_storage.delete(stored_path)
            raise ApplicationSubmissionError(
                "Unable to submit the application. Please try again."
            ) from exc

        return await Application.get(id=application.id).select_related("candidate", "job")
