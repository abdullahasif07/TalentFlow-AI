from typing import TYPE_CHECKING

from tortoise import fields, models

from app.enums import OutreachStatus

if TYPE_CHECKING:
    from app.db.models.application import Application


class OutreachEmail(models.Model):
    id = fields.IntField(primary_key=True)
    application: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="outreach_emails", on_delete=fields.CASCADE
    )
    subject = fields.CharField(max_length=500)
    body = fields.TextField()
    status = fields.CharEnumField(
        OutreachStatus, default=OutreachStatus.DRAFT, max_length=20
    )
    generated_at = fields.DatetimeField(auto_now_add=True)
    approved_at = fields.DatetimeField(null=True)
    sent_at = fields.DatetimeField(null=True)

    class Meta:
        table = "outreach_emails"

