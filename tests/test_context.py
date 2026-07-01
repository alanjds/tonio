import contextvars
import gc
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


def test_throw_ctx_leak_gen(run):
    gc.collect()
    before = sum(1 for o in gc.get_objects() if isinstance(o, contextvars.Context))

    N = 50

    def _fail(_):
        raise ValueError('trigger throw')

    def _run():
        try:
            yield tonio.map_blocking(_fail, range(N))
        except Exception:
            pass

    run(_run())

    gc.collect()
    after = sum(1 for o in gc.get_objects() if isinstance(o, contextvars.Context))
    leaked = after - before
    assert leaked == 0, f'Leaked {leaked} Context objects via PyGenCtxThrower'
