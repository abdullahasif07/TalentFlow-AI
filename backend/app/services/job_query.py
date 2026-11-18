from tortoise.expressions import Q
from tortoise.functions import Count
from tortoise.queryset import QuerySet

from app.db.models import Job
from app.enums import AIProcessingState, ApplicationStatus, JobStatus


class RecruiterJobQueryService:
    @staticmethod
    def with_statistics(query: QuerySet[Job]) -> QuerySet[Job]:
        return query.annotate(
            applicant_count=Count("applications", distinct=True),
            shortlisted_count=Count(
                "applications",
                distinct=True,
                _filter=Q(applications__status=ApplicationStatus.SHORTLISTED),
            ),
            contacted_count=Count(
                "applications",
                distinct=True,
                _filter=Q(applications__status=ApplicationStatus.CONTACTED),
            ),
            interview_count=Count(
                "applications",
                distinct=True,
                _filter=Q(applications__status=ApplicationStatus.INTERVIEW),
            ),
            hired_count=Count(
                "applications",
                distinct=True,
                _filter=Q(applications__status=ApplicationStatus.HIRED),
            ),
            recommended_candidate_count=Count(
                "applications__ai_evaluation",
                distinct=True,
                _filter=Q(
                    applications__evaluation_processing_state=(
                        AIProcessingState.COMPLETED
                    )
                ),
            ),
        )


class PublicJobQueryService:
    """Load only jobs that are currently available to public applicants."""

    @staticmethod
    async def get_open_job(job_id: int) -> Job | None:
        return await Job.filter(id=job_id, status=JobStatus.OPEN).select_related(
            "company"
        ).first()

    @staticmethod
    async def list_open_jobs(limit: int = 20, *, sandbox_company_id: int | None = None) -> list[Job]:
        """Open roles of real companies, or of one demo sandbox when its visitor asks.

        Sandbox roles are hidden from everyone else so the landing page never lists
        other visitors' copies or the jobs they created.
        """

        query = Job.filter(status=JobStatus.OPEN)
        if sandbox_company_id is not None:
            query = query.filter(company_id=sandbox_company_id)
        else:
            query = query.filter(company__is_sandbox=False)
        return await query.select_related("company").order_by("-created_at").limit(limit)
