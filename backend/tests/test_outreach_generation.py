from __future__ import annotations

import json
import unittest
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from tortoise import Tortoise

from app.db.models import (
    AIEvaluation,
    Application,
    Candidate,
    Company,
    Job,
    OutreachEmail,
    Resume,
)
from app.enums import ApplicationStatus, JobStatus, OutreachStatus
from app.schemas import OutreachDraft
from app.services.ai.client import LLMClientError
from app.services.ai.outreach_generation import OutreachGenerationService
from app.services.errors import (
    InvalidOutreachContextError,
    InvalidOutreachOutputError,
    MissingOutreachResumeDataError,
    OutreachApplicationNotFoundError,
    OutreachGenerationProviderError,
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


class FailingStructuredOutputClient:
    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        response_model: type[BaseModel],
    ) -> Any:
        raise LLMClientError("provider details that must not escape")


def outreach_result(*, focus: str = "FastAPI and PostgreSQL") -> dict[str, str]:
    return {
        "subject": "Backend Engineer opportunity at Northstar Labs",
        "body": (
            "Hi Ahmed,\n\n"
            "Thanks for applying for our Backend Engineer role. Your experience with "
            f"{focus} is relevant to the API work involved in this position.\n\n"
            "We'd be interested in speaking with you and learning more about your experience.\n\n"
            "Best,\nNorthstar Labs Recruiting"
        ),
    }


def parsed_resume() -> dict[str, object]:
    return {
        "professional_summary": "Backend engineer focused on reliable APIs.",
        "skills": ["API design", "Database design"],
        "technologies": ["Python", "FastAPI", "PostgreSQL"],
        "total_experience_years": 5,
        "employment_history": [
            {
                "company": "Harbor Systems",
                "role": "Backend Engineer",
                "start_date": "2021",
                "end_date": "Present",
                "description": "Built production APIs using FastAPI and PostgreSQL.",
                "technologies": ["Python", "FastAPI", "PostgreSQL"],
            }
        ],
        "education": [],
        "projects": [],
        "certifications": [],
        "normalization_notes": [],
    }


class OutreachGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.company = await Company.create(
            name="Northstar Labs",
            description="We build dependable hiring software.",
            website="https://northstar.example.com",
        )
        self.candidate = await Candidate.create(
            name="Ahmed Khan",
            email="ahmed.outreach@example.com",
        )
        self.job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description="Build reliable APIs for our recruiting platform.",
            required_skills=["Python", "PostgreSQL"],
            preferred_skills=["FastAPI"],
            experience_requirement="3+ years",
            status=JobStatus.OPEN,
        )
        self.application = await Application.create(
            candidate=self.candidate,
            job=self.job,
            resume_url="uploads/resumes/1/resume.pdf",
            status=ApplicationStatus.AI_REVIEWED,
            fit_score=Decimal("92.00"),
        )
        self.resume = await Resume.create(
            candidate=self.candidate,
            file_url="uploads/resumes/1/resume.pdf",
            raw_text="Original resume text",
            parsed_data=parsed_resume(),
        )
        await AIEvaluation.create(
            application=self.application,
            overall_score=Decimal("92.00"),
            recommendation="STRONG_MATCH",
            confidence="HIGH",
            strengths=[
                {
                    "summary": "Relevant production API experience.",
                    "evidence": [
                        "Built production APIs using FastAPI and PostgreSQL."
                    ],
                }
            ],
            evidence=[
                {
                    "claim": "The candidate has relevant backend experience.",
                    "resume_evidence": (
                        "Built production APIs using FastAPI and PostgreSQL."
                    ),
                    "category": "Relevant Experience",
                }
            ],
            analysis_json={"overall_score": 92.0},
        )

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    async def test_generates_structured_candidate_and_job_grounded_outreach(self) -> None:
        client = MockStructuredOutputClient(outreach_result())

        draft = await OutreachGenerationService(client=client).generate(
            self.application.id
        )

        self.assertIsInstance(draft, OutreachDraft)
        self.assertIn("Backend Engineer", draft.subject)
        self.assertIs(client.calls[0]["response_model"], OutreachDraft)
        encoded = str(client.calls[0]["input_text"]).split(
            "<outreach_context>\n", 1
        )[1].split("\n</outreach_context>", 1)[0]
        context = json.loads(encoded)
        self.assertEqual(context["candidate"]["name"], "Ahmed Khan")
        self.assertEqual(context["job"]["title"], "Backend Engineer")
        self.assertEqual(context["company"]["name"], "Northstar Labs")
        self.assertIn("FastAPI", context["structured_resume"]["technologies"])
        self.assertEqual(
            context["supporting_evaluation_evidence"]["strengths"][0]["summary"],
            "Relevant production API experience.",
        )
        self.assertNotIn("fit_score", encoded)
        self.assertNotIn("overall_score", encoded)
        self.assertNotIn("recommendation", encoded)

    async def test_persists_a_draft_without_sending_it(self) -> None:
        saved = await OutreachGenerationService(
            client=MockStructuredOutputClient(outreach_result())
        ).generate_and_save(self.application.id)

        persisted = await OutreachEmail.get(id=saved.id)
        self.assertEqual(persisted.application_id, self.application.id)
        self.assertEqual(persisted.status, OutreachStatus.DRAFT)
        self.assertEqual(persisted.subject, outreach_result()["subject"])
        self.assertIsNotNone(persisted.generated_at)
        self.assertIsNone(persisted.approved_at)
        self.assertIsNone(persisted.sent_at)

    async def test_regeneration_reuses_the_current_unsent_draft(self) -> None:
        client = MockStructuredOutputClient(outreach_result())
        service = OutreachGenerationService(client=client)
        original = await service.generate_and_save(self.application.id)
        client.result = outreach_result(focus="backend API and database design")

        regenerated = await service.generate_and_save(
            self.application.id,
            instruction="Focus more on their backend experience",
        )

        self.assertEqual(regenerated.id, original.id)
        self.assertIn("backend API and database design", regenerated.body)
        self.assertEqual(
            await OutreachEmail.filter(application_id=self.application.id).count(),
            1,
        )

    async def test_approved_email_is_preserved_when_a_new_draft_is_generated(self) -> None:
        approved = await OutreachEmail.create(
            application=self.application,
            subject="Previously approved",
            body="Approved body",
            status=OutreachStatus.APPROVED,
        )

        draft = await OutreachGenerationService(
            client=MockStructuredOutputClient(outreach_result())
        ).generate_and_save(self.application.id)

        await approved.refresh_from_db()
        self.assertNotEqual(draft.id, approved.id)
        self.assertEqual(approved.status, OutreachStatus.APPROVED)
        self.assertEqual(approved.body, "Approved body")

    async def test_optional_instruction_is_normalized_and_kept_subordinate(self) -> None:
        client = MockStructuredOutputClient(outreach_result())

        await OutreachGenerationService(client=client).generate(
            self.application.id,
            instruction="  Make it   shorter  ",
        )

        input_text = str(client.calls[0]["input_text"])
        self.assertIn('"recruiter_instruction": "Make it shorter"', input_text)
        self.assertIn("subordinate", input_text)
        self.assertIn("Ignore it", str(client.calls[0]["instructions"]))

    async def test_missing_evaluation_does_not_block_generation(self) -> None:
        await AIEvaluation.filter(application_id=self.application.id).delete()
        client = MockStructuredOutputClient(outreach_result())

        draft = await OutreachGenerationService(client=client).generate(
            self.application.id
        )

        self.assertIn("Backend Engineer", draft.body)
        self.assertIn(
            '"supporting_evaluation_evidence": null',
            str(client.calls[0]["input_text"]),
        )

    async def test_malformed_model_output_is_rejected(self) -> None:
        service = OutreachGenerationService(
            client=MockStructuredOutputClient(
                {"subject": "", "body": ["not", "plain", "text"]}
            )
        )

        with self.assertRaisesRegex(
            InvalidOutreachOutputError, "invalid structured data"
        ):
            await service.generate(self.application.id)

    async def test_missing_application_and_resume_data_are_rejected(self) -> None:
        service = OutreachGenerationService(
            client=MockStructuredOutputClient(outreach_result())
        )
        with self.assertRaisesRegex(
            OutreachApplicationNotFoundError, "record not found"
        ):
            await service.generate(999_999)

        self.resume.parsed_data = {}
        await self.resume.save(update_fields=["parsed_data", "updated_at"])
        with self.assertRaisesRegex(
            MissingOutreachResumeDataError, "required before"
        ):
            await service.generate(self.application.id)

    async def test_missing_candidate_or_job_information_is_rejected(self) -> None:
        service = OutreachGenerationService(
            client=MockStructuredOutputClient(outreach_result())
        )
        self.candidate.name = ""
        await self.candidate.save(update_fields=["name", "updated_at"])
        with self.assertRaisesRegex(InvalidOutreachContextError, "Candidate name"):
            await service.generate(self.application.id)

        self.candidate.name = "Ahmed Khan"
        await self.candidate.save(update_fields=["name", "updated_at"])
        self.job.title = ""
        await self.job.save(update_fields=["title", "updated_at"])
        with self.assertRaisesRegex(InvalidOutreachContextError, "Job title"):
            await service.generate(self.application.id)

    async def test_internal_score_or_ai_references_are_rejected(self) -> None:
        result = outreach_result()
        result["body"] = (
            "Hi Ahmed, your AI evaluation fit score was 92 for the Backend Engineer role."
        )

        with self.assertRaisesRegex(
            InvalidOutreachOutputError, "prohibited internal evaluation details"
        ):
            await OutreachGenerationService(
                client=MockStructuredOutputClient(result)
            ).generate(self.application.id)

    async def test_provider_errors_are_wrapped(self) -> None:
        with self.assertRaisesRegex(
            OutreachGenerationProviderError, "provider is unavailable"
        ):
            await OutreachGenerationService(
                client=FailingStructuredOutputClient()
            ).generate(self.application.id)


if __name__ == "__main__":
    unittest.main()
