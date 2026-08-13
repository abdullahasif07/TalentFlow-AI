from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any, cast

from openai import AsyncOpenAI
from pydantic import BaseModel
from tortoise import Tortoise

from app.db.models import Candidate, Resume
from app.schemas import ParsedResume
from app.services.ai.client import OpenAIStructuredOutputClient
from app.services.ai.resume_parser import ResumeParsingService
from app.services.errors import (
    EmptyResumeTextError,
    InvalidResumeParsingOutputError,
    ResumeRecordNotFoundError,
)


class MockStructuredOutputClient:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        response_model: type[BaseModel],
    ) -> Any:
        self.calls.append(
            {
                "instructions": instructions,
                "input_text": input_text,
                "response_model": response_model,
            }
        )
        return self.result


class FakeResponsesAPI:
    def __init__(self, parsed: ParsedResume) -> None:
        self.parsed = parsed
        self.arguments: dict[str, object] = {}

    async def parse(self, **kwargs: object) -> SimpleNamespace:
        self.arguments = kwargs
        return SimpleNamespace(output_parsed=self.parsed)


class ResumeParsingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    async def test_correctly_structured_output(self) -> None:
        client = MockStructuredOutputClient(
            {
                "professional_summary": "Backend engineer building APIs.",
                "skills": ["API design", "System design"],
                "technologies": ["Python", "FastAPI", "PostgreSQL"],
                "total_experience_years": 4.5,
                "employment_history": [
                    {
                        "company": "Northstar Labs",
                        "role": "Backend Engineer",
                        "start_date": "2022-01",
                        "end_date": "Present",
                        "description": "Built recruiting APIs.",
                        "technologies": ["Python", "FastAPI"],
                    }
                ],
                "education": [
                    {
                        "institution": "Example University",
                        "degree": "BS",
                        "field": "Computer Science",
                        "start_date": "2017",
                        "end_date": "2021",
                    }
                ],
                "projects": [
                    {
                        "name": "Talent Portal",
                        "description": "Applicant tracking project.",
                        "technologies": ["Python"],
                        "url": "https://example.com/talent-portal",
                    }
                ],
                "certifications": [
                    {
                        "name": "Cloud Developer",
                        "issuer": "Example Cloud",
                        "date": "2023",
                    }
                ],
                "normalization_notes": ["Normalized B.S. to BS."],
            }
        )
        service = ResumeParsingService(client=client)

        parsed = await service.parse("Jordan Taylor\nBackend Engineer\nPython")

        self.assertIsInstance(parsed, ParsedResume)
        self.assertEqual(parsed.technologies, ["Python", "FastAPI", "PostgreSQL"])
        self.assertEqual(parsed.employment_history[0].company, "Northstar Labs")
        self.assertEqual(parsed.projects[0].name, "Talent Portal")
        self.assertEqual(parsed.education[0].field, "Computer Science")
        self.assertEqual(parsed.certifications[0].issuer, "Example Cloud")
        self.assertIs(client.calls[0]["response_model"], ParsedResume)
        self.assertIn("Never invent", str(client.calls[0]["instructions"]))
        self.assertIn("<resume_text>", str(client.calls[0]["input_text"]))

    async def test_missing_optional_fields_use_nulls_and_empty_lists(self) -> None:
        service = ResumeParsingService(client=MockStructuredOutputClient({}))

        parsed = await service.parse("Jordan Taylor")

        self.assertIsNone(parsed.professional_summary)
        self.assertIsNone(parsed.total_experience_years)
        self.assertEqual(parsed.skills, [])
        self.assertEqual(parsed.employment_history, [])
        self.assertEqual(parsed.education, [])
        self.assertEqual(parsed.projects, [])
        self.assertEqual(parsed.certifications, [])

    async def test_invalid_model_output_is_rejected(self) -> None:
        service = ResumeParsingService(
            client=MockStructuredOutputClient(
                {
                    "skills": "Python",
                    "total_experience_years": -3,
                    "unsupported_judgment": "Great candidate",
                }
            )
        )

        with self.assertRaisesRegex(
            InvalidResumeParsingOutputError, "invalid structured data"
        ):
            await service.parse("Jordan Taylor\nPython")

    async def test_empty_raw_resume_text_is_rejected_without_calling_llm(self) -> None:
        client = MockStructuredOutputClient({})
        service = ResumeParsingService(client=client)

        with self.assertRaisesRegex(EmptyResumeTextError, "must not be empty"):
            await service.parse("  \n\t  ")

        self.assertEqual(client.calls, [])

    async def test_parsed_data_is_saved_and_raw_text_is_unchanged(self) -> None:
        raw_text = "Jordan Taylor\nPython Developer"
        candidate = await Candidate.create(
            name="Jordan Taylor", email="jordan.parsing@example.com"
        )
        resume = await Resume.create(
            candidate=candidate,
            file_url="uploads/resumes/1/resume.pdf",
            raw_text=raw_text,
            parsed_data={"old": "value"},
        )
        service = ResumeParsingService(
            client=MockStructuredOutputClient(
                {
                    "professional_summary": "Python Developer",
                    "skills": ["API design"],
                    "technologies": ["Python"],
                }
            )
        )

        parsed = await service.parse_and_save(resume.id)

        await resume.refresh_from_db()
        self.assertEqual(resume.raw_text, raw_text)
        self.assertEqual(resume.parsed_data, parsed.model_dump(mode="json"))
        self.assertEqual(resume.parsed_data["technologies"], ["Python"])
        self.assertNotIn("old", resume.parsed_data)

    async def test_missing_resume_record_is_rejected(self) -> None:
        service = ResumeParsingService(client=MockStructuredOutputClient({}))

        with self.assertRaisesRegex(ResumeRecordNotFoundError, "record not found"):
            await service.parse_and_save(999_999)

    async def test_openai_adapter_requests_typed_non_stored_output(self) -> None:
        expected = ParsedResume(technologies=["Python"])
        responses_api = FakeResponsesAPI(expected)
        fake_openai = SimpleNamespace(responses=responses_api)
        client = OpenAIStructuredOutputClient(
            client=cast(AsyncOpenAI, fake_openai),
            model="test-structured-model",
        )

        result = await client.generate_structured(
            instructions="Extract facts only.",
            input_text="Jordan Taylor uses Python.",
            response_model=ParsedResume,
        )

        self.assertEqual(result, expected)
        self.assertEqual(responses_api.arguments["model"], "test-structured-model")
        self.assertIs(responses_api.arguments["text_format"], ParsedResume)
        self.assertFalse(responses_api.arguments["store"])


if __name__ == "__main__":
    unittest.main()
