import sys

# Network tests use _io_event_r/_io_event_w, not available on Windows asyncio backend.
collect_ignore = (
    ['test_colored_socket.py', 'test_colored_streams.py', 'test_colored_tls.py']
    if sys.platform == 'win32'
    else []
)
