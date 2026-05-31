"""Platform-conditional import hub.

On Unix/macOS: re-exports Rust types from ._tonio (the compiled extension).
On Windows: re-exports asyncio-backed Python types from ._asyncio_backend.
"""
import sys

if sys.platform == 'win32':
    from ._asyncio_backend._events import Event, Result, Waiter
    from ._asyncio_backend._net import Socket, TLSStream
    from ._asyncio_backend._runtime import BlockingTaskCtl, Runtime, get_runtime, set_runtime
    from ._asyncio_backend._scope import PyAsyncGenScope, PyGenScope
    from ._asyncio_backend._sync import (
        _Barrier as Barrier,
        _Lock as Lock,
        _Semaphore as Semaphore,
        Channel,
        ChannelReceiver,
        ChannelSender,
        LockCtx,
        SemaphoreCtx,
        UnboundedChannel,
        UnboundedChannelReceiver,
        UnboundedChannelSender,
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
        Barrier,
        BlockingTaskCtl,
        CancelledError,
        Channel,
        ChannelReceiver,
        ChannelSender,
        Event,
        Lock,
        LockCtx,
        PyAsyncGenScope,
        PyGenScope,
        ResourceBroken,
        Result,
        Runtime,
        RuntimeAlreadyInitializedError,
        RuntimeNotInitializedError,
        Semaphore,
        SemaphoreCtx,
        Socket,
        TLSStream,
        TimeoutError,
        UnboundedChannel,
        UnboundedChannelReceiver,
        UnboundedChannelSender,
        Waiter,
        WouldBlock,
        get_runtime,
        set_runtime,
    )
