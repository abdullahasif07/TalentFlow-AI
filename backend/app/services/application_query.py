from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal

from tortoise.expressions import Q
from tortoise.functions import Coalesce
from tortoise.queryset import QuerySet

from app.db.models import (
    AIEvaluation,
    Application,
    ApplicationNote,
    ApplicationStatusHistory,
    Job,
    OutreachEmail,
    Resume,
)
from app.enums import ApplicationSort, ApplicationStatus
from app.services.errors import InvalidApplicationInformationError, JobNotFoundError


@dataclass(frozen=True)
class ApplicationListRecord:
    application: Application
    resume: Resume | None
    evaluation: AIEvaluation | None


@dataclass(frozen=True)
class ApplicationPage:
    records: list[ApplicationListRecord]
    total_count: int
    limit: int
    offset: int


@dataclass(frozen=True)
class ApplicationDetailRecord:
    application: Application
    resume: Resume | None
    evaluation: AIEvaluation | None
    status_history: list[ApplicationStatusHistory]
    notes: list[ApplicationNote]
    outreach_emails: list[OutreachEmail]


class RecruiterApplicationQueryService:
    default_limit = 25
    maximum_limit = 100

    @classmethod
    async def list_for_job(
        cls,
        *,
        job_id: int,
        status: ApplicationStatus | None = None,
        minimum_fit_score: Decimal | None = None,
        candidate_search: str | None = None,
        sort: ApplicationSort = ApplicationSort.NEWEST,
        limit: int = default_limit,
        offset: int = 0,
    ) -> ApplicationPage:
        cls._validate_options(
            minimum_fit_score=minimum_fit_score,
            candidate_search=candidate_search,
            limit=limit,
            offset=offset,
        )
        if not await Job.exists(id=job_id):
            raise JobNotFoundError("Job not found.")

        query = Application.filter(job_id=job_id)
        if status is not None:
            query = query.filter(status=status)
        if minimum_fit_score is not None:
            query = query.filter(fit_score__gte=minimum_fit_score)
        search = candidate_search.strip() if candidate_search else ""
        if search:
            query = query.filter(
                Q(candidate__name__icontains=search)
                | Q(candidate__email__icontains=search)
            )

        total_count = await query.count()
        query = cls._apply_sort(query, sort)
        applications = await (
            query.select_related("candidate", "job").offset(offset).limit(limit)
        )
        if not applications:
            return ApplicationPage([], total_count, limit, offset)

        application_ids = [application.id for application in applications]
        candidate_ids = [application.candidate_id for application in applications]
        resumes = await Resume.filter(candidate_id__in=candidate_ids)
        evaluations = await AIEvaluation.filter(application_id__in=application_ids)
        resumes_by_candidate = {resume.candidate_id: resume for resume in resumes}
        evaluations_by_application = {
            evaluation.application_id: evaluation for evaluation in evaluations
        }
        records = [
            ApplicationListRecord(
                application=application,
                resume=resumes_by_candidate.get(application.candidate_id),
                evaluation=evaluations_by_application.get(application.id),
            )
            for application in applications
        ]
        return ApplicationPage(records, total_count, limit, offset)

    @staticmethod
    async def get_detail(application_id: int) -> ApplicationDetailRecord | None:
        application = await Application.get_or_none(id=application_id).select_related(
            "candidate", "job"
        )
        if application is None:
            return None

        resume, evaluation, status_history, notes, outreach_emails = await asyncio.gather(
            Resume.get_or_none(candidate_id=application.candidate_id),
            AIEvaluation.get_or_none(application_id=application.id),
            ApplicationStatusHistory.filter(application_id=application.id).order_by(
                "created_at", "id"
            ),
            ApplicationNote.filter(application_id=application.id)
            .select_related("recruiter")
            .order_by("created_at", "id"),
            OutreachEmail.filter(application_id=application.id).order_by(
                "-generated_at"
            ),
        )
        return ApplicationDetailRecord(
            application=application,
            resume=resume,
            evaluation=evaluation,
            status_history=status_history,
            notes=notes,
            outreach_emails=outreach_emails,
        )

    @classmethod
    def _validate_options(
        cls,
        *,
        minimum_fit_score: Decimal | None,
        candidate_search: str | None,
        limit: int,
        offset: int,
    ) -> None:
        if limit < 1 or limit > cls.maximum_limit:
            raise InvalidApplicationInformationError(
                f"Pagination limit must be between 1 and {cls.maximum_limit}."
            )
        if offset < 0:
            raise InvalidApplicationInformationError(
                "Pagination offset must be zero or greater."
            )
        valid_score = minimum_fit_score is None or (
            Decimal("0") <= minimum_fit_score <= Decimal("100")
        )
        if not valid_score:
            raise InvalidApplicationInformationError(
                "Minimum fit score must be between 0 and 100."
            )
        if candidate_search and len(candidate_search.strip()) > 200:
            raise InvalidApplicationInformationError(
                "Candidate search must not exceed 200 characters."
            )

    @staticmethod
    def _apply_sort(
        query: QuerySet[Application], sort: ApplicationSort
    ) -> QuerySet[Application]:
        if sort == ApplicationSort.OLDEST:
            return query.order_by("applied_at", "id")
        if sort == ApplicationSort.FIT_SCORE_ASC:
            return query.annotate(
                sortable_fit_score=Coalesce("fit_score", 101)
            ).order_by("sortable_fit_score", "-applied_at", "-id")
        if sort == ApplicationSort.FIT_SCORE_DESC:
            return query.annotate(
                sortable_fit_score=Coalesce("fit_score", -1)
            ).order_by("-sortable_fit_score", "-applied_at", "-id")
        return query.order_by("-applied_at", "-id")
