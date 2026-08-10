from typing import TYPE_CHECKING

from tortoise import fields

from app.db.models.base import TimestampedModel

if TYPE_CHECKING:
    from tortoise.fields.relational import ReverseRelation

    from app.db.models.job import Job
    from app.db.models.recruiter import Recruiter


class Company(TimestampedModel):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, unique=True)
    description = fields.TextField(null=True)
    website = fields.CharField(max_length=500, null=True)

    recruiters: "ReverseRelation[Recruiter]"
    jobs: "ReverseRelation[Job]"

    class Meta:
        table = "companies"

