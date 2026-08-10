from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tortoise import fields

from app.db.models.base import TimestampedModel
from app.enums import JobStatus

if TYPE_CHECKING:
    from tortoise.fields.relational import ReverseRelation

    from app.db.models.application import Application
    from app.db.models.company import Company


class Job(TimestampedModel):
    id = fields.IntField(primary_key=True)
    company: fields.ForeignKeyRelation["Company"] = fields.ForeignKeyField(
        "models.Company", related_name="jobs", on_delete=fields.CASCADE
    )
    title = fields.CharField(max_length=255)
    description = fields.TextField()
    required_skills: dict[str, Any] | list[Any] = fields.JSONField(default=list)
    preferred_skills: dict[str, Any] | list[Any] = fields.JSONField(default=list)
    experience_requirement = fields.CharField(max_length=255, null=True)
    evaluation_criteria: dict[str, Any] | list[Any] = fields.JSONField(default=dict)
    status = fields.CharEnumField(JobStatus, default=JobStatus.DRAFT, max_length=20)

    applications: "ReverseRelation[Application]"

    class Meta:
        table = "jobs"
        indexes = (("company_id", "status"),)
