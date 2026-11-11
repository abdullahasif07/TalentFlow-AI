from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.auth import get_session_recruiter
from app.db.models import Application, Recruiter, Resume
from app.services.resume_storage import ResumeStorageService


router = APIRouter(tags=["resumes"])


@router.get("/applications/{application_id}/resume")
async def download_application_resume(
    application_id: int,
    recruiter: Recruiter = Depends(get_session_recruiter),
) -> FileResponse:
    application = await Application.get_or_none(id=application_id).select_related(
        "job", "candidate"
    )
    # Applications from another company are reported as missing, not forbidden, so
    # their existence is not revealed.
    if application is None or application.job.company_id != recruiter.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    resume = await Resume.get_or_none(candidate_id=application.candidate_id)
    stored_path = application.resume_url or (resume.file_url if resume else None)
    if not stored_path or stored_path.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    try:
        path = ResumeStorageService().resolve(stored_path)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found."
        ) from None
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", application.candidate.name).strip("-")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{safe_name or 'resume'}-resume.pdf",
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )

