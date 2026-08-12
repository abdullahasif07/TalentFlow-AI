from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields

from app.db.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.db.models.application import Application
    from app.db.models.recruiter import Recruiter


class ApplicationNote(TimestampedModel):
    id = fields.IntField(primary_key=True)
    application: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="notes", on_delete=fields.CASCADE
    )
    recruiter: fields.ForeignKeyNullableRelation["Recruiter"] = fields.ForeignKeyField(
        "models.Recruiter",
        related_name="application_notes",
        null=True,
        on_delete=fields.SET_NULL,
    )
    content = fields.TextField()

    class Meta:
        table = "application_notes"
        ordering = ["created_at", "id"]
        indexes = (("application_id", "created_at"),)
