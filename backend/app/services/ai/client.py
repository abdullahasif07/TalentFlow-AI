from __future__ import annotations

from typing import Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class LLMClientError(Exception):
    """Base exception for safe structured-output provider failures."""


class LLMConfigurationError(LLMClientError):
    pass


class LLMInvalidResponseError(LLMClientError):
    pass


class StructuredOutputClient(Protocol):
    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel: ...


class OpenAIStructuredOutputClient:
    """OpenAI adapter for typed structured output."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = (model or settings.openai_model).strip()
        if not self.model:
            raise LLMConfigurationError("An OpenAI model must be configured.")

        if client is not None:
            self.client = client
            return

        settings_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else ""
        )
        configured_key = (api_key or settings_key).strip()
        if not configured_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not configured.")
        self.client = AsyncOpenAI(api_key=configured_key)

    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=input_text,
                text_format=response_model,
                store=False,
            )
        except ValidationError:
            raise LLMInvalidResponseError(
                "The structured-output provider returned invalid data."
            ) from None
        except Exception:
            raise LLMClientError(
                "The structured-output provider request failed."
            ) from None

        parsed = response.output_parsed
        if parsed is None:
            raise LLMInvalidResponseError(
                "The structured-output provider returned no parsed result."
            )
        try:
            if isinstance(parsed, response_model):
                return parsed
            return response_model.model_validate(parsed)
        except (TypeError, ValidationError):
            raise LLMInvalidResponseError(
                "The structured-output provider returned invalid data."
            ) from None
