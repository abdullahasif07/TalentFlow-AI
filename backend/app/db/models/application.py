from typing import TYPE_CHECKING

from tortoise import fields

from app.db.models.base import TimestampedModel
from app.enums import ApplicationStatus

if TYPE_CHECKING:
    from tortoise.fields.relational import ReverseRelation

    from app.db.models.ai_evaluation import AIEvaluation
    from app.db.models.application_note import ApplicationNote
    from app.db.models.candidate import Candidate
    from app.db.models.job import Job
    from app.db.models.outreach_email import OutreachEmail
    from app.db.models.status_history import ApplicationStatusHistory


class Application(TimestampedModel):
    id = fields.IntField(primary_key=True)
    candidate: fields.ForeignKeyRelation["Candidate"] = fields.ForeignKeyField(
        "models.Candidate", related_name="applications", on_delete=fields.CASCADE
    )
    job: fields.ForeignKeyRelation["Job"] = fields.ForeignKeyField(
        "models.Job", related_name="applications", on_delete=fields.CASCADE
    )
    resume_url = fields.CharField(max_length=1000, null=True)
    cover_letter = fields.TextField(null=True)
    status = fields.CharEnumField(
        ApplicationStatus, default=ApplicationStatus.APPLIED, max_length=30
    )
    fit_score = fields.DecimalField(max_digits=5, decimal_places=2, null=True)
    applied_at = fields.DatetimeField(auto_now_add=True)

    ai_evaluation: fields.ReverseRelation["AIEvaluation"]
    status_history: "ReverseRelation[ApplicationStatusHistory]"
    outreach_emails: "ReverseRelation[OutreachEmail]"
    notes: "ReverseRelation[ApplicationNote]"

    class Meta:
        table = "applications"
        unique_together = (("candidate", "job"),)
        indexes = (
            ("job_id", "status"),
            ("job_id", "applied_at"),
        )
