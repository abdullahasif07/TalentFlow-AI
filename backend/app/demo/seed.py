"""Create demo accounts and data, and reset the demo to a known state."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from tortoise.transactions import in_transaction

from app.config import settings
from app.db.models import (
    AIEvaluation,
    Application,
    ApplicationNote,
    ApplicationStatusHistory,
    Candidate,
    Company,
    Job,
    OutreachEmail,
    Recruiter,
    Resume,
)
from app.demo.data import CANDIDATES, COMPANY, DEMO_RECRUITER, JOBS, DemoCandidate, DemoJob
from app.enums import AIProcessingState, ApplicationStatus, OutreachStatus
from app.schemas import (
    CandidateEvaluation,
    JobEvaluationCriteria,
    ParsedResume,
)
from app.schemas.candidate_evaluation import (
    EvaluationEvidence,
    EvaluationFinding,
    EvaluationRecommendation,
    RequirementAssessment,
    RequirementMatchStatus,
    WeightedCategoryScore,
)
from app.services.resume_storage import ResumeStorageService, ValidatedResumeFile
from app.services.security import hash_password
from app.utils.pdf import build_text_pdf


logger = logging.getLogger(__name__)
AI_ACTOR = "TalentFlow AI screening"


@dataclass(frozen=True)
class SeedSummary:
    created: bool
    jobs: int = 0
    applications: int = 0
    evaluated: int = 0

    def describe(self) -> str:
        if not self.created:
            return "Demo data already present; no records were added."
        return (
            f"Created {self.jobs} jobs and {self.applications} applications "
            f"({self.evaluated} with AI evaluations)."
        )


# --- Accounts -------------------------------------------------------------------------------


async def ensure_company() -> Company:
    company, _ = await Company.get_or_create(
        name=COMPANY["name"],
        defaults={"description": COMPANY["description"], "website": COMPANY["website"]},
    )
    return company


async def ensure_accounts(company: Company) -> list[str]:
    """Create or update the demo and admin logins. Returns a line per account."""

    lines: list[str] = []
    if settings.demo_mode:
        email = settings.demo_recruiter_email.strip().casefold()
        await Recruiter.update_or_create(
            email=email,
            defaults={
                "company": company,
                "name": DEMO_RECRUITER["name"],
                "role": DEMO_RECRUITER["role"],
                "is_demo": True,
                "password_hash": hash_password(
                    settings.demo_recruiter_password.get_secret_value()
                ),
            },
        )
        lines.append(f"Demo recruiter: {email} (one-click demo login is enabled)")

    if settings.admin_email and settings.admin_password:
        email = settings.admin_email.strip().casefold()
        await Recruiter.update_or_create(
            email=email,
            defaults={
                "company": company,
                "name": "Admin",
                "role": "Hiring Manager",
                "is_demo": False,
                "password_hash": hash_password(settings.admin_password.get_secret_value()),
            },
        )
        lines.append(f"Admin recruiter: {email} (password from ADMIN_PASSWORD)")
    elif not settings.demo_mode:
        lines.append("No login was created: set ADMIN_EMAIL and ADMIN_PASSWORD, or DEMO_MODE=true.")
    return lines


async def _note_author(company: Company) -> Recruiter | None:
    return (
        await Recruiter.filter(company=company, is_demo=True).first()
        or await Recruiter.filter(company=company).first()
    )


# --- Builders -------------------------------------------------------------------------------


def build_criteria(job: DemoJob) -> JobEvaluationCriteria:
    return JobEvaluationCriteria.model_validate(
        {
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "minimum_experience_years": job.minimum_years,
            "relevant_domains": job.domains,
            "relevant_experience": [job.experience_requirement],
            "education_requirements": [],
            "important_responsibilities": job.responsibilities,
            "evaluation_categories": [
                {"name": name, "description": description, "weight": weight}
                for name, description, weight in job.categories
            ],
        }
    )


def build_parsed_resume(candidate: DemoCandidate) -> ParsedResume:
    technologies: list[str] = []
    for role in candidate.roles:
        for technology in role.technologies:
            if technology not in technologies:
                technologies.append(technology)
    institution, degree, field_of_study = candidate.education
    return ParsedResume.model_validate(
        {
            "professional_summary": candidate.headline,
            "skills": candidate.skills,
            "technologies": technologies,
            "total_experience_years": candidate.years,
            "employment_history": [
                {
                    "company": role.company,
                    "role": role.title,
                    "start_date": role.start,
                    "end_date": role.end,
                    "description": role.summary,
                    "technologies": role.technologies,
                }
                for role in candidate.roles
            ],
            "education": [
                {"institution": institution, "degree": degree, "field": field_of_study}
            ],
            "projects": [
                {"name": name, "description": description, "technologies": []}
                for name, description in candidate.projects
            ],
        }
    )


def resume_lines(candidate: DemoCandidate) -> list[str]:
    institution, degree, field_of_study = candidate.education
    lines = [
        f"# {candidate.name}",
        f"{candidate.email} | {candidate.phone} | linkedin.com/in/{candidate.handle}",
        "",
        "# Summary",
        f"{candidate.headline} {candidate.years:g} years of professional experience.",
        "",
        "# Experience",
    ]
    for role in candidate.roles:
        lines += [f"{role.title}, {role.company} ({role.start} - {role.end})", role.summary]
        if role.technologies:
            lines.append(f"Technologies: {', '.join(role.technologies)}")
        lines.append("")
    lines += ["# Skills", ", ".join(candidate.skills), "", "# Education"]
    lines.append(f"{degree} in {field_of_study}, {institution}")
    if candidate.projects:
        lines += ["", "# Projects"]
        lines += [f"{name}: {description}" for name, description in candidate.projects]
    return lines


def _recommendation(score: Decimal) -> EvaluationRecommendation:
    if score >= 85:
        return EvaluationRecommendation.STRONG_MATCH
    if score >= 70:
        return EvaluationRecommendation.GOOD_MATCH
    if score >= 50:
        return EvaluationRecommendation.PARTIAL_MATCH
    return EvaluationRecommendation.WEAK_MATCH


def build_evaluation(candidate: DemoCandidate, job: DemoJob) -> CandidateEvaluation | None:
    if candidate.category_scores is None:
        return None
    if len(candidate.category_scores) != len(job.categories):
        raise ValueError(f"{candidate.name} must score every category of {job.title}.")

    first_evidence = candidate.roles[0].summary.split(";")[0].strip()
    categories: list[WeightedCategoryScore] = []
    total = Decimal("0")
    for (name, _, weight), (score, rationale) in zip(job.categories, candidate.category_scores):
        weighted = (Decimal(score) * Decimal(weight) / Decimal(100)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total += weighted
        categories.append(
            WeightedCategoryScore(
                name=name,
                score=float(score),
                weight=weight,
                weighted_score=float(weighted),
                rationale=rationale,
                evidence=[first_evidence],
            )
        )

    skills = {skill.casefold() for skill in candidate.skills}
    matched: list[RequirementAssessment] = []
    missing: list[RequirementAssessment] = []
    for requirement in job.required_skills + job.preferred_skills:
        if requirement.casefold() in skills:
            matched.append(
                RequirementAssessment(
                    requirement=requirement,
                    status=RequirementMatchStatus.MATCH,
                    evidence=f"Lists {requirement} under skills.",
                )
            )
        else:
            missing.append(
                RequirementAssessment(
                    requirement=requirement,
                    status=RequirementMatchStatus.MISSING_EVIDENCE,
                    evidence=None,
                )
            )

    return CandidateEvaluation(
        overall_score=float(total),
        confidence=candidate.confidence,
        recommendation=_recommendation(total),
        strengths=[
            EvaluationFinding(summary=item.summary, evidence=[item.evidence])
            for item in candidate.strengths
        ],
        gaps=[
            EvaluationFinding(summary=item.summary, evidence=[item.evidence])
            for item in candidate.gaps
        ],
        matched_requirements=matched,
        missing_requirements=missing,
        category_scores=categories,
        evidence=[
            EvaluationEvidence(claim=item.summary, resume_evidence=item.evidence)
            for item in candidate.strengths
        ],
    )


# --- Population -----------------------------------------------------------------------------


async def populate_demo_data(company: Company) -> SeedSummary:
    """Insert the demo jobs and applicants once; later runs leave existing data alone."""

    if await Job.exists(company=company):
        return SeedSummary(created=False)

    storage = ResumeStorageService()
    author = await _note_author(company)
    now = datetime.now(UTC)
    jobs_by_key: dict[str, Job] = {}
    evaluated = 0

    async with in_transaction():
        for index, demo_job in enumerate(JOBS):
            jobs_by_key[demo_job.key] = await Job.create(
                company=company,
                title=demo_job.title,
                description=demo_job.description,
                required_skills=demo_job.required_skills,
                preferred_skills=demo_job.preferred_skills,
                experience_requirement=demo_job.experience_requirement,
                evaluation_criteria=build_criteria(demo_job).model_dump(mode="json"),
                criteria_processing_state=AIProcessingState.COMPLETED,
                status=demo_job.status,
                created_at=now - timedelta(days=30 - index * 3),
            )

        for demo_candidate in CANDIDATES:
            demo_job = next(job for job in JOBS if job.key == demo_candidate.job_key)
            job = jobs_by_key[demo_job.key]
            is_designer = demo_candidate.job_key == "design"
            candidate = await Candidate.create(
                name=demo_candidate.name,
                email=demo_candidate.email,
                phone=demo_candidate.phone,
                linkedin_url=f"https://linkedin.com/in/{demo_candidate.handle}",
                github_url=None if is_designer else f"https://github.com/{demo_candidate.handle}",
                portfolio_url=f"https://{demo_candidate.handle}.example.com" if is_designer else None,
            )

            lines = resume_lines(demo_candidate)
            stored_path = await storage.store(
                candidate.id,
                ValidatedResumeFile(
                    filename=f"{demo_candidate.handle}-resume.pdf",
                    content=build_text_pdf(lines),
                ),
            )
            await Resume.create(
                candidate=candidate,
                file_url=stored_path,
                raw_text="\n".join(line.removeprefix("# ") for line in lines),
                parsed_data=build_parsed_resume(demo_candidate).model_dump(mode="json"),
                processing_state=AIProcessingState.COMPLETED,
            )

            evaluation = build_evaluation(demo_candidate, demo_job)
            applied_at = now - timedelta(days=demo_candidate.days_ago, hours=3)
            final_status = (
                demo_candidate.status_path[-1]
                if demo_candidate.status_path
                else ApplicationStatus.APPLIED
            )
            score = (
                Decimal(str(evaluation.overall_score)).quantize(Decimal("0.01"))
                if evaluation
                else None
            )
            application = await Application.create(
                candidate=candidate,
                job=job,
                resume_url=stored_path,
                cover_letter=demo_candidate.cover_letter
                or f"I'm excited to apply for the {job.title} role at {company.name}.",
                status=final_status,
                fit_score=score,
                evaluation_processing_state=(
                    AIProcessingState.COMPLETED if evaluation else AIProcessingState.NOT_STARTED
                ),
                applied_at=applied_at,
            )

            if evaluation is not None:
                evaluated += 1
                serialized = evaluation.model_dump(mode="json")
                await AIEvaluation.create(
                    application=application,
                    overall_score=score,
                    recommendation=evaluation.recommendation.value,
                    confidence=evaluation.confidence,
                    strengths=serialized["strengths"],
                    gaps=serialized["gaps"],
                    evidence=serialized["evidence"],
                    analysis_json=serialized,
                )

            await _create_history(
                application, demo_candidate, applied_at, author_email=author.email if author else None
            )
            for offset, content in enumerate(demo_candidate.notes):
                await ApplicationNote.create(
                    application=application,
                    recruiter=author,
                    content=content,
                    created_at=applied_at + timedelta(days=1 + offset, hours=2),
                )
            if demo_candidate.outreach:
                subject, body = demo_candidate.outreach
                sent_at = applied_at + timedelta(days=2)
                await OutreachEmail.create(
                    application=application,
                    subject=subject,
                    body=body,
                    status=OutreachStatus.SENT,
                    generated_at=sent_at - timedelta(minutes=20),
                    approved_at=sent_at - timedelta(minutes=5),
                    sent_at=sent_at,
                )

    return SeedSummary(
        created=True, jobs=len(JOBS), applications=len(CANDIDATES), evaluated=evaluated
    )


async def _create_history(
    application: Application,
    demo_candidate: DemoCandidate,
    applied_at: datetime,
    *,
    author_email: str | None,
) -> None:
    await ApplicationStatusHistory.create(
        application=application,
        previous_status=None,
        new_status=ApplicationStatus.APPLIED,
        changed_by=demo_candidate.email,
        created_at=applied_at,
    )
    previous = ApplicationStatus.APPLIED
    steps = demo_candidate.status_path
    # Spread the transitions across the time since the application arrived.
    span_hours = max(demo_candidate.days_ago * 24 - 6, len(steps))
    for step_number, status in enumerate(steps, start=1):
        changed_at = applied_at + timedelta(hours=span_hours * step_number / (len(steps) + 1))
        actor = AI_ACTOR if status == ApplicationStatus.AI_REVIEWED else (author_email or "recruiter")
        await ApplicationStatusHistory.create(
            application=application,
            previous_status=previous,
            new_status=status,
            changed_by=actor,
            created_at=changed_at,
        )
        previous = status


# --- Reset ----------------------------------------------------------------------------------


async def reset_demo_data() -> SeedSummary:
    """Delete every applicant and the demo company's jobs, then seed fresh demo data.

    Candidates are not company-scoped, so this clears all applicants. It is meant for
    the dedicated demo database only, which is why it requires DEMO_MODE.
    """

    if not settings.demo_mode:
        raise RuntimeError("Demo reset is only available when DEMO_MODE is enabled.")

    company = await ensure_company()
    async with in_transaction():
        await Candidate.all().delete()  # Cascades to applications, resumes, notes, history.
        await Job.filter(company=company).delete()

    resumes_dir = ResumeStorageService().upload_root / "resumes"
    if resumes_dir.exists():
        shutil.rmtree(resumes_dir)

    await ensure_accounts(company)
    summary = await populate_demo_data(company)
    logger.info("Demo data reset: %s", summary.describe())
    return summary
