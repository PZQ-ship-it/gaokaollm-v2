import socket
from urllib.parse import urlparse

import pytest

from app.core.db_pg import get_database_url


def require_database() -> None:
    parsed = urlparse(get_database_url())
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=2):
            return
    except OSError as exc:
        pytest.skip(f"PostgreSQL is not reachable at {host}:{port}: {exc}")
