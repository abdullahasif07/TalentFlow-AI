from __future__ import annotations

from tortoise.transactions import in_transaction

from app.db.models import Application, ApplicationStatusHistory, Job, Recruiter
from app.enums import ApplicationStatus
from app.services.errors import (
    ApplicationNotFoundError,
    InvalidPipelineActorError,
    InvalidStatusTransitionError,
    RecruiterCompanyMismatchError,
    RecruiterNotFoundError,
)


class ApplicationPipelineService:
    """Owns application stage transitions and their audit history."""

    automated_transitions: dict[ApplicationStatus, set[ApplicationStatus]] = {
        ApplicationStatus.APPLIED: {ApplicationStatus.AI_REVIEWED},
        ApplicationStatus.AI_REVIEWED: {
            ApplicationStatus.HUMAN_REVIEW,
            ApplicationStatus.REJECTED,
        },
        ApplicationStatus.CONTACTED: {ApplicationStatus.REPLIED},
    }

    @classmethod
    async def update_status(
        cls,
        *,
        application_id: int,
        new_status: ApplicationStatus,
        changed_by: str,
        recruiter_id: int | None = None,
        automated: bool = False,
    ) -> Application:
        actor = cls._validate_actor(changed_by)
        if not isinstance(new_status, ApplicationStatus):
            raise InvalidStatusTransitionError("Invalid application status.")

        async with in_transaction() as connection:
            application = await (
                Application.filter(id=application_id)
                .using_db(connection)
                .select_for_update()
                .first()
            )
            if application is None:
                raise ApplicationNotFoundError("Application not found.")

            if recruiter_id is not None:
                recruiter = await Recruiter.get_or_none(id=recruiter_id).using_db(
                    connection
                )
                if recruiter is None:
                    raise RecruiterNotFoundError("Recruiter not found.")
                job = await Job.get(id=application.job_id).using_db(connection)
                if recruiter.company_id != job.company_id:
                    raise RecruiterCompanyMismatchError(
                        "Recruiter cannot update an application for another company."
                    )
                actor = recruiter.email

            previous_status = ApplicationStatus(application.status)
            changed = previous_status != new_status
            if changed:
                cls.validate_transition(
                    previous_status=previous_status,
                    new_status=new_status,
                    automated=automated,
                )
                application.status = new_status
                await application.save(
                    using_db=connection,
                    update_fields=["status", "updated_at"],
                )
                await ApplicationStatusHistory.create(
                    application_id=application.id,
                    previous_status=previous_status,
                    new_status=new_status,
                    changed_by=actor,
                    using_db=connection,
                )

        refreshed = await Application.get(id=application_id).select_related(
            "candidate", "job"
        )
        return refreshed

    @classmethod
    def validate_transition(
        cls,
        *,
        previous_status: ApplicationStatus,
        new_status: ApplicationStatus,
        automated: bool,
    ) -> None:
        if not automated:
            return
        allowed = cls.automated_transitions.get(previous_status, set())
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Automated transition from {previous_status.value} "
                f"to {new_status.value} is not allowed."
            )

    @staticmethod
    def _validate_actor(changed_by: str) -> str:
        actor = changed_by.strip()
        if not actor or len(actor) > 320:
            raise InvalidPipelineActorError(
                "Changed by must contain between 1 and 320 characters."
            )
        return actor
