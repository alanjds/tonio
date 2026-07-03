from __future__ import annotations

import asyncio

from ._events import Event


class _ImmediateWaiter:
    """Resolves synchronously (no yield point) so the task starts immediately.

    This mirrors the Rust Waiter::new_for_suspension() which resumes the
    coroutine on the same tick.  asyncio.Task cancellation is delivered at
    the first real await *inside* the spawned coroutine, not here.
    """

    def __await__(self):
        return self._run().__await__()

    async def _run(self):
        pass  # no yield — the Task's first real suspend is inside coro

    def abort(self):
        pass

    def unwind(self):
        pass


class _ScopeBase:
    __slots__ = [
        '_entered',
        '_exited',
        '_task_count',
        '_done_event',
        '_task_done_events',
        '_cancelled',
        '_asyncio_tasks',
    ]

    def __init__(self):
        self._entered = False
        self._exited = False
        self._task_count = 0
        self._done_event = Event()
        self._task_done_events: list = []
        self._cancelled = False
        self._asyncio_tasks: list[asyncio.Task] = []

    def _incr(self, val: int) -> bool:
        if val == 0:
            if self._entered:
                return False
            self._entered = True
            return True
        else:
            # Called by __exit__ / __aexit__ — mark scope as exited so post-exit
            # spawn() calls are no-ops (mirrors Rust behaviour).
            self._exited = True
            return True

    def _track(self, wrapper_fn):
        """Register a task wrapper and return the started coroutine."""
        if self._exited:
            return None
        self._task_count += 1
        scope_ref = self

        class _TaskDoneEvent(Event):
            def __init__(self):
                super().__init__()
                self._counted = False

            def set(self):
                super().set()
                if not self._counted:
                    self._counted = True
                    scope_ref._task_count -= 1
                    if scope_ref._task_count <= 0:
                        scope_ref._done_event.set()

        ev_done = _TaskDoneEvent()
        self._task_done_events.append(ev_done)
        return wrapper_fn(ev_done, _ImmediateWaiter())

    def _exit(self):
        """Return a waiter that resolves when all tracked tasks finish."""
        if self._cancelled:
            # Mirror Rust: mark unfinished tasks done so the scope can exit.
            # The asyncio tasks themselves are cancelled via Scope.cancel().
            for ev in self._task_done_events:
                if not ev._counted:
                    ev.set()
        if self._task_count <= 0:
            self._done_event.set()
        return self._done_event.waiter(None)

    def _register_task(self, task: asyncio.Task) -> None:
        """Track a spawned asyncio task so cancel() can reach it."""
        self._asyncio_tasks.append(task)
        if self._cancelled:
            # Scope already cancelled before this task started — cancel it,
            # deferred via call_soon so it gets one step to enter first (3.12+
            # delivers cancellation at the very first step otherwise).
            asyncio.get_running_loop().call_soon(task.cancel)

    def cancel(self) -> bool:
        if self._cancelled:
            return False
        self._cancelled = True
        for task in self._asyncio_tasks:
            if not task.done():
                task.cancel()
        return True


class PyGenScope(_ScopeBase):
    pass


class PyAsyncGenScope(_ScopeBase):
    pass
