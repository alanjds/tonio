from __future__ import annotations

import asyncio

from .exceptions import CancelledError, TimeoutError


class _Waiter:
    """Awaitable (colored API) and iterable via trampoline (pygen API)."""

    __slots__ = ['_asyncio_event', '_timeout_us', '_future']

    def __init__(self, asyncio_event: asyncio.Event, timeout_us: int | None):
        self._asyncio_event = asyncio_event
        self._timeout_us = timeout_us
        self._future: asyncio.Future | None = None

    def __await__(self):
        return self._wait().__await__()

    async def _wait(self):
        coro = self._asyncio_event.wait()
        if self._timeout_us is None:
            await coro
        else:
            try:
                await asyncio.wait_for(coro, timeout=self._timeout_us / 1_000_000)
            except asyncio.TimeoutError:
                pass

    def abort(self):
        pass

    def unwind(self):
        pass


class _CheckpointWaiter:
    """Waiter.checkpoint() — used by timeout() / select() for coroutine cancellation."""

    __slots__ = ['_future']

    def __init__(self):
        self._future: asyncio.Future | None = None

    def __await__(self):
        return self._wait().__await__()

    async def _wait(self):
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()
        try:
            await self._future
        except asyncio.CancelledError:
            raise CancelledError()

    def abort(self):
        if self._future and not self._future.done():
            self._future.cancel()

    def unwind(self):
        self.abort()


class Waiter:
    @staticmethod
    def checkpoint() -> _CheckpointWaiter:
        return _CheckpointWaiter()


class Event:
    """asyncio.Event-backed equivalent of the Rust Event."""

    __slots__ = ['_asyncio_event']

    def __init__(self):
        self._asyncio_event = asyncio.Event()

    def set(self):
        # Thread-safe: may be called from blocking thread pool workers.
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self._asyncio_event.set)
        except RuntimeError:
            self._asyncio_event.set()

    def clear(self):
        self._asyncio_event.clear()

    def is_set(self) -> bool:
        return self._asyncio_event.is_set()

    def waiter(self, timeout_us: int | None) -> _Waiter:
        return _Waiter(self._asyncio_event, timeout_us)

    def wait(self, timeout: int | float | None = None) -> _Waiter:
        timeout_us = round(max(0, timeout * 1_000_000)) if timeout is not None else None
        return self.waiter(timeout_us)


class Result:
    """Cross-coroutine value store (equivalent to the Rust Result type)."""

    __slots__ = ['_values']

    def __init__(self, size: int = 1):
        self._values: list = [None] * size

    def store(self, value, index: int | None = None):
        self._values[0 if index is None else index] = value

    def fetch(self):
        if len(self._values) == 1:
            return self._values[0]
        return list(self._values)
