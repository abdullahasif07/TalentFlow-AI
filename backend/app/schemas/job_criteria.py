from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobCriteriaSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationCategory(JobCriteriaSchema):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1_000)
    weight: int = Field(gt=0, le=100)


class JobEvaluationCriteria(JobCriteriaSchema):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    minimum_experience_years: float | None = Field(default=None, ge=0, le=80)
    relevant_domains: list[str] = Field(default_factory=list)
    relevant_experience: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    important_responsibilities: list[str] = Field(default_factory=list)
    evaluation_categories: list[EvaluationCategory] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_rubric(self) -> "JobEvaluationCriteria":
        total_weight = sum(category.weight for category in self.evaluation_categories)
        if total_weight != 100:
            raise ValueError("evaluation category weights must total 100")

        required = {skill.strip().casefold() for skill in self.required_skills}
        preferred = {skill.strip().casefold() for skill in self.preferred_skills}
        overlap = (required & preferred) - {""}
        if overlap:
            raise ValueError(
                "required and preferred skills must remain distinct"
            )

        category_names = [
            category.name.strip().casefold()
            for category in self.evaluation_categories
        ]
        if len(category_names) != len(set(category_names)):
            raise ValueError("evaluation category names must be unique")
        return self
