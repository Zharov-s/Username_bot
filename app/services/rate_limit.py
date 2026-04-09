from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message


class InMemoryRateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self.window_seconds = 60.0
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def allow(self, key: int) -> tuple[bool, int]:
        async with self._locks[key]:
            now = monotonic()
            bucket = self._events[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()

            if len(bucket) >= self.limit_per_minute:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)
            return True, 0


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limiter: InMemoryRateLimiter) -> None:
        super().__init__()
        self.limiter = limiter

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        allowed, retry_after = await self.limiter.allow(event.from_user.id)
        if not allowed:
            await event.answer(
                f"Слишком много запросов. Подождите примерно {retry_after} сек. и попробуйте снова."
            )
            return None

        return await handler(event, data)
