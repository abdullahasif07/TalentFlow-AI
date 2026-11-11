from __future__ import annotations

import unittest
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from pydantic import BaseModel
from tortoise import Tortoise

from app.db.models import (
    AIEvaluation,
    Application,
    ApplicationStatusHistory,
    Candidate,
    Company,
    Job,
    OutreachEmail,
    Resume,
)
from app.enums import AIProcessingState, ApplicationStatus, JobStatus
from app.graphql.schema import schema
from auth_helpers import execute_as_recruiter, isolate_from_redis
from app.services.ai.client import LLMClientError
from app.services.application_query import RecruiterApplicationQueryService


class MockComparisonClient:
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


class FailingComparisonClient:
    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        response_model: type[BaseModel],
    ) -> Any:
        raise LLMClientError("private provider failure")


def criteria_data() -> dict[str, object]:
    return {
        "required_skills": ["Python"],
        "preferred_skills": ["FastAPI"],
        "minimum_experience_years": 3,
        "relevant_domains": [],
        "relevant_experience": ["Backend API development"],
        "education_requirements": [],
        "important_responsibilities": ["Build reliable APIs"],
        "evaluation_categories": [
            {
                "name": "Technical Skills",
                "description": "Evidence for Python and FastAPI.",
                "weight": 60,
            },
            {
                "name": "Relevant Experience",
                "description": "Evidence for production backend work.",
                "weight": 40,
            },
        ],
    }


def evaluation_data(score: int) -> dict[str, object]:
    return {
        "overall_score": score,
        "confidence": "HIGH",
        "recommendation": "GOOD_MATCH",
        "strengths": [
            {
                "summary": "Python API work is supported.",
                "evidence": ["Built APIs with Python and FastAPI."],
            }
        ],
        "gaps": [
            {
                "summary": "Cloud deployment evidence is not present.",
                "evidence": [],
            }
        ],
        "matched_requirements": [
            {
                "requirement": "Python",
                "status": "MATCH",
                "evidence": "Built APIs with Python and FastAPI.",
            }
        ],
        "missing_requirements": [],
        "category_scores": [
            {
                "name": "Technical Skills",
                "score": score,
                "weight": 60,
                "weighted_score": round(score * 0.6, 2),
                "rationale": "The resume contains direct Python API evidence.",
                "evidence": ["Python", "FastAPI"],
            },
            {
                "name": "Relevant Experience",
                "score": score,
                "weight": 40,
                "weighted_score": round(score * 0.4, 2),
                "rationale": "The resume contains production backend evidence.",
                "evidence": ["Backend APIs"],
            },
        ],
        "evidence": [
            {
                "claim": "Python API experience is supported.",
                "resume_evidence": "Built APIs with Python and FastAPI.",
                "category": "Technical Skills",
            }
        ],
    }


def comparison_summary(application_ids: list[int]) -> dict[str, object]:
    first, second = application_ids[:2]
    return {
        "overview": "The applications provide different depths of backend evidence.",
        "relative_strengths": [
            f"Application {first} provides deeper API evidence than Application {second}."
        ],
        "tradeoffs": [
            f"Application {second} shows broader tooling, while Application "
            f"{first} shows deeper API delivery."
        ],
        "differentiating_experience": [
            f"Application {first} documents production FastAPI work."
        ],
        "notable_gaps": [
            f"Application {second} does not provide cloud deployment evidence."
        ],
        "comparable_areas": [
            "Both applications support the core Python requirement."
        ],
    }


COMPARE_MUTATION = """
mutation CompareCandidates($input: CompareCandidatesInput!) {
  compareCandidates(input: $input) {
    success
    job { id title }
    candidates {
      applicationId
      candidateId
      name
      overallScore
      confidence
      recommendation
      strengths { summary evidence }
      gaps { summary evidence }
    }
    categories {
      name
      weight
      candidates { applicationId available score summary }
    }
    summary {
      overview
      relativeStrengths
      tradeoffs
      differentiatingExperience
      notableGaps
      comparableAreas
    }
    errors { code message field }
  }
}
"""


class CandidateComparisonGraphQLTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        isolate_from_redis(self)
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.company = await Company.create(name="Comparison GraphQL Company")
        self.job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description="Build reliable Python APIs.",
            required_skills=["Python"],
            preferred_skills=["FastAPI"],
            evaluation_criteria=criteria_data(),
            criteria_processing_state=AIProcessingState.COMPLETED,
            status=JobStatus.OPEN,
        )
        self.applications = [
            await self.create_application(index=index, score=96 - index * 4)
            for index in range(1, 6)
        ]

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    async def create_application(
        self,
        *,
        index: int,
        score: int,
        job: Job | None = None,
        evaluated: bool = True,
    ) -> Application:
        selected_job = job or self.job
        candidate = await Candidate.create(
            name=f"GraphQL Candidate {index}",
            email=f"comparison-graphql-{selected_job.id}-{index}@example.com",
        )
        application = await Application.create(
            candidate=candidate,
            job=selected_job,
            status=ApplicationStatus.SHORTLISTED,
            fit_score=Decimal(str(score)) if evaluated else None,
            evaluation_processing_state=(
                AIProcessingState.COMPLETED
                if evaluated
                else AIProcessingState.NOT_STARTED
            ),
        )
        await Resume.create(
            candidate=candidate,
            file_url=f"uploads/resumes/{candidate.id}/resume.pdf",
            raw_text="Backend engineer with Python and FastAPI experience.",
            parsed_data={
                "professional_summary": "Backend engineer building Python APIs.",
                "skills": ["Python", "FastAPI"],
            },
            processing_state=AIProcessingState.COMPLETED,
        )
        if evaluated:
            analysis = evaluation_data(score)
            await AIEvaluation.create(
                application=application,
                overall_score=Decimal(str(score)),
                recommendation="GOOD_MATCH",
                confidence="HIGH",
                strengths=analysis["strengths"],
                gaps=analysis["gaps"],
                evidence=analysis["evidence"],
                analysis_json=analysis,
            )
        return application

    async def execute_comparison(
        self,
        application_ids: list[int],
        *,
        job_id: int | None = None,
        client: object | None = None,
    ) -> dict:
        summary_ids = application_ids if len(application_ids) >= 2 else [1, 2]
        selected_client = client or MockComparisonClient(
            comparison_summary(summary_ids)
        )
        with patch(
            "app.services.ai.candidate_comparison.OpenAIStructuredOutputClient",
            return_value=selected_client,
        ):
            result = await execute_as_recruiter(
                COMPARE_MUTATION,
                variable_values={
                    "input": {
                        "jobId": str(job_id or self.job.id),
                        "applicationIds": [
                            str(application_id) for application_id in application_ids
                        ],
                    }
                },
            )
        self.assertIsNone(result.errors, result.errors)
        self.assertIsNotNone(result.data)
        return result.data["compareCandidates"]

    async def test_two_candidate_comparison_returns_typed_output_without_writes(self) -> None:
        selected = self.applications[:2]
        selected_ids = [application.id for application in selected]
        original_fit_scores = [application.fit_score for application in selected]
        original_statuses = [application.status for application in selected]
        original_application_updates = [
            application.updated_at for application in selected
        ]
        evaluations = await AIEvaluation.filter(
            application_id__in=selected_ids
        ).order_by("application_id")
        original_evaluations = [
            (
                evaluation.overall_score,
                evaluation.analysis_json,
                evaluation.updated_at,
            )
            for evaluation in evaluations
        ]
        resumes = await Resume.filter(
            candidate_id__in=[application.candidate_id for application in selected]
        ).order_by("candidate_id")
        original_resumes = [
            (resume.raw_text, resume.parsed_data, resume.updated_at)
            for resume in resumes
        ]
        recommended_before = [
            record.application.id
            for record in (
                await RecruiterApplicationQueryService.list_recommended_for_job(
                    job_id=self.job.id,
                    limit=5,
                )
            ).records
        ]

        payload = await self.execute_comparison(selected_ids)

        self.assertTrue(payload["success"])
        self.assertEqual(payload["job"], {"id": str(self.job.id), "title": self.job.title})
        self.assertEqual(
            [candidate["applicationId"] for candidate in payload["candidates"]],
            [str(application_id) for application_id in selected_ids],
        )
        self.assertEqual(
            Decimal(payload["candidates"][0]["overallScore"]),
            Decimal("92.00"),
        )
        self.assertEqual(payload["candidates"][0]["confidence"], "HIGH")
        self.assertEqual(payload["candidates"][0]["recommendation"], "GOOD_MATCH")
        self.assertEqual(
            payload["candidates"][0]["strengths"][0]["summary"],
            "Python API work is supported.",
        )
        self.assertEqual(payload["categories"][0]["name"], "Technical Skills")
        self.assertTrue(payload["categories"][0]["candidates"][0]["available"])
        self.assertEqual(
            Decimal(payload["categories"][0]["candidates"][0]["score"]),
            Decimal("92.00"),
        )
        self.assertIn("different depths", payload["summary"]["overview"])
        self.assertEqual(payload["errors"], [])

        refreshed = [await Application.get(id=application.id) for application in selected]
        self.assertEqual([application.fit_score for application in refreshed], original_fit_scores)
        self.assertEqual([application.status for application in refreshed], original_statuses)
        self.assertEqual(
            [application.updated_at for application in refreshed],
            original_application_updates,
        )
        refreshed_evaluations = await AIEvaluation.filter(
            application_id__in=selected_ids
        ).order_by("application_id")
        self.assertEqual(
            [
                (
                    evaluation.overall_score,
                    evaluation.analysis_json,
                    evaluation.updated_at,
                )
                for evaluation in refreshed_evaluations
            ],
            original_evaluations,
        )
        refreshed_resumes = await Resume.filter(
            candidate_id__in=[application.candidate_id for application in selected]
        ).order_by("candidate_id")
        self.assertEqual(
            [
                (resume.raw_text, resume.parsed_data, resume.updated_at)
                for resume in refreshed_resumes
            ],
            original_resumes,
        )
        recommended_after = [
            record.application.id
            for record in (
                await RecruiterApplicationQueryService.list_recommended_for_job(
                    job_id=self.job.id,
                    limit=5,
                )
            ).records
        ]
        self.assertEqual(recommended_after, recommended_before)
        self.assertEqual(await ApplicationStatusHistory.all().count(), 0)
        self.assertEqual(await OutreachEmail.all().count(), 0)

    async def test_five_candidate_comparison_returns_every_selection(self) -> None:
        payload = await self.execute_comparison(
            [application.id for application in self.applications]
        )

        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["candidates"]), 5)
        self.assertEqual(len(payload["categories"][0]["candidates"]), 5)

    async def test_invalid_selection_counts_and_duplicates_are_rejected(self) -> None:
        cases = (
            ([self.applications[0].id], "between 2 and 5"),
            ([1, 2, 3, 4, 5, 6], "between 2 and 5"),
            ([self.applications[0].id, self.applications[0].id], "unique"),
        )
        for application_ids, expected_message in cases:
            with self.subTest(application_ids=application_ids):
                payload = await self.execute_comparison(application_ids)
                self.assertFalse(payload["success"])
                self.assertEqual(payload["errors"][0]["code"], "VALIDATION_ERROR")
                self.assertEqual(payload["errors"][0]["field"], "applicationIds")
                self.assertIn(expected_message, payload["errors"][0]["message"])

    async def test_cross_job_and_missing_applications_return_clean_errors(self) -> None:
        other_job = await Job.create(
            company=self.company,
            title="Platform Engineer",
            description="Build platform services.",
            evaluation_criteria=criteria_data(),
            status=JobStatus.OPEN,
        )
        other_application = await self.create_application(
            index=20,
            score=80,
            job=other_job,
        )

        cross_job = await self.execute_comparison(
            [self.applications[0].id, other_application.id]
        )
        self.assertFalse(cross_job["success"])
        self.assertEqual(cross_job["errors"][0]["code"], "CONFLICT")
        self.assertEqual(cross_job["errors"][0]["field"], "applicationIds")

        missing = await self.execute_comparison([self.applications[0].id, 999_999])
        self.assertFalse(missing["success"])
        self.assertEqual(missing["errors"][0]["code"], "NOT_FOUND")
        self.assertEqual(missing["errors"][0]["field"], "applicationIds")

    async def test_missing_evaluation_is_rejected(self) -> None:
        unevaluated = await self.create_application(
            index=30,
            score=0,
            evaluated=False,
        )

        payload = await self.execute_comparison(
            [self.applications[0].id, unevaluated.id]
        )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["errors"][0]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["errors"][0]["field"], "applicationIds")
        self.assertIn(str(unevaluated.id), payload["errors"][0]["message"])

    async def test_missing_category_is_returned_as_unavailable(self) -> None:
        application = self.applications[1]
        evaluation = await AIEvaluation.get(application_id=application.id)
        analysis = dict(evaluation.analysis_json)
        analysis["category_scores"] = analysis["category_scores"][:1]
        evaluation.analysis_json = analysis
        await evaluation.save(update_fields=["analysis_json", "updated_at"])

        payload = await self.execute_comparison(
            [self.applications[0].id, application.id]
        )

        self.assertTrue(payload["success"])
        relevant_experience = payload["categories"][1]
        unavailable = relevant_experience["candidates"][1]
        self.assertEqual(relevant_experience["name"], "Relevant Experience")
        self.assertFalse(unavailable["available"])
        self.assertIsNone(unavailable["score"])
        self.assertIn("No stored evaluation score", unavailable["summary"])

    async def test_generation_failure_is_returned_without_provider_details(self) -> None:
        payload = await self.execute_comparison(
            [self.applications[0].id, self.applications[1].id],
            client=FailingComparisonClient(),
        )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["errors"][0]["code"], "INTERNAL_ERROR")
        self.assertNotIn("private provider failure", payload["errors"][0]["message"])


if __name__ == "__main__":
    unittest.main()
