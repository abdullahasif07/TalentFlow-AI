from __future__ import annotations

import unittest
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from tortoise import Tortoise

from app.db.models import AIEvaluation, Application, Candidate, Company, Job, Resume
from app.enums import AIProcessingState, ApplicationStatus, JobStatus
from app.schemas import CandidateComparison, CandidateTradeoffSummary
from app.services.ai.candidate_comparison import CandidateComparisonService
from app.services.ai.client import LLMClientError
from app.services.errors import (
    CandidateComparisonProviderError,
    ComparisonApplicationNotFoundError,
    ComparisonJobMismatchError,
    ComparisonJobNotFoundError,
    IncompleteCandidateComparisonDataError,
    InvalidCandidateComparisonInputError,
    InvalidCandidateComparisonOutputError,
    MissingCandidateEvaluationError,
    MissingComparisonJobCriteriaError,
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
        raise LLMClientError("provider details must not escape")


def job_criteria() -> dict[str, object]:
    return {
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["FastAPI"],
        "minimum_experience_years": 3,
        "relevant_domains": ["Recruitment technology"],
        "relevant_experience": ["Production API development"],
        "education_requirements": [],
        "important_responsibilities": ["Build reliable backend services"],
        "evaluation_categories": [
            {
                "name": "Technical Skills",
                "description": "Evidence for required and preferred technologies.",
                "weight": 60,
            },
            {
                "name": "Relevant Experience",
                "description": "Evidence of relevant production API work.",
                "weight": 40,
            },
        ],
    }


def parsed_resume(index: int) -> dict[str, object]:
    return {
        "professional_summary": f"Backend engineer profile {index}.",
        "skills": ["Python", "PostgreSQL"],
        "technologies": ["FastAPI", "Docker"],
        "total_experience_years": float(index + 2),
        "employment_history": [
            {
                "company": f"Example Systems {index}",
                "role": "Backend Engineer",
                "start_date": "2021",
                "end_date": "Present",
                "description": "Built production APIs using Python and PostgreSQL.",
                "technologies": ["Python", "PostgreSQL", "FastAPI"],
            }
        ],
        "education": [],
        "projects": [],
        "certifications": [],
        "normalization_notes": [],
    }


def stored_evaluation(
    *,
    technical_score: float,
    experience_score: float,
) -> dict[str, object]:
    technical_weighted = round(technical_score * 0.6, 2)
    experience_weighted = round(experience_score * 0.4, 2)
    overall_score = round(technical_weighted + experience_weighted, 2)
    return {
        "overall_score": overall_score,
        "confidence": "HIGH",
        "recommendation": "GOOD_MATCH",
        "strengths": [
            {
                "summary": "Relevant Python API experience.",
                "evidence": ["Built production APIs using Python and PostgreSQL."],
            }
        ],
        "gaps": [
            {
                "summary": "Recruitment technology experience is not stated.",
                "evidence": [],
            }
        ],
        "matched_requirements": [
            {
                "requirement": "Python",
                "status": "MATCH",
                "evidence": "Built production APIs using Python and PostgreSQL.",
            }
        ],
        "missing_requirements": [
            {
                "requirement": "Recruitment technology",
                "status": "MISSING_EVIDENCE",
                "evidence": None,
            }
        ],
        "category_scores": [
            {
                "name": "Technical Skills",
                "score": technical_score,
                "weight": 60,
                "weighted_score": technical_weighted,
                "rationale": "The resume explicitly lists the required technologies.",
                "evidence": ["Python", "PostgreSQL"],
            },
            {
                "name": "Relevant Experience",
                "score": experience_score,
                "weight": 40,
                "weighted_score": experience_weighted,
                "rationale": "The resume describes relevant production API work.",
                "evidence": ["Built production APIs using Python and PostgreSQL."],
            },
        ],
        "evidence": [
            {
                "claim": "The candidate has production API experience.",
                "resume_evidence": "Built production APIs using Python and PostgreSQL.",
                "category": "Relevant Experience",
            }
        ],
    }


def tradeoff_result(application_ids: list[int]) -> dict[str, object]:
    first, second = application_ids[:2]
    return {
        "overview": "The selected applications show different evidence across the job rubric.",
        "relative_strengths": [
            f"Application {first} has stronger explicit backend API evidence "
            f"than Application {second}."
        ],
        "tradeoffs": [
            f"Application {second} shows broader infrastructure evidence, while "
            f"Application {first} shows deeper API evidence."
        ],
        "differentiating_experience": [
            f"Application {first} documents production FastAPI work."
        ],
        "notable_gaps": [
            f"Application {second} does not provide evidence of recruitment technology work."
        ],
        "comparable_areas": [
            "Both applications provide evidence for the core Python requirement."
        ],
    }


class CandidateComparisonTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.company = await Company.create(name="Comparison Test Company")
        self.job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description="Build Python APIs backed by PostgreSQL.",
            required_skills=["Python", "PostgreSQL"],
            preferred_skills=["FastAPI"],
            experience_requirement="3+ years",
            evaluation_criteria=job_criteria(),
            status=JobStatus.OPEN,
        )
        self.applications = [
            await self.create_evaluated_application(index=index)
            for index in range(1, 6)
        ]

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    async def create_evaluated_application(
        self,
        *,
        index: int,
        job: Job | None = None,
        evaluated: bool = True,
    ) -> Application:
        selected_job = job or self.job
        candidate = await Candidate.create(
            name=f"Display Candidate {index}",
            email=f"comparison-{selected_job.id}-{index}@example.com",
        )
        application = await Application.create(
            candidate=candidate,
            job=selected_job,
            status=ApplicationStatus.HUMAN_REVIEW,
            fit_score=Decimal("0.00") if evaluated else None,
            evaluation_processing_state=(
                AIProcessingState.COMPLETED
                if evaluated
                else AIProcessingState.NOT_STARTED
            ),
        )
        await Resume.create(
            candidate=candidate,
            file_url=f"uploads/resumes/{candidate.id}/resume.pdf",
            parsed_data=parsed_resume(index),
            processing_state=AIProcessingState.COMPLETED,
        )
        if evaluated:
            analysis = stored_evaluation(
                technical_score=95 - index * 5,
                experience_score=85 - index * 5,
            )
            application.fit_score = Decimal(str(analysis["overall_score"]))
            await application.save(update_fields=["fit_score", "updated_at"])
            await AIEvaluation.create(
                application=application,
                overall_score=Decimal(str(analysis["overall_score"])),
                recommendation=str(analysis["recommendation"]),
                confidence=str(analysis["confidence"]),
                strengths=analysis["strengths"],
                gaps=analysis["gaps"],
                evidence=analysis["evidence"],
                analysis_json=analysis,
            )
        return application

    async def compare(
        self,
        applications: list[Application],
        *,
        result: object | None = None,
    ) -> tuple[CandidateComparison, MockStructuredOutputClient]:
        application_ids = [application.id for application in applications]
        client = MockStructuredOutputClient(result or tradeoff_result(application_ids))
        comparison = await CandidateComparisonService(client=client).compare(
            job_id=self.job.id,
            application_ids=application_ids,
        )
        return comparison, client

    async def test_compares_two_applications_using_stored_evaluations(self) -> None:
        selected = self.applications[:2]

        comparison, client = await self.compare(selected)

        self.assertIsInstance(comparison, CandidateComparison)
        self.assertEqual(comparison.job_id, self.job.id)
        self.assertEqual(
            [candidate.application_id for candidate in comparison.candidates],
            [application.id for application in selected],
        )
        self.assertEqual(
            [category.category for category in comparison.criteria_comparison],
            ["Technical Skills", "Relevant Experience"],
        )
        self.assertIs(client.calls[0]["response_model"], CandidateTradeoffSummary)
        input_text = str(client.calls[0]["input_text"])
        self.assertNotIn("Display Candidate", input_text)
        self.assertIn("protected or personal attribute", str(client.calls[0]["instructions"]))

    async def test_compares_five_applications(self) -> None:
        comparison, _ = await self.compare(self.applications)

        self.assertEqual(len(comparison.candidates), 5)
        self.assertTrue(
            all(
                len(category.candidates) == 5
                for category in comparison.criteria_comparison
            )
        )

    async def test_applications_from_another_job_are_rejected(self) -> None:
        other_job = await Job.create(
            company=self.company,
            title="Platform Engineer",
            description="Build platform services.",
            evaluation_criteria=job_criteria(),
            status=JobStatus.OPEN,
        )
        other_application = await self.create_evaluated_application(
            index=20,
            job=other_job,
        )

        with self.assertRaises(ComparisonJobMismatchError) as raised:
            await CandidateComparisonService(
                client=MockStructuredOutputClient({})
            ).compare(
                job_id=self.job.id,
                application_ids=[self.applications[0].id, other_application.id],
            )

        self.assertEqual(raised.exception.application_ids, (other_application.id,))

    async def test_unevaluated_application_is_rejected_with_its_id(self) -> None:
        unevaluated = await self.create_evaluated_application(
            index=30,
            evaluated=False,
        )

        with self.assertRaises(MissingCandidateEvaluationError) as raised:
            await CandidateComparisonService(
                client=MockStructuredOutputClient({})
            ).compare(
                job_id=self.job.id,
                application_ids=[self.applications[0].id, unevaluated.id],
            )

        self.assertEqual(raised.exception.application_ids, (unevaluated.id,))

    async def test_duplicate_application_ids_are_rejected(self) -> None:
        application_id = self.applications[0].id

        with self.assertRaisesRegex(
            InvalidCandidateComparisonInputError,
            "unique",
        ):
            await CandidateComparisonService(
                client=MockStructuredOutputClient({})
            ).compare(
                job_id=self.job.id,
                application_ids=[application_id, application_id],
            )

    async def test_deterministic_stored_scores_are_preserved(self) -> None:
        comparison, _ = await self.compare(self.applications[:2])
        persisted = await AIEvaluation.filter(
            application_id__in=[application.id for application in self.applications[:2]]
        ).order_by("application_id")

        self.assertEqual(
            [Decimal(str(candidate.overall_score)) for candidate in comparison.candidates],
            [evaluation.overall_score for evaluation in persisted],
        )
        self.assertEqual(
            comparison.criteria_comparison[0].candidates[0].score,
            90.0,
        )

    async def test_llm_cannot_add_or_overwrite_score_fields(self) -> None:
        result = tradeoff_result([application.id for application in self.applications[:2]])
        result["overall_scores"] = {str(self.applications[0].id): 1}

        with self.assertRaisesRegex(
            InvalidCandidateComparisonOutputError,
            "invalid structured data",
        ):
            await self.compare(self.applications[:2], result=result)

    async def test_malformed_or_decision_making_output_is_rejected(self) -> None:
        malformed = tradeoff_result(
            [application.id for application in self.applications[:2]]
        )
        malformed["overview"] = "Hire Candidate 1 for this role."

        with self.assertRaises(InvalidCandidateComparisonOutputError):
            await self.compare(self.applications[:2], result=malformed)

        unselected = tradeoff_result(
            [application.id for application in self.applications[:2]]
        )
        unselected["relative_strengths"] = [
            "Application 999 has stronger evidence than the selected applications."
        ]
        with self.assertRaisesRegex(
            InvalidCandidateComparisonOutputError,
            "unselected application",
        ):
            await self.compare(self.applications[:2], result=unselected)

    async def test_provider_failure_is_wrapped(self) -> None:
        with self.assertRaisesRegex(
            CandidateComparisonProviderError,
            "provider is unavailable",
        ):
            await CandidateComparisonService(
                client=FailingStructuredOutputClient()
            ).compare(
                job_id=self.job.id,
                application_ids=[
                    self.applications[0].id,
                    self.applications[1].id,
                ],
            )

    async def test_missing_and_incomplete_records_are_cleanly_reported(self) -> None:
        with self.assertRaises(ComparisonJobNotFoundError):
            await CandidateComparisonService(
                client=MockStructuredOutputClient({})
            ).compare(
                job_id=999_999,
                application_ids=[
                    self.applications[0].id,
                    self.applications[1].id,
                ],
            )

        with self.assertRaises(ComparisonApplicationNotFoundError) as missing:
            await CandidateComparisonService(
                client=MockStructuredOutputClient({})
            ).compare(
                job_id=self.job.id,
                application_ids=[self.applications[0].id, 999_999],
            )
        self.assertEqual(missing.exception.application_ids, (999_999,))

        evaluation = await AIEvaluation.get(
            application_id=self.applications[1].id
        )
        evaluation.analysis_json = {}
        await evaluation.save(update_fields=["analysis_json", "updated_at"])
        with self.assertRaises(IncompleteCandidateComparisonDataError) as incomplete:
            await CandidateComparisonService(
                client=MockStructuredOutputClient({})
            ).compare(
                job_id=self.job.id,
                application_ids=[
                    self.applications[0].id,
                    self.applications[1].id,
                ],
            )
        self.assertEqual(
            incomplete.exception.application_ids,
            (self.applications[1].id,),
        )

    async def test_application_count_bounds_are_enforced(self) -> None:
        with self.assertRaisesRegex(
            InvalidCandidateComparisonInputError,
            "between 2 and 5",
        ):
            await CandidateComparisonService(
                client=MockStructuredOutputClient({})
            ).compare(
                job_id=self.job.id,
                application_ids=[self.applications[0].id],
            )

        with self.assertRaisesRegex(
            InvalidCandidateComparisonInputError,
            "between 2 and 5",
        ):
            await CandidateComparisonService(
                client=MockStructuredOutputClient({})
            ).compare(
                job_id=self.job.id,
                application_ids=[1, 2, 3, 4, 5, 6],
            )

    async def test_missing_job_criteria_are_rejected_before_llm_use(self) -> None:
        self.job.evaluation_criteria = {}
        await self.job.save(update_fields=["evaluation_criteria", "updated_at"])
        client = MockStructuredOutputClient({})

        with self.assertRaises(MissingComparisonJobCriteriaError):
            await CandidateComparisonService(client=client).compare(
                job_id=self.job.id,
                application_ids=[
                    self.applications[0].id,
                    self.applications[1].id,
                ],
            )

        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
