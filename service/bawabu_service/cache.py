"""Verdicts cached per exact package version, so each version is judged once.

Each verdict records the engine that made it. A lookup only accepts verdicts from an engine at least
`min_engine`, so when the checks improve, older verdicts are judged again instead of trusted. Verdicts also
expire, so new information (a fresh malware report) gets picked up.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CachedVerdict:
    verdict: str
    reason: str
    engine: int
    signals: tuple[str, ...] = ()
    suggestion: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Cache(Protocol):
    name: str

    # `registry` is "" for the public registry, else the private registry's URL: verdicts never cross registries.
    async def get(self, ecosystem: str, package: str, version: str, min_engine: int, registry: str = "") -> CachedVerdict | None: ...

    async def put(self, ecosystem: str, package: str, version: str, verdict: CachedVerdict, ttl_seconds: int, registry: str = "") -> None: ...


class MemoryCache:
    """Per-process cache for tests and local runs; lost on restart."""

    name = "memory"

    def __init__(self, clock=_now) -> None:
        self._items: dict[tuple[str, ...], tuple[CachedVerdict, datetime]] = {}
        self._clock = clock

    @staticmethod
    def _key(ecosystem: str, package: str, version: str, registry: str) -> tuple[str, ...]:
        return (ecosystem, package, version) if not registry else (ecosystem, registry, package, version)

    async def get(self, ecosystem: str, package: str, version: str, min_engine: int, registry: str = "") -> CachedVerdict | None:
        hit = self._items.get(self._key(ecosystem, package, version, registry))
        if hit and hit[0].engine >= min_engine and hit[1] > self._clock():
            return hit[0]
        return None

    async def put(self, ecosystem: str, package: str, version: str, verdict: CachedVerdict, ttl_seconds: int, registry: str = "") -> None:
        self._items[self._key(ecosystem, package, version, registry)] = (verdict, self._clock() + timedelta(seconds=ttl_seconds))


class SupabaseCache:
    """The `verdicts` table through Supabase's REST API, with the project's secret key (server-side only)."""

    name = "supabase"

    def __init__(self, url: str, key: str, client: httpx.AsyncClient | None = None, clock=_now) -> None:
        self._table = f"{url.rstrip('/')}/rest/v1/verdicts"
        # New-style secret keys (sb_secret_...) go in `apikey` only; legacy JWT keys also need Authorization.
        self._headers = {"apikey": key} if key.startswith("sb_") else {"apikey": key, "Authorization": f"Bearer {key}"}
        self._client = client or httpx.AsyncClient(timeout=10)
        self._clock = clock

    async def get(self, ecosystem: str, package: str, version: str, min_engine: int, registry: str = "") -> CachedVerdict | None:
        params = {
            "select": "verdict,reason,engine,signals,suggestion",
            "ecosystem": f"eq.{ecosystem}",
            "registry": f"eq.{registry}",
            "name": f"eq.{package}",
            "version": f"eq.{version}",
            "engine": f"gte.{min_engine}",
            "expires_at": f"gt.{self._clock().isoformat()}",
            "limit": "1",
        }
        response = await self._client.get(self._table, headers=self._headers, params=params)
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        row = rows[0]
        return CachedVerdict(row["verdict"], row["reason"], row["engine"], tuple(row.get("signals") or ()), row.get("suggestion"))

    async def put(self, ecosystem: str, package: str, version: str, verdict: CachedVerdict, ttl_seconds: int, registry: str = "") -> None:
        response = await self._client.post(
            self._table,
            headers={**self._headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
            params={"on_conflict": "ecosystem,registry,name,version"},
            json={
                "ecosystem": ecosystem,
                "registry": registry,
                "name": package,
                "version": version,
                "verdict": verdict.verdict,
                "reason": verdict.reason,
                "engine": verdict.engine,
                "signals": list(verdict.signals),
                "suggestion": verdict.suggestion,
                "expires_at": (self._clock() + timedelta(seconds=ttl_seconds)).isoformat(),
            },
        )
        response.raise_for_status()


def cache_from_env() -> Cache:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
    if url and key:
        return SupabaseCache(url, key)
    log.warning("SUPABASE_URL / SUPABASE_SECRET_KEY not set: using an in-memory cache")
    return MemoryCache()
