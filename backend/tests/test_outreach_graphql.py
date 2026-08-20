from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from tortoise import Tortoise

from app.db.models import (
    Application,
    ApplicationStatusHistory,
    Candidate,
    Company,
    Job,
    OutreachEmail,
)
from app.enums import ApplicationStatus, JobStatus, OutreachStatus
from app.graphql.schema import schema
from app.services.errors import OutreachApplicationNotFoundError


class FakeOutreachGenerationService:
    calls: list[tuple[int, str | None]] = []

    async def generate_and_save(
        self,
        application_id: int,
        *,
        instruction: str | None = None,
    ) -> OutreachEmail:
        self.calls.append((application_id, instruction))
        application = await Application.get_or_none(id=application_id)
        if application is None:
            raise OutreachApplicationNotFoundError("Application record not found.")
        return await OutreachEmail.create(
            application=application,
            subject="Platform Engineer opportunity",
            body="Hi Taylor, we'd like to discuss the Platform Engineer role.",
            status=OutreachStatus.DRAFT,
        )


class OutreachGraphQLTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        FakeOutreachGenerationService.calls = []
        self.company = await Company.create(name="Outreach Workflow Company")
        self.job = await Job.create(
            company=self.company,
            title="Platform Engineer",
            description="Build dependable hiring systems.",
            status=JobStatus.OPEN,
        )
        self.candidate = await Candidate.create(
            name="Taylor Morgan",
            email="taylor.outreach-workflow@example.com",
        )
        self.application = await Application.create(
            candidate=self.candidate,
            job=self.job,
            status=ApplicationStatus.HUMAN_REVIEW,
        )
        await ApplicationStatusHistory.create(
            application=self.application,
            previous_status=ApplicationStatus.APPLIED,
            new_status=ApplicationStatus.HUMAN_REVIEW,
            changed_by="recruiter@example.com",
        )

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    def assert_graphql_success(self, result: object) -> dict:
        errors = getattr(result, "errors")
        self.assertIsNone(errors, errors)
        data = getattr(result, "data")
        self.assertIsNotNone(data)
        return data

    async def run_mutation(
        self,
        field: str,
        input_type: str,
        input_value: dict[str, object],
    ) -> dict:
        result = await schema.execute(
            f"""
            mutation OutreachAction($input: {input_type}!) {{
              {field}(input: $input) {{
                success
                outreach {{
                  id subject body status generatedAt approvedAt sentAt
                }}
                errors {{ code message field }}
              }}
            }}
            """,
            variable_values={"input": input_value},
        )
        return self.assert_graphql_success(result)[field]

    async def test_generate_mutation_persists_and_returns_a_draft(self) -> None:
        with patch(
            "app.graphql.mutations.outreach.OutreachGenerationService",
            FakeOutreachGenerationService,
        ):
            payload = await self.run_mutation(
                "generateOutreach",
                "GenerateOutreachInput",
                {
                    "applicationId": str(self.application.id),
                    "instruction": "Make it shorter",
                },
            )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outreach"]["status"], "DRAFT")
        self.assertEqual(
            FakeOutreachGenerationService.calls,
            [(self.application.id, "Make it shorter")],
        )
        saved = await OutreachEmail.get(id=int(payload["outreach"]["id"]))
        self.assertEqual(saved.application_id, self.application.id)
        self.assertEqual(saved.status, OutreachStatus.DRAFT)

    async def test_draft_can_be_edited_and_empty_content_is_rejected(self) -> None:
        outreach = await self.create_outreach()
        updated = await self.run_mutation(
            "updateOutreachDraft",
            "UpdateOutreachDraftInput",
            {
                "outreachId": str(outreach.id),
                "subject": "  Updated   subject  ",
                "body": "  Updated body.  ",
            },
        )

        self.assertTrue(updated["success"])
        self.assertEqual(updated["outreach"]["subject"], "Updated subject")
        self.assertEqual(updated["outreach"]["body"], "Updated body.")

        invalid = await self.run_mutation(
            "updateOutreachDraft",
            "UpdateOutreachDraftInput",
            {
                "outreachId": str(outreach.id),
                "subject": "  ",
                "body": "Still has a body",
            },
        )
        self.assertFalse(invalid["success"])
        self.assertEqual(invalid["errors"][0]["code"], "VALIDATION_ERROR")
        self.assertEqual(invalid["errors"][0]["field"], "subject")

    async def test_approve_then_send_marks_sent_and_advances_pipeline(self) -> None:
        outreach = await self.create_outreach()
        approved = await self.run_mutation(
            "approveOutreach",
            "ApproveOutreachInput",
            {"outreachId": str(outreach.id)},
        )

        self.assertTrue(approved["success"])
        self.assertEqual(approved["outreach"]["status"], "APPROVED")
        self.assertIsNotNone(approved["outreach"]["approvedAt"])

        sent = await self.run_mutation(
            "sendOutreach",
            "SendOutreachInput",
            {"outreachId": str(outreach.id)},
        )

        self.assertTrue(sent["success"])
        self.assertEqual(sent["outreach"]["status"], "SENT")
        self.assertIsNotNone(sent["outreach"]["sentAt"])
        await self.application.refresh_from_db()
        self.assertEqual(self.application.status, ApplicationStatus.CONTACTED)
        history = await ApplicationStatusHistory.filter(
            application_id=self.application.id
        ).order_by("created_at", "id")
        self.assertEqual(history[-1].previous_status, ApplicationStatus.HUMAN_REVIEW)
        self.assertEqual(history[-1].new_status, ApplicationStatus.CONTACTED)
        self.assertEqual(history[-1].changed_by, "Outreach email sent")

    async def test_unapproved_or_sent_outreach_cannot_be_modified_incorrectly(self) -> None:
        draft = await self.create_outreach()
        unapproved = await self.run_mutation(
            "sendOutreach",
            "SendOutreachInput",
            {"outreachId": str(draft.id)},
        )
        self.assertFalse(unapproved["success"])
        self.assertEqual(unapproved["errors"][0]["code"], "CONFLICT")
        self.assertIn("APPROVED", unapproved["errors"][0]["message"])

        draft.status = OutreachStatus.SENT
        draft.sent_at = datetime.now(UTC)
        await draft.save(update_fields=["status", "sent_at"])
        edit = await self.run_mutation(
            "updateOutreachDraft",
            "UpdateOutreachDraftInput",
            {
                "outreachId": str(draft.id),
                "subject": "Cannot change",
                "body": "Cannot change",
            },
        )
        self.assertFalse(edit["success"])
        self.assertEqual(edit["errors"][0]["code"], "CONFLICT")

        approve = await self.run_mutation(
            "approveOutreach",
            "ApproveOutreachInput",
            {"outreachId": str(draft.id)},
        )
        self.assertFalse(approve["success"])
        self.assertEqual(approve["errors"][0]["code"], "CONFLICT")

    async def test_sending_does_not_move_a_later_stage_backwards(self) -> None:
        self.application.status = ApplicationStatus.INTERVIEW
        await self.application.save(update_fields=["status", "updated_at"])
        outreach = await self.create_outreach(status=OutreachStatus.APPROVED)
        history_count = await ApplicationStatusHistory.filter(
            application_id=self.application.id
        ).count()

        sent = await self.run_mutation(
            "sendOutreach",
            "SendOutreachInput",
            {"outreachId": str(outreach.id)},
        )

        self.assertTrue(sent["success"])
        await self.application.refresh_from_db()
        self.assertEqual(self.application.status, ApplicationStatus.INTERVIEW)
        self.assertEqual(
            await ApplicationStatusHistory.filter(
                application_id=self.application.id
            ).count(),
            history_count,
        )

    async def test_application_query_returns_newest_outreach_first(self) -> None:
        older = await self.create_outreach(subject="Older draft")
        older.generated_at = datetime.now(UTC) - timedelta(days=1)
        await older.save(update_fields=["generated_at"])
        newer = await self.create_outreach(subject="Newer draft")

        result = await schema.execute(
            """
            query ApplicationOutreach($input: ApplicationQueryInput!) {
              application(input: $input) {
                success
                application {
                  outreachEmails {
                    id subject body status generatedAt approvedAt sentAt
                  }
                }
                errors { code message field }
              }
            }
            """,
            variable_values={"input": {"id": str(self.application.id)}},
        )
        payload = self.assert_graphql_success(result)["application"]

        self.assertTrue(payload["success"])
        self.assertEqual(
            [item["id"] for item in payload["application"]["outreachEmails"]],
            [str(newer.id), str(older.id)],
        )

    async def test_invalid_application_and_missing_outreach_return_clean_errors(self) -> None:
        with patch(
            "app.graphql.mutations.outreach.OutreachGenerationService",
            FakeOutreachGenerationService,
        ):
            invalid_application = await self.run_mutation(
                "generateOutreach",
                "GenerateOutreachInput",
                {"applicationId": "999999"},
            )
        self.assertFalse(invalid_application["success"])
        self.assertEqual(invalid_application["errors"][0]["code"], "NOT_FOUND")

        missing_outreach = await self.run_mutation(
            "approveOutreach",
            "ApproveOutreachInput",
            {"outreachId": "999999"},
        )
        self.assertFalse(missing_outreach["success"])
        self.assertEqual(missing_outreach["errors"][0]["code"], "NOT_FOUND")

    async def create_outreach(
        self,
        *,
        subject: str = "Platform Engineer opportunity",
        status: OutreachStatus = OutreachStatus.DRAFT,
    ) -> OutreachEmail:
        return await OutreachEmail.create(
            application=self.application,
            subject=subject,
            body="Hi Taylor, we'd like to discuss the Platform Engineer role.",
            status=status,
            approved_at=datetime.now(UTC)
            if status == OutreachStatus.APPROVED
            else None,
        )


if __name__ == "__main__":
    unittest.main()
