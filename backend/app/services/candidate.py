from __future__ import annotations

import re

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, EmailStr, Field, ValidationError
from pydantic import field_validator
from tortoise.backends.base.client import BaseDBAsyncClient

from app.db.models import Candidate
from app.services.errors import InvalidCandidateInformationError


class CandidateSubmissionData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    linkedin_url: AnyHttpUrl | None = None
    github_url: AnyHttpUrl | None = None
    portfolio_url: AnyHttpUrl | None = None

    @field_validator("phone", "linkedin_url", "github_url", "portfolio_url", mode="before")
    @classmethod
    def empty_strings_are_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) < 7 or not re.fullmatch(r"[0-9+().\-\s]+", value):
            raise ValueError("must contain only common phone-number characters")
        return value


class CandidateService:
    @staticmethod
    async def find_by_email(email: str) -> Candidate | None:
        normalized_email = email.strip().casefold()
        return await Candidate.filter(email=normalized_email).first()

    @staticmethod
    def validate(
        *,
        full_name: str,
        email: str,
        phone: str | None,
        linkedin_url: str | None,
        github_url: str | None,
        portfolio_url: str | None,
    ) -> CandidateSubmissionData:
        try:
            return CandidateSubmissionData(
                full_name=full_name,
                email=email,
                phone=phone,
                linkedin_url=linkedin_url,
                github_url=github_url,
                portfolio_url=portfolio_url,
            )
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors()
            )
            raise InvalidCandidateInformationError(
                f"Invalid candidate information: {details}"
            ) from None

    @staticmethod
    async def get_or_create(
        data: CandidateSubmissionData,
        *,
        connection: BaseDBAsyncClient,
    ) -> Candidate:
        normalized_email = str(data.email).strip().casefold()
        candidate, created = await Candidate.get_or_create(
            email=normalized_email,
            defaults={
                "name": data.full_name,
                "phone": data.phone,
                "linkedin_url": str(data.linkedin_url) if data.linkedin_url else None,
                "github_url": str(data.github_url) if data.github_url else None,
                "portfolio_url": str(data.portfolio_url) if data.portfolio_url else None,
            },
            using_db=connection,
        )
        if created:
            return candidate

        updates: list[str] = []
        optional_values = {
            "phone": data.phone,
            "linkedin_url": str(data.linkedin_url) if data.linkedin_url else None,
            "github_url": str(data.github_url) if data.github_url else None,
            "portfolio_url": str(data.portfolio_url) if data.portfolio_url else None,
        }
        for field_name, value in optional_values.items():
            if value and not getattr(candidate, field_name):
                setattr(candidate, field_name, value)
                updates.append(field_name)
        if updates:
            updates.append("updated_at")
            await candidate.save(using_db=connection, update_fields=updates)
        return candidate
