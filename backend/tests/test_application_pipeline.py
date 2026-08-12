from __future__ import annotations

import unittest

from tortoise import Tortoise

from app.db.models import (
    Application,
    ApplicationNote,
    ApplicationStatusHistory,
    Candidate,
    Company,
    Job,
    Recruiter,
)
from app.enums import ApplicationStatus, JobStatus
from app.graphql.schema import schema


class ApplicationPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.company = await Company.create(name="Pipeline Company")
        self.recruiter = await Recruiter.create(
            company=self.company,
            name="Riley Recruiter",
            email="riley@pipeline.example",
            role="Senior Recruiter",
        )
        self.job = await Job.create(
            company=self.company,
            title="Platform Engineer",
            description="Build a dependable hiring platform.",
            status=JobStatus.OPEN,
        )
        self.applications: list[Application] = []
        for index in range(3):
            candidate = await Candidate.create(
                name=f"Pipeline Candidate {index + 1}",
                email=f"candidate{index + 1}@pipeline.example",
            )
            application = await Application.create(candidate=candidate, job=self.job)
            await ApplicationStatusHistory.create(
                application=application,
                previous_status=None,
                new_status=ApplicationStatus.APPLIED,
                changed_by=candidate.email,
            )
            self.applications.append(application)

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    def assert_success(self, result: object) -> dict:
        errors = getattr(result, "errors")
        self.assertIsNone(errors, errors)
        data = getattr(result, "data")
        self.assertIsNotNone(data)
        return data

    async def update_status(
        self,
        application: Application,
        status: str,
        *,
        automated: bool = False,
    ) -> dict:
        result = await schema.execute(
            """
            mutation UpdateStatus($input: UpdateApplicationStatusInput!) {
              updateApplicationStatus(input: $input) {
                success
                application { id status }
                errors { code message field }
              }
            }
            """,
            variable_values={
                "input": {
                    "applicationId": str(application.id),
                    "status": status,
                    "changedBy": "fallback-actor@example.com",
                    "recruiterId": str(self.recruiter.id),
                    "automated": automated,
                }
            },
        )
        return self.assert_success(result)["updateApplicationStatus"]

    async def test_individual_update_records_history_and_noop_does_not(self) -> None:
        application = self.applications[0]
        updated = await self.update_status(application, "SHORTLISTED")

        self.assertTrue(updated["success"])
        self.assertEqual(updated["application"]["status"], "SHORTLISTED")
        history = await ApplicationStatusHistory.filter(
            application_id=application.id
        ).order_by("created_at", "id")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1].previous_status, ApplicationStatus.APPLIED)
        self.assertEqual(history[-1].new_status, ApplicationStatus.SHORTLISTED)
        self.assertEqual(history[-1].changed_by, self.recruiter.email)

        repeated = await self.update_status(application, "SHORTLISTED")
        self.assertTrue(repeated["success"])
        self.assertEqual(
            await ApplicationStatusHistory.filter(
                application_id=application.id
            ).count(),
            2,
        )

    async def test_human_moves_are_flexible_but_invalid_automation_is_rejected(self) -> None:
        automated = await self.update_status(
            self.applications[0], "HIRED", automated=True
        )
        self.assertFalse(automated["success"])
        self.assertEqual(automated["errors"][0]["code"], "VALIDATION_ERROR")
        await self.applications[0].refresh_from_db()
        self.assertEqual(self.applications[0].status, ApplicationStatus.APPLIED)

        manual = await self.update_status(self.applications[0], "HIRED")
        self.assertTrue(manual["success"])
        self.assertEqual(manual["application"]["status"], "HIRED")

    async def test_add_note_and_application_detail_returns_complete_timeline(self) -> None:
        application = self.applications[0]
        await self.update_status(application, "HUMAN_REVIEW")
        await self.update_status(application, "SHORTLISTED")

        note_result = await schema.execute(
            """
            mutation AddNote($input: AddApplicationNoteInput!) {
              addApplicationNote(input: $input) {
                success
                note {
                  id content createdAt updatedAt
                  recruiter { id name email }
                }
                errors { code message field }
              }
            }
            """,
            variable_values={
                "input": {
                    "applicationId": str(application.id),
                    "recruiterId": str(self.recruiter.id),
                    "content": "  Strong communication during the screen.  ",
                }
            },
        )
        note = self.assert_success(note_result)["addApplicationNote"]
        self.assertTrue(note["success"])
        self.assertEqual(note["note"]["content"], "Strong communication during the screen.")
        self.assertEqual(note["note"]["recruiter"]["email"], self.recruiter.email)
        self.assertEqual(await ApplicationNote.filter(application_id=application.id).count(), 1)

        detail_result = await schema.execute(
            """
            query Detail($input: ApplicationQueryInput!) {
              application(input: $input) {
                success
                application {
                  status
                  statusHistory { previousStatus newStatus changedBy createdAt }
                  notes { content recruiter { email } createdAt updatedAt }
                }
                errors { code message field }
              }
            }
            """,
            variable_values={"input": {"id": str(application.id)}},
        )
        detail = self.assert_success(detail_result)["application"]
        self.assertTrue(detail["success"])
        self.assertEqual(
            [item["newStatus"] for item in detail["application"]["statusHistory"]],
            ["APPLIED", "HUMAN_REVIEW", "SHORTLISTED"],
        )
        self.assertEqual(
            detail["application"]["notes"][0]["content"],
            "Strong communication during the screen.",
        )

    async def test_bulk_update_returns_successes_and_per_id_failures(self) -> None:
        first, second = self.applications[:2]
        result = await schema.execute(
            """
            mutation BulkUpdate($input: BulkUpdateApplicationStatusInput!) {
              bulkUpdateApplicationStatus(input: $input) {
                success
                applications { id status }
                failures { applicationId errors { code message field } }
                errors { code message field }
              }
            }
            """,
            variable_values={
                "input": {
                    "applicationIds": [str(first.id), str(second.id), "999999"],
                    "status": "INTERVIEW",
                    "changedBy": self.recruiter.email,
                    "recruiterId": str(self.recruiter.id),
                }
            },
        )
        payload = self.assert_success(result)["bulkUpdateApplicationStatus"]

        self.assertFalse(payload["success"])
        self.assertEqual(
            {item["id"] for item in payload["applications"]},
            {str(first.id), str(second.id)},
        )
        self.assertTrue(
            all(item["status"] == "INTERVIEW" for item in payload["applications"])
        )
        self.assertEqual(payload["failures"][0]["applicationId"], "999999")
        self.assertEqual(payload["failures"][0]["errors"][0]["code"], "NOT_FOUND")
        for application in (first, second):
            self.assertEqual(
                await ApplicationStatusHistory.filter(
                    application_id=application.id
                ).count(),
                2,
            )


if __name__ == "__main__":
    unittest.main()
