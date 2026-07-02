from __future__ import annotations

from typing import Any

from ._events import Event
from .exceptions import WouldBlock


class LockCtx:
    __slots__ = ['_lock']

    def __init__(self, lock: _Lock):
        self._lock = lock

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._lock.release()


class _Lock:
    __slots__ = ['_locked', '_waiters']

    def __init__(self):
        self._locked = False
        self._waiters: list[Event] = []

    def acquire(self) -> Event | None:
        if not self._locked:
            self._locked = True
            return None
        ev = Event()
        self._waiters.append(ev)
        return ev

    def try_acquire(self):
        if self._locked:
            raise WouldBlock()
        self._locked = True

    def release(self):
        if self._waiters:
            self._waiters.pop(0).set()
        else:
            self._locked = False

    def or_raise(self) -> LockCtx:
        self.try_acquire()
        return LockCtx(self)


class SemaphoreCtx:
    __slots__ = ['_semaphore']

    def __init__(self, semaphore: _Semaphore):
        self._semaphore = semaphore

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._semaphore.release()


class _Semaphore:
    __slots__ = ['_value', '_waiters']

    def __init__(self, value: int):
        self._value = value
        self._waiters: list[Event] = []

    def acquire(self) -> Event | None:
        if self._value > 0:
            self._value -= 1
            return None
        ev = Event()
        self._waiters.append(ev)
        return ev

    def try_acquire(self):
        if self._value <= 0:
            raise WouldBlock()
        self._value -= 1

    def release(self):
        if self._waiters:
            self._waiters.pop(0).set()
        else:
            self._value += 1

    def tokens(self) -> int:
        return self._value

    def or_raise(self) -> SemaphoreCtx:
        self.try_acquire()
        return SemaphoreCtx(self)


class _Barrier:
    __slots__ = ['_count', '_event']

    def __init__(self, value: int):
        self._count = value
        self._event = Event()

    def ack(self) -> int:
        self._count -= 1
        if self._count <= 0:
            self._event.set()
        return self._count

    def value(self) -> int:
        return self._count


class Channel:
    __slots__ = ['_size', '_queue', '_send_waiters', '_recv_event', '_closed']

    def __init__(self, size: int):
        self._size = size
        self._queue: list = []
        self._send_waiters: list[Event] = []
        self._recv_event = Event()
        self._closed = False


class ChannelSender:
    __slots__ = ['_channel']

    def __init__(self, channel: Channel):
        self._channel = channel

    def _send(self, message: Any) -> Event:
        ch = self._channel
        ev = Event()
        if len(ch._queue) < ch._size:
            ch._queue.append(message)
            ev.set()
            ch._recv_event.set()  # level-triggered: stays set until queue drains
        else:
            ch._send_waiters.append((message, ev))
        return ev

    def close(self):
        self._channel._closed = True
        self._channel._recv_event.set()  # wake all receivers permanently


class ChannelReceiver:
    __slots__ = ['_channel']

    def __init__(self, channel: Channel):
        self._channel = channel

    def _receive(self) -> tuple:
        ch = self._channel
        if ch._queue:
            message = ch._queue.pop(0)
            if ch._send_waiters:
                pending_msg, pending_ev = ch._send_waiters.pop(0)
                ch._queue.append(pending_msg)
                pending_ev.set()
            elif not ch._queue:
                if not ch._closed:
                    ch._recv_event.clear()
            return ch._recv_event, False, message  # False = not blocking = return message
        if ch._closed:
            raise WouldBlock()
        ch._recv_event.clear()  # prevent spin on spurious deferred-set wakeups
        return ch._recv_event, True, None  # True = blocking = wait on event


class UnboundedChannel:
    __slots__ = ['_queue', '_recv_event', '_closed']

    def __init__(self):
        self._queue: list = []
        self._recv_event = Event()
        self._closed = False


class UnboundedChannelSender:
    __slots__ = ['_channel']

    def __init__(self, channel: UnboundedChannel):
        self._channel = channel

    def send(self, message: Any):
        self._channel._queue.append(message)
        if not self._channel._recv_event.is_set():
            self._channel._recv_event.set()

    def close(self):
        self._channel._closed = True
        self._channel._recv_event.set()


class UnboundedChannelReceiver:
    __slots__ = ['_channel']

    def __init__(self, channel: UnboundedChannel):
        self._channel = channel

    def _receive(self) -> tuple:
        ch = self._channel
        if ch._queue:
            message = ch._queue.pop(0)
            if not ch._queue:
                if not ch._closed:
                    ch._recv_event.clear()
            return ch._recv_event, False, message  # False = not blocking = return message
        if ch._closed:
            raise WouldBlock()
        ch._recv_event.clear()
        return ch._recv_event, True, None  # True = blocking = wait on event
