from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from starlette.datastructures import Headers, UploadFile
from strawberry.fastapi import GraphQLRouter
from tortoise import Tortoise

from app.config import settings
from app.db.models import (
    Application,
    ApplicationStatusHistory,
    Candidate,
    Company,
    Job,
    Resume,
)
from app.enums import AIProcessingState, ApplicationStatus, JobStatus
from app.graphql.schema import schema
from auth_helpers import execute_as_recruiter, isolate_from_redis
from app.services.ai_processing import ProcessingRequest


def make_upload(
    *,
    filename: str = "resume.pdf",
    content_type: str = "application/pdf",
    content: bytes = b"%PDF-1.7\nPublic application test resume",
) -> UploadFile:
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class PublicApplicationGraphQLTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        isolate_from_redis(self)
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_upload_root = settings.upload_root
        settings.upload_root = Path(self.temporary_directory.name) / "uploads"

        self.company = await Company.create(
            name="Public Jobs Company",
            website="https://public-jobs.example.com",
            description="Internal company description",
        )
        self.open_job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description="Build reliable APIs.",
            required_skills=["Python", "PostgreSQL"],
            preferred_skills=["FastAPI"],
            experience_requirement="3+ years",
            evaluation_criteria={"internal": "must not be public"},
            status=JobStatus.OPEN,
        )
        self.second_open_job = await Job.create(
            company=self.company,
            title="Platform Engineer",
            description="Build reliable infrastructure.",
            status=JobStatus.OPEN,
        )
        self.closed_job = await Job.create(
            company=self.company,
            title="Closed Role",
            description="No longer available.",
            status=JobStatus.CLOSED,
        )
        self.draft_job = await Job.create(
            company=self.company,
            title="Draft Role",
            description="Not published.",
            status=JobStatus.DRAFT,
        )

    async def asyncTearDown(self) -> None:
        settings.upload_root = self.original_upload_root
        await Tortoise.close_connections()
        self.temporary_directory.cleanup()

    def result_data(self, result: object) -> dict:
        errors = getattr(result, "errors")
        self.assertIsNone(errors, errors)
        data = getattr(result, "data")
        self.assertIsNotNone(data)
        return data

    async def query_public_job(self, job_id: int) -> dict:
        result = await schema.execute(
            """
            query PublicJob($input: PublicJobQueryInput!) {
              publicJob(input: $input) {
                success
                job {
                  id title description requiredSkills preferredSkills
                  experienceRequirement status
                  company { name website }
                }
                errors { code message field }
              }
            }
            """,
            variable_values={"input": {"id": str(job_id)}},
        )
        return self.result_data(result)["publicJob"]

    async def submit(
        self,
        *,
        job_id: int,
        email: str = "applicant@example.com",
        full_name: str = "Public Applicant",
        upload: UploadFile | None = None,
    ) -> dict:
        result = await schema.execute(
            """
            mutation SubmitApplication($input: SubmitApplicationInput!) {
              submitApplication(input: $input) {
                success
                application {
                  id candidateName jobTitle status submittedAt
                  processingState processingMessage statusToken
                }
                errors { code message field }
              }
            }
            """,
            variable_values={
                "input": {
                    "jobId": str(job_id),
                    "fullName": full_name,
                    "email": email,
                    "phone": "+1 415 555 0199",
                    "linkedinUrl": "https://linkedin.com/in/public-applicant",
                    "githubUrl": "https://github.com/public-applicant",
                    "portfolioUrl": "https://public-applicant.example.com",
                    "coverLetter": "I am interested in contributing to this role.",
                    "resume": upload or make_upload(),
                }
            },
        )
        return self.result_data(result)["submitApplication"]

    async def test_only_open_job_is_available_through_public_query(self) -> None:
        public_job = await self.query_public_job(self.open_job.id)

        self.assertTrue(public_job["success"])
        self.assertEqual(public_job["job"]["title"], "Backend Engineer")
        self.assertEqual(public_job["job"]["company"]["name"], self.company.name)
        self.assertEqual(public_job["job"]["status"], "OPEN")

        for unavailable_job in (self.closed_job, self.draft_job):
            result = await self.query_public_job(unavailable_job.id)
            self.assertFalse(result["success"])
            self.assertIsNone(result["job"])
            self.assertEqual(result["errors"][0]["code"], "NOT_FOUND")
            self.assertEqual(result["errors"][0]["message"], "This job is not available.")

    async def test_submission_persists_safe_receipt_and_queues_resume_processing(self) -> None:
        processing = ProcessingRequest(
            accepted=True,
            resource_id=1,
            state=AIProcessingState.PROCESSING,
            message="Resume processing was queued.",
            task_id="resume-task-1",
        )
        with patch(
            "app.graphql.mutations.application.AIProcessingService."
            "process_application_resume",
            new_callable=AsyncMock,
            return_value=processing,
        ) as enqueue:
            payload = await self.submit(
                job_id=self.open_job.id,
                upload=make_upload(filename="../../Jordan Taylor resume.pdf"),
            )

        self.assertTrue(payload["success"])
        self.assertEqual(
            set(payload["application"]),
            {
                "id",
                "candidateName",
                "jobTitle",
                "status",
                "submittedAt",
                "processingState",
                "processingMessage",
                "statusToken",
            },
        )
        self.assertEqual(payload["application"]["status"], "APPLIED")
        self.assertEqual(payload["application"]["processingState"], "PROCESSING")

        application = await Application.get(id=int(payload["application"]["id"]))
        enqueue.assert_awaited_once_with(application.id)
        history = await ApplicationStatusHistory.get(application_id=application.id)
        self.assertIsNone(history.previous_status)
        self.assertEqual(history.new_status, ApplicationStatus.APPLIED)

        resume = await Resume.get(candidate_id=application.candidate_id)
        self.assertNotIn("..", resume.file_url)
        self.assertTrue(resume.file_url.endswith(".pdf"))
        stored_resume = settings.upload_root / Path(resume.file_url).relative_to(
            "uploads"
        )
        self.assertTrue(stored_resume.is_file())

    async def test_fastapi_graphql_endpoint_accepts_multipart_pdf_upload(self) -> None:
        test_app = FastAPI()
        test_app.include_router(
            GraphQLRouter(schema, multipart_uploads_enabled=True),
            prefix="/graphql",
        )
        operations = {
            "query": """
                mutation Submit($input: SubmitApplicationInput!) {
                  submitApplication(input: $input) {
                    success application { id status processingState }
                    errors { code message field }
                  }
                }
            """,
            "variables": {
                "input": {
                    "jobId": str(self.open_job.id),
                    "fullName": "Multipart Applicant",
                    "email": "multipart@example.com",
                    "coverLetter": "I am interested in this role.",
                    "resume": None,
                }
            },
        }
        processing = ProcessingRequest(
            accepted=True,
            resource_id=1,
            state=AIProcessingState.PROCESSING,
            message="Resume processing was queued.",
        )

        with patch(
            "app.graphql.mutations.application.AIProcessingService."
            "process_application_resume",
            new_callable=AsyncMock,
            return_value=processing,
        ) as enqueue:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    "/graphql",
                    data={
                        "operations": json.dumps(operations),
                        "map": json.dumps({"0": ["variables.input.resume"]}),
                    },
                    files={
                        "0": (
                            "resume.pdf",
                            b"%PDF-1.7\nMultipart resume",
                            "application/pdf",
                        )
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["submitApplication"]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["application"]["processingState"], "PROCESSING")
        enqueue.assert_awaited_once()

    async def test_submitted_applicant_is_visible_to_recruiter_with_processing_state(
        self,
    ) -> None:
        with patch(
            "app.worker.tasks.process_resume.delay",
            return_value=SimpleNamespace(id="resume-task-integration"),
        ) as enqueue:
            submission = await self.submit(
                job_id=self.open_job.id,
                email="visible-applicant@example.com",
            )

        self.assertTrue(submission["success"])
        self.assertEqual(submission["application"]["processingState"], "PROCESSING")
        application_id = submission["application"]["id"]
        enqueue.assert_called_once_with(int(application_id))

        recruiter_result = self.result_data(
            await execute_as_recruiter(
                """
                query RecruiterApplicants($input: ApplicationsQueryInput!) {
                  applications(input: $input) {
                    success totalCount
                    items {
                      id status fitScore evaluationProcessingState appliedAt
                      candidate { name email }
                      resume { processingState }
                    }
                    errors { code message field }
                  }
                }
                """,
                variable_values={"input": {"jobId": str(self.open_job.id)}},
            )
        )["applications"]

        self.assertTrue(recruiter_result["success"])
        self.assertEqual(recruiter_result["totalCount"], 1)
        applicant = recruiter_result["items"][0]
        self.assertEqual(applicant["id"], application_id)
        self.assertEqual(applicant["status"], "APPLIED")
        self.assertIsNone(applicant["fitScore"])
        self.assertEqual(applicant["evaluationProcessingState"], "NOT_STARTED")
        self.assertEqual(applicant["resume"]["processingState"], "PROCESSING")
        self.assertEqual(
            applicant["candidate"]["email"],
            "visible-applicant@example.com",
        )
        self.assertEqual(
            await ApplicationStatusHistory.filter(
                application_id=int(application_id),
                new_status=ApplicationStatus.APPLIED,
            ).count(),
            1,
        )

    async def test_existing_candidate_is_reused_and_duplicate_job_is_rejected(self) -> None:
        processing = ProcessingRequest(
            accepted=True,
            resource_id=1,
            state=AIProcessingState.PROCESSING,
            message="Resume processing was queued.",
        )
        with patch(
            "app.graphql.mutations.application.AIProcessingService."
            "process_application_resume",
            new_callable=AsyncMock,
            return_value=processing,
        ) as enqueue:
            first = await self.submit(
                job_id=self.open_job.id,
                email=" Applicant@Example.com ",
            )
            second = await self.submit(
                job_id=self.second_open_job.id,
                email="applicant@example.com",
                upload=make_upload(filename="updated.pdf"),
            )
            duplicate = await self.submit(
                job_id=self.open_job.id,
                email="APPLICANT@example.com",
                upload=make_upload(filename="duplicate.pdf"),
            )

        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertFalse(duplicate["success"])
        self.assertEqual(duplicate["errors"][0]["code"], "CONFLICT")
        self.assertEqual(await Candidate.all().count(), 1)
        self.assertEqual(await Application.all().count(), 2)
        self.assertEqual(enqueue.await_count, 2)

    async def test_non_open_jobs_and_invalid_pdf_are_rejected_without_queueing(self) -> None:
        with patch(
            "app.graphql.mutations.application.AIProcessingService."
            "process_application_resume",
            new_callable=AsyncMock,
        ) as enqueue:
            closed = await self.submit(job_id=self.closed_job.id)
            draft = await self.submit(job_id=self.draft_job.id)
            missing = await self.submit(job_id=999_999)
            invalid_pdf = await self.submit(
                job_id=self.open_job.id,
                upload=make_upload(content=b"not a PDF"),
            )

        self.assertEqual(closed["errors"][0]["code"], "JOB_CLOSED")
        self.assertEqual(draft["errors"][0]["code"], "JOB_CLOSED")
        self.assertEqual(missing["errors"][0]["code"], "NOT_FOUND")
        self.assertEqual(invalid_pdf["errors"][0]["code"], "INVALID_FILE")
        enqueue.assert_not_awaited()

    async def test_job_closed_after_public_load_is_rechecked_at_submission(self) -> None:
        public_job = await self.query_public_job(self.open_job.id)
        self.assertTrue(public_job["success"])

        self.open_job.status = JobStatus.CLOSED
        await self.open_job.save(update_fields=["status", "updated_at"])
        with patch(
            "app.graphql.mutations.application.AIProcessingService."
            "process_application_resume",
            new_callable=AsyncMock,
        ) as enqueue:
            submission = await self.submit(job_id=self.open_job.id)

        self.assertFalse(submission["success"])
        self.assertEqual(submission["errors"][0]["code"], "JOB_CLOSED")
        enqueue.assert_not_awaited()

    async def test_queue_failure_keeps_application_and_exposes_failed_processing_state(
        self,
    ) -> None:
        with (
            self.assertLogs(
                "app.graphql.mutations.application",
                level="WARNING",
            ),
            patch(
                "app.worker.tasks.process_resume.delay",
                side_effect=ConnectionError("broker unavailable"),
            ),
        ):
            submission = await self.submit(
                job_id=self.open_job.id,
                email="queue-failure@example.com",
            )

        self.assertTrue(submission["success"])
        self.assertEqual(submission["application"]["status"], "APPLIED")
        self.assertEqual(submission["application"]["processingState"], "FAILED")
        application = await Application.get(
            id=int(submission["application"]["id"])
        )
        resume = await Resume.get(candidate_id=application.candidate_id)
        self.assertEqual(resume.processing_state, AIProcessingState.FAILED)
        self.assertTrue(
            (settings.upload_root / Path(resume.file_url).relative_to("uploads")).is_file()
        )

    async def test_public_types_do_not_expose_recruiter_or_evaluation_fields(self) -> None:
        result = self.result_data(
            await schema.execute(
                """
                query PublicTypeFields {
                  publicJob: __type(name: "PublicJobType") { fields { name } }
                  receipt: __type(name: "PublicApplicationReceipt") { fields { name } }
                }
                """
            )
        )
        public_job_fields = {field["name"] for field in result["publicJob"]["fields"]}
        receipt_fields = {field["name"] for field in result["receipt"]["fields"]}

        self.assertEqual(
            public_job_fields,
            {
                "id",
                "title",
                "description",
                "requiredSkills",
                "preferredSkills",
                "experienceRequirement",
                "company",
                "status",
            },
        )
        self.assertEqual(
            receipt_fields,
            {
                "id",
                "candidateName",
                "jobTitle",
                "status",
                "submittedAt",
                "processingState",
                "processingMessage",
                "statusToken",
            },
        )
        self.assertNotIn("evaluationCriteria", public_job_fields)
        self.assertNotIn("fitScore", receipt_fields)
        self.assertNotIn("recruiter", receipt_fields)


if __name__ == "__main__":
    unittest.main()
