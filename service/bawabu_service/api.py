"""The HTTP API. Run locally with:

    uv run --env-file .env uvicorn --app-dir service bawabu_service.api:create_app --factory --port 8787
"""

import asyncio
import os
import secrets

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response

from . import __version__
from .brand import MASCOT_PNG
from .cache import Cache, cache_from_env
from .investigations import Investigations, Store
from .models import CheckRequest, CheckResponse
from .net import new_client
from .registry import Source, sources_from_env
from .report_page import PAGE
from .screener import Screener
from .verdicts import ENGINE, judge, judge_manifest, overall

# How many packages one request judges at once (each one fetches registry metadata).
PARALLEL_JUDGEMENTS = 8
HIDDEN = "(hidden: private registry)"


def redact(result: dict | None, events: list[dict]) -> tuple[dict | None, list[dict]]:
    """For packages from a private registry: keep the verdict and the story, drop the code (snippets, quotes, tool
    output), since anyone with the link can open the report."""
    if result:
        result = {**result, "snippets": {}}
        for key in ("evidence", "rejected"):
            result[key] = [{**e, "quote": None} for e in result.get(key) or []]
        for key in ("sandbox",):
            if result.get(key):
                result[key] = {**result[key], "output": None}
        result["reruns"] = [{**r, "output": None} for r in result.get("reruns") or []]
    events = [{**e, "title": HIDDEN} if e.get("kind") == "result" else e for e in events]
    return result, events


def page_response() -> HTMLResponse:
    """The report page with a fresh nonce: only its own script may run, and it may only talk to this service
    (and load the mascot from it)."""
    nonce = secrets.token_urlsafe(16)
    return HTMLResponse(PAGE.replace("__NONCE__", nonce), headers={
        "Content-Security-Policy": f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; "
                                   "img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; "
                                   "frame-ancestors 'none'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    })


def create_app(cache: Cache | None = None, client: httpx.AsyncClient | None = None, *,
               investigations: Investigations | None = None, sources: dict[str, Source] | None = None,
               screener: Screener | None = None, public_feed: bool | None = None) -> FastAPI:
    """Without `investigations`, suspicious packages get the quick checks' "ask" (local runs and tests).
    `public_feed` (default: BAWABU_PUBLIC_FEED=1) lists recent investigations for the /live page; it shows package
    names from every client, so it's off unless the operator turns it on."""
    public_feed = os.environ.get("BAWABU_PUBLIC_FEED") == "1" if public_feed is None else public_feed
    cache = cache or cache_from_env()
    client = client or new_client()
    sources = sources_from_env() if sources is None else sources
    app = FastAPI(title="Bawabu", version=__version__, docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "version": __version__, "engine": ENGINE, "cache": cache.name,
                "investigations": bool(investigations), "screener": bool(screener), "private_registries": len(sources)}

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
        result, events = row.get("result"), await store.events(inv_id)
        known = sources.get(row.get("registry") or "")
        if row.get("registry") and not (known and known.show_code):
            result, events = redact(result, events)
        return {"id": inv_id, "package": {k: row.get(k) for k in ("ecosystem", "name", "version")},
                "private_registry": bool(row.get("registry")), "code_hidden": bool(row.get("registry")) and not (known and known.show_code),
                "status": row["status"], "result": result, "events": events}

    @app.get("/investigations")
    async def recent(limit: int = 10) -> list[dict]:
        if not (public_feed and investigations):
            raise HTTPException(404, "the live feed is off")
        rows = await investigations.store.recent(max(1, min(limit, 25)))
        return [{k: r.get(k) for k in ("id", "name", "version", "status", "verdict", "created_at")} | {"private_registry": bool(r.get("registry"))}
                for r in rows]

    @app.get("/r/{inv_id}", response_class=HTMLResponse, include_in_schema=False)
    async def report(inv_id: str) -> HTMLResponse:
        return page_response()

    @app.get("/live", response_class=HTMLResponse, include_in_schema=False)
    async def live() -> HTMLResponse:
        return page_response()

    @app.get("/mascot.png", include_in_schema=False)
    async def mascot() -> Response:
        return Response(MASCOT_PNG, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"})

    @app.post("/check")
    async def check(request: CheckRequest) -> CheckResponse:
        unique = list({(p.ecosystem, p.name, p.version): p for p in request.packages}.values())
        limit = asyncio.Semaphore(PARALLEL_JUDGEMENTS)

        async def judge_one(package):
            async with limit:
                return await judge(package, cache, client, sources=sources, investigations=investigations,
                                   screener=screener, open_weights=request.open_weights)

        results = await asyncio.gather(*(judge_one(p) for p in unique))
        manifests = [judge_manifest(m) for m in request.manifests]
        verdict = overall([r.verdict for r in results] + [m.verdict for m in manifests])
        return CheckResponse(verdict=verdict, results=list(results), manifests=manifests)

    return app
