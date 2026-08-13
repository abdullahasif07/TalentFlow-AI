from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from tortoise import Tortoise

from app.db.models import Candidate, Resume
from app.services.errors import (
    InvalidResumePDFError,
    ResumeFileNotFoundError,
    ResumeRecordNotFoundError,
    ResumeTextNotFoundError,
)
from app.services.resume_extraction import ResumeExtractionService
from app.services.resume_storage import ResumeStorageService


def make_pdf(text_lines: list[str] | None = None) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    if text_lines:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_reference = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): font_reference}
                )
            }
        )
        commands = ["BT /F1 12 Tf 72 720 Td"]
        for index, line in enumerate(text_lines):
            escaped = (
                line.replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            if index:
                commands.append("0 -18 Td")
            commands.append(f"({escaped}) Tj")
        commands.append("ET")
        content = DecodedStreamObject()
        content.set_data(" ".join(commands).encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(content)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class ResumeExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.upload_root = Path(self.temporary_directory.name) / "uploads"
        self.storage = ResumeStorageService(upload_root=self.upload_root)
        self.service = ResumeExtractionService()

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()
        self.temporary_directory.cleanup()

    def store_test_file(self, relative_path: str, content: bytes) -> Path:
        path = self.upload_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    async def test_valid_pdf_text_is_extracted_and_normalized(self) -> None:
        path = self.store_test_file(
            "resumes/1/valid.pdf",
            make_pdf(["Jordan Taylor", "Python    FastAPI", "PostgreSQL"]),
        )

        text = await self.service.extract(path)

        self.assertEqual(text, "Jordan Taylor\nPython FastAPI\nPostgreSQL")

    async def test_missing_pdf_is_rejected(self) -> None:
        with self.assertRaisesRegex(ResumeFileNotFoundError, "could not be found"):
            await self.service.extract(self.upload_root / "resumes/missing.pdf")

    async def test_invalid_pdf_and_library_errors_are_clean(self) -> None:
        invalid_path = self.store_test_file(
            "resumes/1/corrupt.pdf", b"this is not a PDF"
        )
        with self.assertRaisesRegex(InvalidResumePDFError, "not a readable PDF"):
            await self.service.extract(invalid_path)

        valid_path = self.store_test_file(
            "resumes/1/library-error.pdf", make_pdf(["Readable text"])
        )
        with patch.object(
            ResumeExtractionService,
            "_extract_pages",
            side_effect=RuntimeError("low-level parser detail"),
        ):
            with self.assertRaisesRegex(InvalidResumePDFError, "not a readable PDF"):
                await self.service.extract(valid_path)

    async def test_pdf_without_extractable_text_is_rejected(self) -> None:
        path = self.store_test_file("resumes/1/blank.pdf", make_pdf())

        with self.assertRaisesRegex(ResumeTextNotFoundError, "no extractable text"):
            await self.service.extract(path)

    async def test_extracted_text_is_saved_without_changing_parsed_data(self) -> None:
        candidate = await Candidate.create(
            name="Jordan Taylor", email="jordan.extraction@example.com"
        )
        file_url = f"uploads/resumes/{candidate.id}/resume.pdf"
        self.store_test_file(
            f"resumes/{candidate.id}/resume.pdf",
            make_pdf(["Jordan Taylor", "Backend Engineer"]),
        )
        resume = await Resume.create(
            candidate=candidate,
            file_url=file_url,
            raw_text=None,
            parsed_data={"preserve": True},
        )

        text = await self.service.extract_and_save(resume.id, storage=self.storage)

        await resume.refresh_from_db()
        self.assertEqual(text, "Jordan Taylor\nBackend Engineer")
        self.assertEqual(resume.raw_text, text)
        self.assertEqual(resume.parsed_data, {"preserve": True})

    async def test_missing_resume_record_is_rejected(self) -> None:
        with self.assertRaisesRegex(ResumeRecordNotFoundError, "record not found"):
            await self.service.extract_and_save(999_999, storage=self.storage)


if __name__ == "__main__":
    unittest.main()
