from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from starlette.datastructures import Headers, UploadFile
from tortoise import Tortoise

from app.config import settings
from app.db.models import Application, Candidate, Company, Job
from app.enums import ApplicationStatus, JobStatus
from app.graphql.schema import schema


class GraphQLContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.db.models"]})
        await Tortoise.generate_schemas()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_upload_root = settings.upload_root
        settings.upload_root = Path(self.temporary_directory.name) / "uploads"

        self.company = await Company.create(name="GraphQL Contract Company")
        self.job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description="Build dependable APIs",
            status=JobStatus.OPEN,
        )
        candidate = await Candidate.create(name="Existing Candidate", email="existing@example.com")
        self.application = await Application.create(candidate=candidate, job=self.job)

    async def asyncTearDown(self) -> None:
        settings.upload_root = self.original_upload_root
        await Tortoise.close_connections()
        self.temporary_directory.cleanup()

    def assert_success(self, result: object) -> dict:
        errors = getattr(result, "errors")
        self.assertIsNone(errors, errors)
        data = getattr(result, "data")
        self.assertIsNotNone(data)
        return data

    async def test_all_queries_use_input_and_result_types(self) -> None:
        jobs = self.assert_success(
            await schema.execute(
                """
                query {
                  jobs(input: { status: OPEN }) {
                    success totalCount items { id title } errors { code message field }
                  }
                }
                """
            )
        )["jobs"]
        self.assertTrue(jobs["success"])
        self.assertEqual(jobs["totalCount"], 1)

        job = self.assert_success(
            await schema.execute(
                """
                query($input: JobQueryInput!) {
                  job(input: $input) { success job { id title } errors { code message field } }
                }
                """,
                variable_values={"input": {"id": str(self.job.id)}},
            )
        )["job"]
        self.assertTrue(job["success"])

        applications = self.assert_success(
            await schema.execute(
                """
                query($input: ApplicationsQueryInput!) {
                  applications(input: $input) {
                    success totalCount items { id status } errors { code message field }
                  }
                }
                """,
                variable_values={"input": {"jobId": str(self.job.id)}},
            )
        )["applications"]
        self.assertTrue(applications["success"])
        self.assertEqual(applications["totalCount"], 1)

        application = self.assert_success(
            await schema.execute(
                """
                query($input: ApplicationQueryInput!) {
                  application(input: $input) {
                    success application { id status } errors { code message field }
                  }
                }
                """,
                variable_values={"input": {"id": str(self.application.id)}},
            )
        )["application"]
        self.assertTrue(application["success"])

        missing = self.assert_success(
            await schema.execute(
                """
                query {
                  job(input: { id: "999999" }) {
                    success job { id } errors { code message field }
                  }
                }
                """
            )
        )["job"]
        self.assertFalse(missing["success"])
        self.assertEqual(missing["errors"][0]["code"], "NOT_FOUND")

    async def test_all_mutations_use_input_and_payload_types(self) -> None:
        created = self.assert_success(
            await schema.execute(
                """
                mutation($input: CreateJobInput!) {
                  createJob(input: $input) {
                    success job { id title status } errors { code message field }
                  }
                }
                """,
                variable_values={
                    "input": {
                        "companyId": str(self.company.id),
                        "title": "Platform Engineer",
                        "description": "Build platform infrastructure",
                        "requiredSkills": ["Python"],
                        "preferredSkills": ["PostgreSQL"],
                        "status": "OPEN",
                    }
                },
            )
        )["createJob"]
        self.assertTrue(created["success"])

        updated = self.assert_success(
            await schema.execute(
                """
                mutation($input: UpdateApplicationStatusInput!) {
                  updateApplicationStatus(input: $input) {
                    success application { id status } errors { code message field }
                  }
                }
                """,
                variable_values={
                    "input": {
                        "applicationId": str(self.application.id),
                        "status": "SHORTLISTED",
                        "changedBy": "recruiter@example.com",
                    }
                },
            )
        )["updateApplicationStatus"]
        self.assertTrue(updated["success"])
        self.assertEqual(updated["application"]["status"], "SHORTLISTED")

        upload = UploadFile(
            BytesIO(b"%PDF-1.7\nGraphQL contract resume"),
            filename="resume.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )
        submitted = self.assert_success(
            await schema.execute(
                """
                mutation($input: SubmitApplicationInput!) {
                  submitApplication(input: $input) {
                    success application { id status resumeUrl } errors { code message field }
                  }
                }
                """,
                variable_values={
                    "input": {
                        "jobId": str(self.job.id),
                        "fullName": "New Applicant",
                        "email": "new.applicant@example.com",
                        "coverLetter": "I am interested in this role.",
                        "resume": upload,
                    }
                },
            )
        )["submitApplication"]
        self.assertTrue(submitted["success"])
        self.assertEqual(submitted["application"]["status"], ApplicationStatus.APPLIED.value)

        duplicate_upload = UploadFile(
            BytesIO(b"%PDF-1.7\nDuplicate GraphQL contract resume"),
            filename="duplicate.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )
        duplicate = self.assert_success(
            await schema.execute(
                """
                mutation($input: SubmitApplicationInput!) {
                  submitApplication(input: $input) {
                    success application { id } errors { code message field }
                  }
                }
                """,
                variable_values={
                    "input": {
                        "jobId": str(self.job.id),
                        "fullName": "New Applicant",
                        "email": "NEW.APPLICANT@example.com",
                        "coverLetter": "I am interested in this role.",
                        "resume": duplicate_upload,
                    }
                },
            )
        )["submitApplication"]
        self.assertFalse(duplicate["success"])
        self.assertIsNone(duplicate["application"])
        self.assertEqual(duplicate["errors"][0]["code"], "CONFLICT")

    def test_schema_exposes_named_contract_types(self) -> None:
        schema_text = schema.as_str()
        expected = (
            "jobs(input: JobsQueryInput = null): JobsResult!",
            "job(input: JobQueryInput!): JobResult!",
            "applications(input: ApplicationsQueryInput!): ApplicationsResult!",
            "application(input: ApplicationQueryInput!): ApplicationResult!",
            "createJob(input: CreateJobInput!): CreateJobPayload!",
            "submitApplication(input: SubmitApplicationInput!): SubmitApplicationPayload!",
            "updateApplicationStatus(input: UpdateApplicationStatusInput!): "
            "UpdateApplicationStatusPayload!",
        )
        for contract in expected:
            self.assertIn(contract, schema_text)


if __name__ == "__main__":
    unittest.main()
