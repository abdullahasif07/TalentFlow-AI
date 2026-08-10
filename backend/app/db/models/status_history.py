from typing import TYPE_CHECKING

from tortoise import fields, models

from app.enums import ApplicationStatus

if TYPE_CHECKING:
    from app.db.models.application import Application


class ApplicationStatusHistory(models.Model):
    id = fields.IntField(primary_key=True)
    application: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="status_history", on_delete=fields.CASCADE
    )
    previous_status = fields.CharEnumField(ApplicationStatus, max_length=30)
    new_status = fields.CharEnumField(ApplicationStatus, max_length=30)
    changed_by = fields.CharField(max_length=320)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "application_status_history"
        ordering = ["-created_at"]

