"""Platform-conditional import hub.

On Unix/macOS: re-exports Rust types from ._tonio (the compiled extension).
On Windows (or when TONIO_BACKEND=asyncio): re-exports asyncio-backed Python types.
"""

import os
import sys


_use_asyncio = sys.platform == 'win32' or os.environ.get('TONIO_BACKEND') == 'asyncio'

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
