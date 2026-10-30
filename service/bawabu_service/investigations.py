"""Investigations: the deep check (diff + sandbox + Muse Spark) for packages the quick checks find suspicious.

/check never runs one itself: it takes 30-90 s and needs a sandbox on Modal and a model on Meta's API. It
starts the investigation as a separate Modal function (or joins one already running for that package
version) and waits for the verdict for a while. If it isn't ready in time, the agent is told to try again
in a minute; the investigation carries on, and the retry gets the cached verdict.

Every step is written as an event, in order, so the report page can show the investigation as it happens.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Protocol

import httpx

from . import diff, investigator
from .cache import Cache, CachedVerdict
from .registry import Source

log = logging.getLogger(__name__)

HOUR = 3600
DAY = 24 * HOUR
TTL = {"block": 30 * DAY, "allow": 7 * DAY, "ask": 6 * HOUR}
STALE = timedelta(minutes=10)  # a "running" investigation older than this has died; start a new one
REUSE = timedelta(hours=24)  # a finished investigation this recent answers a retry even if the cache missed it


@dataclass(frozen=True)
class Outcome:
    verdict: str
    reason: str
    signals: tuple[str, ...] = ()
    suggestion: str | None = None
    report_id: str | None = None
    pending: bool = False


def outcome_from_result(result: dict, report_id: str) -> Outcome:
    """The CLI-facing verdict from a finished investigation: reason plus its verified evidence, one line each."""
    lines = []
    for e in result.get("evidence") or []:
        where = f"{e['file']}:{e['line']}: " if e.get("file") and e.get("line") else f"{e['file']}: " if e.get("file") else ""
        lines.append(f"{where}{e.get('detail', '')}".strip())
    return Outcome(result.get("verdict", "ask"), result.get("reason", ""), tuple(lines[:6]), result.get("safe_alternative"), report_id)


# ---------------------------------------------------------------------------------------------- storage


class Store(Protocol):
    name: str

    async def create(self, ecosystem: str, registry: str, name: str, version: str) -> str: ...

    async def latest(self, ecosystem: str, registry: str, name: str, version: str) -> dict | None:
        """The newest investigation of this package version started within REUSE, any status."""
        ...

    async def get(self, inv_id: str) -> dict | None: ...

    async def add_event(self, inv_id: str, seq: int, event: dict) -> None: ...

    async def finish(self, inv_id: str, status: str, result: dict) -> None: ...

    async def events(self, inv_id: str) -> list[dict]: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryStore:
    name = "memory"

    def __init__(self, clock=_now) -> None:
        self.rows: dict[str, dict] = {}
        self.event_log: dict[str, list[dict]] = {}
        self._clock = clock
        self._n = 0

    async def create(self, ecosystem: str, registry: str, name: str, version: str) -> str:
        self._n += 1
        inv_id = f"inv-{self._n}"
        self.rows[inv_id] = {"id": inv_id, "ecosystem": ecosystem, "registry": registry, "name": name, "version": version,
                             "status": "running", "result": None, "created_at": self._clock()}
        return inv_id

    async def latest(self, ecosystem: str, registry: str, name: str, version: str) -> dict | None:
        for row in reversed(list(self.rows.values())):
            if (row["ecosystem"], row["registry"], row["name"], row["version"]) == (ecosystem, registry, name, version) \
                    and row["created_at"] > self._clock() - REUSE:
                return row
        return None

    async def get(self, inv_id: str) -> dict | None:
        return self.rows.get(inv_id)

    async def add_event(self, inv_id: str, seq: int, event: dict) -> None:
        self.event_log.setdefault(inv_id, []).append({"seq": seq, **event})

    async def finish(self, inv_id: str, status: str, result: dict) -> None:
        self.rows[inv_id].update(status=status, result=result)

    async def events(self, inv_id: str) -> list[dict]:
        return list(self.event_log.get(inv_id, []))


class SupabaseStore:
    """`investigations` and `investigation_events` through Supabase's REST API (secret key, server side only)."""

    name = "supabase"

    def __init__(self, url: str, key: str, client: httpx.AsyncClient | None = None, clock=_now) -> None:
        self._base = f"{url.rstrip('/')}/rest/v1"
        self._headers = {"apikey": key} if key.startswith("sb_") else {"apikey": key, "Authorization": f"Bearer {key}"}
        self._client = client or httpx.AsyncClient(timeout=10)
        self._clock = clock

    async def _req(self, method: str, table: str, **kw) -> httpx.Response:
        headers = {**self._headers, **kw.pop("headers", {})}
        response = await self._client.request(method, f"{self._base}/{table}", headers=headers, **kw)
        response.raise_for_status()
        return response

    async def create(self, ecosystem: str, registry: str, name: str, version: str) -> str:
        r = await self._req("POST", "investigations", headers={"Prefer": "return=representation"},
                            json={"ecosystem": ecosystem, "registry": registry, "name": name, "version": version})
        return r.json()[0]["id"]

    async def latest(self, ecosystem: str, registry: str, name: str, version: str) -> dict | None:
        r = await self._req("GET", "investigations", params={
            "select": "id,status,result,created_at", "ecosystem": f"eq.{ecosystem}", "registry": f"eq.{registry}",
            "name": f"eq.{name}", "version": f"eq.{version}", "created_at": f"gt.{(self._clock() - REUSE).isoformat()}",
            "order": "created_at.desc", "limit": "1"})
        rows = r.json()
        return rows[0] if rows else None

    async def get(self, inv_id: str) -> dict | None:
        r = await self._req("GET", "investigations", params={"select": "*", "id": f"eq.{inv_id}", "limit": "1"})
        rows = r.json()
        return rows[0] if rows else None

    async def add_event(self, inv_id: str, seq: int, event: dict) -> None:
        await self._req("POST", "investigation_events", headers={"Prefer": "return=minimal"},
                        json={"investigation_id": inv_id, "seq": seq, "event": event})

    async def finish(self, inv_id: str, status: str, result: dict) -> None:
        await self._req("PATCH", "investigations", params={"id": f"eq.{inv_id}"}, headers={"Prefer": "return=minimal"},
                        json={"status": status, "result": result, "updated_at": self._clock().isoformat()})

    async def events(self, inv_id: str) -> list[dict]:
        r = await self._req("GET", "investigation_events", params={
            "select": "seq,event,created_at", "investigation_id": f"eq.{inv_id}", "order": "seq.asc"})
        return [{"seq": row["seq"], **row["event"]} for row in r.json()]


def _when(value: datetime | str) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def store_from_env() -> Store:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
    return SupabaseStore(url, key) if url and key else MemoryStore()


# ---------------------------------------------------------------------------------------------- waiting (/check)

# start(investigation id, payload): launch the investigation without waiting for it.
Spawn = Callable[[str, dict], Awaitable[Any]]


class Investigations:
    def __init__(self, store: Store, spawn: Spawn, budget_s: float = 110, poll_s: float = 2.0) -> None:
        self.store, self.spawn, self.budget_s, self.poll_s = store, spawn, budget_s, poll_s

    async def verdict(self, ecosystem: str, name: str, version: str, source: Source, signals: list[str]) -> Outcome:
        row = await self.store.latest(ecosystem, source.key, name, version)
        if row and row["status"] == "done" and row.get("result"):
            return outcome_from_result(row["result"], row["id"])  # finished already (the cache missed it)
        alive = row and row["status"] == "running" and _when(row["created_at"]) > _now() - STALE
        inv_id = row["id"] if alive else None
        if inv_id is None:
            inv_id = await self.store.create(ecosystem, source.key, name, version)
            await self.spawn(inv_id, {"ecosystem": ecosystem, "name": name, "version": version, "registry_url": source.url,
                                      "registry_key": source.key, "headers": [list(h) for h in source.headers], "signals": signals})
        deadline = time.monotonic() + self.budget_s
        while True:
            row = await self.store.get(inv_id)
            if row and row["status"] == "done" and row.get("result"):
                return outcome_from_result(row["result"], inv_id)
            if row and row["status"] == "failed":
                return Outcome("ask", "Bawabu's investigation of this package failed, so a human should decide.",
                               report_id=inv_id)
            if time.monotonic() >= deadline:
                return Outcome("ask", f"Bawabu is still investigating {name}@{version} in its sandbox; the first check of a "
                               "package takes about a minute. Wait a minute, then run the same install again: the "
                               "verdict will be ready.", report_id=inv_id, pending=True)
            await asyncio.sleep(self.poll_s)


# ---------------------------------------------------------------------------------------------- running (Modal)

# sandbox(name, version, registry_url or None, registry_auth or None, env, fake_date) -> sandbox report dict
SandboxFn = Callable[[str, str, str | None, str | None, dict | None, str | None], dict]


def _basic_auth(headers: list[list[str]]) -> str | None:
    for key, value in headers:
        if key.lower() == "authorization" and value.startswith("Basic "):
            return value.removeprefix("Basic ")
    return None


async def run(inv_id: str, payload: dict, *, store: Store, cache: Cache, http: httpx.AsyncClient, spark: Any, model: str,
              sandbox: SandboxFn | None, engine: int, effort: str | None = "low") -> dict:
    """The whole investigation; writes events as it goes and the verdict at the end (also into the cache)."""
    name, version = payload["name"], payload["version"]
    source = Source(payload["registry_url"], tuple(tuple(h) for h in payload.get("headers") or ()))
    registry_url = None if source.public else source.url
    auth = _basic_auth(payload.get("headers") or [])
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    async def writer() -> None:
        seq = 0
        while (event := await queue.get()) is not None:
            try:
                await store.add_event(inv_id, seq, event)
            except Exception:
                log.warning("couldn't store event %s of %s", seq, inv_id, exc_info=True)
            seq += 1

    def emit(event: dict) -> None:  # callable from any thread (the Spark loop runs in one)
        loop.call_soon_threadsafe(queue.put_nowait, {**event, "t": round(time.time(), 2)})

    def box(ver: str, env: dict | None = None, date: str | None = None) -> dict:
        return sandbox(name, ver, registry_url, auth, env, date) if sandbox else {}

    writing = asyncio.create_task(writer())
    try:
        # The version is already exact (resolved by /check), so the diff and the first sandbox run go in parallel.
        emit({"kind": "stage", "title": "Reading the code and comparing it with the previous version"})
        if sandbox:
            emit({"kind": "stage", "title": "Running the install in a locked sandbox with planted secrets"})
        report, first = await asyncio.gather(diff.analyze(http, name, version, source),
                                             asyncio.to_thread(box, version) if sandbox else asyncio.sleep(0, None))
        emit({"kind": "stage", "title": f"Static analysis: risk {report.risk}" + (f" (compared with {report.previous})" if report.previous else " (first release)"),
              "signals": report.headline(6)})
        if first:
            emit({"kind": "stage", "title": f"Sandbox: {first.get('summary', 'no result')}"})
        material = investigator.Material(payload["ecosystem"], name, report.version, diff=report, sandbox=first,
                                         metadata={"version": report.version, "previous_version": report.previous,
                                                   "registry": "public npm" if source.public else "private registry",
                                                   "signals": payload.get("signals") or []})
        rerun = (lambda env, date: box(report.version, env, date)) if sandbox else None
        inv = await asyncio.to_thread(investigator.investigate, material, spark, model, rerun=rerun, emit=emit, reasoning_effort=effort)
        result = {**inv.to_dict(), "version": report.version, "previous": report.previous}
        verdict = CachedVerdict(inv.verdict, inv.reason, engine, tuple(outcome_from_result(result, inv_id).signals), inv.safe_alternative)
        try:
            await cache.put(payload["ecosystem"], name, report.version, verdict, TTL[inv.verdict], registry=payload["registry_key"])
        except Exception:
            log.exception("couldn't cache the verdict for %s@%s", name, report.version)
        await store.finish(inv_id, "done", result)
        return result
    except Exception as exc:
        log.exception("investigation %s failed", inv_id)
        emit({"kind": "error", "title": "The investigation failed", "detail": f"{type(exc).__name__}: {exc}"[:300]})
        await store.finish(inv_id, "failed", {"error": f"{type(exc).__name__}: {exc}"[:500]})
        return {"error": str(exc)}
    finally:
        loop.call_soon_threadsafe(queue.put_nowait, None)
        await writing
