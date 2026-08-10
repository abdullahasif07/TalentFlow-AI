from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tortoise import fields

from app.db.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.db.models.candidate import Candidate


class Resume(TimestampedModel):
    id = fields.IntField(primary_key=True)
    candidate: fields.OneToOneRelation["Candidate"] = fields.OneToOneField(
        "models.Candidate", related_name="resume", on_delete=fields.CASCADE
    )
    file_url = fields.CharField(max_length=1000)
    raw_text = fields.TextField(null=True)
    parsed_data: dict[str, Any] | list[Any] = fields.JSONField(default=dict)

    class Meta:
        table = "resumes"
