class CancelledError(BaseException):
    pass


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
