class Socket:
    """Stub Socket for Windows asyncio backend. Full networking not yet implemented."""

    def __init__(self, stdlib_socket):
        self._sock = stdlib_socket

    def _eof_get(self) -> bool:
        return False

    def _eof_set(self):
        pass


class TLSStream:
    """Stub TLSStream for Windows asyncio backend. TLS not yet implemented."""

    _state: int = 0

    def _handshake_pre(self):
        raise NotImplementedError('TLS not available on Windows asyncio backend')

    def _handshake_post(self):
        raise NotImplementedError('TLS not available on Windows asyncio backend')

    def _set_broken(self):
        pass

    def _set_closed(self):
        pass

    def _check_ready(self):
        raise NotImplementedError('TLS not available on Windows asyncio backend')
