from typing import TYPE_CHECKING

from tortoise import fields

from app.db.models.base import TimestampedModel

if TYPE_CHECKING:
    from tortoise.fields.relational import ReverseRelation

    from app.db.models.application import Application
    from app.db.models.resume import Resume


class Candidate(TimestampedModel):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=320, unique=True)
    phone = fields.CharField(max_length=50, null=True)
    linkedin_url = fields.CharField(max_length=500, null=True)
    github_url = fields.CharField(max_length=500, null=True)
    portfolio_url = fields.CharField(max_length=500, null=True)

    applications: "ReverseRelation[Application]"
    resume: fields.ReverseRelation["Resume"]

    class Meta:
        table = "candidates"

