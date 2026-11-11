from __future__ import annotations

import tempfile
import time
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from starlette.datastructures import Headers, UploadFile
from tortoise import Tortoise

from app.config import settings
from app.db.models import (
    AIEvaluation,
    Application,
    Candidate,
    Company,
    Job,
    Recruiter,
    Resume,
)
from app.demo.seed import ensure_accounts, ensure_company, populate_demo_data, reset_demo_data
from app.enums import AIProcessingState, JobStatus
from app.graphql.context import IsAuthenticated
from app.graphql.schema import schema
from app.main import app
from app.schemas import CandidateEvaluation, JobEvaluationCriteria, ParsedResume
from app.services import usage_guard
from app.services.application_progress import create_status_token
from app.services.errors import AIBudgetExceededError, AIBudgetUnavailableError
from app.services.security import hash_password, sign_value, unsign_value, verify_password
from app.utils.pdf import build_text_pdf
from app.worker.tasks import _caused_by_usage_limit
from auth_helpers import execute_as_recruiter, isolate_from_redis


PUBLIC_QUERY_FIELDS = {"publicJob", "publicJobs", "publicApplicationStatus"}
PUBLIC_MUTATION_FIELDS = {"submitApplication"}


class SecurityPrimitiveTests(unittest.TestCase):
    def test_password_hash_round_trip(self) -> None:
        encoded = hash_password("correct horse")
        self.assertTrue(verify_password("correct horse", encoded))
        self.assertFalse(verify_password("wrong", encoded))
        self.assertFalse(verify_password("correct horse", None))
        self.assertFalse(verify_password("correct horse", "not-a-hash"))
        self.assertNotEqual(encoded, hash_password("correct horse"))

    def test_signed_values_reject_tampering_wrong_purpose_and_expiry(self) -> None:
        token = sign_value(42, purpose="session")
        self.assertEqual(unsign_value(token, purpose="session", max_age_seconds=60), "42")
        self.assertIsNone(unsign_value(token, purpose="other", max_age_seconds=60))
        self.assertIsNone(
            unsign_value(token.replace("42.", "43.", 1), purpose="session", max_age_seconds=60)
        )
        with patch("app.services.security.time.time", return_value=time.time() + 120):
            self.assertIsNone(unsign_value(token, purpose="session", max_age_seconds=60))
        self.assertIsNone(unsign_value("garbage", purpose="session", max_age_seconds=60))

    def test_usage_limit_is_detected_through_wrapped_exceptions(self) -> None:
        try:
            try:
                raise AIBudgetExceededError("budget")
            except AIBudgetExceededError as exc:
                raise RuntimeError("provider unavailable") from exc
        except RuntimeError as wrapped:
            self.assertTrue(_caused_by_usage_limit(wrapped))
        self.assertFalse(_caused_by_usage_limit(RuntimeError("other")))

    def test_every_non_public_field_requires_a_recruiter(self) -> None:
        for type_name, public in (
            ("Query", PUBLIC_QUERY_FIELDS),
            ("Mutation", PUBLIC_MUTATION_FIELDS),
        ):
            definition = schema.get_type_by_name(type_name)
            for field in definition.fields:
                name = schema.config.name_converter.get_graphql_name(field)
                guarded = any(
                    isinstance(permission, IsAuthenticated) or permission is IsAuthenticated
                    for permission in field.permission_classes
                )
                if name in public:
                    self.assertFalse(guarded, f"{type_name}.{name} should be public")
                else:
                    self.assertTrue(guarded, f"{type_name}.{name} must require a recruiter")


class UsageGuardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        isolate_from_redis(self)
        usage_guard._reset_availability_for_tests()
        self.original_limit = settings.ai_daily_call_limit
        settings.ai_daily_call_limit = 2

    async def asyncTearDown(self) -> None:
        settings.ai_daily_call_limit = self.original_limit
        usage_guard._reset_availability_for_tests()

    async def test_budget_reservation_stops_after_the_daily_limit(self) -> None:
        counter = {"value": 0}

        async def fake_with_redis(operation):
            counter["value"] += 1
            return counter["value"]

        with patch.object(usage_guard, "_with_redis", new=fake_with_redis):
            await usage_guard.reserve_ai_call()
            await usage_guard.reserve_ai_call()
            with self.assertRaises(AIBudgetExceededError):
                await usage_guard.reserve_ai_call()

    async def test_budget_fails_closed_but_rate_limits_fail_open_without_redis(self) -> None:
        async def unavailable(operation):
            raise usage_guard.RedisUnavailableError("down")

        with patch.object(usage_guard, "_with_redis", new=unavailable):
            with self.assertRaises(AIBudgetUnavailableError):
                await usage_guard.reserve_ai_call()
            self.assertTrue(
                await usage_guard.hit_rate_limit("apply", "1.2.3.4", limit=1, window_seconds=60)
            )
            await usage_guard.ensure_ai_budget_available()

    async def test_precheck_reports_an_exhausted_budget(self) -> None:
        async def spent(operation):
            return "2"

        with patch.object(usage_guard, "_with_redis", new=spent):
            with self.assertRaises(AIBudgetExceededError):
                await usage_guard.ensure_ai_budget_available()


class AuthenticatedAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        isolate_from_redis(self)
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.db.models"]})
        await Tortoise.generate_schemas()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_upload_root = settings.upload_root
        settings.upload_root = Path(self.temporary_directory.name) / "uploads"

        self.company = await Company.create(name="Auth Company")
        self.recruiter = await Recruiter.create(
            company=self.company,
            name="Avery Admin",
            email="avery@auth.example",
            role="Recruiter",
            password_hash=hash_password("s3cret-password"),
        )
        self.job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description="Build APIs.",
            status=JobStatus.OPEN,
        )
        candidate = await Candidate.create(name="Casey Candidate", email="casey@example.com")
        self.application = await Application.create(candidate=candidate, job=self.job)
        resume_dir = settings.upload_root / "resumes" / str(candidate.id)
        resume_dir.mkdir(parents=True)
        (resume_dir / "casey.pdf").write_bytes(build_text_pdf(["# Casey Candidate"]))
        self.application.resume_url = f"uploads/resumes/{candidate.id}/casey.pdf"
        await self.application.save()
        await Resume.create(candidate=candidate, file_url=self.application.resume_url)

        self.rate_limit = patch(
            "app.api.auth.hit_rate_limit", new=AsyncMock(return_value=True)
        )
        self.rate_limit.start()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        )

    async def asyncTearDown(self) -> None:
        self.rate_limit.stop()
        await self.client.aclose()
        settings.upload_root = self.original_upload_root
        await Tortoise.close_connections()
        self.temporary_directory.cleanup()

    async def login(self) -> httpx.Response:
        return await self.client.post(
            "/auth/login", json={"email": "Avery@Auth.example", "password": "s3cret-password"}
        )

    async def test_login_sets_http_only_cookie_and_me_returns_recruiter(self) -> None:
        response = await self.login()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["company_name"], "Auth Company")
        cookie_header = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie_header)
        self.assertIn("SameSite=lax", cookie_header)

        me = await self.client.get("/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "avery@auth.example")

        await self.client.post("/auth/logout")
        self.client.cookies.clear()
        self.assertEqual((await self.client.get("/auth/me")).status_code, 401)

    async def test_wrong_password_is_rejected(self) -> None:
        response = await self.client.post(
            "/auth/login", json={"email": "avery@auth.example", "password": "nope"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("set-cookie", response.headers)

    async def test_login_rate_limit_returns_429(self) -> None:
        with patch("app.api.auth.hit_rate_limit", new=AsyncMock(return_value=False)):
            response = await self.login()
        self.assertEqual(response.status_code, 429)

    async def test_demo_login_requires_a_seeded_demo_account(self) -> None:
        self.assertEqual((await self.client.post("/auth/demo")).status_code, 404)
        await Recruiter.create(
            company=self.company,
            name="Demo Recruiter",
            email=settings.demo_recruiter_email,
            role="Recruiter",
            is_demo=True,
            password_hash=hash_password("demo"),
        )
        response = await self.client.post("/auth/demo")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_demo"])

    async def test_graphql_requires_session_for_recruiter_data(self) -> None:
        query = {"query": "{ jobs { success totalCount } }"}
        anonymous = (await self.client.post("/graphql", json=query)).json()
        self.assertIsNone(anonymous["data"])
        self.assertEqual(anonymous["errors"][0]["extensions"]["code"], "UNAUTHENTICATED")

        public = (await self.client.post(
            "/graphql", json={"query": "{ publicJobs { success items { title } } }"}
        )).json()
        self.assertEqual(public["data"]["publicJobs"]["items"], [{"title": "Backend Engineer"}])

        await self.login()
        signed_in = (await self.client.post("/graphql", json=query)).json()
        self.assertEqual(signed_in["data"]["jobs"], {"success": True, "totalCount": 1})

    async def test_resume_download_requires_session_and_same_company(self) -> None:
        path = f"/applications/{self.application.id}/resume"
        self.assertEqual((await self.client.get(path)).status_code, 401)

        await self.login()
        response = await self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))

        other_company = await Company.create(name="Other")
        other_job = await Job.create(company=other_company, title="X", description="Y")
        other_candidate = await Candidate.create(name="Other", email="other@example.com")
        other_application = await Application.create(
            candidate=other_candidate, job=other_job, resume_url=self.application.resume_url
        )
        hidden = await self.client.get(f"/applications/{other_application.id}/resume")
        self.assertEqual(hidden.status_code, 404)

    async def test_jobs_are_scoped_to_the_recruiters_company(self) -> None:
        other_company = await Company.create(name="Other Co")
        other_job = await Job.create(company=other_company, title="Hidden", description="Z")
        result = await execute_as_recruiter(
            "{ jobs { items { title } } }", recruiter=self.recruiter
        )
        self.assertEqual(result.data["jobs"]["items"], [{"title": "Backend Engineer"}])

        detail = await execute_as_recruiter(
            "query($input: JobQueryInput!) { job(input: $input) { success errors { code } } }",
            variable_values={"input": {"id": str(other_job.id)}},
            recruiter=self.recruiter,
        )
        self.assertEqual(detail.data["job"]["errors"][0]["code"], "NOT_FOUND")

    async def test_public_status_token_reports_progress_without_scores(self) -> None:
        query = """
            query($input: PublicApplicationStatusInput!) {
              publicApplicationStatus(input: $input) {
                success progress { stage finished jobTitle } errors { code }
              }
            }
        """
        token = create_status_token(self.application.id)
        result = await schema.execute(query, variable_values={"input": {"token": token}})
        payload = result.data["publicApplicationStatus"]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["progress"]["stage"], "RECEIVED")

        await Resume.filter(candidate_id=self.application.candidate_id).update(
            processing_state=AIProcessingState.COMPLETED
        )
        await Application.filter(id=self.application.id).update(
            evaluation_processing_state=AIProcessingState.COMPLETED
        )
        result = await schema.execute(query, variable_values={"input": {"token": token}})
        self.assertEqual(result.data["publicApplicationStatus"]["progress"]["stage"], "COMPLETE")

        tampered = await schema.execute(
            query, variable_values={"input": {"token": token[:-2] + "xx"}}
        )
        self.assertEqual(
            tampered.data["publicApplicationStatus"]["errors"][0]["code"], "NOT_FOUND"
        )

    async def submit(self, **overrides: object):
        upload = UploadFile(
            BytesIO(b"%PDF-1.7\nresume"),
            filename="resume.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )
        variables = {
            "input": {
                "jobId": str(self.job.id),
                "fullName": "New Applicant",
                "email": "new@example.com",
                "coverLetter": "Hello",
                "resume": upload,
                **overrides,
            }
        }
        return await schema.execute(
            """
            mutation($input: SubmitApplicationInput!) {
              submitApplication(input: $input) {
                success application { statusToken } errors { code }
              }
            }
            """,
            variable_values=variables,
        )

    async def test_honeypot_and_rate_limit_block_submissions(self) -> None:
        with patch(
            "app.graphql.mutations.application.hit_rate_limit", new=AsyncMock(return_value=True)
        ):
            bot = await self.submit(website="https://spam.example")
        self.assertFalse(bot.data["submitApplication"]["success"])
        with patch(
            "app.graphql.mutations.application.hit_rate_limit", new=AsyncMock(return_value=False)
        ):
            limited = await self.submit()
        self.assertEqual(limited.data["submitApplication"]["errors"][0]["code"], "RATE_LIMITED")
        self.assertEqual(await Application.filter(job=self.job).count(), 1)

    async def test_submission_returns_status_token_when_screening_is_paused(self) -> None:
        with (
            patch(
                "app.graphql.mutations.application.hit_rate_limit",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "app.services.ai_processing.ensure_ai_budget_available",
                new=AsyncMock(side_effect=AIBudgetExceededError("spent")),
            ),
        ):
            result = await self.submit()
        payload = result.data["submitApplication"]
        self.assertTrue(payload["success"], payload)
        self.assertTrue(payload["application"]["statusToken"])


class DemoSeedTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        isolate_from_redis(self)
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.db.models"]})
        await Tortoise.generate_schemas()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_upload_root = settings.upload_root
        settings.upload_root = Path(self.temporary_directory.name) / "uploads"

    async def asyncTearDown(self) -> None:
        settings.upload_root = self.original_upload_root
        await Tortoise.close_connections()
        self.temporary_directory.cleanup()

    async def test_seed_creates_valid_demo_data_and_reset_restores_it(self) -> None:
        company = await ensure_company()
        await ensure_accounts(company)
        summary = await populate_demo_data(company)
        self.assertTrue(summary.created)
        self.assertFalse((await populate_demo_data(company)).created)

        demo = await Recruiter.get(email=settings.demo_recruiter_email)
        self.assertTrue(demo.is_demo)
        self.assertTrue(verify_password(
            settings.demo_recruiter_password.get_secret_value(), demo.password_hash
        ))

        for job in await Job.all():
            JobEvaluationCriteria.model_validate(job.evaluation_criteria)
        for resume in await Resume.all():
            ParsedResume.model_validate(resume.parsed_data)
            self.assertTrue((settings.upload_root / resume.file_url.removeprefix("uploads/")).is_file())
        for evaluation in await AIEvaluation.all():
            CandidateEvaluation.model_validate(evaluation.analysis_json)
        unevaluated = await Application.filter(
            evaluation_processing_state=AIProcessingState.NOT_STARTED
        ).count()
        self.assertGreater(unevaluated, 0, "Some applicants should be left for live screening.")

        await Application.all().delete()
        restored = await reset_demo_data()
        self.assertEqual(await Application.all().count(), restored.applications)


if __name__ == "__main__":
    unittest.main()
