"""The HTTP API. Run locally with:

    uv run --env-file .env uvicorn --app-dir service bawabu_service.api:create_app --factory --port 8787
"""

import asyncio

import httpx
from fastapi import FastAPI, HTTPException

from . import __version__
from .cache import Cache, cache_from_env
from .investigations import Investigations, Store
from .models import CheckRequest, CheckResponse
from .net import new_client
from .registry import Source, sources_from_env
from .verdicts import ENGINE, judge, judge_manifest, overall

# How many packages one request judges at once (each one fetches registry metadata).
PARALLEL_JUDGEMENTS = 8


def create_app(cache: Cache | None = None, client: httpx.AsyncClient | None = None, *,
               investigations: Investigations | None = None, sources: dict[str, Source] | None = None) -> FastAPI:
    """Without `investigations`, suspicious packages get the quick checks' "ask" (local runs and tests)."""
    cache = cache or cache_from_env()
    client = client or new_client()
    sources = sources_from_env() if sources is None else sources
    app = FastAPI(title="Bawabu", version=__version__, docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "version": __version__, "engine": ENGINE, "cache": cache.name,
                "investigations": bool(investigations), "private_registries": len(sources)}

    @app.get("/investigations/{inv_id}")
    async def investigation(inv_id: str) -> dict:
        """An investigation's status, events so far and result: what the report page (Step 10) shows."""
        store: Store | None = investigations.store if investigations else None
        try:
            row = await store.get(inv_id) if store and len(inv_id) <= 64 else None
        except httpx.HTTPError:  # e.g. not a UUID
            row = None
        if not row:
            raise HTTPException(404, "no such investigation")
        return {"id": inv_id, "package": {k: row.get(k) for k in ("ecosystem", "name", "version")},
                "private_registry": bool(row.get("registry")), "status": row["status"],
                "result": row.get("result"), "events": await store.events(inv_id)}

    @app.post("/check")
    async def check(request: CheckRequest) -> CheckResponse:
        unique = list({(p.ecosystem, p.name, p.version): p for p in request.packages}.values())
        limit = asyncio.Semaphore(PARALLEL_JUDGEMENTS)

        async def judge_one(package):
            async with limit:
                return await judge(package, cache, client, sources=sources, investigations=investigations)

        results = await asyncio.gather(*(judge_one(p) for p in unique))
        manifests = [judge_manifest(m) for m in request.manifests]
        verdict = overall([r.verdict for r in results] + [m.verdict for m in manifests])
        return CheckResponse(verdict=verdict, results=list(results), manifests=manifests)

    return app
