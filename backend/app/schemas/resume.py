from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResumeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmploymentHistoryEntry(ResumeSchema):
    company: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class Education(ResumeSchema):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class Project(ResumeSchema):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None


class Certification(ResumeSchema):
    name: str | None = None
    issuer: str | None = None
    date: str | None = None


class ParsedResume(ResumeSchema):
    professional_summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    total_experience_years: float | None = Field(default=None, ge=0, le=80)
    employment_history: list[EmploymentHistoryEntry] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    normalization_notes: list[str] = Field(default_factory=list)
