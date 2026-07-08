import tonio


def test_select(run):
    enter = []
    exit = []

    def _sleep(idx, t):
        enter.append(idx)
        yield tonio.sleep(t)
        exit.append(idx)

    def _run():
        c1 = _sleep(1, 0.1)
        c2 = _sleep(2, 1)

        yield tonio.select(c1, c2)
        yield tonio.sleep(2)

    run(_run())

    assert set(enter) == {1, 2}
    assert set(exit) == {1}


def test_select_rv(run):
    def _coro(v, t):
        yield tonio.sleep(t)
        return v

    def _run():
        c1 = _coro(1, 0.1)
        c2 = _coro(2, 1)

        ret = yield tonio.select(c1, c2)
        yield tonio.sleep(2)
        return ret

    assert run(_run()) == 1


def test_select_events(run):
    exe = []

    def _coro(v, ev):
        yield ev.wait()
        exe.append(v)
        return v

    def _run():
        e1, e2 = tonio.Event(), tonio.Event()
        c1 = _coro(1, e1)
        c2 = _coro(2, e2)

        e1.set()
        ret = yield tonio.select(c1, c2)
        yield tonio.sleep(0.2)
        return ret

    assert run(_run()) == 1
    assert set(exe) == {1}


def test_as_completed(run):
    def _sleep(x):
        yield tonio.sleep(x)
        return x

    def _run():
        outs = []
        for coro in tonio.as_completed(_sleep(0.3), _sleep(0.1), _sleep(0.2)):
            x = yield coro
            outs.append(x)
        return outs

    assert run(_run()) == [0.1, 0.2, 0.3]


def test_waiter_multiple_events_immediate(run):
    # A multi-event Waiter is a join: it resolves only once *every* event
    # passed to it is set, not on the first one (unlike tonio.select()).
    def _run():
        e1, e2 = tonio.Event(), tonio.Event()
        e1.set()
        e2.set()
        yield tonio.Waiter(e1, e2)
        return True

    assert run(_run()) is True


def test_waiter_multiple_events_wait(run):
    exe = []

    def _setter(ev, t):
        yield tonio.sleep(t)
        exe.append(ev)
        ev.set()

    def _waiter(e1, e2):
        yield tonio.Waiter(e1, e2)
        exe.append('woken')

    def _run():
        e1, e2 = tonio.Event(), tonio.Event()
        yield tonio.spawn(_setter(e1, 0.05), _setter(e2, 0.1), _waiter(e1, e2))

    run(_run())
    # woken only after *both* events fired, i.e. last in the list
    assert exe[-1] == 'woken'
    assert len(exe) == 3
