"""Redis-backed rate limits, the daily AI budget, and a small JSON cache.

Rate limits and caching fail open (a Redis outage must not take the public form down).
The AI budget fails closed: if usage cannot be counted, no paid AI call is made.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar

from redis.asyncio import Redis

from app.config import settings
from app.services.errors import AIBudgetExceededError, AIBudgetUnavailableError


logger = logging.getLogger(__name__)
ResultType = TypeVar("ResultType")

# After a connection failure, skip Redis for a short time instead of paying for a
# connection attempt on every request.
_UNAVAILABLE_BACKOFF_SECONDS = 30.0
_unavailable_until = 0.0


class RedisUnavailableError(Exception):
    pass


async def _with_redis(operation: Callable[[Redis], Awaitable[ResultType]]) -> ResultType:
    global _unavailable_until
    if time.monotonic() < _unavailable_until:
        raise RedisUnavailableError("Redis was recently unavailable.")
    # A client per operation keeps this safe in Celery tasks, which each run in a new
    # event loop.
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=2,
        decode_responses=True,
    )
    try:
        return await operation(client)
    except Exception as exc:
        _unavailable_until = time.monotonic() + _UNAVAILABLE_BACKOFF_SECONDS
        raise RedisUnavailableError(str(exc)) from exc
    finally:
        try:
            await client.aclose()
        except Exception:
            pass


def _reset_availability_for_tests() -> None:
    global _unavailable_until
    _unavailable_until = 0.0


async def _increment_window(client: Redis, key: str, window_seconds: int) -> int:
    pipeline = client.pipeline()
    pipeline.incr(key)
    pipeline.expire(key, window_seconds, nx=True)
    count, _ = await pipeline.execute()
    return int(count)


async def hit_rate_limit(scope: str, identity: str, *, limit: int, window_seconds: int) -> bool:
    """Count one attempt; return True while the caller is within ``limit``."""

    if limit <= 0:
        return True
    window = int(time.time() // window_seconds)
    key = f"talentflow:rate:{scope}:{identity}:{window}"
    try:
        count = await _with_redis(lambda client: _increment_window(client, key, window_seconds))
    except RedisUnavailableError:
        logger.warning("Rate limiting skipped for %s because Redis is unavailable.", scope)
        return True
    return count <= limit


def _budget_key() -> str:
    return f"talentflow:ai-calls:{datetime.now(UTC).date().isoformat()}"


async def ai_calls_used_today() -> int | None:
    try:
        value = await _with_redis(lambda client: client.get(_budget_key()))
    except RedisUnavailableError:
        return None
    return int(value or 0)


async def ensure_ai_budget_available() -> None:
    """Raise before queueing AI work when today's budget is known to be spent."""

    limit = settings.ai_daily_call_limit
    if limit <= 0:
        return
    used = await ai_calls_used_today()
    # This check only improves the message shown before queueing. When usage cannot be
    # read it allows the request; reserve_ai_call still blocks the paid call itself.
    if used is not None and used >= limit:
        raise AIBudgetExceededError(
            "The daily AI usage limit for this demo has been reached. Please try again tomorrow."
        )


async def reserve_ai_call() -> None:
    """Count one paid AI request against today's budget, or raise if none remain."""

    limit = settings.ai_daily_call_limit
    if limit <= 0:
        return
    try:
        count = await _with_redis(
            lambda client: _increment_window(client, _budget_key(), 2 * 24 * 60 * 60)
        )
    except RedisUnavailableError as exc:
        raise AIBudgetUnavailableError(
            "AI usage tracking is unavailable, so AI processing is paused."
        ) from exc
    if count > limit:
        raise AIBudgetExceededError(
            "The daily AI usage limit for this demo has been reached. Please try again tomorrow."
        )


async def cache_get(key: str) -> str | None:
    try:
        return await _with_redis(lambda client: client.get(f"talentflow:cache:{key}"))
    except RedisUnavailableError:
        return None


async def cache_set(key: str, value: str, *, ttl_seconds: int) -> None:
    try:
        await _with_redis(
            lambda client: client.set(f"talentflow:cache:{key}", value, ex=ttl_seconds)
        )
    except RedisUnavailableError:
        logger.warning("Unable to cache %s because Redis is unavailable.", key)
