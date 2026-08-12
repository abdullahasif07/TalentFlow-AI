from typing import TYPE_CHECKING

from tortoise import fields

from app.db.models.base import TimestampedModel

if TYPE_CHECKING:
    from tortoise.fields.relational import ReverseRelation

    from app.db.models.application_note import ApplicationNote
    from app.db.models.company import Company


class Recruiter(TimestampedModel):
    id = fields.IntField(primary_key=True)
    company: fields.ForeignKeyRelation["Company"] = fields.ForeignKeyField(
        "models.Company", related_name="recruiters", on_delete=fields.CASCADE
    )
    name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=320, unique=True)
    role = fields.CharField(max_length=100)

    application_notes: "ReverseRelation[ApplicationNote]"

    class Meta:
        table = "recruiters"
