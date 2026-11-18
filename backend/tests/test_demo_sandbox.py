from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from tortoise import Tortoise

from app.config import settings
from app.db.models import Application, Candidate, Company, Job, Recruiter, Resume
from app.demo.data import CANDIDATES, JOBS
from app.demo.sandbox import cleanup_expired_sandboxes, create_demo_sandbox
from app.demo.seed import ensure_accounts, ensure_company, populate_demo_data, reset_demo_data
from app.main import app
from app.services.security import hash_password
from auth_helpers import isolate_from_redis


JOBS_QUERY = {"query": "{ jobs { success totalCount items { id title } } }"}
PUBLIC_JOBS_QUERY = {"query": "{ publicJobs { success items { id title } } }"}


class DemoSandboxTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        isolate_from_redis(self)
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.db.models"]})
        await Tortoise.generate_schemas()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_upload_root = settings.upload_root
        settings.upload_root = Path(self.temporary_directory.name) / "uploads"

        # The shared demo company, as created by the seed script.
        self.shared = await ensure_company()
        await ensure_accounts(self.shared)
        await populate_demo_data(self.shared)

        self.rate_limit = patch("app.api.auth.hit_rate_limit", new=AsyncMock(return_value=True))
        self.rate_limit.start()

    async def asyncTearDown(self) -> None:
        self.rate_limit.stop()
        settings.upload_root = self.original_upload_root
        await Tortoise.close_connections()
        self.temporary_directory.cleanup()

    def new_client(self) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        )
        self.addAsyncCleanup(client.aclose)
        return client

    async def test_each_visitor_gets_an_isolated_copy(self) -> None:
        first, second = self.new_client(), self.new_client()
        first_session = (await first.post("/auth/demo")).json()
        second_session = (await second.post("/auth/demo")).json()
        self.assertNotEqual(first_session["company_id"], second_session["company_id"])
        self.assertEqual(first_session["company_name"], "Northstar Labs")

        first_jobs = (await first.post("/graphql", json=JOBS_QUERY)).json()["data"]["jobs"]
        second_jobs = (await second.post("/graphql", json=JOBS_QUERY)).json()["data"]["jobs"]
        self.assertEqual(first_jobs["totalCount"], len(JOBS))
        first_ids = {job["id"] for job in first_jobs["items"]}
        second_ids = {job["id"] for job in second_jobs["items"]}
        self.assertFalse(first_ids & second_ids, "Sandboxes must not share jobs.")

        # A job created in one sandbox is invisible in the other.
        sandbox = await Company.get(id=int(first_session["company_id"]))
        await Job.create(company=sandbox, title="Visitor Job", description="Private.")
        titles = {
            job["title"]
            for job in (await second.post("/graphql", json=JOBS_QUERY)).json()["data"]["jobs"][
                "items"
            ]
        }
        self.assertNotIn("Visitor Job", titles)

    async def test_sandbox_copies_the_full_dataset_with_unique_applicants(self) -> None:
        recruiter = await create_demo_sandbox()
        applications = await Application.filter(job__company_id=recruiter.company_id)
        self.assertEqual(len(applications), len(CANDIDATES))
        emails = await Candidate.filter(
            applications__job__company_id=recruiter.company_id
        ).values_list("email", flat=True)
        self.assertTrue(all("+" in email for email in emails))
        self.assertIsNone(recruiter.password_hash)
        for resume in await Resume.filter(candidate__email__in=emails):
            self.assertTrue(
                (settings.upload_root / resume.file_url.removeprefix("uploads/")).is_file()
            )

    async def test_repeat_demo_login_reuses_the_visitors_sandbox(self) -> None:
        client = self.new_client()
        first = (await client.post("/auth/demo")).json()
        again = (await client.post("/auth/demo")).json()
        self.assertEqual(first["company_id"], again["company_id"])
        self.assertEqual(await Company.filter(is_sandbox=True).count(), 1)

    async def test_shared_demo_password_login_also_opens_a_sandbox(self) -> None:
        response = await self.new_client().post(
            "/auth/login",
            json={
                "email": settings.demo_recruiter_email,
                "password": settings.demo_recruiter_password.get_secret_value(),
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotEqual(response.json()["company_id"], str(self.shared.id))

    async def test_public_jobs_show_only_real_or_own_sandbox_roles(self) -> None:
        anonymous = self.new_client()
        visitor = self.new_client()
        visitor_company = (await visitor.post("/auth/demo")).json()["company_id"]
        await self.new_client().post("/auth/demo")  # Someone else's sandbox.

        anonymous_ids = {
            int(job["id"])
            for job in (await anonymous.post("/graphql", json=PUBLIC_JOBS_QUERY)).json()["data"][
                "publicJobs"
            ]["items"]
        }
        shared_ids = set(
            await Job.filter(company=self.shared).values_list("id", flat=True)
        )
        self.assertTrue(anonymous_ids)
        self.assertTrue(anonymous_ids <= shared_ids)

        visitor_ids = {
            int(job["id"])
            for job in (await visitor.post("/graphql", json=PUBLIC_JOBS_QUERY)).json()["data"][
                "publicJobs"
            ]["items"]
        }
        own_ids = set(
            await Job.filter(company_id=int(visitor_company)).values_list("id", flat=True)
        )
        self.assertTrue(visitor_ids)
        self.assertTrue(visitor_ids <= own_ids)

    async def test_cleanup_removes_expired_sandboxes_and_their_files(self) -> None:
        expired = await create_demo_sandbox()
        fresh = await create_demo_sandbox()
        expired_resumes = await Resume.filter(
            candidate__applications__job__company_id=expired.company_id
        )
        expired_dirs = [
            (settings.upload_root / resume.file_url.removeprefix("uploads/")).parent
            for resume in expired_resumes
        ]
        await Company.filter(id=expired.company_id).update(
            created_at=datetime.now(UTC) - timedelta(hours=settings.demo_sandbox_ttl_hours + 1)
        )

        self.assertEqual(await cleanup_expired_sandboxes(), 1)
        self.assertFalse(await Company.exists(id=expired.company_id))
        self.assertFalse(await Recruiter.exists(id=expired.id))
        self.assertTrue(expired_dirs)
        self.assertFalse(any(path.exists() for path in expired_dirs))
        self.assertEqual(
            await Application.filter(job__company_id=fresh.company_id).count(), len(CANDIDATES)
        )
        self.assertEqual(
            await Application.filter(job__company=self.shared).count(), len(CANDIDATES)
        )
        # Only the shared company's and the fresh sandbox's applicants remain.
        self.assertEqual(await Candidate.all().count(), 2 * len(CANDIDATES))

    async def test_sandbox_cap_removes_the_oldest(self) -> None:
        with patch.object(settings, "demo_sandbox_max_active", 2):
            first = await create_demo_sandbox()
            await create_demo_sandbox()
            await create_demo_sandbox()
        self.assertEqual(await Company.filter(is_sandbox=True).count(), 2)
        self.assertFalse(await Company.exists(id=first.company_id))

    async def test_nightly_reset_leaves_sandboxes_alone(self) -> None:
        sandbox = await create_demo_sandbox()
        await Job.create(company=self.shared, title="Leftover", description="Removed on reset.")

        await reset_demo_data()

        self.assertFalse(await Job.exists(company=self.shared, title="Leftover"))
        self.assertEqual(await Job.filter(company=self.shared).count(), len(JOBS))
        self.assertEqual(
            await Application.filter(job__company_id=sandbox.company_id).count(), len(CANDIDATES)
        )

    async def test_admin_login_still_uses_the_shared_company(self) -> None:
        await Recruiter.create(
            company=self.shared,
            name="Admin",
            email="admin@example.com",
            role="Hiring Manager",
            password_hash=hash_password("admin-password"),
        )
        response = await self.new_client().post(
            "/auth/login", json={"email": "admin@example.com", "password": "admin-password"}
        )
        self.assertEqual(response.json()["company_id"], str(self.shared.id))
        self.assertEqual(await Company.filter(is_sandbox=True).count(), 0)


if __name__ == "__main__":
    unittest.main()
