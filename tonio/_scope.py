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
            except CancelledError:
                pass
            except BaseException as exc:
                raise exc
            finally:
                event.set()

        if wrapped_coro := self._track(wrapper):
            # The asyncio backend needs to track the task for cancelation.
            # The native backend returns None.
            if task := get_runtime()._spawn_pyasyncgen(wrapped_coro) is not None:
                self._register_task(task)

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
