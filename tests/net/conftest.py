import sys

# Network tests use _io_event_r/_io_event_w, not available on Windows asyncio backend.
collect_ignore = ['test_socket.py', 'test_streams.py', 'test_tls.py'] if sys.platform == 'win32' else []
