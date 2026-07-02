import os
import sys

import pytest

import tonio
from tonio._utils import is_asyncg


_runtime = tonio.runtime(threads=4, blocking_threadpool_size=8, blocking_threadpool_idle_ttl=10, context=True)


@pytest.fixture(scope='function')
def run():
    def inner(coro):
        runner = _runtime.run_pyasyncgen_until_complete if is_asyncg(coro) else _runtime.run_pygen_until_complete
        return runner(coro)

    return inner


def pytest_collection_modifyitems(items, config):
    _asyncio_backend = sys.platform == 'win32' or os.environ.get('TONIO_BACKEND') == 'asyncio'
    if not _asyncio_backend:
        return
    skip = pytest.mark.skip(reason='blocking task abort not supported on asyncio backend (threads cannot be cancelled)')
    for item in items:
        if 'test_abort' in item.nodeid:
            item.add_marker(skip)
