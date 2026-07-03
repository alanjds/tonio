# Re-export asyncio's CancelledError so shared code can catch a single backend
# CancelledError without importing asyncio: on this backend, task cancellation
# raises asyncio.CancelledError.
from asyncio import CancelledError as CancelledError


class TimeoutError(BaseException):
    pass


class ResourceBroken(Exception):
    pass


class WouldBlock(Exception):
    pass


class RuntimeAlreadyInitializedError(RuntimeError):
    pass


class RuntimeNotInitializedError(RuntimeError):
    pass
