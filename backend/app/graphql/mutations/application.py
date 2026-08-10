import strawberry
from tortoise.transactions import in_transaction

from app.db.models import Application, ApplicationStatusHistory
from app.enums import ApplicationStatus
from app.graphql.types import ApplicationType


@strawberry.type
class ApplicationMutation:
    @strawberry.mutation
    async def update_application_status(
        self,
        application_id: strawberry.ID,
        status: ApplicationStatus,
        changed_by: str,
    ) -> ApplicationType:
        async with in_transaction() as connection:
            application = await Application.get_or_none(
                id=int(application_id), using_db=connection
            )
            if application is None:
                raise ValueError(f"Application {application_id} does not exist")

            previous_status = application.status
            application.status = status
            await application.save(using_db=connection, update_fields=["status", "updated_at"])
            await ApplicationStatusHistory.create(
                application_id=application.id,
                previous_status=previous_status,
                new_status=status,
                changed_by=changed_by,
                using_db=connection,
            )

        refreshed = await Application.get(id=application.id).select_related(
            "candidate", "job"
        )
        return ApplicationType.from_model(refreshed)

