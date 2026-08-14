from __future__ import annotations

import asyncio
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from pydantic import BaseModel
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from tortoise import Tortoise

from app.config import settings
from app.db.models import AIEvaluation, Application, Candidate, Company, Job, Resume
from app.enums import AIProcessingState, ApplicationStatus, JobStatus
from app.services.ai.candidate_evaluation import CandidateEvaluationService
from app.services.ai.job_criteria import JobCriteriaService
from app.services.ai.resume_parser import ResumeParsingService
from app.services.errors import (
    JobCriteriaProviderError,
    MissingStructuredResumeDataError,
)
from app.worker import tasks as worker_tasks
from app.worker.celery_app import celery_app
from app.worker.runtime import run_async_db_operation


class MockStructuredOutputClient:
    def __init__(self, result: object) -> None:
        self.result = result

    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        response_model: type[BaseModel],
    ) -> Any:
        return self.result


def make_text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
    )
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(content)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def criteria_result() -> dict[str, object]:
    return {
        "required_skills": ["Python"],
        "preferred_skills": [],
        "minimum_experience_years": None,
        "relevant_domains": [],
        "relevant_experience": ["API development"],
        "education_requirements": [],
        "important_responsibilities": ["Build backend APIs"],
        "evaluation_categories": [
            {
                "name": "Technical Skills",
                "description": "Evidence of required Python skills.",
                "weight": 100,
            }
        ],
    }


def evaluation_result() -> dict[str, object]:
    return {
        "confidence": "HIGH",
        "recommendation": "GOOD_MATCH",
        "strengths": [
            {"summary": "Python is explicitly listed.", "evidence": ["Python"]}
        ],
        "gaps": [],
        "matched_requirements": [
            {"requirement": "Python", "status": "MATCH", "evidence": "Python"}
        ],
        "missing_requirements": [],
        "category_scores": [
            {
                "name": "Technical Skills",
                "score": 82,
                "rationale": "The required language is explicitly supported.",
                "evidence": ["Python"],
            }
        ],
        "evidence": [
            {
                "claim": "Python experience is supported.",
                "resume_evidence": "Python",
                "category": "Technical Skills",
            }
        ],
    }


class WorkerWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.upload_root = Path(self.temporary_directory.name) / "uploads"
        self.upload_patch = patch.object(settings, "upload_root", self.upload_root)
        self.upload_patch.start()

        company = await Company.create(name="Worker Test Company")
        self.candidate = await Candidate.create(
            name="Worker Candidate",
            email="worker-candidate@example.com",
        )
        self.job = await Job.create(
            company=company,
            title="Backend Engineer",
            description="Build Python APIs.",
            required_skills=["Python"],
            preferred_skills=[],
            evaluation_criteria=criteria_result(),
            status=JobStatus.OPEN,
        )
        self.application = await Application.create(
            candidate=self.candidate,
            job=self.job,
            status=ApplicationStatus.APPLIED,
            resume_url=f"uploads/resumes/{self.candidate.id}/resume.pdf",
        )
        resume_path = (
            self.upload_root / "resumes" / str(self.candidate.id) / "resume.pdf"
        )
        resume_path.parent.mkdir(parents=True, exist_ok=True)
        resume_path.write_bytes(make_text_pdf("Python backend engineer"))
        self.resume = await Resume.create(
            candidate=self.candidate,
            file_url=self.application.resume_url,
            raw_text=None,
            parsed_data={"skills": ["Python"]},
        )

    async def asyncTearDown(self) -> None:
        self.upload_patch.stop()
        await Tortoise.close_connections()
        self.temporary_directory.cleanup()

    async def test_resume_processing_workflow_extracts_parses_and_persists(self) -> None:
        parser = ResumeParsingService(
            client=MockStructuredOutputClient(
                {
                    "professional_summary": None,
                    "skills": ["Python"],
                    "technologies": [],
                    "total_experience_years": None,
                    "employment_history": [],
                    "education": [],
                    "projects": [],
                    "certifications": [],
                    "normalization_notes": [],
                }
            )
        )
        with patch.object(worker_tasks, "ResumeParsingService", return_value=parser):
            result = await worker_tasks.process_resume_workflow(self.application.id)

        await self.resume.refresh_from_db()
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self.resume.raw_text, "Python backend engineer")
        self.assertEqual(self.resume.parsed_data["skills"], ["Python"])
        self.assertEqual(
            self.resume.processing_state,
            AIProcessingState.COMPLETED,
        )

    async def test_job_criteria_workflow_generates_and_persists(self) -> None:
        self.job.evaluation_criteria = {}
        await self.job.save(update_fields=["evaluation_criteria", "updated_at"])
        service = JobCriteriaService(
            client=MockStructuredOutputClient(criteria_result())
        )
        with patch.object(worker_tasks, "JobCriteriaService", return_value=service):
            result = await worker_tasks.generate_job_criteria_workflow(self.job.id)

        await self.job.refresh_from_db()
        self.assertEqual(result["category_count"], 1)
        self.assertEqual(self.job.evaluation_criteria, criteria_result())
        self.assertEqual(
            self.job.criteria_processing_state,
            AIProcessingState.COMPLETED,
        )

    async def test_evaluation_workflow_is_idempotent_and_persists(self) -> None:
        service = CandidateEvaluationService(
            client=MockStructuredOutputClient(evaluation_result())
        )
        with patch.object(
            worker_tasks,
            "CandidateEvaluationService",
            return_value=service,
        ):
            first = await worker_tasks.evaluate_application_workflow(
                self.application.id
            )
            second = await worker_tasks.evaluate_application_workflow(
                self.application.id
            )

        await self.application.refresh_from_db()
        self.assertEqual(first["overall_score"], 82.0)
        self.assertEqual(second["overall_score"], 82.0)
        self.assertEqual(self.application.fit_score, 82)
        self.assertEqual(
            self.application.evaluation_processing_state,
            AIProcessingState.COMPLETED,
        )
        self.assertEqual(
            await AIEvaluation.filter(application_id=self.application.id).count(),
            1,
        )


class WorkerRuntimeTests(unittest.TestCase):
    def test_celery_registers_all_tasks(self) -> None:
        self.assertIn("talentflow.process_resume", celery_app.tasks)
        self.assertIn("talentflow.generate_job_criteria", celery_app.tasks)
        self.assertIn("talentflow.evaluate_application", celery_app.tasks)

    def test_each_operation_uses_and_closes_a_fresh_event_loop(self) -> None:
        lifecycle: list[tuple[str, asyncio.AbstractEventLoop]] = []

        async def fake_init() -> None:
            lifecycle.append(("init", asyncio.get_running_loop()))

        async def fake_close() -> None:
            lifecycle.append(("close", asyncio.get_running_loop()))

        async def operation() -> str:
            lifecycle.append(("operation", asyncio.get_running_loop()))
            return "done"

        with (
            patch("app.worker.runtime.init_db", side_effect=fake_init),
            patch("app.worker.runtime.close_db", side_effect=fake_close),
        ):
            self.assertEqual(run_async_db_operation(operation), "done")
            self.assertEqual(run_async_db_operation(operation), "done")

        first_loop = lifecycle[0][1]
        second_loop = lifecycle[3][1]
        self.assertTrue(all(loop is first_loop for _, loop in lifecycle[:3]))
        self.assertTrue(all(loop is second_loop for _, loop in lifecycle[3:]))
        self.assertIsNot(first_loop, second_loop)
        self.assertTrue(first_loop.is_closed())
        self.assertTrue(second_loop.is_closed())
        self.assertEqual(
            [event for event, _ in lifecycle],
            ["init", "operation", "close", "init", "operation", "close"],
        )

    def test_registered_celery_tasks_execute_their_workflows(self) -> None:
        async def resume_workflow(application_id: int) -> dict[str, object]:
            return {"application_id": application_id, "status": "processed"}

        async def criteria_workflow(job_id: int) -> dict[str, object]:
            return {"job_id": job_id, "status": "generated"}

        async def evaluation_workflow(application_id: int) -> dict[str, object]:
            return {"application_id": application_id, "status": "evaluated"}

        def execute(operation: Any) -> dict[str, object]:
            return asyncio.run(operation())

        with (
            patch.object(worker_tasks, "run_async_db_operation", side_effect=execute),
            patch.object(
                worker_tasks,
                "process_resume_workflow",
                side_effect=resume_workflow,
            ),
            patch.object(
                worker_tasks,
                "generate_job_criteria_workflow",
                side_effect=criteria_workflow,
            ),
            patch.object(
                worker_tasks,
                "evaluate_application_workflow",
                side_effect=evaluation_workflow,
            ),
        ):
            resume = worker_tasks.process_resume.apply(args=[11], throw=True).get()
            criteria = worker_tasks.generate_job_criteria.apply(
                args=[22], throw=True
            ).get()
            evaluation = worker_tasks.evaluate_application.apply(
                args=[33], throw=True
            ).get()

        self.assertEqual(resume, {"application_id": 11, "status": "processed"})
        self.assertEqual(criteria, {"job_id": 22, "status": "generated"})
        self.assertEqual(
            evaluation,
            {"application_id": 33, "status": "evaluated"},
        )

    def test_transient_failures_retry_and_permanent_failures_do_not(self) -> None:
        class RetryRequested(Exception):
            pass

        class FakeTask:
            name = "talentflow.test"
            request = SimpleNamespace(retries=1)

            def __init__(self) -> None:
                self.retry_call: dict[str, object] | None = None

            def retry(self, **kwargs: object) -> None:
                self.retry_call = kwargs
                raise RetryRequested

        task = FakeTask()
        with patch.object(
            worker_tasks,
            "run_async_db_operation",
            side_effect=JobCriteriaProviderError("provider unavailable"),
        ):
            with self.assertRaises(RetryRequested):
                worker_tasks._execute_task(
                    task,
                    operation=lambda: worker_tasks.generate_job_criteria_workflow(1),
                    entity_name="job_id",
                    entity_id=1,
                )
        self.assertEqual(task.retry_call["countdown"], 10)

        task = FakeTask()
        with patch.object(
            worker_tasks,
            "run_async_db_operation",
            side_effect=MissingStructuredResumeDataError("resume data missing"),
        ):
            with self.assertRaises(MissingStructuredResumeDataError):
                worker_tasks._execute_task(
                    task,
                    operation=lambda: worker_tasks.evaluate_application_workflow(1),
                    entity_name="application_id",
                    entity_id=1,
                )
        self.assertIsNone(task.retry_call)


if __name__ == "__main__":
    unittest.main()
