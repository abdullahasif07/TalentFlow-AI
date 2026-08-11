from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import strawberry

from app.db.models import (
    AIEvaluation,
    Application,
    ApplicationStatusHistory,
    Candidate,
    Job,
    OutreachEmail,
    Resume,
)
from app.enums import (
    ApplicationStatus,
    EvaluationConfidence,
    JobStatus,
    OutreachStatus,
)
from app.graphql.types.common import OffsetPageInfo, OperationError
from app.graphql.types.job import JobSummary


@strawberry.type
class CandidateSummary:
    id: strawberry.ID
    name: str
    email: str


@strawberry.type
class CandidateDetails:
    id: strawberry.ID
    name: str
    email: str
    phone: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None

    @classmethod
    def from_model(cls, candidate: Candidate) -> "CandidateDetails":
        return cls(
            id=strawberry.ID(str(candidate.id)),
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            linkedin_url=candidate.linkedin_url,
            github_url=candidate.github_url,
            portfolio_url=candidate.portfolio_url,
        )


@strawberry.type
class ResumeType:
    id: strawberry.ID
    file_url: str

    @classmethod
    def from_model(
        cls, resume: Resume, *, application_file_url: str | None = None
    ) -> "ResumeType":
        return cls(
            id=strawberry.ID(str(resume.id)),
            file_url=application_file_url or resume.file_url,
        )


@strawberry.type
class EvaluationType:
    overall_score: Decimal
    recommendation: str
    confidence: EvaluationConfidence

    @classmethod
    def from_model(cls, evaluation: AIEvaluation) -> "EvaluationType":
        return cls(
            overall_score=evaluation.overall_score,
            recommendation=evaluation.recommendation,
            confidence=evaluation.confidence,
        )


@strawberry.type
class ApplicationJobType:
    id: strawberry.ID
    company_id: strawberry.ID
    title: str
    description: str
    status: JobStatus

    @classmethod
    def from_model(cls, job: Job) -> "ApplicationJobType":
        return cls(
            id=strawberry.ID(str(job.id)),
            company_id=strawberry.ID(str(job.company_id)),
            title=job.title,
            description=job.description,
            status=job.status,
        )


@strawberry.type
class ApplicationStatusHistoryType:
    id: strawberry.ID
    previous_status: ApplicationStatus | None
    new_status: ApplicationStatus
    changed_by: str
    created_at: datetime

    @classmethod
    def from_model(
        cls, history: ApplicationStatusHistory
    ) -> "ApplicationStatusHistoryType":
        return cls(
            id=strawberry.ID(str(history.id)),
            previous_status=history.previous_status,
            new_status=history.new_status,
            changed_by=history.changed_by,
            created_at=history.created_at,
        )


@strawberry.type
class OutreachEmailType:
    id: strawberry.ID
    subject: str
    body: str
    status: OutreachStatus
    generated_at: datetime
    approved_at: datetime | None
    sent_at: datetime | None

    @classmethod
    def from_model(cls, email: OutreachEmail) -> "OutreachEmailType":
        return cls(
            id=strawberry.ID(str(email.id)),
            subject=email.subject,
            body=email.body,
            status=email.status,
            generated_at=email.generated_at,
            approved_at=email.approved_at,
            sent_at=email.sent_at,
        )


@strawberry.type
class ApplicationType:
    id: strawberry.ID
    candidate_id: strawberry.ID
    job_id: strawberry.ID
    candidate: CandidateSummary
    job: JobSummary
    resume_url: str | None
    cover_letter: str | None
    status: ApplicationStatus
    fit_score: Decimal | None
    applied_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, application: Application) -> "ApplicationType":
        return cls(
            id=strawberry.ID(str(application.id)),
            candidate_id=strawberry.ID(str(application.candidate_id)),
            job_id=strawberry.ID(str(application.job_id)),
            candidate=CandidateSummary(
                id=strawberry.ID(str(application.candidate.id)),
                name=application.candidate.name,
                email=application.candidate.email,
            ),
            job=JobSummary.from_model(application.job),
            resume_url=application.resume_url,
            cover_letter=application.cover_letter,
            status=application.status,
            fit_score=application.fit_score,
            applied_at=application.applied_at,
            updated_at=application.updated_at,
        )


@strawberry.type
class ApplicationListItemType:
    id: strawberry.ID
    candidate_id: strawberry.ID
    job_id: strawberry.ID
    status: ApplicationStatus
    fit_score: Decimal | None
    resume_url: str | None
    cover_letter: str | None
    applied_at: datetime
    updated_at: datetime
    candidate: CandidateDetails
    job: JobSummary
    resume: ResumeType | None
    evaluation: EvaluationType | None

    @classmethod
    def from_models(
        cls,
        application: Application,
        resume: Resume | None,
        evaluation: AIEvaluation | None,
    ) -> "ApplicationListItemType":
        return cls(
            id=strawberry.ID(str(application.id)),
            candidate_id=strawberry.ID(str(application.candidate_id)),
            job_id=strawberry.ID(str(application.job_id)),
            status=application.status,
            fit_score=application.fit_score,
            resume_url=application.resume_url,
            cover_letter=application.cover_letter,
            applied_at=application.applied_at,
            updated_at=application.updated_at,
            candidate=CandidateDetails.from_model(application.candidate),
            job=JobSummary.from_model(application.job),
            resume=(
                ResumeType.from_model(
                    resume, application_file_url=application.resume_url
                )
                if resume
                else None
            ),
            evaluation=EvaluationType.from_model(evaluation) if evaluation else None,
        )


@strawberry.type
class ApplicationDetailType:
    id: strawberry.ID
    candidate_id: strawberry.ID
    job_id: strawberry.ID
    status: ApplicationStatus
    fit_score: Decimal | None
    resume_url: str | None
    cover_letter: str | None
    applied_at: datetime
    updated_at: datetime
    candidate: CandidateDetails
    job: ApplicationJobType
    resume: ResumeType | None
    evaluation: EvaluationType | None
    status_history: list[ApplicationStatusHistoryType]
    outreach_emails: list[OutreachEmailType]

    @classmethod
    def from_models(
        cls,
        application: Application,
        resume: Resume | None,
        evaluation: AIEvaluation | None,
        status_history: list[ApplicationStatusHistory],
        outreach_emails: list[OutreachEmail],
    ) -> "ApplicationDetailType":
        return cls(
            id=strawberry.ID(str(application.id)),
            candidate_id=strawberry.ID(str(application.candidate_id)),
            job_id=strawberry.ID(str(application.job_id)),
            status=application.status,
            fit_score=application.fit_score,
            resume_url=application.resume_url,
            cover_letter=application.cover_letter,
            applied_at=application.applied_at,
            updated_at=application.updated_at,
            candidate=CandidateDetails.from_model(application.candidate),
            job=ApplicationJobType.from_model(application.job),
            resume=(
                ResumeType.from_model(
                    resume, application_file_url=application.resume_url
                )
                if resume
                else None
            ),
            evaluation=EvaluationType.from_model(evaluation) if evaluation else None,
            status_history=[
                ApplicationStatusHistoryType.from_model(item) for item in status_history
            ],
            outreach_emails=[OutreachEmailType.from_model(item) for item in outreach_emails],
        )


@strawberry.type
class ApplicationsResult:
    success: bool
    items: list[ApplicationListItemType]
    total_count: int
    page_info: OffsetPageInfo | None
    errors: list[OperationError]


@strawberry.type
class ApplicationResult:
    success: bool
    application: ApplicationDetailType | None
    errors: list[OperationError]


@strawberry.type
class SubmitApplicationPayload:
    success: bool
    application: ApplicationType | None
    errors: list[OperationError]


@strawberry.type
class UpdateApplicationStatusPayload:
    success: bool
    application: ApplicationType | None
    errors: list[OperationError]
