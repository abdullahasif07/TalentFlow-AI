from __future__ import annotations

import strawberry

from app.db.models import Job
from app.graphql.types import JobType


@strawberry.type
class JobQuery:
    @strawberry.field
    async def jobs(self) -> list[JobType]:
        records = await Job.all().order_by("-created_at")
        return [JobType.from_model(record) for record in records]

    @strawberry.field
    async def job(self, id: strawberry.ID) -> JobType | None:
        record = await Job.get_or_none(id=int(id))
        return JobType.from_model(record) if record else None
