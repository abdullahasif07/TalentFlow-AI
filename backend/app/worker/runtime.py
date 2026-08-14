from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.db import close_db, init_db


ResultType = TypeVar("ResultType")


async def _run_with_database(
    operation: Callable[[], Awaitable[ResultType]],
) -> ResultType:
    initialized = False
    try:
        await init_db()
        initialized = True
        return await operation()
    finally:
        if initialized:
            await close_db()


def run_async_db_operation(
    operation: Callable[[], Awaitable[ResultType]],
) -> ResultType:
    """Run one worker operation in a fresh event loop and ORM lifecycle."""

    return asyncio.run(_run_with_database(operation))
