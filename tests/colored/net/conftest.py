import sys

import pytest


def pytest_collection_modifyitems(items, config):
    if sys.platform != 'win32':
        return
    skip_tls = pytest.mark.skip(reason='TLS not supported on Windows asyncio backend')
    for item in items:
        if 'test_colored_tls' in item.nodeid:
            item.add_marker(skip_tls)
