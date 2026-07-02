import asyncio

from ._backend import CancelledError, PyGenScope as _Scope, get_runtime
from ._types import Coro


class Scope(_Scope):
    def spawn(self, coro: Coro):
        def inner(waiter):
            yield waiter
            yield coro

        def wrapper(event, waiter):
            try:
                yield inner(waiter)
            except (CancelledError, asyncio.CancelledError):
                pass
            except BaseException as exc:
                raise exc
            finally:
                event.set()

        if wrapped_coro := self._track(wrapper):
            task = get_runtime()._spawn_pygen(wrapped_coro)
            # On the asyncio backend _spawn_pygen returns an asyncio.Task;
            # on the Rust backend it returns None.
            if task is not None:
                if not hasattr(self, '_asyncio_tasks'):
                    self._asyncio_tasks = []
                self._asyncio_tasks.append(task)
                # If the scope was already cancelled before this spawn, defer the
                # cancel via call_soon so the task gets one step to enter before
                # CancelledError is delivered.
                if getattr(self, '_cancelled', False):
                    asyncio.get_running_loop().call_soon(task.cancel)

    def cancel(self) -> bool:
        result = super().cancel()
        if result and hasattr(self, '_asyncio_tasks'):
            for task in self._asyncio_tasks:
                if not task.done():
                    task.cancel()
        return result

    def __enter__(self):
        if not self._incr(0):
            raise RuntimeError('Cannot enter the same scope multiple times.')
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._incr(1)
        return

    def __call__(self):
        waiter = self._exit()
        yield waiter


def scope():
    return Scope()
