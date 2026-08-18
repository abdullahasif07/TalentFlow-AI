from __future__ import annotations

import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from tortoise import Tortoise, connections

from app.db.models import AIEvaluation, Application, Candidate, Company, Job, Resume
from app.enums import AIProcessingState, EvaluationConfidence, JobStatus
from app.graphql.schema import schema
from app.services import RecruiterApplicationQueryService
from app.worker import tasks as worker_tasks


def criteria_data() -> dict[str, object]:
    return {
        "required_skills": ["Python"],
        "preferred_skills": [],
        "minimum_experience_years": None,
        "relevant_domains": [],
        "relevant_experience": ["Backend development"],
        "education_requirements": [],
        "important_responsibilities": ["Build APIs"],
        "evaluation_categories": [
            {
                "name": "Technical Skills",
                "description": "Evidence of Python skills.",
                "weight": 100,
            }
        ],
    }


def evaluation_analysis(score: int) -> dict[str, object]:
    return {
        "overall_score": score,
        "confidence": "HIGH",
        "recommendation": "GOOD_MATCH",
        "strengths": [
            {"summary": "Python is explicitly supported.", "evidence": ["Python"]}
        ],
        "gaps": [
            {"summary": "Cloud experience is not shown.", "evidence": []}
        ],
        "matched_requirements": [
            {"requirement": "Python", "status": "MATCH", "evidence": "Python"}
        ],
        "missing_requirements": [
            {
                "requirement": "Cloud experience",
                "status": "MISSING_EVIDENCE",
                "evidence": None,
            }
        ],
        "category_scores": [
            {
                "name": "Technical Skills",
                "score": score,
                "weight": 100,
                "weighted_score": score,
                "rationale": "The resume names Python.",
                "evidence": ["Python"],
            }
        ],
        "evidence": [
            {
                "claim": "Python is supported.",
                "resume_evidence": "Python",
                "category": "Technical Skills",
            }
        ],
    }


class AIGraphQLTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.company = await Company.create(name="AI GraphQL Company")
        self.job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description="Build Python APIs.",
            required_skills=["Python"],
            preferred_skills=[],
            evaluation_criteria=criteria_data(),
            criteria_processing_state=AIProcessingState.COMPLETED,
            status=JobStatus.OPEN,
        )
        self.candidate = await Candidate.create(
            name="Main Applicant",
            email="main-ai-graphql@example.com",
        )
        self.application = await Application.create(
            candidate=self.candidate,
            job=self.job,
            resume_url="uploads/resumes/main/resume.pdf",
        )
        self.resume = await Resume.create(
            candidate=self.candidate,
            file_url="uploads/resumes/main/resume.pdf",
            raw_text="Python backend engineer",
            parsed_data={"skills": ["Python"]},
            processing_state=AIProcessingState.COMPLETED,
        )

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    def assert_success(self, result: object) -> dict:
        self.assertIsNone(getattr(result, "errors"), getattr(result, "errors"))
        data = getattr(result, "data")
        self.assertIsNotNone(data)
        return data

    async def test_ai_mutations_enqueue_tasks_and_return_immediately(self) -> None:
        with (
            patch.object(
                worker_tasks.generate_job_criteria,
                "delay",
                return_value=SimpleNamespace(id="criteria-task"),
            ) as criteria_delay,
            patch.object(
                worker_tasks.process_resume,
                "delay",
                return_value=SimpleNamespace(id="resume-task"),
            ) as resume_delay,
            patch.object(
                worker_tasks.evaluate_application,
                "delay",
                return_value=SimpleNamespace(id="evaluation-task"),
            ) as evaluation_delay,
        ):
            result = self.assert_success(
                await schema.execute(
                    """
                    mutation TriggerAI(
                      $criteria: GenerateJobCriteriaInput!
                      $resume: ProcessApplicationResumeInput!
                      $evaluation: GenerateCandidateEvaluationInput!
                    ) {
                      generateJobCriteria(input: $criteria) {
                        success accepted resourceId state message taskId errors { code }
                      }
                      processApplicationResume(input: $resume) {
                        success accepted resourceId state message taskId errors { code }
                      }
                      generateCandidateEvaluation(input: $evaluation) {
                        success accepted resourceId state message taskId errors { code }
                      }
                    }
                    """,
                    variable_values={
                        "criteria": {"jobId": str(self.job.id)},
                        "resume": {"applicationId": str(self.application.id)},
                        "evaluation": {"applicationId": str(self.application.id)},
                    },
                )
            )

        self.assertEqual(result["generateJobCriteria"]["taskId"], "criteria-task")
        self.assertEqual(result["processApplicationResume"]["taskId"], "resume-task")
        self.assertEqual(
            result["generateCandidateEvaluation"]["taskId"],
            "evaluation-task",
        )
        for payload in result.values():
            self.assertTrue(payload["success"])
            self.assertTrue(payload["accepted"])
            self.assertEqual(payload["state"], "PROCESSING")
        criteria_delay.assert_called_once_with(self.job.id)
        resume_delay.assert_called_once_with(self.application.id)
        evaluation_delay.assert_called_once_with(self.application.id)

        await self.job.refresh_from_db()
        await self.resume.refresh_from_db()
        await self.application.refresh_from_db()
        self.assertEqual(
            self.job.criteria_processing_state,
            AIProcessingState.PROCESSING,
        )
        self.assertEqual(self.resume.processing_state, AIProcessingState.PROCESSING)
        self.assertEqual(
            self.application.evaluation_processing_state,
            AIProcessingState.PROCESSING,
        )

    async def test_invalid_resource_ids_are_cleanly_rejected(self) -> None:
        result = self.assert_success(
            await schema.execute(
                """
                mutation {
                  generateJobCriteria(input: { jobId: "999999" }) {
                    success accepted errors { code field }
                  }
                  processApplicationResume(input: { applicationId: "999999" }) {
                    success accepted errors { code field }
                  }
                  generateCandidateEvaluation(input: { applicationId: "bad-id" }) {
                    success accepted errors { code field }
                  }
                }
                """
            )
        )

        self.assertEqual(
            result["generateJobCriteria"]["errors"][0]["code"],
            "NOT_FOUND",
        )
        self.assertEqual(
            result["processApplicationResume"]["errors"][0]["code"],
            "NOT_FOUND",
        )
        self.assertEqual(
            result["generateCandidateEvaluation"]["errors"][0]["code"],
            "VALIDATION_ERROR",
        )

    async def test_queue_failure_is_persisted_as_failed(self) -> None:
        with patch.object(
            worker_tasks.process_resume,
            "delay",
            side_effect=ConnectionError("broker unavailable"),
        ):
            payload = self.assert_success(
                await schema.execute(
                    """
                    mutation($input: ProcessApplicationResumeInput!) {
                      processApplicationResume(input: $input) {
                        success accepted state errors { code }
                      }
                    }
                    """,
                    variable_values={
                        "input": {"applicationId": str(self.application.id)}
                    },
                )
            )["processApplicationResume"]

        self.assertFalse(payload["success"])
        self.assertEqual(payload["state"], "FAILED")
        self.assertEqual(payload["errors"][0]["code"], "INTERNAL_ERROR")
        await self.resume.refresh_from_db()
        self.assertEqual(self.resume.processing_state, AIProcessingState.FAILED)

    async def create_evaluated_application(
        self,
        *,
        index: int,
        score: int,
    ) -> Application:
        candidate = await Candidate.create(
            name=f"Ranked Candidate {index}",
            email=f"ranked-{index}@example.com",
        )
        application = await Application.create(
            candidate=candidate,
            job=self.job,
            fit_score=Decimal(score),
            evaluation_processing_state=AIProcessingState.COMPLETED,
        )
        analysis = evaluation_analysis(score)
        await AIEvaluation.create(
            application=application,
            overall_score=Decimal(score),
            recommendation="GOOD_MATCH",
            confidence=EvaluationConfidence.HIGH,
            strengths=analysis["strengths"],
            gaps=analysis["gaps"],
            evidence=analysis["evidence"],
            analysis_json=analysis,
        )
        return application

    async def test_recommended_candidates_are_ordered_limited_and_evaluated(self) -> None:
        for index, score in enumerate([65, 95, 72, 88, 79, 91], start=1):
            await self.create_evaluated_application(index=index, score=score)

        default_result = self.assert_success(
            await schema.execute(
                """
                query($input: RecommendedCandidatesInput!) {
                  recommendedCandidates(input: $input) {
                    success totalCount limit
                    items {
                      candidate { name email }
                      application { id fitScore evaluationProcessingState }
                      evaluation { overallScore confidence processingState }
                    }
                    errors { code field }
                  }
                }
                """,
                variable_values={"input": {"jobId": str(self.job.id)}},
            )
        )["recommendedCandidates"]

        self.assertEqual(default_result["totalCount"], 6)
        self.assertEqual(default_result["limit"], 5)
        self.assertEqual(
            [Decimal(item["application"]["fitScore"]) for item in default_result["items"]],
            [Decimal("95"), Decimal("91"), Decimal("88"), Decimal("79"), Decimal("72")],
        )
        self.assertNotIn(
            self.candidate.email,
            {item["candidate"]["email"] for item in default_result["items"]},
        )

        limited = self.assert_success(
            await schema.execute(
                """
                query($input: RecommendedCandidatesInput!) {
                  recommendedCandidates(input: $input) {
                    success limit items { application { fitScore } } errors { code }
                  }
                }
                """,
                variable_values={
                    "input": {"jobId": str(self.job.id), "limit": 2}
                },
            )
        )["recommendedCandidates"]
        self.assertEqual(len(limited["items"]), 2)
        self.assertEqual(limited["limit"], 2)

        invalid_limit = self.assert_success(
            await schema.execute(
                """
                query($input: RecommendedCandidatesInput!) {
                  recommendedCandidates(input: $input) {
                    success items { application { id } } errors { code field }
                  }
                }
                """,
                variable_values={
                    "input": {"jobId": str(self.job.id), "limit": 51}
                },
            )
        )["recommendedCandidates"]
        self.assertFalse(invalid_limit["success"])
        self.assertEqual(invalid_limit["errors"][0]["field"], "limit")

    async def test_batch_screening_only_queues_eligible_unevaluated_applications(self) -> None:
        completed = await self.create_evaluated_application(index=20, score=90)

        unparsed_candidate = await Candidate.create(
            name="Unparsed Candidate",
            email="unparsed@example.com",
        )
        unparsed = await Application.create(candidate=unparsed_candidate, job=self.job)
        await Resume.create(
            candidate=unparsed_candidate,
            file_url="uploads/resumes/unparsed.pdf",
            parsed_data={},
        )

        second_candidate = await Candidate.create(
            name="Second Eligible",
            email="second-eligible@example.com",
        )
        second_eligible = await Application.create(
            candidate=second_candidate,
            job=self.job,
        )
        await Resume.create(
            candidate=second_candidate,
            file_url="uploads/resumes/second.pdf",
            parsed_data={"skills": ["Python"]},
        )

        processing_candidate = await Candidate.create(
            name="Already Processing",
            email="already-processing@example.com",
        )
        processing = await Application.create(
            candidate=processing_candidate,
            job=self.job,
            evaluation_processing_state=AIProcessingState.PROCESSING,
        )
        await Resume.create(
            candidate=processing_candidate,
            file_url="uploads/resumes/processing.pdf",
            parsed_data={"skills": ["Python"]},
        )

        with patch.object(
            worker_tasks.evaluate_application,
            "delay",
            return_value=SimpleNamespace(id="batch-task"),
        ) as delay:
            payload = self.assert_success(
                await schema.execute(
                    """
                    mutation($input: ScreenJobApplicantsInput!) {
                      screenJobApplicants(input: $input) {
                        success accepted state queuedCount applicationIds
                        failedApplicationIds errors { code }
                      }
                    }
                    """,
                    variable_values={"input": {"jobId": str(self.job.id)}},
                )
            )["screenJobApplicants"]

        expected_ids = {str(self.application.id), str(second_eligible.id)}
        self.assertEqual(set(payload["applicationIds"]), expected_ids)
        self.assertEqual(payload["queuedCount"], 2)
        self.assertEqual(
            {call.args[0] for call in delay.call_args_list},
            {self.application.id, second_eligible.id},
        )
        self.assertNotIn(completed.id, {call.args[0] for call in delay.call_args_list})
        self.assertNotIn(unparsed.id, {call.args[0] for call in delay.call_args_list})
        self.assertNotIn(processing.id, {call.args[0] for call in delay.call_args_list})

    async def test_recommended_candidates_use_a_fixed_number_of_queries(self) -> None:
        for index, score in enumerate([70, 80, 90], start=30):
            await self.create_evaluated_application(index=index, score=score)

        connection = connections.get("default")
        original_execute_query = connection.execute_query
        query_count = 0

        async def counting_execute_query(*args: object, **kwargs: object):
            nonlocal query_count
            query_count += 1
            return await original_execute_query(*args, **kwargs)

        connection.execute_query = counting_execute_query
        try:
            page = await RecruiterApplicationQueryService.list_recommended_for_job(
                job_id=self.job.id,
                limit=5,
            )
        finally:
            connection.execute_query = original_execute_query

        self.assertEqual(len(page.records), 3)
        self.assertEqual(query_count, 3)

    async def test_application_query_returns_persisted_evaluation_details(self) -> None:
        analysis = evaluation_analysis(84)
        await Application.filter(id=self.application.id).update(
            fit_score=Decimal("84"),
            evaluation_processing_state=AIProcessingState.COMPLETED,
        )
        await AIEvaluation.create(
            application=self.application,
            overall_score=Decimal("84"),
            recommendation="GOOD_MATCH",
            confidence=EvaluationConfidence.HIGH,
            strengths=analysis["strengths"],
            gaps=analysis["gaps"],
            evidence=analysis["evidence"],
            analysis_json=analysis,
        )

        payload = self.assert_success(
            await schema.execute(
                """
                query($input: ApplicationQueryInput!) {
                  application(input: $input) {
                    success
                    application {
                      fitScore evaluationProcessingState
                      resume { processingState }
                      evaluation {
                        overallScore confidence recommendation processingState
                        strengths { summary evidence }
                        gaps { summary evidence }
                        matchedRequirements { requirement status evidence }
                        missingRequirements { requirement status evidence }
                        evidence { claim resumeEvidence category }
                        categoryScores {
                          name score weight weightedScore rationale evidence
                        }
                      }
                    }
                    errors { code }
                  }
                }
                """,
                variable_values={"input": {"id": str(self.application.id)}},
            )
        )["application"]

        evaluation = payload["application"]["evaluation"]
        self.assertEqual(payload["application"]["fitScore"], "84")
        self.assertEqual(payload["application"]["evaluationProcessingState"], "COMPLETED")
        self.assertEqual(evaluation["strengths"][0]["summary"], "Python is explicitly supported.")
        self.assertEqual(evaluation["gaps"][0]["summary"], "Cloud experience is not shown.")
        self.assertEqual(evaluation["evidence"][0]["resumeEvidence"], "Python")
        self.assertEqual(evaluation["matchedRequirements"][0]["status"], "MATCH")
        self.assertEqual(
            evaluation["missingRequirements"][0]["status"],
            "MISSING_EVIDENCE",
        )
        self.assertIsNone(evaluation["missingRequirements"][0]["evidence"])
        self.assertEqual(evaluation["categoryScores"][0]["weight"], 100)


if __name__ == "__main__":
    unittest.main()
