from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OutreachDraft(BaseModel):
    """Validated, plain-text outreach content returned by the LLM."""

    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=10_000)

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        subject = " ".join(value.split())
        if not subject:
            raise ValueError("subject must not be empty")
        return subject

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        body = value.strip()
        if not body:
            raise ValueError("body must not be empty")
        return body
