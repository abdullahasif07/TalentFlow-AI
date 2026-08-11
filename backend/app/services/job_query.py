from tortoise.expressions import Q
from tortoise.functions import Count
from tortoise.queryset import QuerySet

from app.db.models import Job
from app.enums import ApplicationStatus


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
        )
