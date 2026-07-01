import subprocess
import sys
import textwrap

import tonio.colored as tonio


def test_scope_cancel(run):
    enter = []
    exit = []

    async def _sleep(idx, t):
        enter.append(idx)
        await tonio.sleep(t)
        exit.append(idx)

    async def _run():
        async with tonio.scope() as scope:
            scope.spawn(_sleep(1, 0.1))
            scope.spawn(_sleep(2, 2))
            await tonio.sleep(0.2)
            scope.cancel()
        await tonio.sleep(2)

    run(_run())

    assert set(enter) == {1, 2}
    assert set(exit) == {1}


def test_scope_cancel_immediate(run):
    enter = []
    exit = []

    async def _sleep(idx, t):
        enter.append(idx)
        await tonio.sleep(t)
        exit.append(idx)

    async def _run():
        async with tonio.scope() as scope:
            scope.cancel()
            scope.spawn(_sleep(1, 0.3))
            await tonio.sleep(0.1)

        await tonio.sleep(0.5)

    run(_run())

    assert set(enter) == {1}
    assert not exit


def test_scope_cancel_pending_sleep_does_not_hang_runtime():
    # Regression test: cancelling many tasks suspended in `tonio.sleep()` leaves
    # their timers in the scheduler's heap (never removed on cancel). If the
    # runtime later computes its poll timeout while one of those stale, already
    # elapsed timers sits at the top of the heap, it can end up blocking the
    # reactor indefinitely instead of returning immediately to drain it -
    # hanging the whole runtime, even though there is other pending work
    # (here, the trailing `tonio.sleep(0.3)`) that should complete shortly after.
    #
    # Run in a subprocess: the runtime is a process-wide singleton, and a hang
    # here must not corrupt it for other tests in this session.
    script = textwrap.dedent("""
        import tonio
        import tonio.colored as ctonio

        rt = tonio.runtime(threads=4, blocking_threadpool_size=8, blocking_threadpool_idle_ttl=10, context=True)

        N = 50

        async def _run():
            async with ctonio.scope() as scope:
                for _ in range(N):
                    scope.spawn(ctonio.sleep(0.01))
                await ctonio.yield_now()
                scope.cancel()
            await ctonio.sleep(0.3)

        rt.run_pyasyncgen_until_complete(_run())
        print('OK')
    """)

    try:
        proc = subprocess.run(  # noqa: S603
            [sys.executable, '-c', script], capture_output=True, text=True, timeout=5.0
        )
    except subprocess.TimeoutExpired:
        raise AssertionError(
            'runtime hung after scope.cancel() left elapsed sleep() timers in the scheduler heap'
        ) from None

    assert proc.returncode == 0, proc.stderr
    assert 'OK' in proc.stdout
