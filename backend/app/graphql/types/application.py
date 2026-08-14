from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import strawberry

from app.db.models import (
    AIEvaluation,
    Application,
    ApplicationNote,
    ApplicationStatusHistory,
    Candidate,
    Job,
    OutreachEmail,
    Resume,
    Recruiter,
)
from app.enums import (
    AIProcessingState,
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
class RecruiterSummary:
    id: strawberry.ID
    name: str
    email: str

    @classmethod
    def from_model(cls, recruiter: Recruiter) -> "RecruiterSummary":
        return cls(
            id=strawberry.ID(str(recruiter.id)),
            name=recruiter.name,
            email=recruiter.email,
        )


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
    processing_state: AIProcessingState

    @classmethod
    def from_model(
        cls, resume: Resume, *, application_file_url: str | None = None
    ) -> "ResumeType":
        return cls(
            id=strawberry.ID(str(resume.id)),
            file_url=application_file_url or resume.file_url,
            processing_state=resume.processing_state,
        )


@strawberry.type
class EvaluationFindingType:
    summary: str
    evidence: list[str]


@strawberry.type
class EvaluationEvidenceType:
    claim: str
    resume_evidence: str
    category: str | None


@strawberry.type
class EvaluationCategoryScoreType:
    name: str
    score: Decimal
    weight: int
    weighted_score: Decimal
    rationale: str
    evidence: list[str]


@strawberry.type
class EvaluationType:
    id: strawberry.ID
    overall_score: Decimal
    recommendation: str
    confidence: EvaluationConfidence
    strengths: list[EvaluationFindingType]
    gaps: list[EvaluationFindingType]
    evidence: list[EvaluationEvidenceType]
    category_scores: list[EvaluationCategoryScoreType]
    processing_state: AIProcessingState

    @classmethod
    def from_model(cls, evaluation: AIEvaluation) -> "EvaluationType":
        analysis = (
            evaluation.analysis_json
            if isinstance(evaluation.analysis_json, dict)
            else {}
        )
        return cls(
            id=strawberry.ID(str(evaluation.id)),
            overall_score=evaluation.overall_score,
            recommendation=evaluation.recommendation,
            confidence=evaluation.confidence,
            strengths=cls._findings(evaluation.strengths),
            gaps=cls._findings(evaluation.gaps),
            evidence=cls._evidence(evaluation.evidence),
            category_scores=cls._category_scores(analysis.get("category_scores", [])),
            processing_state=AIProcessingState.COMPLETED,
        )

    @staticmethod
    def _findings(value: object) -> list[EvaluationFindingType]:
        if not isinstance(value, list):
            return []
        findings: list[EvaluationFindingType] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                findings.append(EvaluationFindingType(summary=item.strip(), evidence=[]))
            elif isinstance(item, dict) and str(item.get("summary", "")).strip():
                evidence = item.get("evidence", [])
                findings.append(
                    EvaluationFindingType(
                        summary=str(item["summary"]).strip(),
                        evidence=[str(entry) for entry in evidence]
                        if isinstance(evidence, list)
                        else [],
                    )
                )
        return findings

    @staticmethod
    def _evidence(value: object) -> list[EvaluationEvidenceType]:
        if not isinstance(value, list):
            return []
        evidence_items: list[EvaluationEvidenceType] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                evidence_items.append(
                    EvaluationEvidenceType(
                        claim=item.strip(),
                        resume_evidence=item.strip(),
                        category=None,
                    )
                )
            elif isinstance(item, dict):
                claim = str(item.get("claim", "")).strip()
                resume_evidence = str(item.get("resume_evidence", "")).strip()
                if claim and resume_evidence:
                    category = item.get("category")
                    evidence_items.append(
                        EvaluationEvidenceType(
                            claim=claim,
                            resume_evidence=resume_evidence,
                            category=str(category) if category else None,
                        )
                    )
        return evidence_items

    @staticmethod
    def _category_scores(value: object) -> list[EvaluationCategoryScoreType]:
        if not isinstance(value, list):
            return []
        scores: list[EvaluationCategoryScoreType] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            try:
                evidence = item.get("evidence", [])
                scores.append(
                    EvaluationCategoryScoreType(
                        name=str(item["name"]),
                        score=Decimal(str(item["score"])),
                        weight=int(item["weight"]),
                        weighted_score=Decimal(str(item["weighted_score"])),
                        rationale=str(item["rationale"]),
                        evidence=[str(entry) for entry in evidence]
                        if isinstance(evidence, list)
                        else [],
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return scores


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
class ApplicationNoteType:
    id: strawberry.ID
    content: str
    recruiter: RecruiterSummary | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, note: ApplicationNote) -> "ApplicationNoteType":
        recruiter = note.recruiter if note.recruiter_id is not None else None
        return cls(
            id=strawberry.ID(str(note.id)),
            content=note.content,
            recruiter=RecruiterSummary.from_model(recruiter) if recruiter else None,
            created_at=note.created_at,
            updated_at=note.updated_at,
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
    evaluation_processing_state: AIProcessingState
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
            evaluation_processing_state=application.evaluation_processing_state,
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
    evaluation_processing_state: AIProcessingState
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
            evaluation_processing_state=application.evaluation_processing_state,
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
    evaluation_processing_state: AIProcessingState
    resume_url: str | None
    cover_letter: str | None
    applied_at: datetime
    updated_at: datetime
    candidate: CandidateDetails
    job: ApplicationJobType
    resume: ResumeType | None
    evaluation: EvaluationType | None
    status_history: list[ApplicationStatusHistoryType]
    notes: list[ApplicationNoteType]
    outreach_emails: list[OutreachEmailType]

    @classmethod
    def from_models(
        cls,
        application: Application,
        resume: Resume | None,
        evaluation: AIEvaluation | None,
        status_history: list[ApplicationStatusHistory],
        notes: list[ApplicationNote],
        outreach_emails: list[OutreachEmail],
    ) -> "ApplicationDetailType":
        return cls(
            id=strawberry.ID(str(application.id)),
            candidate_id=strawberry.ID(str(application.candidate_id)),
            job_id=strawberry.ID(str(application.job_id)),
            status=application.status,
            fit_score=application.fit_score,
            evaluation_processing_state=application.evaluation_processing_state,
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
            notes=[ApplicationNoteType.from_model(item) for item in notes],
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
class RecommendedApplicationType:
    id: strawberry.ID
    status: ApplicationStatus
    fit_score: Decimal
    evaluation_processing_state: AIProcessingState
    applied_at: datetime

    @classmethod
    def from_model(cls, application: Application) -> "RecommendedApplicationType":
        return cls(
            id=strawberry.ID(str(application.id)),
            status=application.status,
            fit_score=application.fit_score or Decimal("0"),
            evaluation_processing_state=application.evaluation_processing_state,
            applied_at=application.applied_at,
        )


@strawberry.type
class RecommendedCandidateType:
    candidate: CandidateDetails
    application: RecommendedApplicationType
    evaluation: EvaluationType

    @classmethod
    def from_models(
        cls,
        application: Application,
        evaluation: AIEvaluation,
    ) -> "RecommendedCandidateType":
        return cls(
            candidate=CandidateDetails.from_model(application.candidate),
            application=RecommendedApplicationType.from_model(application),
            evaluation=EvaluationType.from_model(evaluation),
        )


@strawberry.type
class RecommendedCandidatesResult:
    success: bool
    items: list[RecommendedCandidateType]
    total_count: int
    limit: int
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


@strawberry.type
class ApplicationStatusUpdateFailure:
    application_id: strawberry.ID
    errors: list[OperationError]


@strawberry.type
class BulkUpdateApplicationStatusPayload:
    success: bool
    applications: list[ApplicationType]
    failures: list[ApplicationStatusUpdateFailure]
    errors: list[OperationError]


@strawberry.type
class AddApplicationNotePayload:
    success: bool
    note: ApplicationNoteType | None
    errors: list[OperationError]
