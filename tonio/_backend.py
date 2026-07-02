"""Backend selection hub.

The backend is resolved once, early and explicitly, from the ``TONIO_BACKEND``
environment variable:

* unset / ``"auto"`` -- ``"asyncio"`` on Windows, ``"native"`` (Rust) elsewhere
* ``"asyncio"``      -- the pure-Python asyncio backend, on any platform
* ``"native"``       -- the Rust extension; if it is unavailable (e.g. requested
                        on Windows, where it is not built) the ImportError surfaces

On the ``native`` path this re-exports the compiled ``._tonio`` types; on the
``asyncio`` path it re-exports the ``._asyncio_backend`` Python types.
"""

import os
import sys


_requested = os.environ.get('TONIO_BACKEND', 'auto')
if _requested == 'auto':
    _use_asyncio = sys.platform == 'win32'
elif _requested == 'asyncio':
    _use_asyncio = True
elif _requested == 'native':
    _use_asyncio = False
else:
    raise RuntimeError(f"Invalid TONIO_BACKEND={_requested!r}; expected 'auto', 'asyncio', or 'native'")

if _use_asyncio:
    from ._asyncio_backend._events import Event, Result, Waiter
    from ._asyncio_backend._net import Socket, TLSStream
    from ._asyncio_backend._runtime import BlockingTaskCtl, Runtime, get_runtime, set_runtime
    from ._asyncio_backend._scope import PyAsyncGenScope, PyGenScope
    from ._asyncio_backend._sync import (
        Channel,
        ChannelReceiver,
        ChannelSender,
        LockCtx,
        SemaphoreCtx,
        UnboundedChannel,
        UnboundedChannelReceiver,
        UnboundedChannelSender,
        _Barrier as Barrier,
        _Lock as Lock,
        _Semaphore as Semaphore,
    )
    from ._asyncio_backend.exceptions import (
        CancelledError,
        ResourceBroken,
        RuntimeAlreadyInitializedError,
        RuntimeNotInitializedError,
        TimeoutError,
        WouldBlock,
    )
else:
    from ._tonio import (
        Barrier as Barrier,
        BlockingTaskCtl as BlockingTaskCtl,
        CancelledError as CancelledError,
        Channel as Channel,
        ChannelReceiver as ChannelReceiver,
        ChannelSender as ChannelSender,
        Event as Event,
        Lock as Lock,
        LockCtx as LockCtx,
        PyAsyncGenScope as PyAsyncGenScope,
        PyGenScope as PyGenScope,
        ResourceBroken as ResourceBroken,
        Result as Result,
        Runtime as Runtime,
        RuntimeAlreadyInitializedError as RuntimeAlreadyInitializedError,
        RuntimeNotInitializedError as RuntimeNotInitializedError,
        Semaphore as Semaphore,
        SemaphoreCtx as SemaphoreCtx,
        Socket as Socket,
        TimeoutError as TimeoutError,
        TLSStream as TLSStream,
        UnboundedChannel as UnboundedChannel,
        UnboundedChannelReceiver as UnboundedChannelReceiver,
        UnboundedChannelSender as UnboundedChannelSender,
        Waiter as Waiter,
        WouldBlock as WouldBlock,
        get_runtime as get_runtime,
        set_runtime as set_runtime,
    )
