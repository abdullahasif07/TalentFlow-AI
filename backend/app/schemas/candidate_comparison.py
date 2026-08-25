from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import EvaluationConfidence
from app.schemas.candidate_evaluation import (
    EvaluationFinding,
    EvaluationRecommendation,
    WeightedCategoryScore,
)


ComparisonStatement = Annotated[str, Field(min_length=1, max_length=2_000)]

_HIRING_DECISION_PATTERNS = (
    re.compile(
        r"\b(?:should|must|recommend(?:s|ed|ing)?(?:\s+to)?)\s+(?:hire|reject)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:hire|hiring|reject|rejecting)\s+(?:candidate|application)\b",
        re.I,
    ),
)
_PROTECTED_ATTRIBUTE_PATTERN = re.compile(
    r"\b(?:age|gender|ethnicity|religion|marital status|photograph|photo|disability|"
    r"sexual orientation|pregnancy|nationality|medical condition|family status|"
    r"veteran status)\b",
    re.I,
)


class CandidateComparisonSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ComparisonCandidateSummary(CandidateComparisonSchema):
    application_id: int = Field(gt=0)
    candidate_id: int = Field(gt=0)
    candidate_name: str = Field(min_length=1, max_length=255)
    overall_score: float = Field(ge=0, le=100)
    confidence: EvaluationConfidence
    recommendation: EvaluationRecommendation
    strengths: list[EvaluationFinding] = Field(default_factory=list)
    gaps: list[EvaluationFinding] = Field(default_factory=list)
    category_scores: list[WeightedCategoryScore] = Field(min_length=1)


class CriteriaCandidateComparison(CandidateComparisonSchema):
    application_id: int = Field(gt=0)
    available: bool
    score: float | None = Field(default=None, ge=0, le=100)
    summary: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_availability(self) -> "CriteriaCandidateComparison":
        if self.available != (self.score is not None):
            raise ValueError("category availability must match score presence")
        return self


class CriteriaComparison(CandidateComparisonSchema):
    category: str = Field(min_length=1, max_length=100)
    weight: int = Field(gt=0, le=100)
    candidates: list[CriteriaCandidateComparison] = Field(min_length=2, max_length=5)


class CandidateTradeoffSummary(CandidateComparisonSchema):
    """Identity-independent narrative returned by the comparison LLM."""

    overview: ComparisonStatement
    relative_strengths: list[ComparisonStatement] = Field(default_factory=list, max_length=10)
    tradeoffs: list[ComparisonStatement] = Field(default_factory=list, max_length=10)
    differentiating_experience: list[ComparisonStatement] = Field(
        default_factory=list,
        max_length=10,
    )
    notable_gaps: list[ComparisonStatement] = Field(default_factory=list, max_length=10)
    comparable_areas: list[ComparisonStatement] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_decision_support_content(self) -> "CandidateTradeoffSummary":
        statements = [
            self.overview,
            *self.relative_strengths,
            *self.tradeoffs,
            *self.differentiating_experience,
            *self.notable_gaps,
            *self.comparable_areas,
        ]
        if len(statements) == 1:
            raise ValueError("comparison must contain at least one supporting insight")

        combined = "\n".join(statements)
        if any(pattern.search(combined) for pattern in _HIRING_DECISION_PATTERNS):
            raise ValueError("comparison must not make a hiring or rejection decision")
        if _PROTECTED_ATTRIBUTE_PATTERN.search(combined):
            raise ValueError("comparison must not discuss protected attributes")
        return self


class CandidateComparison(CandidateComparisonSchema):
    job_id: int = Field(gt=0)
    job_title: str = Field(min_length=1, max_length=255)
    candidates: list[ComparisonCandidateSummary] = Field(min_length=2, max_length=5)
    criteria_comparison: list[CriteriaComparison] = Field(min_length=1)
    tradeoff_summary: CandidateTradeoffSummary

    @model_validator(mode="after")
    def validate_application_alignment(self) -> "CandidateComparison":
        application_ids = [candidate.application_id for candidate in self.candidates]
        if len(application_ids) != len(set(application_ids)):
            raise ValueError("comparison applications must be unique")
        expected_ids = set(application_ids)
        for category in self.criteria_comparison:
            category_ids = [candidate.application_id for candidate in category.candidates]
            if len(category_ids) != len(set(category_ids)):
                raise ValueError("category comparison applications must be unique")
            if set(category_ids) != expected_ids:
                raise ValueError("every category must compare every selected application")
        return self
