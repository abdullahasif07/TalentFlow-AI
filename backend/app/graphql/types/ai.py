import strawberry

from app.enums import AIProcessingState
from app.graphql.types.common import OperationError


@strawberry.type
class AIProcessingPayload:
    success: bool
    accepted: bool
    resource_id: strawberry.ID | None
    state: AIProcessingState
    message: str
    task_id: str | None
    errors: list[OperationError]


@strawberry.type
class BatchScreeningPayload:
    success: bool
    accepted: bool
    job_id: strawberry.ID | None
    state: AIProcessingState
    message: str
    queued_count: int
    application_ids: list[strawberry.ID]
    failed_application_ids: list[strawberry.ID]
    errors: list[OperationError]
