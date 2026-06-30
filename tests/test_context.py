import contextvars
import time

import tonio


def test_contextvar(run):
    var = contextvars.ContextVar('_test')
    bef = []
    res = {}
    aft = []

    def _step(i):
        bef.append(var.get())
        token = var.set(i)
        yield
        res[i] = var.get()
        var.reset(token)
        aft.append(var.get())

    def _run():
        var.set('empty')
        out = yield tonio.spawn(*[_step(i) for i in range(50)])
        return out

    run(_run())

    assert set(bef) == {'empty'}
    assert set(aft) == {'empty'}
    assert list(res.keys()) == list(res.values())


def test_contextvar_blocking(run):
    var = contextvars.ContextVar('_test')
    bef = []
    res = {}
    aft = []

    def _step(i):
        bef.append(var.get())
        token = var.set(i)
        time.sleep(0.01)
        res[i] = var.get()
        var.reset(token)
        aft.append(var.get())

    def _run():
        var.set('empty')
        out = yield tonio.map_blocking(_step, range(50))
        return out

    run(_run())

    assert set(bef) == {'empty'}
    assert set(aft) == {'empty'}
    assert list(res.keys()) == list(res.values())


def test_contextvar_blocking_stress(run):
    """Regression guard: BlockingTask::run must not use-after-free the context ptr.

    map(|v| v.as_ptr()) inside an unsafe block moves v into the closure then
    drops it (Py_DECREF → free) before PyContext_Enter uses the pointer.  Under
    free-threaded Python (no-GIL) the freed slot is reused immediately by
    concurrent allocations, corrupting the interpreter.  Run many tasks per
    batch and many batches so the allocator pressure reliably surfaces the bug.
    """
    var = contextvars.ContextVar('_stress', default='base')

    def work(_):
        return var.get()

    def _run():
        var.set('set')
        for _ in range(10):
            results = yield tonio.map_blocking(work, range(100))
            assert all(r == 'set' for r in results)

    run(_run())
