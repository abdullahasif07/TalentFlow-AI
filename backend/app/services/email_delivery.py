from __future__ import annotations

import logging
from typing import Protocol


logger = logging.getLogger(__name__)


class EmailDeliveryService(Protocol):
    """Replaceable boundary for external email delivery providers."""

    async def send(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None: ...


class SimulatedEmailDeliveryService:
    """MVP adapter that records delivery intent without contacting a provider."""

    async def send(
        self,
        *,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None:
        logger.info(
            "Simulated outreach delivery to %s with subject %r",
            recipient_email,
            subject,
        )
