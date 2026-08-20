from __future__ import annotations

import strawberry

from app.graphql.types.application import OutreachEmailType
from app.graphql.types.common import OperationError


@strawberry.type
class OutreachMutationPayload:
    success: bool
    outreach: OutreachEmailType | None
    errors: list[OperationError]
