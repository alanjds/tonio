import asyncio

from .._backend import CancelledError, PyAsyncGenScope as _Scope, get_runtime
from . import yield_now


class Scope(_Scope):
    def spawn(self, coro):
        async def inner(waiter):
            await waiter
            await coro

        async def wrapper(event, waiter):
            try:
                await inner(waiter)
            except (CancelledError, asyncio.CancelledError):
                pass
            except BaseException as exc:
                raise exc
            finally:
                event.set()

        if wrapped_coro := self._track(wrapper):
            task = get_runtime()._spawn_pyasyncgen(wrapped_coro)
            # On the asyncio backend _spawn_pyasyncgen returns an asyncio.Task;
            # on the Rust backend it returns None.
            if task is not None:
                if not hasattr(self, '_asyncio_tasks'):
                    self._asyncio_tasks = []
                self._asyncio_tasks.append(task)
                # If the scope was already cancelled before this spawn, defer the
                # cancel via call_soon so the task gets one step to enter before
                # CancelledError is delivered (Python 3.12+ injects cancellation
                # at the very first step if cancel() is called before the task runs).
                if getattr(self, '_cancelled', False):
                    asyncio.get_running_loop().call_soon(task.cancel)

    def cancel(self) -> bool:
        result = super().cancel()
        if result and hasattr(self, '_asyncio_tasks'):
            for task in self._asyncio_tasks:
                if not task.done():
                    task.cancel()
        return result

    async def __aenter__(self):
        if not self._incr(0):
            raise RuntimeError('Cannot enter the same scope multiple times.')
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        self._incr(1)
        await yield_now()
        waiter = self._exit()
        await waiter


def scope():
    return Scope()
