"""Evaluation harness: judges packages through Bawabu's real decision path (quick checks → open-weights screener →
investigation with the sandbox and Muse Spark), the same `judge()` the service runs, but with a fresh in-memory cache
so nothing is replayed, and with investigations run in-process instead of spawned on Modal.

Needs .env: META_API_KEY, BASETEN_API_KEY, and for the test lab BAWABU_REGISTRY + VERDACCIO_AUTH_BASIC. The sandbox
runs on Modal (needs `modal setup`).
"""

from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "service"), str(ROOT / "sandbox")]

from openai import OpenAI  # noqa: E402

from bawabu_sandbox.runner import investigate as sandbox_run  # noqa: E402
from bawabu_service import investigations as inv_mod  # noqa: E402
from bawabu_service.cache import MemoryCache  # noqa: E402
from bawabu_service.investigations import Investigations, MemoryStore  # noqa: E402
from bawabu_service.models import Package  # noqa: E402
from bawabu_service.net import new_client  # noqa: E402
from bawabu_service.registry import Source, clean_url  # noqa: E402
from bawabu_service.screener import Screener  # noqa: E402
from bawabu_service.verdicts import ENGINE, judge  # noqa: E402

MODELS = {
    "meta": ("https://api.meta.ai/v1", "META_API_KEY", "muse-spark-1.3", "Muse Spark (Meta Model API)"),
    "open": ("https://inference.baseten.co/v1", "BASETEN_API_KEY", "meta-models/muse-spark-open-1026", "Muse Spark Open (open weights, Baseten)"),
}
RESULTS = ROOT / "eval" / "results"


def dotenv() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'").strip('"')
    return env


@dataclass
class Outcome:
    name: str
    version: str | None
    verdict: str
    reason: str
    seconds: float
    decided_by: str  # quick checks | screener | investigation
    signals: list[str] = field(default_factory=list)
    screener: str | None = None
    steps: int | None = None
    reruns: int | None = None
    verified_evidence: int | None = None
    rejected_evidence: int | None = None
    rules: list[str] = field(default_factory=list)
    error: str | None = None


class RecordingScreener(Screener):
    """The real screener, remembering what it decided per package."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.decisions: dict[str, str] = {}

    async def screen(self, name, facts, signals, source, http, judge_dependency):
        result = await super().screen(name, facts, signals, source, http, judge_dependency)
        self.decisions[f"{name}@{facts.version}"] = f"{result.decision} ({result.by}): {result.reason}"
        return result


class Engine:
    def __init__(self, model: str = "meta", lab: bool = False, sandbox: bool = True, max_investigations: int = 3) -> None:
        env = dotenv()
        url, key, self.model, self.model_label = MODELS[model]
        self.spark = OpenAI(base_url=url, api_key=env[key], timeout=120)
        self.screener = RecordingScreener(OpenAI(base_url=MODELS["open"][0], api_key=env["BASETEN_API_KEY"], timeout=60), MODELS["open"][2])
        self.sources: dict[str, Source] = {}
        self.registry: str | None = None
        if lab:
            self.registry = clean_url(env["BAWABU_REGISTRY"])
            self.sources = {self.registry: Source(self.registry, (("authorization", f"Basic {env['VERDACCIO_AUTH_BASIC']}"),))}
        self.use_sandbox = sandbox
        self.slots = asyncio.Semaphore(max_investigations)
        self.store = MemoryStore()
        self.cache = MemoryCache()

    def _sandbox(self, name, version, registry_url, auth, env, date) -> dict:
        return sandbox_run(name, version, registry=registry_url, registry_auth=auth, env=env, fake_date=date).report()

    async def judge(self, http, name: str, version: str = "") -> Outcome:
        started = time.monotonic()
        investigations = Investigations(self.store, lambda inv_id, payload: self._spawn(http, inv_id, payload), budget_s=900, poll_s=1)
        try:
            r = await judge(Package(ecosystem="npm", name=name, version=version, registry=self.registry), self.cache, http,
                            sources=self.sources, investigations=investigations, screener=self.screener)
        except Exception as exc:  # one broken package mustn't stop the run
            return Outcome(name, version or None, "error", "", round(time.monotonic() - started, 1), "error", error=f"{type(exc).__name__}: {exc}")
        seconds = round(time.monotonic() - started, 1)
        # Packages run in parallel, so find this package's own investigation by name and version.
        mine = [row for row in self.store.rows.values() if row["name"] == name and row["version"] == r.version]
        screen = self.screener.decisions.get(f"{name}@{r.version}")
        out = Outcome(name, r.version, r.verdict, r.reason, seconds, "quick checks", list(r.signals), screen)
        if mine:
            res = mine[-1].get("result") or {}
            out.decided_by = "investigation"
            out.steps, out.reruns = res.get("steps"), len(res.get("reruns") or [])
            out.verified_evidence = sum(1 for e in res.get("evidence") or [] if e.get("verified"))
            out.rejected_evidence = len(res.get("rejected") or [])
            out.rules, out.error = list(res.get("rules") or []), res.get("error")
        elif screen and screen.startswith("allow"):
            out.decided_by = "screener"
        return out

    async def _spawn(self, http, inv_id: str, payload: dict) -> None:
        async def go() -> None:
            async with self.slots:
                await inv_mod.run(inv_id, payload, store=self.store, cache=self.cache, http=http, spark=self.spark,
                                  model=self.model, sandbox=self._sandbox if self.use_sandbox else None, engine=ENGINE)
        asyncio.create_task(go())


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(p / 100 * (len(ordered) - 1))))]


def save(kind: str, label: str, meta: dict, outcomes: list[Outcome]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    path = RESULTS / f"{kind}-{label}-{stamp}.json"
    path.write_text(json.dumps({"meta": meta, "outcomes": [asdict(o) for o in outcomes]}, indent=1))
    return path


def timing(outcomes: list[Outcome]) -> dict:
    secs = [o.seconds for o in outcomes if o.verdict != "error"]
    return {"median_s": round(statistics.median(secs), 1) if secs else None, "p95_s": percentile(secs, 95), "max_s": max(secs, default=None)}


__all__ = ["Engine", "Outcome", "new_client", "save", "timing", "percentile", "MODELS"]
