from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

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
from app.enums import (
    AIProcessingState,
    ApplicationSort,
    ApplicationStatus,
    EvaluationConfidence,
    JobStatus,
    OutreachStatus,
)
from app.graphql.schema import schema
from app.services import RecruiterApplicationQueryService


class RecruiterApplicationQueryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()

        self.company = await Company.create(name="Recruiter Query Company")
        self.job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description="Build reliable recruiting APIs.",
            status=JobStatus.OPEN,
        )
        self.other_job = await Job.create(
            company=self.company,
            title="Product Designer",
            description="Design thoughtful recruiting workflows.",
            status=JobStatus.OPEN,
        )

        candidate_data = [
            ("Alice Stone", "alice@alpha.example", ApplicationStatus.APPLIED, "70"),
            (
                "Bob Rivera",
                "bob@beta.example",
                ApplicationStatus.SHORTLISTED,
                "92",
            ),
            (
                "Casey Morgan",
                "casey@gamma.example",
                ApplicationStatus.CONTACTED,
                None,
            ),
            (
                "Devon Lee",
                "devon@delta.example",
                ApplicationStatus.INTERVIEW,
                "80",
            ),
            ("Evelyn Shah", "evelyn@epsilon.example", ApplicationStatus.HIRED, "96"),
            (
                "Frank Woods",
                "frank@zeta.example",
                ApplicationStatus.REJECTED,
                "40",
            ),
        ]
        self.applications: list[Application] = []
        for index, (name, email, status, score) in enumerate(candidate_data, start=1):
            candidate = await Candidate.create(
                name=name,
                email=email,
                phone=f"+1 415 555 01{index:02d}",
                linkedin_url=f"https://linkedin.com/in/{name.lower().replace(' ', '-')}",
                github_url=f"https://github.com/{name.split()[0].lower()}",
                portfolio_url=f"https://{name.split()[0].lower()}.example.com",
            )
            application = await Application.create(
                candidate=candidate,
                job=self.job,
                cover_letter=f"Cover letter from {name}.",
                resume_url=f"uploads/resumes/{candidate.id}/{name.split()[0].lower()}.pdf",
                status=status,
                fit_score=Decimal(score) if score else None,
            )
            applied_at = datetime(2026, 1, index, 12, 0, tzinfo=timezone.utc)
            await Application.filter(id=application.id).update(applied_at=applied_at)
            application.applied_at = applied_at
            self.applications.append(application)

        self.alice, self.bob, self.casey, self.devon, self.evelyn, self.frank = (
            self.applications
        )
        await Resume.create(
            candidate_id=self.bob.candidate_id,
            file_url="uploads/resumes/current/bob-current.pdf",
        )
        await AIEvaluation.create(
            application=self.bob,
            overall_score=Decimal("92"),
            recommendation="Strong match",
            confidence=EvaluationConfidence.HIGH,
        )
        await Application.filter(id=self.bob.id).update(
            evaluation_processing_state=AIProcessingState.COMPLETED
        )
        self.bob.evaluation_processing_state = AIProcessingState.COMPLETED
        await ApplicationStatusHistory.create(
            application=self.bob,
            previous_status=None,
            new_status=ApplicationStatus.APPLIED,
            changed_by="candidate",
        )
        await ApplicationStatusHistory.create(
            application=self.bob,
            previous_status=ApplicationStatus.APPLIED,
            new_status=ApplicationStatus.SHORTLISTED,
            changed_by="recruiter@example.com",
        )
        await OutreachEmail.create(
            application=self.bob,
            subject="Backend Engineer interview",
            body="We would like to arrange an interview.",
            status=OutreachStatus.DRAFT,
        )

        other_candidate = await Candidate.create(
            name="Other Job Applicant", email="other@example.com"
        )
        await Application.create(candidate=other_candidate, job=self.other_job)

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    def assert_success(self, result: object) -> dict:
        errors = getattr(result, "errors")
        self.assertIsNone(errors, errors)
        data = getattr(result, "data")
        self.assertIsNotNone(data)
        return data

    async def query_applications(self, input_value: dict) -> dict:
        result = await schema.execute(
            """
            query RecruiterApplications($input: ApplicationsQueryInput!) {
              applications(input: $input) {
                success
                totalCount
                pageInfo { limit offset hasNextPage hasPreviousPage }
                items {
                  id status fitScore appliedAt
                  candidate {
                    id name email phone linkedinUrl githubUrl portfolioUrl
                  }
                  resume { id fileUrl }
                  evaluation { overallScore recommendation confidence }
                }
                errors { code message field }
              }
            }
            """,
            variable_values={"input": input_value},
        )
        return self.assert_success(result)["applications"]

    async def test_filtering_and_nested_relationships(self) -> None:
        filtered = await self.query_applications(
            {
                "jobId": str(self.job.id),
                "filters": {"status": "SHORTLISTED", "candidateSearch": "BOB"},
            }
        )

        self.assertTrue(filtered["success"])
        self.assertEqual(filtered["totalCount"], 1)
        item = filtered["items"][0]
        self.assertEqual(item["candidate"]["email"], "bob@beta.example")
        self.assertEqual(item["resume"]["fileUrl"], self.bob.resume_url)
        self.assertEqual(item["evaluation"]["recommendation"], "Strong match")

        email_search = await self.query_applications(
            {
                "jobId": str(self.job.id),
                "filters": {"candidateSearch": "GAMMA.EXAMPLE"},
            }
        )
        self.assertEqual(
            [item["candidate"]["name"] for item in email_search["items"]],
            ["Casey Morgan"],
        )

        scored = await self.query_applications(
            {"jobId": str(self.job.id), "filters": {"minimumFitScore": "90"}}
        )
        self.assertEqual(scored["totalCount"], 2)
        self.assertEqual(
            {item["candidate"]["name"] for item in scored["items"]},
            {"Bob Rivera", "Evelyn Shah"},
        )

        legacy_status_filter = await self.query_applications(
            {"jobId": str(self.job.id), "status": "CONTACTED"}
        )
        self.assertEqual(
            [item["candidate"]["name"] for item in legacy_status_filter["items"]],
            ["Casey Morgan"],
        )

    async def test_applications_are_scoped_to_the_requested_job(self) -> None:
        first_job = await self.query_applications({"jobId": str(self.job.id)})
        other_job = await self.query_applications({"jobId": str(self.other_job.id)})

        self.assertEqual(first_job["totalCount"], 6)
        self.assertNotIn(
            "Other Job Applicant",
            {item["candidate"]["name"] for item in first_job["items"]},
        )
        self.assertEqual(other_job["totalCount"], 1)
        self.assertEqual(
            other_job["items"][0]["candidate"]["name"],
            "Other Job Applicant",
        )

    async def test_sorting_and_pagination(self) -> None:
        newest = await self.query_applications({"jobId": str(self.job.id)})
        self.assertEqual(newest["items"][0]["candidate"]["name"], "Frank Woods")

        oldest = await self.query_applications(
            {"jobId": str(self.job.id), "sort": "OLDEST"}
        )
        self.assertEqual(oldest["items"][0]["candidate"]["name"], "Alice Stone")

        ascending = await self.query_applications(
            {"jobId": str(self.job.id), "sort": "FIT_SCORE_ASC"}
        )
        self.assertEqual(
            [
                Decimal(item["fitScore"]) if item["fitScore"] is not None else None
                for item in ascending["items"]
            ],
            [
                Decimal("40"),
                Decimal("70"),
                Decimal("80"),
                Decimal("92"),
                Decimal("96"),
                None,
            ],
        )

        page = await self.query_applications(
            {
                "jobId": str(self.job.id),
                "sort": "FIT_SCORE_DESC",
                "pagination": {"limit": 2, "offset": 1},
            }
        )
        self.assertEqual(page["totalCount"], 6)
        self.assertEqual(
            [item["candidate"]["name"] for item in page["items"]],
            ["Bob Rivera", "Devon Lee"],
        )
        self.assertEqual(
            page["pageInfo"],
            {
                "limit": 2,
                "offset": 1,
                "hasNextPage": True,
                "hasPreviousPage": True,
            },
        )

    async def test_individual_application_detail(self) -> None:
        result = await schema.execute(
            """
            query ApplicationDetail($input: ApplicationQueryInput!) {
              application(input: $input) {
                success
                application {
                  id status fitScore coverLetter appliedAt updatedAt
                  candidate { name email phone linkedinUrl githubUrl portfolioUrl }
                  job { id companyId title description status }
                  resume { id fileUrl }
                  evaluation { overallScore recommendation confidence }
                  statusHistory { previousStatus newStatus changedBy createdAt }
                  outreachEmails { subject body status generatedAt approvedAt sentAt }
                }
                errors { code message field }
              }
            }
            """,
            variable_values={"input": {"id": str(self.bob.id)}},
        )
        detail = self.assert_success(result)["application"]

        self.assertTrue(detail["success"])
        application = detail["application"]
        self.assertEqual(application["candidate"]["name"], "Bob Rivera")
        self.assertEqual(application["job"]["title"], "Backend Engineer")
        self.assertEqual(application["resume"]["fileUrl"], self.bob.resume_url)
        self.assertEqual(application["evaluation"]["confidence"], "HIGH")
        self.assertEqual(len(application["statusHistory"]), 2)
        self.assertEqual(application["outreachEmails"][0]["status"], "DRAFT")

    async def test_job_statistics(self) -> None:
        result = await schema.execute(
            """
            query JobStatistics($input: JobQueryInput!) {
              job(input: $input) {
                success
                job {
                  applicantCount shortlistedCount contactedCount
                  interviewCount hiredCount recommendedCandidateCount
                }
                errors { code message field }
              }
            }
            """,
            variable_values={"input": {"id": str(self.job.id)}},
        )
        job = self.assert_success(result)["job"]

        self.assertTrue(job["success"])
        self.assertEqual(
            job["job"],
            {
                "applicantCount": 6,
                "shortlistedCount": 1,
                "contactedCount": 1,
                "interviewCount": 1,
                "hiredCount": 1,
                "recommendedCandidateCount": 1,
            },
        )

    async def test_list_query_uses_a_fixed_number_of_database_queries(self) -> None:
        connection = Tortoise.get_connection("default")
        original_execute_query = connection.execute_query
        query_count = 0

        async def counting_execute_query(*args, **kwargs):
            nonlocal query_count
            query_count += 1
            return await original_execute_query(*args, **kwargs)

        connection.execute_query = counting_execute_query
        try:
            page = await RecruiterApplicationQueryService.list_for_job(
                job_id=self.job.id,
                sort=ApplicationSort.NEWEST,
                limit=100,
            )
        finally:
            connection.execute_query = original_execute_query

        self.assertEqual(len(page.records), 6)
        self.assertEqual(query_count, 5)


if __name__ == "__main__":
    unittest.main()
