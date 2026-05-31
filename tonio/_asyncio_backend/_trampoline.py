from __future__ import annotations

import asyncio
import inspect


async def drive_generator(gen):
    """Run a tonio pygen (generator-based) coroutine inside asyncio.

    Tonio generators yield sub-generators or awaitable objects (Waiter).
    This trampoline drives them recursively inside the asyncio event loop.
    """
    try:
        yielded = gen.send(None)
    except StopIteration as e:
        return e.value

    while True:
        try:
            if asyncio.iscoroutine(yielded) or inspect.isawaitable(yielded):
                result = await yielded
            elif inspect.isgenerator(yielded):
                result = await drive_generator(yielded)
            else:
                await asyncio.sleep(0)
                result = None
        except BaseException as exc:
            try:
                yielded = gen.throw(exc)
            except StopIteration as e:
                return e.value
        else:
            try:
                yielded = gen.send(result)
            except StopIteration as e:
                return e.value
