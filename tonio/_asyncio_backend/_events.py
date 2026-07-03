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
        if self._asyncio_event.is_set():
            # The event is already set. The native Waiter always resumes a ready
            # waiter through the scheduler queue (one yield), never inline — so a
            # ready waiter still cedes control once. asyncio.Event.wait() returns
            # without suspending when already set, so yield explicitly to mirror
            # native; without this, yield_now() (set() + waiter) wouldn't yield.
            await asyncio.sleep(0)
            return
        if self._timeout_us is None:
            await self._asyncio_event.wait()
        else:
            try:
                await asyncio.wait_for(self._asyncio_event.wait(), timeout=self._timeout_us / 1_000_000)
            except asyncio.TimeoutError:
                pass

    def abort(self):
        pass

    def unwind(self):
        pass


class _CheckpointWaiter:
    """Waiter.checkpoint() — used by timeout() / select() for coroutine cancellation.

    Mirrors the native backend's ``Waiter::checkpoint()`` which creates a
    zero-events ``Waiter``.  On registration the native code checks an
    ``aborted`` atomic flag and, if set, immediately throws ``CancelledError``
    into the coroutine.  This class uses an ``_aborted`` flag checked at
    ``__await__`` entry to achieve the same effect.
    """

    __slots__ = ['_aborted', '_fut', '_handle', '_task']

    def __init__(self):
        self._aborted = False
        self._fut: asyncio.Future | None = None
        self._handle: asyncio.Handle | None = None
        self._task: asyncio.Task | None = None

    def __await__(self):
        if self._aborted:
            raise CancelledError()
        self._task = asyncio.current_task()
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._fut = fut
        # Resolve after one tick so normal execution continues; guarded so
        # cancelling the future (via abort) doesn't crash the call_soon callback.
        self._handle = loop.call_soon(lambda: None if fut.done() else fut.set_result(None))
        try:
            return fut.__await__()
        except asyncio.CancelledError:
            raise CancelledError()

    def abort(self):
        """Mark as aborted and cancel the future if the await has started.

        If the checkpoint already resolved (future is done), cancel the
        containing task instead so the coroutine is cancelled wherever it
        is now — mirroring the native backend's ``unwind()`` behaviour.
        """
        self._aborted = True
        if self._handle is not None:
            self._handle.cancel()
            self._handle = None
        if self._fut is not None and not self._fut.done():
            self._fut.cancel()
        elif self._task is not None and not self._task.done():
            self._task.cancel()

    def unwind(self):
        """Cancel the containing task regardless of whether the checkpoint
        has already resolved (the coroutine may already be running past it).

        We keep a reference to the task captured at ``__await__`` time because
        by the time ``unwind()`` is called (e.g. from a scope exit) the current
        running task may be different.
        """
        self.abort()
        if self._task is not None and not self._task.done():
            self._task.cancel()


class Waiter:
    @staticmethod
    def checkpoint() -> _CheckpointWaiter:
        return _CheckpointWaiter()


class Event:
    """asyncio.Event-backed equivalent of the Rust Event."""

    __slots__ = ['_asyncio_event', '_loop']

    def __init__(self):
        self._asyncio_event = asyncio.Event()
        # Capture the running loop so an off-thread set() (e.g. from a blocking
        # pool worker) can hand the actual set to the loop thread. May be None
        # if the Event is constructed before a loop is running.
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    def set(self):
        # The native Event is level-triggered and set() is synchronous: once
        # set, is_set() is immediately True and a following clear() wins. When
        # we are already on the loop thread (the overwhelmingly common case:
        # every set() originates from a coroutine or a loop I/O callback) set
        # synchronously to preserve those semantics. Only when called from a
        # foreign thread — where asyncio primitives are not thread-safe — do we
        # defer the set onto the loop via call_soon_threadsafe.
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._asyncio_event.set)
                return
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
