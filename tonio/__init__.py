from ._ctl import (
    as_completed as as_completed,
    block_on as block_on,
    map as map,
    map_blocking as map_blocking,
    select as select,
    spawn as spawn,
    spawn_blocking as spawn_blocking,
)
from ._deco import main as main
from ._events import Event as Event, Result as Result, Waiter as Waiter
from ._runtime import Runtime as Runtime, new as runtime, run as run  # noqa: F401
from ._scope import scope as scope
from .signals import signal_receiver as signal_receiver
from .time import sleep as sleep


try:
    from ._tonio import __version__ as __version__
except ImportError:
    # If the native module is not available (like on Windows)
    # the version will be fetched from the package metadata instead.
    from importlib.metadata import PackageNotFoundError, version as _pkg_version

    try:
        __version__ = _pkg_version('tonio')
    except PackageNotFoundError:
        __version__ = '0.0.0+unknown'
