from __future__ import annotations

import asyncio
import concurrent.futures
import contextvars
import ctypes
import inspect
import multiprocessing
import sys
import threading
import time as _time_mod

from ._events import Event, Result
from ._trampoline import drive_generator
from .exceptions import CancelledError, RuntimeNotInitializedError


_current_runtime: Runtime | None = None


def get_runtime() -> Runtime:
    if _current_runtime is None:
        raise RuntimeNotInitializedError('no runtime is active')
    return _current_runtime


def set_runtime(rt: Runtime | None):
    global _current_runtime
    _current_runtime = rt


# Set up the ctypes binding for PyThreadState_SetAsyncExc once at module level.
_PyThreadState_SetAsyncExc = ctypes.pythonapi.PyThreadState_SetAsyncExc
_PyThreadState_SetAsyncExc.argtypes = [ctypes.c_ulong, ctypes.py_object]
_PyThreadState_SetAsyncExc.restype = ctypes.c_int


def _async_raise(tid: int, exc_type: type[BaseException]) -> None:
    """Best-effort injection of *exc_type* into the thread identified by *tid*.

    Mirrors the native backend's ``BlockingTaskCtl::abort()`` which calls
    ``PyThreadState_SetAsyncExc`` through the PyO3 FFI.  This is inherently
    best-effort:

    * If the thread is blocked in a C call that does not check pending calls
      (e.g. deep inside a native extension) the exception will be queued but
      never delivered.
    * If the thread ID has already been recycled the call silently returns 0.
    * On success (return == 1) the exception will be raised at the next
      bytecode boundary, GIL re-acquisition, or pending-call check.
    """
    ret = _PyThreadState_SetAsyncExc(ctypes.c_ulong(tid), exc_type)
    if ret != 1:
        # An error occurred (0 = thread not found, >1 = unexpected state).
        # Clean up by clearing any spurious injected exceptions.
        if ret > 1:
            _PyThreadState_SetAsyncExc(ctypes.c_ulong(tid), None)


class BlockingTaskCtl:
    __slots__ = ['_task', '_thread_id']

    def __init__(self, task: asyncio.Task | None):
        self._task = task
        self._thread_id: int | None = None

    def _set_tid(self, tid: int) -> None:
        """Store the native thread ID (called from the executor thread)."""
        self._thread_id = tid

    def abort(self):
        # Best-effort: inject CancelledError into the blocking thread, just
        # like the native backend does via PyThreadState_SetAsyncExc.
        if self._thread_id is not None:
            _async_raise(self._thread_id, CancelledError)
        # Cancel the asyncio wrapper task so the caller is unblocked quickly.
        if self._task is not None:
            self._task.cancel()


class Runtime:
    """asyncio-backed runtime for Windows (tier-2 support)."""

    def __init__(
        self,
        threads: int,
        threads_blocking: int,
        threads_blocking_timeout: int,
        context: bool,
        signals: list[int],
    ):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=threads_blocking)
        self._stopping = False
        self._ssock_r = None
        self._ssock_w = None
        self._sig_listening = False
        self._sigset = signals
        self._sig_wfd = -1
        self._epoch = _time_mod.monotonic()
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def _clock(self) -> int:
        return round((_time_mod.monotonic() - self._epoch) * 1_000_000)

    def _spawn_pyasyncgen(self, coro) -> asyncio.Task | None:
        try:
            return asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            # Called from a non-async thread (e.g. block_on from a ThreadPoolExecutor worker)
            asyncio.run_coroutine_threadsafe(coro, self._loop)
            return None

    def _spawn_pygen(self, gen) -> asyncio.Task | None:
        coro = drive_generator(gen)
        try:
            return asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
            return None

    def _spawn_blocking(self, fn, *args, **kwargs) -> tuple[BlockingTaskCtl, Event, Result]:
        event = Event()
        # Use size=2 to match the native backend ABI: index 0 = err flag, index 1 = value.
        # This ensures res.fetch() always returns a 2-element list [err_flag, value],
        # even on timeout (returns [None, None]), which _ctl.py's unpacking expects.
        result = Result(size=2)

        # Capture the caller's context and run fn inside it on the executor
        # thread. The native backend propagates context in Rust; the asyncio
        # backend is self-contained here so no shared code has to change.
        ctx = contextvars.copy_context()

        # Create the ctl before the task so the executor thread can store its
        # native thread ID into it via _set_tid().
        ctl = BlockingTaskCtl(task=None)

        async def _run():
            loop = asyncio.get_running_loop()
            try:
                # Wrap the function to capture the executor thread's native ID
                # before running the actual payload.  This gives abort() the
                # same best-effort thread-kill capability as the native backend.
                def _wrapper():
                    ctl._set_tid(threading.get_ident())
                    return ctx.run(fn, *args, **kwargs)

                val = await loop.run_in_executor(self._executor, _wrapper)
                result.store(False, 0)
                result.store(val, 1)
            except Exception as e:
                result.store(True, 0)
                result.store(e, 1)
            finally:
                event.set()

        try:
            task = asyncio.get_running_loop().create_task(_run())
            ctl._task = task
        except RuntimeError:
            # Called from a non-async thread (e.g. block_on from a ThreadPoolExecutor worker)
            loop = self._loop
            if loop is not None:
                asyncio.run_coroutine_threadsafe(_run(), loop)
            # ctl._task stays None in this case (no asyncio task to cancel)

        return ctl, event, result

    def _io_event_r(self, fd: int) -> Event:
        from ._events import _IOEvent

        loop = asyncio.get_running_loop()
        self._check_fd_socket(fd, loop)
        event = _IOEvent(fd, loop.remove_reader)

        def _fire():
            loop.remove_reader(fd)
            event.set()

        loop.add_reader(fd, _fire)
        return event

    def _io_event_w(self, fd: int) -> Event:
        from ._events import _IOEvent

        loop = asyncio.get_running_loop()
        self._check_fd_socket(fd, loop)
        event = _IOEvent(fd, loop.remove_writer)

        def _fire():
            loop.remove_writer(fd)
            event.set()

        loop.add_writer(fd, _fire)
        return event

    @staticmethod
    def _check_fd_socket(fd: int, loop: asyncio.AbstractEventLoop) -> None:
        """Raise a clear error if *fd* is not a socket on Windows.

        ``asyncio.SelectorEventLoop`` (used on Windows) relies on ``select()``
        which only accepts socket handles.  Pipes, files and console handles
        will fail with an opaque ``ValueError`` or ``OSError`` at registration
        time; this check gives the user a much clearer message upfront.
        """
        if sys.platform != 'win32':
            return
        try:
            import select as _select

            _select.select([fd], [], [], 0)
        except (ValueError, OSError) as exc:
            raise RuntimeError(
                f'asyncio backend only supports TCP socket FDs on Windows; FD {fd} is not a socket ({exc})'
            ) from exc

    def _sig_add(self, sig: int) -> Event:
        raise NotImplementedError('Signal handling is not available on the asyncio backend')

    def _sig_rem(self, sig: int) -> bool:
        return False

    def stop(self):
        self._stopping = True
        self._executor.shutdown(wait=False)

    def run_pygen_until_complete(self, coro):
        return self._run(drive_generator(coro))

    def run_pyasyncgen_until_complete(self, coro):
        return self._run(coro)

    def run_until_complete(self, coro):
        if inspect.iscoroutine(coro):
            return self.run_pyasyncgen_until_complete(coro)
        return self.run_pygen_until_complete(coro)

    def _run(self, main_coro):
        async def _setup_and_run():
            self._loop = asyncio.get_running_loop()
            set_runtime(self)
            try:
                return await main_coro
            finally:
                set_runtime(None)

        if sys.platform == 'win32':
            return asyncio.run(_setup_and_run(), loop_factory=asyncio.SelectorEventLoop)

        return asyncio.run(_setup_and_run())


def new(
    context: bool = False,
    signals: list[int] | None = None,
    threads: int | None = None,
    blocking_threadpool_size: int = 128,
    blocking_threadpool_idle_ttl: int = 30,
) -> Runtime:
    threads = threads or multiprocessing.cpu_count()
    rt = Runtime(
        threads=threads,
        threads_blocking=blocking_threadpool_size,
        threads_blocking_timeout=blocking_threadpool_idle_ttl,
        context=context,
        signals=signals or [],
    )
    set_runtime(rt)
    return rt


def run(
    coro,
    context: bool = False,
    signals: list[int] | None = None,
    threads: int | None = None,
    blocking_threadpool_size: int = 128,
    blocking_threadpool_idle_ttl: int = 30,
):
    return new(
        context=context,
        signals=signals,
        threads=threads,
        blocking_threadpool_size=blocking_threadpool_size,
        blocking_threadpool_idle_ttl=blocking_threadpool_idle_ttl,
    ).run_until_complete(coro)
