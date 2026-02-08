"""Retry helper with exponential backoff."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def async_retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    description: str | None = None,
) -> T:
    """Retry an async callable with exponential backoff.

    Args:
        func: Zero-arg async callable to invoke.
        retries: Number of retries before raising.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay between retries.
    """
    _ = description
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await func()
        except Exception as exc:  # pragma: no cover - exercised by callers
            last_error = exc
            if attempt >= retries:
                break
            delay = min(max_delay, base_delay * (2**attempt))
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error
