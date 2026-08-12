from __future__ import annotations

from app.db.models import Application, ApplicationNote, Recruiter
from app.services.errors import (
    ApplicationNotFoundError,
    InvalidApplicationNoteError,
    RecruiterCompanyMismatchError,
    RecruiterNotFoundError,
)


class ApplicationNoteService:
    max_content_length = 5_000

    @classmethod
    async def add_note(
        cls,
        *,
        application_id: int,
        content: str,
        recruiter_id: int | None,
    ) -> ApplicationNote:
        normalized_content = content.strip()
        if not normalized_content:
            raise InvalidApplicationNoteError("Note content must not be empty.")
        if len(normalized_content) > cls.max_content_length:
            raise InvalidApplicationNoteError(
                f"Note content must not exceed {cls.max_content_length} characters."
            )

        application = await Application.get_or_none(id=application_id).select_related(
            "job"
        )
        if application is None:
            raise ApplicationNotFoundError("Application not found.")

        recruiter = None
        if recruiter_id is not None:
            recruiter = await Recruiter.get_or_none(id=recruiter_id)
            if recruiter is None:
                raise RecruiterNotFoundError("Recruiter not found.")
            if recruiter.company_id != application.job.company_id:
                raise RecruiterCompanyMismatchError(
                    "Recruiter cannot add notes to an application for another company."
                )

        note = await ApplicationNote.create(
            application_id=application.id,
            recruiter_id=recruiter.id if recruiter else None,
            content=normalized_content,
        )
        return await ApplicationNote.get(id=note.id).select_related("recruiter")
