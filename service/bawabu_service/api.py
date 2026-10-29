"""The HTTP API. Run locally with:

    uv run --env-file .env uvicorn --app-dir service bawabu_service.api:create_app --factory --port 8787
"""

import asyncio

import httpx
from fastapi import FastAPI

from . import __version__
from .cache import Cache, cache_from_env
from .models import CheckRequest, CheckResponse
from .net import new_client
from .verdicts import ENGINE, judge, judge_manifest, overall

# How many packages one request judges at once (each one fetches registry metadata).
PARALLEL_JUDGEMENTS = 8


def create_app(cache: Cache | None = None, client: httpx.AsyncClient | None = None) -> FastAPI:
    cache = cache or cache_from_env()
    client = client or new_client()
    app = FastAPI(title="Bawabu", version=__version__, docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "version": __version__, "engine": ENGINE, "cache": cache.name}

    @app.post("/check")
    async def check(request: CheckRequest) -> CheckResponse:
        unique = list({(p.ecosystem, p.name, p.version): p for p in request.packages}.values())
        limit = asyncio.Semaphore(PARALLEL_JUDGEMENTS)

        async def judge_one(package):
            async with limit:
                return await judge(package, cache, client)

        results = await asyncio.gather(*(judge_one(p) for p in unique))
        manifests = [judge_manifest(m) for m in request.manifests]
        verdict = overall([r.verdict for r in results] + [m.verdict for m in manifests])
        return CheckResponse(verdict=verdict, results=list(results), manifests=manifests)

    return app
