"""Bawabu on your own machine, with your own API keys: the whole service in one process.

Compared with the hosted service (modal_app.py):
  * verdicts and investigations are kept in memory, so there's no Supabase to set up;
  * investigations run in this process instead of as a Modal function;
  * the test lab is served from testlab/packages at /lab, so the attack samples work without our hosted registry or
    its password (and only Bawabu can download them, never npm: see lab_registry.py);
  * the sandbox is optional. It runs on Modal, so it needs a Modal account (`modal setup`), and it can only reach
    packages on the internet, not this machine's test lab. Without it, investigations are the diff plus Muse Spark
    reading the code, and the hard rule about leaked secrets can't fire.

Started by service/run_local.py.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

from . import investigations as inv_mod
from . import lab_registry
from .api import create_app
from .cache import MemoryCache
from .investigations import Investigations, MemoryStore
from .net import new_client
from .registry import Source, sources_from_env
from .screener import Screener
from .verdicts import ENGINE

log = logging.getLogger(__name__)

META = ("https://api.meta.ai/v1", "muse-spark-1.3", "Muse Spark (Meta Model API)")
OPEN = ("https://inference.baseten.co/v1", "meta-models/muse-spark-open-1026", "Muse Spark Open (open weights, Baseten)")
PACKAGES = Path(__file__).resolve().parents[2] / "testlab" / "packages"
PARALLEL_INVESTIGATIONS = 2


@dataclass
class Settings:
    meta_key: str | None = None
    baseten_key: str | None = None
    port: int = 8787
    open_weights: bool = False  # investigate everything with Muse Spark Open
    sandbox: bool = False
    packages_dir: Path = PACKAGES
    # For tests: ready-made model clients ({"meta": ..., "open": ...}) instead of real OpenAI clients.
    clients: dict[str, Any] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def lab_url(self) -> str:
        return f"{self.base_url}/lab"


class LabTransport(httpx.AsyncBaseTransport):
    """Sends the service's own requests for the test lab straight into the app (no network round trip, and no
    deadlock waiting on itself); everything else goes out to the internet."""

    def __init__(self, lab_url: str) -> None:
        self.lab_url = lab_url
        self.app: FastAPI | None = None
        self.outside = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self.app is not None and str(request.url).startswith(self.lab_url + "/"):
            return await httpx.ASGITransport(app=self.app).handle_async_request(request)
        return await self.outside.handle_async_request(request)

    async def aclose(self) -> None:
        await self.outside.aclose()


def describe(s: Settings) -> dict[str, str]:
    """What's switched on, for the startup banner."""
    meta = bool(s.meta_key or "meta" in s.clients)
    opened = bool(s.baseten_key or "open" in s.clients)
    investigator = OPEN[2] if (s.open_weights or not meta) and opened else META[2]
    return {
        "investigator": investigator,
        "screener": "Muse Spark Open" if opened else "off (no BASETEN_API_KEY)",
        "sandbox": "on (Modal), for packages on the internet" if s.sandbox else "off: investigations read the code, nothing is run",
    }


def build(s: Settings) -> FastAPI:
    if not (s.meta_key or s.baseten_key or s.clients):
        raise ValueError("Set META_API_KEY (Muse Spark) or BASETEN_API_KEY (Muse Spark Open).")

    def client(which: str) -> Any:
        if which not in s.clients:
            from openai import OpenAI

            url, key = (META[0], s.meta_key) if which == "meta" else (OPEN[0], s.baseten_key)
            s.clients[which] = OpenAI(base_url=url, api_key=key, timeout=120)
        return s.clients[which]

    have_meta = bool(s.meta_key or "meta" in s.clients)
    have_open = bool(s.baseten_key or "open" in s.clients)

    def spark_for(open_requested: bool) -> tuple[Any, str]:
        if (open_requested or s.open_weights or not have_meta) and have_open:
            return client("open"), OPEN[1]
        return client("meta"), META[1]

    token = secrets.token_urlsafe(24)
    lab = Source(s.lab_url, (("authorization", f"Bearer {token}"),), show_code=True)
    transport = LabTransport(s.lab_url)
    http = new_client(transport)

    sandbox_fn = None
    if s.sandbox:
        from bawabu_sandbox.runner import investigate as sandbox_run

        def sandbox_fn(name, version, registry_url, auth, env, date):
            if registry_url and registry_url.startswith(s.lab_url):
                return {"summary": "Not run: the cloud sandbox can't reach the test lab on this machine, so this package "
                                   "was judged from its code."}
            return sandbox_run(name, version, registry=registry_url, registry_auth=auth, env=env, fake_date=date).report()

    store, cache = MemoryStore(), MemoryCache()
    slots = asyncio.Semaphore(PARALLEL_INVESTIGATIONS)
    running: set[asyncio.Task] = set()

    async def spawn(inv_id: str, payload: dict) -> None:
        spark, model = spark_for(bool(payload.get("open_weights")))

        async def go() -> None:
            async with slots:
                await inv_mod.run(inv_id, payload, store=store, cache=cache, http=http, spark=spark, model=model,
                                  sandbox=sandbox_fn, engine=ENGINE)

        task = asyncio.create_task(go())
        running.add(task)  # keep a reference so the task isn't garbage-collected mid-run
        task.add_done_callback(running.discard)

    screener = Screener(client("open"), OPEN[1]) if have_open else None
    app = create_app(cache, http, investigations=Investigations(store, spawn), sources={**sources_from_env(), s.lab_url: lab},
                     screener=screener, public_feed=True)
    app.include_router(lab_registry.router(s.packages_dir, s.lab_url, token))
    transport.app = app
    return app
