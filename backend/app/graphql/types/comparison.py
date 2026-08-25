from __future__ import annotations

from decimal import Decimal

import strawberry

from app.enums import EvaluationConfidence
from app.graphql.types.application import EvaluationFindingType
from app.graphql.types.common import OperationError
from app.schemas import (
    CandidateComparison,
    CandidateTradeoffSummary,
    ComparisonCandidateSummary,
    CriteriaCandidateComparison,
    CriteriaComparison,
)


@strawberry.type
class ComparisonJobType:
    id: strawberry.ID
    title: str


@strawberry.type
class ComparedCandidateType:
    application_id: strawberry.ID
    candidate_id: strawberry.ID
    name: str
    overall_score: Decimal
    confidence: EvaluationConfidence
    recommendation: str
    strengths: list[EvaluationFindingType]
    gaps: list[EvaluationFindingType]

    @classmethod
    def from_schema(cls, candidate: ComparisonCandidateSummary) -> "ComparedCandidateType":
        return cls(
            application_id=strawberry.ID(str(candidate.application_id)),
            candidate_id=strawberry.ID(str(candidate.candidate_id)),
            name=candidate.candidate_name,
            overall_score=Decimal(str(candidate.overall_score)),
            confidence=candidate.confidence,
            recommendation=candidate.recommendation.value,
            strengths=[
                EvaluationFindingType(
                    summary=finding.summary,
                    evidence=finding.evidence,
                )
                for finding in candidate.strengths
            ],
            gaps=[
                EvaluationFindingType(
                    summary=finding.summary,
                    evidence=finding.evidence,
                )
                for finding in candidate.gaps
            ],
        )


@strawberry.type
class CandidateCategoryResultType:
    application_id: strawberry.ID
    available: bool
    score: Decimal | None
    summary: str

    @classmethod
    def from_schema(
        cls,
        candidate: CriteriaCandidateComparison,
    ) -> "CandidateCategoryResultType":
        return cls(
            application_id=strawberry.ID(str(candidate.application_id)),
            available=candidate.available,
            score=(
                Decimal(str(candidate.score))
                if candidate.score is not None
                else None
            ),
            summary=candidate.summary,
        )


@strawberry.type
class ComparisonCategoryType:
    name: str
    weight: int
    candidates: list[CandidateCategoryResultType]

    @classmethod
    def from_schema(cls, category: CriteriaComparison) -> "ComparisonCategoryType":
        return cls(
            name=category.category,
            weight=category.weight,
            candidates=[
                CandidateCategoryResultType.from_schema(candidate)
                for candidate in category.candidates
            ],
        )


@strawberry.type
class CandidateComparisonSummaryType:
    overview: str
    relative_strengths: list[str]
    tradeoffs: list[str]
    differentiating_experience: list[str]
    notable_gaps: list[str]
    comparable_areas: list[str]

    @classmethod
    def from_schema(
        cls,
        summary: CandidateTradeoffSummary,
    ) -> "CandidateComparisonSummaryType":
        return cls(
            overview=summary.overview,
            relative_strengths=summary.relative_strengths,
            tradeoffs=summary.tradeoffs,
            differentiating_experience=summary.differentiating_experience,
            notable_gaps=summary.notable_gaps,
            comparable_areas=summary.comparable_areas,
        )


@strawberry.type
class CandidateComparisonResult:
    success: bool
    job: ComparisonJobType | None
    candidates: list[ComparedCandidateType]
    categories: list[ComparisonCategoryType]
    summary: CandidateComparisonSummaryType | None
    errors: list[OperationError]

    @classmethod
    def success_result(cls, comparison: CandidateComparison) -> "CandidateComparisonResult":
        return cls(
            success=True,
            job=ComparisonJobType(
                id=strawberry.ID(str(comparison.job_id)),
                title=comparison.job_title,
            ),
            candidates=[
                ComparedCandidateType.from_schema(candidate)
                for candidate in comparison.candidates
            ],
            categories=[
                ComparisonCategoryType.from_schema(category)
                for category in comparison.criteria_comparison
            ],
            summary=CandidateComparisonSummaryType.from_schema(
                comparison.tradeoff_summary
            ),
            errors=[],
        )

    @classmethod
    def failure(cls, errors: list[OperationError]) -> "CandidateComparisonResult":
        return cls(
            success=False,
            job=None,
            candidates=[],
            categories=[],
            summary=None,
            errors=errors,
        )
