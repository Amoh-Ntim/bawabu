"""Verdicts cached per exact package version, so each version is judged once.

Each verdict records the engine that made it. A lookup only accepts verdicts from an engine at least
`min_engine`, so when the checks improve, older verdicts are judged again instead of trusted.
"""

import logging
import os
from dataclasses import asdict, dataclass
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CachedVerdict:
    verdict: str
    reason: str
    engine: int


class Cache(Protocol):
    name: str

    async def get(self, ecosystem: str, package: str, version: str, min_engine: int) -> CachedVerdict | None: ...

    async def put(self, ecosystem: str, package: str, version: str, verdict: CachedVerdict) -> None: ...


class MemoryCache:
    """Per-process cache for tests and local runs; lost on restart."""

    name = "memory"

    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str], CachedVerdict] = {}

    async def get(self, ecosystem: str, package: str, version: str, min_engine: int) -> CachedVerdict | None:
        hit = self._items.get((ecosystem, package, version))
        return hit if hit and hit.engine >= min_engine else None

    async def put(self, ecosystem: str, package: str, version: str, verdict: CachedVerdict) -> None:
        self._items[(ecosystem, package, version)] = verdict


class SupabaseCache:
    """The `verdicts` table through Supabase's REST API, with the project's secret key (server-side only)."""

    name = "supabase"

    def __init__(self, url: str, key: str, client: httpx.AsyncClient | None = None) -> None:
        self._table = f"{url.rstrip('/')}/rest/v1/verdicts"
        # New-style secret keys (sb_secret_...) go in `apikey` only; legacy JWT keys also need Authorization.
        self._headers = {"apikey": key} if key.startswith("sb_") else {"apikey": key, "Authorization": f"Bearer {key}"}
        self._client = client or httpx.AsyncClient(timeout=10)

    async def get(self, ecosystem: str, package: str, version: str, min_engine: int) -> CachedVerdict | None:
        params = {
            "select": "verdict,reason,engine",
            "ecosystem": f"eq.{ecosystem}",
            "name": f"eq.{package}",
            "version": f"eq.{version}",
            "engine": f"gte.{min_engine}",
            "limit": "1",
        }
        response = await self._client.get(self._table, headers=self._headers, params=params)
        response.raise_for_status()
        rows = response.json()
        return CachedVerdict(**rows[0]) if rows else None

    async def put(self, ecosystem: str, package: str, version: str, verdict: CachedVerdict) -> None:
        response = await self._client.post(
            self._table,
            headers={**self._headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
            params={"on_conflict": "ecosystem,name,version"},
            json={"ecosystem": ecosystem, "name": package, "version": version, **asdict(verdict)},
        )
        response.raise_for_status()


def cache_from_env() -> Cache:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
    if url and key:
        return SupabaseCache(url, key)
    log.warning("SUPABASE_URL / SUPABASE_SECRET_KEY not set: using an in-memory cache")
    return MemoryCache()
