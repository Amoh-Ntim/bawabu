"""Run one package through the Bawabu sandbox X-ray and print the evidence. Needs Modal auth.

    uv run sandbox/scripts/run_sandbox.py env-loader-plus 1.0.0            # from the test lab (reads .env)
    uv run sandbox/scripts/run_sandbox.py ci-build-cache-helper 1.0.0 --ci
    uv run sandbox/scripts/run_sandbox.py date-fns-lite-utils 1.0.0 --date 2027-02-01
    uv run sandbox/scripts/run_sandbox.py left-pad 1.3.0 --registry https://registry.npmjs.org

By default it installs from the test-lab Verdaccio registry (BAWABU_REGISTRY + VERDACCIO_AUTH_BASIC in .env).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # sandbox/ on the path

from bawabu_sandbox.runner import investigate


def _dotenv(root: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    f = root / ".env"
    if not f.exists():
        return env
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip("'").strip('"')
    return env


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("version", nargs="?", default="")
    ap.add_argument("--registry", default=None, help="registry URL (default: test-lab Verdaccio from .env)")
    ap.add_argument("--ci", action="store_true", help="set CI=true and GITHUB_ACTIONS=true")
    ap.add_argument("--date", default=None, help="fake the clock, e.g. 2027-02-01")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--debug", action="store_true", help="print trigger output and sink diagnostics")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    env = _dotenv(root)
    registry = args.registry or env.get("BAWABU_REGISTRY")
    auth = None if args.registry else env.get("VERDACCIO_AUTH_BASIC")
    extra = {"CI": "true", "GITHUB_ACTIONS": "true"} if args.ci else {}

    print(f"Investigating {args.name}@{args.version or 'latest'}"
          + (f" from {registry}" if registry else " from npm")
          + (" [CI]" if args.ci else "") + (f" [date={args.date}]" if args.date else ""))
    run = investigate(
        args.name, args.version, registry=registry, registry_auth=auth,
        env=extra, fake_date=args.date, timeout=args.timeout,
    )
    if not run.ok():
        print(f"\nERROR: {run.error}")
        sys.exit(2)

    ev = run.evidence
    print(f"\n{'='*60}\nVERDICT SIGNAL: {ev.summary()}\n{'='*60}")
    print(f"duration: {ev.duration_s}s   install scripts: {run.install_scripts or 'none'}")
    print("\nsecret files read:")
    for p in ev.secret_reads or ["  (none)"]:
        print(f"  - {p}" if ev.secret_reads else p)
    print("\nnetwork attempts:")
    if ev.network:
        for n in ev.network:
            flag = "  ⚠ CANARY: " + ", ".join(n.canaries) if n.canaries else ("  (known-good)" if n.benign_destination else "")
            print(f"  - {n.scheme.upper()} {n.method} {n.host}{n.path}{flag}")
    else:
        print("  (none)")
    print("\nDNS lookups:", ", ".join(ev.dns_queries) or "(none)")
    print("notable processes:")
    for p in ev.processes or ["  (none)"]:
        print(f"  - {p}" if ev.processes else p)
    if ev.canaries_leaked:
        print("\n🔴 CANARIES LEAKED:")
        for c in ev.canaries_leaked:
            print(f"  - {c}")
    if ev.notes:
        print("\nnotes:", " ".join(ev.notes))
    if args.debug:
        print(f"\n--- diagnostics ---\nsink_ready: {run.sink_ready}")
        print("trigger output:\n" + run.trigger_output)
        print("raw sink log:\n" + (run.sink_log_raw or "(empty)"))


if __name__ == "__main__":
    main()
