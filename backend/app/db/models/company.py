from typing import TYPE_CHECKING

from tortoise import fields

from app.db.models.base import TimestampedModel

if TYPE_CHECKING:
    from tortoise.fields.relational import ReverseRelation

    from app.db.models.job import Job
    from app.db.models.recruiter import Recruiter


class Company(TimestampedModel):
    id = fields.IntField(primary_key=True)
    # Not unique: every demo sandbox is a private copy of the same demo company.
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    website = fields.CharField(max_length=500, null=True)
    # A per-visitor demo workspace, deleted automatically after DEMO_SANDBOX_TTL_HOURS.
    is_sandbox = fields.BooleanField(default=False)

    recruiters: "ReverseRelation[Recruiter]"
    jobs: "ReverseRelation[Job]"

    class Meta:
        table = "companies"

