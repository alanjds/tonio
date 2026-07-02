import os
import sys

import pytest


def pytest_collection_modifyitems(items, config):
    _asyncio_backend = sys.platform == 'win32' or os.environ.get('TONIO_BACKEND') == 'asyncio'
    if not _asyncio_backend:
        return
    skip_tls = pytest.mark.skip(reason='TLS not supported on asyncio backend')
    for item in items:
        if 'test_colored_tls' in item.nodeid:
            item.add_marker(skip_tls)
