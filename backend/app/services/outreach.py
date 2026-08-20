from __future__ import annotations

from datetime import UTC, datetime

from tortoise.transactions import in_transaction

from app.db.models import OutreachEmail
from app.enums import ApplicationStatus, OutreachStatus
from app.services.application_pipeline import ApplicationPipelineService
from app.services.email_delivery import (
    EmailDeliveryService,
    SimulatedEmailDeliveryService,
)
from app.services.errors import (
    InvalidOutreachBodyError,
    InvalidOutreachStatusTransitionError,
    InvalidOutreachSubjectError,
    OutreachDeliveryError,
    OutreachNotFoundError,
)


class OutreachWorkflowService:
    """Owns the recruiter-controlled draft, approval, and delivery workflow."""

    maximum_subject_length = 500
    maximum_body_length = 10_000
    contacted_from_statuses = {
        ApplicationStatus.HUMAN_REVIEW,
        ApplicationStatus.SHORTLISTED,
    }

    def __init__(
        self,
        delivery_service: EmailDeliveryService | None = None,
    ) -> None:
        self.delivery_service = (
            delivery_service
            if delivery_service is not None
            else SimulatedEmailDeliveryService()
        )

    @classmethod
    async def update_draft(
        cls,
        *,
        outreach_id: int,
        subject: str,
        body: str,
    ) -> OutreachEmail:
        normalized_subject, normalized_body = cls._validate_content(
            subject=subject,
            body=body,
        )
        async with in_transaction() as connection:
            outreach = await (
                OutreachEmail.filter(id=outreach_id)
                .using_db(connection)
                .select_for_update()
                .first()
            )
            if outreach is None:
                raise OutreachNotFoundError("Outreach email not found.")
            cls._require_status(
                outreach=outreach,
                required=OutreachStatus.DRAFT,
                action="edited",
            )
            outreach.subject = normalized_subject
            outreach.body = normalized_body
            await outreach.save(
                using_db=connection,
                update_fields=["subject", "body"],
            )
            return outreach

    @classmethod
    async def approve(cls, outreach_id: int) -> OutreachEmail:
        async with in_transaction() as connection:
            outreach = await (
                OutreachEmail.filter(id=outreach_id)
                .using_db(connection)
                .select_for_update()
                .first()
            )
            if outreach is None:
                raise OutreachNotFoundError("Outreach email not found.")
            cls._require_status(
                outreach=outreach,
                required=OutreachStatus.DRAFT,
                action="approved",
            )
            outreach.status = OutreachStatus.APPROVED
            outreach.approved_at = datetime.now(UTC)
            await outreach.save(
                using_db=connection,
                update_fields=["status", "approved_at"],
            )
            return outreach

    async def send(self, outreach_id: int) -> OutreachEmail:
        application_id: int
        async with in_transaction() as connection:
            outreach = await (
                OutreachEmail.filter(id=outreach_id)
                .using_db(connection)
                .select_for_update()
                .select_related("application", "application__candidate")
                .first()
            )
            if outreach is None:
                raise OutreachNotFoundError("Outreach email not found.")
            self._require_status(
                outreach=outreach,
                required=OutreachStatus.APPROVED,
                action="sent",
            )

            try:
                await self.delivery_service.send(
                    recipient_email=outreach.application.candidate.email,
                    subject=outreach.subject,
                    body=outreach.body,
                )
            except OutreachDeliveryError:
                raise
            except Exception as exc:
                raise OutreachDeliveryError(
                    "Unable to deliver the outreach email."
                ) from exc

            outreach.status = OutreachStatus.SENT
            outreach.sent_at = datetime.now(UTC)
            await outreach.save(
                using_db=connection,
                update_fields=["status", "sent_at"],
            )
            application_id = outreach.application_id

        await ApplicationPipelineService.update_status(
            application_id=application_id,
            new_status=ApplicationStatus.CONTACTED,
            changed_by="Outreach email sent",
            automated=False,
            allowed_previous_statuses=self.contacted_from_statuses,
        )
        return outreach

    @classmethod
    def _validate_content(cls, *, subject: str, body: str) -> tuple[str, str]:
        normalized_subject = " ".join(subject.split())
        normalized_body = body.strip()
        if not normalized_subject:
            raise InvalidOutreachSubjectError("Outreach subject must not be empty.")
        if len(normalized_subject) > cls.maximum_subject_length:
            raise InvalidOutreachSubjectError(
                f"Outreach subject must be {cls.maximum_subject_length} characters or fewer."
            )
        if not normalized_body:
            raise InvalidOutreachBodyError("Outreach body must not be empty.")
        if len(normalized_body) > cls.maximum_body_length:
            raise InvalidOutreachBodyError(
                f"Outreach body must be {cls.maximum_body_length} characters or fewer."
            )
        return normalized_subject, normalized_body

    @staticmethod
    def _require_status(
        *,
        outreach: OutreachEmail,
        required: OutreachStatus,
        action: str,
    ) -> None:
        current = OutreachStatus(outreach.status)
        if current != required:
            raise InvalidOutreachStatusTransitionError(
                f"Only {required.value} outreach emails can be {action}; "
                f"current status is {current.value}."
            )
