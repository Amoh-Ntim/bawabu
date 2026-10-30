"""Run the quick checks + the open-weights screener (Muse Spark Open on Baseten) on packages, without the
investigation, and show what the screener decided and why. Needs BASETEN_API_KEY in .env.

    uv run service/scripts/run_screener.py --lab docs-gen-postinstall@1.0.0 markdown-tiny-render
    uv run service/scripts/run_screener.py --discover 8          # little-used real npm packages from npm search
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "service"))

from openai import OpenAI  # noqa: E402

from bawabu_service.cache import MemoryCache  # noqa: E402
from bawabu_service.models import Package  # noqa: E402
from bawabu_service.net import new_client  # noqa: E402
from bawabu_service.registry import Source, clean_url  # noqa: E402
from bawabu_service.screener import Screener  # noqa: E402
from bawabu_service.verdicts import judge  # noqa: E402

MODEL = "meta-models/muse-spark-open-1026"
DISCOVER_QUERIES = ["string format", "color convert", "date helper", "array utils", "slug", "env config", "logger tiny", "markdown"]


def dotenv() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'").strip('"')
    return env


async def discover(http, count: int) -> list[str]:
    """Real npm packages with few downloads: the kind the quick checks flag and the screener should mostly clear."""
    found: list[str] = []
    for query in DISCOVER_QUERIES:
        r = await http.get("https://registry.npmjs.org/-/v1/search", params={"text": query, "size": 50})
        for obj in r.json().get("objects", []):
            weekly = (obj.get("downloads") or {}).get("weekly")
            name = obj["package"]["name"]
            if weekly is not None and weekly < 300 and name not in found:
                found.append(name)
                break
        if len(found) >= count:
            break
    return found


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("packages", nargs="*")
    ap.add_argument("--lab", action="store_true")
    ap.add_argument("--discover", type=int, default=0)
    args = ap.parse_args()

    env = dotenv()
    decisions: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record):
            if record.getMessage().startswith("screener:"):
                decisions.append(record.getMessage())

    log = logging.getLogger("bawabu_service.verdicts")
    log.setLevel(logging.INFO)
    log.addHandler(Capture())

    sources: dict[str, Source] = {}
    registry = None
    if args.lab:
        registry = clean_url(env["BAWABU_REGISTRY"])
        sources = {registry: Source(registry, (("authorization", f"Basic {env['VERDACCIO_AUTH_BASIC']}"),))}
    screener = Screener(OpenAI(base_url="https://inference.baseten.co/v1", api_key=env["BASETEN_API_KEY"], timeout=60), MODEL)
    cache = MemoryCache()
    async with new_client() as http:
        names = list(args.packages) + (await discover(http, args.discover) if args.discover else [])
        for spec in names:
            at = spec.rfind("@")
            name, version = (spec[:at], spec[at + 1:]) if at > 0 else (spec, "")
            decisions.clear()
            t = time.monotonic()
            r = await judge(Package(ecosystem="npm", name=name, version=version, registry=registry), cache, http,
                            sources=sources, screener=screener)
            screen = decisions[-1].split(" -> ", 1)[1] if decisions else "not screened (quick checks decided)"
            print(f"\n### {name}@{r.version}: {r.verdict.upper()}  ({time.monotonic() - t:.1f}s)")
            print(f"    screener: {screen}")
            if r.verdict != "allow":
                for s in r.signals[:3]:
                    print(f"    flag: {s}")


if __name__ == "__main__":
    asyncio.run(main())
