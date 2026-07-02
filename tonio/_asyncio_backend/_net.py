"""Networking primitives for the asyncio backend.

These mirror the thin native (Rust) `Socket` / `TLSStream` wrappers: all of the
actual non-blocking IO, the SSL `MemoryBIO` dance and the stream/listener logic
live in the backend-agnostic `tonio/_net` (and `tonio/_colored/_net`) layers,
which drive readiness through `Runtime._io_event_r` / `_io_event_w`. The classes
here only wrap a stdlib socket (tracking write-EOF) and track the TLS handshake
lifecycle state. The event loop is single-threaded, so plain attributes replace
the atomics the native backend needs.
"""

from __future__ import annotations

import socket as _stdlib_socket


class Socket:
    """Wraps a non-blocking stdlib socket; tracks the write-EOF flag.

    The wrapped socket is set to non-blocking by `from_stdlib_socket` before it
    reaches here. The shared `_net._socket._Socket` mixin supplies `fileno()`,
    `recv`/`send`/`accept`/`connect` and the rest, delegating to `self._sock`.
    """

    def __init__(self, stdlib_socket: _stdlib_socket.socket):
        self._sock = stdlib_socket
        self._eof = False

    def _eof_get(self) -> bool:
        return self._eof

    def _eof_set(self) -> None:
        self._eof = True


# TLS handshake lifecycle states (mirrors the native TLSStreamState enum).
_TLS_INIT = 0
_TLS_HANDSHAKE = 1
_TLS_READY = 2
_TLS_BROKEN = 3
_TLS_CLOSED = 4


class TLSStream:
    """TLS handshake/lifecycle state machine for the asyncio backend.

    The shared `_net._tls.TLSStream` owns the `ssl.MemoryBIO` handshake; this
    base only guards the lifecycle transitions it relies on. `_state` defaults
    via the class attribute (the shared subclass uses `__slots__` and does not
    call `super().__init__()`); transitions assign the instance attribute.
    """

    _state: int = _TLS_INIT

    def _handshake_pre(self) -> None:
        if self._state != _TLS_INIT:
            raise RuntimeError('Invalid TLSStream state change')
        self._state = _TLS_HANDSHAKE

    def _handshake_post(self) -> None:
        if self._state != _TLS_HANDSHAKE:
            raise RuntimeError('Invalid TLSStream state change')
        self._state = _TLS_READY

    def _set_broken(self) -> None:
        self._state = _TLS_BROKEN

    def _set_closed(self) -> None:
        self._state = _TLS_CLOSED

    def _check_ready(self) -> None:
        if self._state != _TLS_READY:
            raise RuntimeError('TLSStream in bad state')
