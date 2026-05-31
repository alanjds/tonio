from __future__ import annotations

from ._events import Event


class _ScopeBase:
    """Base for PyGenScope and PyAsyncGenScope: tracks tasks, provides cancellation gate."""

    __slots__ = ['_entered', '_task_count', '_done_event', '_cancel_events']

    def __init__(self):
        self._entered = False
        self._task_count = 0
        self._done_event = Event()
        self._cancel_events: list[Event] = []

    def _incr(self, val: int) -> bool:
        if val == 0:
            # Called by __enter__ / __aenter__
            if self._entered:
                return False
            self._entered = True
            return True
        else:
            # Called by __exit__ / __aexit__ to signal the joiner
            self._task_count -= 1
            if self._task_count <= 0:
                self._done_event.set()
            return True

    def _track(self, wrapper_fn):
        """Register a task wrapper and return the started coroutine."""
        ev_done = Event()
        ev_cancel = Event()
        self._cancel_events.append(ev_cancel)
        self._task_count += 1

        # The wrapper receives (done_event, cancel_waiter)
        return wrapper_fn(ev_done, ev_cancel.waiter(None))

    def _exit(self):
        """Return a waiter that resolves when all tracked tasks finish."""
        if self._task_count <= 0:
            self._done_event.set()
        return self._done_event.waiter(None)

    def cancel(self) -> bool:
        for ev in self._cancel_events:
            if not ev.is_set():
                ev.set()
        return True


class PyGenScope(_ScopeBase):
    pass


class PyAsyncGenScope(_ScopeBase):
    pass
