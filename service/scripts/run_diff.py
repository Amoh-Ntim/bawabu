"""Run the diff engine on packages and print what changed since the previous version. Nothing is executed.

    uv run service/scripts/run_diff.py docs-gen-postinstall@2.0.0 --lab     # from the test-lab registry (.env)
    uv run service/scripts/run_diff.py esbuild left-pad@1.3.0               # from the public npm
    uv run service/scripts/run_diff.py docs-gen-postinstall@2.0.0 --lab --diff   # also print the code diffs
"""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "service"))

from bawabu_service import diff  # noqa: E402
from bawabu_service.net import new_client  # noqa: E402

ICON = {"high": "🔴", "medium": "🟠", "low": "⚪"}


def dotenv() -> dict[str, str]:
    env: dict[str, str] = {}
    path = ROOT / ".env"
    for line in path.read_text().splitlines() if path.exists() else []:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip("'").strip('"')
    return env


def split(spec: str) -> tuple[str, str]:
    at = spec.rfind("@")
    return (spec[:at], spec[at + 1:]) if at > 0 else (spec, "latest")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("packages", nargs="+", help="name or name@version")
    ap.add_argument("--lab", action="store_true", help="use the test-lab Verdaccio registry from .env")
    ap.add_argument("--diff", action="store_true", help="print the unified diffs too")
    args = ap.parse_args()

    source = diff.Source()
    if args.lab:
        env = dotenv()
        source = diff.Source(env["BAWABU_REGISTRY"], (("authorization", f"Basic {env['VERDACCIO_AUTH_BASIC']}"),))

    async with new_client() as client:
        for spec in args.packages:
            name, version = split(spec)
            try:
                r = await diff.analyze(client, name, version, source)
            except Exception as exc:
                print(f"\n### {spec}: ERROR {type(exc).__name__}: {exc}")
                continue
            since = f"vs {r.previous}" if r.previous else "first release"
            print(f"\n### {name}@{r.version} ({since}) — risk: {r.risk.upper()}")
            if r.previous:
                print(f"    files: +{len(r.added)} added, ~{len(r.changed)} changed, -{len(r.removed)} removed")
            for s in sorted(r.signals, key=lambda s: (not (s.new or not r.previous), -diff.SEVERITY_RANK[s.severity])):
                tag = "" if (s.new or not r.previous) else "  (unchanged)"
                print(f"    {ICON[s.severity]} {s.cite()}{tag}")
                if s.excerpt:
                    print(f"         │ {s.excerpt}")
            for note in r.notes:
                print(f"    note: {note}")
            if args.diff:
                for path, text in r.diffs.items():
                    print(f"\n--- diff {path} ---\n{text}")


if __name__ == "__main__":
    asyncio.run(main())
