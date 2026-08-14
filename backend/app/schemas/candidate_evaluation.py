from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import EvaluationConfidence


class CandidateEvaluationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequirementMatchStatus(str, Enum):
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    NOT_MET = "NOT_MET"


class EvaluationRecommendation(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    WEAK_MATCH = "WEAK_MATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvaluationFinding(CandidateEvaluationSchema):
    summary: str = Field(min_length=1, max_length=1_000)
    evidence: list[str] = Field(default_factory=list)


class RequirementAssessment(CandidateEvaluationSchema):
    requirement: str = Field(min_length=1, max_length=500)
    status: RequirementMatchStatus
    evidence: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def require_supported_conclusion(self) -> "RequirementAssessment":
        if (
            self.status != RequirementMatchStatus.MISSING_EVIDENCE
            and not (self.evidence or "").strip()
        ):
            raise ValueError(f"{self.status.value} requires resume evidence")
        return self


class EvaluationEvidence(CandidateEvaluationSchema):
    claim: str = Field(min_length=1, max_length=1_000)
    resume_evidence: str = Field(min_length=1, max_length=2_000)
    category: str | None = Field(default=None, max_length=100)


class LLMCategoryScore(CandidateEvaluationSchema):
    name: str = Field(min_length=1, max_length=100)
    score: float = Field(ge=0, le=100)
    rationale: str = Field(min_length=1, max_length=2_000)
    evidence: list[str] = Field(default_factory=list)


class CandidateEvaluationAnalysis(CandidateEvaluationSchema):
    """Structured facts returned by the LLM before deterministic aggregation."""

    confidence: EvaluationConfidence
    recommendation: EvaluationRecommendation
    strengths: list[EvaluationFinding] = Field(default_factory=list)
    gaps: list[EvaluationFinding] = Field(default_factory=list)
    matched_requirements: list[RequirementAssessment] = Field(default_factory=list)
    missing_requirements: list[RequirementAssessment] = Field(default_factory=list)
    category_scores: list[LLMCategoryScore] = Field(min_length=1)
    evidence: list[EvaluationEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_requirement_groups(self) -> "CandidateEvaluationAnalysis":
        matched_statuses = {
            RequirementMatchStatus.MATCH,
            RequirementMatchStatus.PARTIAL_MATCH,
        }
        missing_statuses = {
            RequirementMatchStatus.MISSING_EVIDENCE,
            RequirementMatchStatus.NOT_MET,
        }
        if any(item.status not in matched_statuses for item in self.matched_requirements):
            raise ValueError("matched requirements must use a match status")
        if any(item.status not in missing_statuses for item in self.missing_requirements):
            raise ValueError("missing requirements must use a missing status")

        matched = {
            item.requirement.strip().casefold() for item in self.matched_requirements
        }
        missing = {
            item.requirement.strip().casefold() for item in self.missing_requirements
        }
        if matched & missing:
            raise ValueError("a requirement cannot be both matched and missing")
        return self


class WeightedCategoryScore(CandidateEvaluationSchema):
    name: str
    score: float = Field(ge=0, le=100)
    weight: int = Field(gt=0, le=100)
    weighted_score: float = Field(ge=0, le=100)
    rationale: str
    evidence: list[str] = Field(default_factory=list)


class CandidateEvaluation(CandidateEvaluationSchema):
    overall_score: float = Field(ge=0, le=100)
    confidence: EvaluationConfidence
    recommendation: EvaluationRecommendation
    strengths: list[EvaluationFinding] = Field(default_factory=list)
    gaps: list[EvaluationFinding] = Field(default_factory=list)
    matched_requirements: list[RequirementAssessment] = Field(default_factory=list)
    missing_requirements: list[RequirementAssessment] = Field(default_factory=list)
    category_scores: list[WeightedCategoryScore] = Field(min_length=1)
    evidence: list[EvaluationEvidence] = Field(default_factory=list)
