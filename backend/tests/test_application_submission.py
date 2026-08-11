from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from starlette.datastructures import Headers, UploadFile
from tortoise import Tortoise

from app.db.models import (
    Application,
    ApplicationStatusHistory,
    Candidate,
    Company,
    Job,
    Resume,
)
from app.enums import ApplicationStatus, JobStatus
from app.services.application import ApplicationService
from app.services.errors import (
    DuplicateApplicationError,
    InvalidApplicationInformationError,
    InvalidCandidateInformationError,
    InvalidResumeTypeError,
    JobClosedError,
    JobNotFoundError,
    MissingResumeError,
    ResumeTooLargeError,
)
from app.services.resume_storage import ResumeStorageService


def make_upload(
    *,
    filename: str = "resume.pdf",
    content_type: str = "application/pdf",
    content: bytes = b"%PDF-1.7\nTalentFlow test resume",
) -> UploadFile:
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class ApplicationSubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.db.models"]})
        await Tortoise.generate_schemas()
        self.temporary_directory = tempfile.TemporaryDirectory()
        upload_root = Path(self.temporary_directory.name) / "uploads"
        self.storage = ResumeStorageService(upload_root=upload_root, max_size_bytes=1024)
        self.service = ApplicationService(resume_storage=self.storage)

        company = await Company.create(name="Submission Test Company")
        self.first_job = await Job.create(
            company=company,
            title="Backend Engineer",
            description="Build APIs",
            status=JobStatus.OPEN,
        )
        self.second_job = await Job.create(
            company=company,
            title="Platform Engineer",
            description="Build infrastructure",
            status=JobStatus.OPEN,
        )
        self.closed_job = await Job.create(
            company=company,
            title="Closed Role",
            description="No longer accepting applications",
            status=JobStatus.CLOSED,
        )

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()
        self.temporary_directory.cleanup()

    async def submit(self, job_id: int, email: str, upload: UploadFile) -> Application:
        return await self.service.submit(
            job_id=str(job_id),
            full_name="Jordan Taylor",
            email=email,
            phone="+1 415 555 0142",
            linkedin_url="https://linkedin.com/in/jordan-taylor",
            github_url="https://github.com/jordantaylor",
            portfolio_url="https://jordantaylor.example.com",
            cover_letter="I would love to help build dependable recruiting software.",
            resume=upload,
        )

    async def test_candidate_reuse_resume_and_duplicate_prevention(self) -> None:
        first = await self.submit(self.first_job.id, " Jordan@Example.com ", make_upload())
        first_path = self.storage.resolve(first.resume_url or "")

        self.assertEqual(first.status, ApplicationStatus.APPLIED)
        self.assertTrue(first_path.is_file())
        self.assertEqual(await Candidate.all().count(), 1)
        self.assertEqual(await Resume.all().count(), 1)
        history = await ApplicationStatusHistory.get(application_id=first.id)
        self.assertIsNone(history.previous_status)
        self.assertEqual(history.new_status, ApplicationStatus.APPLIED)

        second = await self.submit(
            self.second_job.id,
            "jordan@example.com",
            make_upload(filename="updated-resume.pdf"),
        )
        self.assertEqual(first.candidate_id, second.candidate_id)
        self.assertEqual(await Candidate.all().count(), 1)
        self.assertEqual(await Application.all().count(), 2)
        self.assertEqual(await Resume.all().count(), 1)
        resume = await Resume.get(candidate_id=first.candidate_id)
        self.assertEqual(resume.file_url, second.resume_url)
        self.assertTrue(self.storage.resolve(resume.file_url).is_file())

        with self.assertRaisesRegex(DuplicateApplicationError, "already applied"):
            await self.submit(
                self.first_job.id,
                "JORDAN@example.com",
                make_upload(filename="duplicate.pdf"),
            )
        self.assertEqual(await Application.all().count(), 2)

    async def test_job_errors_are_clean(self) -> None:
        with self.assertRaises(JobNotFoundError):
            await self.submit(999_999, "new@example.com", make_upload())
        with self.assertRaises(JobClosedError):
            await self.submit(self.closed_job.id, "new@example.com", make_upload())

    async def test_resume_validation(self) -> None:
        with self.assertRaises(MissingResumeError):
            await self.service.submit(
                job_id=str(self.first_job.id),
                full_name="Jordan Taylor",
                email="new@example.com",
                phone=None,
                linkedin_url=None,
                github_url=None,
                portfolio_url=None,
                cover_letter="Interested in the role.",
                resume=None,
            )
        with self.assertRaises(MissingResumeError):
            await self.submit(
                self.first_job.id,
                "new@example.com",
                make_upload(content=b""),
            )
        with self.assertRaises(InvalidResumeTypeError):
            await self.submit(
                self.first_job.id,
                "new@example.com",
                make_upload(filename="resume.txt", content_type="text/plain"),
            )
        with self.assertRaises(InvalidResumeTypeError):
            await self.submit(
                self.first_job.id,
                "new@example.com",
                make_upload(content=b"not actually a pdf"),
            )
        with self.assertRaises(ResumeTooLargeError):
            await self.submit(
                self.first_job.id,
                "new@example.com",
                make_upload(content=b"%PDF-1.7\n" + b"x" * 1024),
            )

    async def test_candidate_and_cover_letter_validation(self) -> None:
        with self.assertRaises(InvalidCandidateInformationError):
            await self.service.submit(
                job_id=str(self.first_job.id),
                full_name=" ",
                email="not-an-email",
                phone=None,
                linkedin_url=None,
                github_url=None,
                portfolio_url=None,
                cover_letter="Interested in the role.",
                resume=make_upload(),
            )
        with self.assertRaises(InvalidApplicationInformationError):
            await self.service.submit(
                job_id=str(self.first_job.id),
                full_name="Jordan Taylor",
                email="jordan@example.com",
                phone=None,
                linkedin_url=None,
                github_url=None,
                portfolio_url=None,
                cover_letter=" ",
                resume=make_upload(),
            )


if __name__ == "__main__":
    unittest.main()
