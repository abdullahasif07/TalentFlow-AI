"""Private demo workspaces: each "Try the demo" visitor gets their own company copy.

A sandbox is a regular ``Company`` row flagged ``is_sandbox`` with its own demo
recruiter and a fresh copy of the demo dataset. Everything recruiters can see is
already scoped to their company, so sandboxes are isolated from each other without
any special-casing elsewhere. Seeded evaluations are precomputed, so creating one makes
no AI calls.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.db.models import Company, Recruiter
from app.demo.data import COMPANY, DEMO_RECRUITER
from app.demo.seed import delete_companies, populate_demo_data


logger = logging.getLogger(__name__)


def _sandbox_recruiter_email(tag: str) -> str:
    _, _, domain = settings.demo_recruiter_email.strip().casefold().partition("@")
    return f"demo+{tag}@{domain or 'example.com'}"


async def is_sandbox_recruiter(recruiter: Recruiter | None) -> bool:
    if recruiter is None or not recruiter.is_demo:
        return False
    return await Company.filter(id=recruiter.company_id, is_sandbox=True).exists()


async def _make_room_for_sandbox() -> None:
    """Keep the number of sandboxes under the cap by removing the oldest ones."""

    limit = max(settings.demo_sandbox_max_active, 1)
    excess = await Company.filter(is_sandbox=True).count() - limit + 1
    if excess <= 0:
        return
    oldest = (
        await Company.filter(is_sandbox=True)
        .order_by("created_at", "id")
        .limit(excess)
        .values_list("id", flat=True)
    )
    logger.info("Sandbox limit reached; removing %d oldest sandboxes.", len(oldest))
    await delete_companies(list(oldest))


async def create_demo_sandbox() -> Recruiter:
    """Create a private copy of the demo company and return its demo recruiter."""

    await _make_room_for_sandbox()
    tag = secrets.token_hex(4)
    company = await Company.create(
        name=COMPANY["name"],
        description=COMPANY["description"],
        website=COMPANY["website"],
        is_sandbox=True,
    )
    try:
        recruiter = await Recruiter.create(
            company=company,
            name=DEMO_RECRUITER["name"],
            email=_sandbox_recruiter_email(tag),
            role=DEMO_RECRUITER["role"],
            is_demo=True,
            password_hash=None,  # Reachable only through the session cookie.
        )
        await populate_demo_data(company, email_tag=tag)
    except Exception:
        await delete_companies([company.id])
        raise
    return recruiter


async def cleanup_expired_sandboxes() -> int:
    """Delete sandboxes older than DEMO_SANDBOX_TTL_HOURS. Returns how many."""

    cutoff = datetime.now(UTC) - timedelta(hours=settings.demo_sandbox_ttl_hours)
    expired = await Company.filter(is_sandbox=True, created_at__lt=cutoff).values_list(
        "id", flat=True
    )
    await delete_companies(list(expired))
    if expired:
        logger.info("Deleted %d expired demo sandboxes.", len(expired))
    return len(expired)
