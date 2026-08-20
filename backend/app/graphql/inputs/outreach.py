from __future__ import annotations

import strawberry


@strawberry.input
class GenerateOutreachInput:
    application_id: strawberry.ID
    instruction: str | None = None


@strawberry.input
class UpdateOutreachDraftInput:
    outreach_id: strawberry.ID
    subject: str
    body: str


@strawberry.input
class ApproveOutreachInput:
    outreach_id: strawberry.ID


@strawberry.input
class SendOutreachInput:
    outreach_id: strawberry.ID
