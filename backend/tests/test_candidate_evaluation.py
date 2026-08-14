from __future__ import annotations

import json
import unittest
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from tortoise import Tortoise

from app.db.models import AIEvaluation, Application, Candidate, Company, Job, Resume
from app.enums import ApplicationStatus, JobStatus
from app.schemas import CandidateEvaluation, CandidateEvaluationAnalysis
from app.services.ai.candidate_evaluation import CandidateEvaluationService
from app.services.errors import (
    InvalidCandidateEvaluationOutputError,
    MissingJobEvaluationCriteriaError,
    MissingStructuredResumeDataError,
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
                "description": "Evidence for the required and preferred technologies.",
                "weight": 60,
            },
            {
                "name": "Relevant Experience",
                "description": "Evidence of relevant production API work.",
                "weight": 40,
            },
        ],
    }


def parsed_resume() -> dict[str, object]:
    return {
        "professional_summary": "Backend engineer building production APIs.",
        "skills": ["Python", "PostgreSQL", "FastAPI"],
        "technologies": ["Docker"],
        "total_experience_years": 4,
        "employment_history": [
            {
                "company": "Example Systems",
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


def evaluation_result(
    *,
    technical_score: float,
    experience_score: float,
    recommendation: str,
    confidence: str = "HIGH",
) -> dict[str, object]:
    return {
        "confidence": confidence,
        "recommendation": recommendation,
        "strengths": [
            {
                "summary": "The resume shows relevant Python API work.",
                "evidence": ["Built production APIs using Python and PostgreSQL."],
            }
        ],
        "gaps": [
            {
                "summary": "No recruitment technology work is stated.",
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
                "rationale": "The resume explicitly lists required technologies.",
                "evidence": ["Python", "PostgreSQL"],
            },
            {
                "name": "Relevant Experience",
                "score": experience_score,
                "rationale": "The resume describes production API work.",
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


class CandidateEvaluationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        company = await Company.create(name="Evaluation Test Company")
        self.candidate = await Candidate.create(
            name="Private Candidate Name",
            email="private-candidate@example.com",
        )
        self.job = await Job.create(
            company=company,
            title="Backend Engineer",
            description="Build Python APIs backed by PostgreSQL.",
            required_skills=["Python", "PostgreSQL"],
            preferred_skills=["FastAPI"],
            experience_requirement="3+ years",
            evaluation_criteria=job_criteria(),
            status=JobStatus.OPEN,
        )
        self.application = await Application.create(
            candidate=self.candidate,
            job=self.job,
            status=ApplicationStatus.HUMAN_REVIEW,
            resume_url="uploads/resumes/1/resume.pdf",
        )
        self.resume = await Resume.create(
            candidate=self.candidate,
            file_url="uploads/resumes/1/resume.pdf",
            raw_text="Original extracted text",
            parsed_data=parsed_resume(),
        )

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    async def evaluate(self, result: dict[str, object]) -> CandidateEvaluation:
        return await CandidateEvaluationService(
            client=MockStructuredOutputClient(result)
        ).evaluate_and_save(self.application.id)

    async def test_strong_candidate_uses_deterministic_weighted_score(self) -> None:
        client = MockStructuredOutputClient(
            evaluation_result(
                technical_score=90,
                experience_score=80,
                recommendation="STRONG_MATCH",
            )
        )

        evaluation = await CandidateEvaluationService(
            client=client
        ).evaluate_and_save(self.application.id)

        self.assertIsInstance(evaluation, CandidateEvaluation)
        self.assertEqual(evaluation.overall_score, 86.0)
        self.assertEqual(
            [item.weighted_score for item in evaluation.category_scores],
            [54.0, 32.0],
        )
        self.assertIs(client.calls[0]["response_model"], CandidateEvaluationAnalysis)
        input_text = str(client.calls[0]["input_text"])
        self.assertNotIn(self.candidate.name, input_text)
        self.assertNotIn(self.candidate.email, input_text)
        self.assertIn("protected or personal attribute", str(client.calls[0]["instructions"]))

    async def test_weak_candidate_is_scored_from_the_same_rubric(self) -> None:
        evaluation = await self.evaluate(
            evaluation_result(
                technical_score=20,
                experience_score=10,
                recommendation="WEAK_MATCH",
                confidence="MEDIUM",
            )
        )

        self.assertEqual(evaluation.overall_score, 16.0)
        self.assertEqual(evaluation.recommendation.value, "WEAK_MATCH")

    async def test_partially_matching_candidate_is_supported(self) -> None:
        result = evaluation_result(
            technical_score=60,
            experience_score=50,
            recommendation="PARTIAL_MATCH",
            confidence="MEDIUM",
        )
        result["matched_requirements"] = [
            {
                "requirement": "Python",
                "status": "PARTIAL_MATCH",
                "evidence": "Python is listed, but depth is not described.",
            }
        ]

        evaluation = await self.evaluate(result)

        self.assertEqual(evaluation.overall_score, 56.0)
        self.assertEqual(
            evaluation.matched_requirements[0].status.value,
            "PARTIAL_MATCH",
        )

    async def test_missing_structured_resume_data_is_rejected(self) -> None:
        self.resume.parsed_data = {}
        await self.resume.save(update_fields=["parsed_data", "updated_at"])

        with self.assertRaisesRegex(
            MissingStructuredResumeDataError, "required before"
        ):
            await self.evaluate(
                evaluation_result(
                    technical_score=50,
                    experience_score=50,
                    recommendation="INSUFFICIENT_EVIDENCE",
                )
            )

    async def test_missing_job_criteria_are_rejected(self) -> None:
        self.job.evaluation_criteria = {}
        await self.job.save(update_fields=["evaluation_criteria", "updated_at"])

        with self.assertRaisesRegex(
            MissingJobEvaluationCriteriaError, "required before"
        ):
            await self.evaluate(
                evaluation_result(
                    technical_score=50,
                    experience_score=50,
                    recommendation="PARTIAL_MATCH",
                )
            )

    async def test_out_of_range_model_score_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            InvalidCandidateEvaluationOutputError, "invalid structured data"
        ):
            await self.evaluate(
                evaluation_result(
                    technical_score=101,
                    experience_score=50,
                    recommendation="GOOD_MATCH",
                )
            )

    async def test_evaluation_is_persisted_without_pipeline_changes(self) -> None:
        initial_status = self.application.status
        existing = await AIEvaluation.create(
            application=self.application,
            overall_score=Decimal("1.00"),
            recommendation="OLD",
            confidence="LOW",
        )

        evaluation = await self.evaluate(
            evaluation_result(
                technical_score=75,
                experience_score=65,
                recommendation="GOOD_MATCH",
            )
        )

        await self.application.refresh_from_db()
        await self.resume.refresh_from_db()
        saved = await AIEvaluation.get(application_id=self.application.id)
        self.assertEqual(saved.id, existing.id)
        self.assertEqual(await AIEvaluation.filter(application_id=self.application.id).count(), 1)
        self.assertEqual(saved.overall_score, Decimal("71.00"))
        self.assertEqual(self.application.fit_score, Decimal("71.00"))
        self.assertEqual(self.application.status, initial_status)
        self.assertEqual(saved.recommendation, "GOOD_MATCH")
        self.assertEqual(saved.analysis_json, evaluation.model_dump(mode="json"))
        self.assertEqual(self.resume.raw_text, "Original extracted text")
        self.assertEqual(self.resume.parsed_data, parsed_resume())


if __name__ == "__main__":
    unittest.main()
