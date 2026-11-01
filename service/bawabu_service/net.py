"""The service's HTTP client for registries and OSV."""

import httpx

from . import __version__


def new_client(transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    """`transport` lets the local service answer its own test-lab requests in-process (see local.py)."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(20, connect=5),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=20),
        headers={"user-agent": f"bawabu/{__version__} (+https://github.com/Amoh-Ntim/bawabu)"},
        transport=transport,
    )
