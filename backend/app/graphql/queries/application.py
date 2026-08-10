from __future__ import annotations

import strawberry

from app.db.models import Application
from app.graphql.types import ApplicationType


@strawberry.type
class ApplicationQuery:
    @strawberry.field
    async def applications(self, job_id: strawberry.ID) -> list[ApplicationType]:
        records = (
            await Application.filter(job_id=int(job_id))
            .select_related("candidate", "job")
            .order_by("-applied_at")
        )
        return [ApplicationType.from_model(record) for record in records]

    @strawberry.field
    async def application(self, id: strawberry.ID) -> ApplicationType | None:
        record = await Application.get_or_none(id=int(id)).select_related(
            "candidate", "job"
        )
        return ApplicationType.from_model(record) if record else None
