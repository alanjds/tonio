from __future__ import annotations

import asyncio

from .exceptions import CancelledError


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

    __slots__ = ['_future', '_handle', '_task']

    def __init__(self):
        self._future: asyncio.Future | None = None
        self._handle = None
        self._task = None

    def __await__(self):
        return self._wait().__await__()

    async def _wait(self):
        loop = asyncio.get_running_loop()
        self._task = asyncio.current_task()
        self._future = loop.create_future()
        # Resolve after one tick so normal execution continues; guarded so
        # cancelling the future (via abort) doesn't crash the call_soon callback.
        self._handle = loop.call_soon(lambda: None if self._future.done() else self._future.set_result(None))
        try:
            await self._future
        except asyncio.CancelledError:
            raise CancelledError()

    def abort(self):
        if self._handle:
            self._handle.cancel()
            self._handle = None
        if self._future and not self._future.done():
            self._future.cancel()
        elif self._task is not None and not self._task.done():
            # Checkpoint already resolved — cancel the containing task so the
            # coroutine is cancelled wherever it is now (mirrors unwind()).
            self._task.cancel()

    def unwind(self):
        # Cancel the wrapper task regardless of whether the checkpoint has
        # already resolved (the coro may already be running past the checkpoint).
        if self._task is not None and not self._task.done():
            self._task.cancel()
        else:
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


class _IOWaiter(_Waiter):
    """Like _Waiter but calls remove_fn(fd) on cancellation to avoid WinError 10038."""

    __slots__ = ['_fd', '_remove_fn']

    def __init__(
        self,
        asyncio_event: asyncio.Event,
        timeout_us: int | None,
        fd: int,
        remove_fn,
    ):
        super().__init__(asyncio_event, timeout_us)
        self._fd = fd
        self._remove_fn = remove_fn

    async def _wait(self):
        try:
            coro = self._asyncio_event.wait()
            if self._timeout_us is None:
                await coro
            else:
                try:
                    await asyncio.wait_for(coro, timeout=self._timeout_us / 1_000_000)
                except asyncio.TimeoutError:
                    pass
        except BaseException:
            try:
                self._remove_fn(self._fd)
            except Exception:
                pass
            raise


class _IOEvent(Event):
    """Event backed by add_reader/add_writer; cleans up on cancellation."""

    __slots__ = ['_fd', '_remove_fn']

    def __init__(self, fd: int, remove_fn):
        super().__init__()
        self._fd = fd
        self._remove_fn = remove_fn

    def waiter(self, timeout_us: int | None) -> _IOWaiter:
        return _IOWaiter(self._asyncio_event, timeout_us, self._fd, self._remove_fn)


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
