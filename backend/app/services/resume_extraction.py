from __future__ import annotations

import asyncio
import re
from pathlib import Path

from pypdf import PdfReader

from app.db.models import Resume
from app.services.errors import (
    InvalidResumePDFError,
    ResumeExtractionError,
    ResumeFileNotFoundError,
    ResumeRecordNotFoundError,
    ResumeTextNotFoundError,
)
from app.services.resume_storage import ResumeStorageService


class ResumeExtractionService:
    """Extract plain text from stored, text-based PDF resumes."""

    async def extract(self, stored_file: str | Path) -> str:
        path = Path(stored_file)
        if not path.is_file():
            raise ResumeFileNotFoundError("The stored resume PDF could not be found.")

        try:
            page_text = await asyncio.to_thread(self._extract_pages, path)
        except ResumeExtractionError:
            raise
        except Exception:
            raise InvalidResumePDFError(
                "The stored resume is not a readable PDF."
            ) from None

        normalized_text = self.normalize_text("\n\n".join(page_text))
        if not normalized_text:
            raise ResumeTextNotFoundError(
                "The resume PDF contains no extractable text."
            )
        return normalized_text

    async def extract_and_save(
        self,
        resume_id: int,
        *,
        storage: ResumeStorageService | None = None,
    ) -> str:
        resume = await Resume.get_or_none(id=resume_id)
        if resume is None:
            raise ResumeRecordNotFoundError("Resume record not found.")

        storage_service = storage or ResumeStorageService()
        try:
            stored_file = storage_service.resolve(resume.file_url)
        except (TypeError, ValueError):
            raise ResumeFileNotFoundError(
                "The stored resume PDF could not be found."
            ) from None

        raw_text = await self.extract(stored_file)
        resume.raw_text = raw_text
        await resume.save(update_fields=["raw_text", "updated_at"])
        return raw_text

    @staticmethod
    def _extract_pages(path: Path) -> list[str]:
        with path.open("rb") as stored_file:
            if b"%PDF-" not in stored_file.read(1024):
                raise InvalidResumePDFError(
                    "The stored resume is not a readable PDF."
                )

        reader = PdfReader(path)
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception:
                unlocked = 0
            if not unlocked:
                raise InvalidResumePDFError(
                    "Encrypted resume PDFs are not supported."
                )

        return [page.extract_text() or "" for page in reader.pages]

    @staticmethod
    def normalize_text(text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = normalized.replace("\f", "\n").replace("\u00a0", " ")
        lines = [
            re.sub(r"[ \t]+", " ", line).strip()
            for line in normalized.split("\n")
        ]

        cleaned_lines: list[str] = []
        previous_was_blank = True
        for line in lines:
            if line:
                cleaned_lines.append(line)
                previous_was_blank = False
            elif not previous_was_blank:
                cleaned_lines.append("")
                previous_was_blank = True

        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
        return "\n".join(cleaned_lines)
