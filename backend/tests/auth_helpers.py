"""Run GraphQL operations as a signed-in recruiter in tests."""

from __future__ import annotations

from typing import Any

from app.db.models import Company, Recruiter
from app.graphql.context import GraphQLContext
from app.graphql.schema import schema


async def default_recruiter(company: Company | None = None) -> Recruiter:
    if company is None:
        company = await Company.all().order_by("id").first()
        if company is None:
            company = await Company.create(name="Test Recruiting Company")
    recruiter = await Recruiter.filter(company=company).order_by("id").first()
    if recruiter is None:
        recruiter = await Recruiter.create(
            company=company,
            name="Test Recruiter",
            email=f"test-recruiter-{company.id}@example.com",
            role="Recruiter",
            password_hash="test-only",
        )
    return recruiter


async def execute_as_recruiter(
    *args: Any,
    recruiter: Recruiter | None = None,
    **kwargs: Any,
):
    recruiter = recruiter or await default_recruiter()
    return await schema.execute(
        *args, context_value=GraphQLContext(recruiter=recruiter, client_ip="127.0.0.1"), **kwargs
    )


def isolate_from_redis(test_case) -> None:
    """Make Redis look unavailable so tests never read or write a developer's real Redis.

    Rate limits and the comparison cache then allow everything, and paid AI calls stay
    blocked, which matches the behaviour the tests were written against.
    """

    from unittest.mock import patch

    from app.services import usage_guard

    async def unavailable(operation):
        raise usage_guard.RedisUnavailableError("Redis is disabled in tests.")

    patcher = patch.object(usage_guard, "_with_redis", new=unavailable)
    patcher.start()
    test_case.addCleanup(patcher.stop)
