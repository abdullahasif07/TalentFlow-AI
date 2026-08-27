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
