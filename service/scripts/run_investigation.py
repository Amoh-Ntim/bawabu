"""Run the full investigation on one package from the laptop: diff + sandbox (on Modal) + Muse Spark, with the
event stream printed live. Needs .env (META_API_KEY; for --lab also BAWABU_REGISTRY + VERDACCIO_AUTH_BASIC).

    uv run service/scripts/run_investigation.py ci-build-cache-helper --lab
    uv run service/scripts/run_investigation.py string-format-pro-utils@1.0.0 --lab --model muse-spark-1.3
    uv run service/scripts/run_investigation.py some-package --provider baseten     # open weights
"""

import argparse
import asyncio
import concurrent.futures
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "service"), str(ROOT / "sandbox")]

from openai import OpenAI  # noqa: E402

from bawabu_sandbox.runner import investigate as sandbox_run  # noqa: E402
from bawabu_service import diff  # noqa: E402
from bawabu_service.investigator import Material, investigate  # noqa: E402
from bawabu_service.net import new_client  # noqa: E402

PROVIDERS = {
    "meta": ("https://api.meta.ai/v1", "META_API_KEY", "muse-spark-1.3"),
    "baseten": ("https://inference.baseten.co/v1", "BASETEN_API_KEY", "meta-models/muse-spark-open-1026"),
}
ICON = {"start": "🔎", "thinking": "💭", "tool": "🛠 ", "result": "   ↳", "rerun": "🔁", "rejected": "🗑 ", "rule": "⚖️ ",
        "verdict": "🏁", "error": "❌"}


def dotenv() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'").strip('"')
    return env


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("package", help="name or name@version")
    ap.add_argument("--lab", action="store_true")
    ap.add_argument("--provider", choices=PROVIDERS, default="meta")
    ap.add_argument("--model")
    ap.add_argument("--effort", default="low", help="reasoning effort: minimal, low, medium, high")
    ap.add_argument("--no-sandbox", action="store_true", help="skip the sandbox (code reading only)")
    args = ap.parse_args()

    env = dotenv()
    at = args.package.rfind("@")
    name, version = (args.package[:at], args.package[at + 1:]) if at > 0 else (args.package, "latest")
    registry = env["BAWABU_REGISTRY"] if args.lab else None
    auth = env.get("VERDACCIO_AUTH_BASIC") if args.lab else None
    source = diff.Source(registry, (("authorization", f"Basic {auth}"),)) if args.lab else diff.Source()
    base_url, key_var, default_model = PROVIDERS[args.provider]
    model = args.model or default_model
    client = OpenAI(base_url=base_url, api_key=env[key_var], timeout=120)
    t0 = time.monotonic()

    def stamp() -> str:
        return f"[{time.monotonic() - t0:5.1f}s]"

    def sandbox(ver: str, extra_env: dict | None = None, date: str | None = None) -> dict:
        run = sandbox_run(name, ver, registry=registry, registry_auth=auth, env=extra_env, fake_date=date)
        return run.report()

    print(f"{stamp()} gathering evidence for {name}@{version}: diff, then sandbox")

    async def get_diff():
        async with new_client() as http:
            return await diff.analyze(http, name, version, source)

    report = asyncio.run(get_diff())
    print(f"{stamp()} diff: {report.version} vs {report.previous or '(first release)'}, risk {report.risk}")
    with concurrent.futures.ThreadPoolExecutor() as pool:
        first = None if args.no_sandbox else pool.submit(sandbox, report.version).result()
    if first:
        print(f"{stamp()} sandbox: {first['summary']}")

    m = Material("npm", name, report.version, diff=report, sandbox=first,
                 metadata={"version": report.version, "previous_version": report.previous,
                           "install_scripts": first.get("install_scripts") if first else None,
                           "signals": [s.cite() for s in report.signals if s.severity == "high"][:5]})

    def rerun(extra_env: dict, date: str | None) -> dict:
        r = sandbox(report.version, extra_env, date)
        return r

    def emit(event: dict) -> None:
        print(f"{stamp()} {ICON.get(event['kind'], '•')} {event.get('title', '')}")

    print(f"{stamp()} handing over to {model} ({args.provider}, effort {args.effort})\n")
    inv = investigate(m, client, model, rerun=None if args.no_sandbox else rerun, emit=emit, reasoning_effort=args.effort)

    print(f"\n{'=' * 70}\n{inv.verdict.upper()} ({inv.confidence})  —  {inv.reason}")
    if inv.safe_alternative:
        print(f"Safe alternative: {inv.safe_alternative}")
    print(f"{inv.steps} tool calls, {len(inv.reruns)} sandbox re-runs, investigator {inv.duration_s}s, total {time.monotonic() - t0:.0f}s")
    for e in inv.evidence:
        where = f" {e.file}:{e.line}" if e.file else ""
        print(f"  ✅ [{e.type}]{where} {e.detail}" + (f'\n       "{e.quote}"' if e.quote else ""))
    for e in inv.rejected:
        print(f"  🗑  [{e.type}] {e.detail}  — rejected: {e.why_rejected}")
    for r in inv.rules:
        print(f"  ⚖️  hard rule: {r}")
    if inv.error:
        print(f"  error: {inv.error}")


if __name__ == "__main__":
    main()
