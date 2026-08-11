from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.config import BACKEND_DIR, settings
from app.services.errors import (
    InvalidResumeTypeError,
    MissingResumeError,
    ResumeTooLargeError,
)


@dataclass(frozen=True)
class ValidatedResumeFile:
    filename: str
    content: bytes


class UploadedFile(Protocol):
    filename: str | None
    content_type: str | None

    async def read(self, size: int = -1) -> bytes: ...

    async def close(self) -> None: ...


class ResumeStorageService:
    """Validate and persist resumes behind a replaceable storage boundary."""

    storage_prefix = "uploads"

    def __init__(
        self,
        upload_root: Path | None = None,
        max_size_bytes: int | None = None,
    ) -> None:
        configured_root = upload_root or settings.upload_root
        self.upload_root = (
            configured_root
            if configured_root.is_absolute()
            else (BACKEND_DIR / configured_root).resolve()
        )
        self.max_size_bytes = max_size_bytes or settings.max_resume_size_bytes

    async def validate(self, upload: UploadedFile | None) -> ValidatedResumeFile:
        if upload is None or not upload.filename:
            raise MissingResumeError("A resume PDF is required.")

        filename = Path(upload.filename).name
        if Path(filename).suffix.casefold() != ".pdf":
            raise InvalidResumeTypeError("Resume must be a PDF file.")
        if upload.content_type != "application/pdf":
            raise InvalidResumeTypeError("Resume must use the application/pdf content type.")

        try:
            content = await upload.read(self.max_size_bytes + 1)
        except Exception:
            raise MissingResumeError("The supplied resume could not be read.") from None
        finally:
            await upload.close()

        if not content:
            raise MissingResumeError("The supplied resume is empty.")
        if len(content) > self.max_size_bytes:
            size_mb = self.max_size_bytes // (1024 * 1024)
            raise ResumeTooLargeError(f"Resume must not exceed {size_mb} MB.")
        if b"%PDF-" not in content[:1024]:
            raise InvalidResumeTypeError("The supplied file is not a valid PDF.")

        return ValidatedResumeFile(filename=filename, content=content)

    async def store(self, candidate_id: int, resume: ValidatedResumeFile) -> str:
        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(resume.filename).stem).strip("-")
        safe_stem = (safe_stem or "resume")[:80]
        stored_name = f"{uuid4().hex}_{safe_stem}.pdf"
        relative_path = Path("resumes") / str(candidate_id) / stored_name
        destination = self.upload_root / relative_path

        await asyncio.to_thread(self._write_file, destination, resume.content)
        return (Path(self.storage_prefix) / relative_path).as_posix()

    async def delete(self, stored_path: str) -> None:
        path = self.resolve(stored_path)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    def resolve(self, stored_path: str) -> Path:
        relative = Path(stored_path)
        if relative.parts and relative.parts[0] == self.storage_prefix:
            relative = Path(*relative.parts[1:])
        resolved = (self.upload_root / relative).resolve()
        try:
            resolved.relative_to(self.upload_root.resolve())
        except ValueError:
            raise ValueError("Stored resume path is outside the upload directory.") from None
        return resolved

    @staticmethod
    def _write_file(destination: Path, content: bytes) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(destination)
