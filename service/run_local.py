"""Run the whole Bawabu service on your own machine, with your own API keys. From the repo root:

    export META_API_KEY=...        # Meta Model API key: Muse Spark investigates
    export BASETEN_API_KEY=...     # optional: Muse Spark Open screens packages (and can investigate)
    uv run service/run_local.py [--port 8787] [--open-weights] [--sandbox]

Keys can also go in a .env file at the repo root (see .env.example). Nothing is stored outside this process.
--sandbox runs suspicious packages in the Modal sandbox (needs `uv run modal setup` first).
"""

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "service"), str(ROOT / "sandbox")]

import uvicorn  # noqa: E402

from bawabu_service.local import Settings, build, describe  # noqa: E402


def keys() -> dict[str, str]:
    """Environment variables first, then .env."""
    found: dict[str, str] = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if v.strip().strip("'\""):
                    found[k.strip()] = v.strip().strip("'\"")
    found.update({k: v for k, v in os.environ.items() if v})
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the Bawabu service locally with your own API keys.")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--open-weights", action="store_true", help="investigate with Muse Spark Open (needs BASETEN_API_KEY)")
    ap.add_argument("--sandbox", action="store_true", help="run suspicious packages in the Modal sandbox (needs `modal setup`)")
    args = ap.parse_args()

    k = keys()
    settings = Settings(meta_key=k.get("META_API_KEY"), baseten_key=k.get("BASETEN_API_KEY"), port=args.port,
                        open_weights=args.open_weights, sandbox=args.sandbox)
    if args.open_weights and not settings.baseten_key:
        sys.exit("--open-weights needs BASETEN_API_KEY.")
    try:
        app = build(settings)
    except ValueError as exc:
        sys.exit(str(exc))

    base = settings.base_url
    on = describe(settings)
    print(f"""
Bawabu is running at {base}
  investigator  {on['investigator']}
  screener      {on['screener']}
  sandbox       {on['sandbox']}
  test lab      {settings.lab_url}  (the practice packages; only Bawabu can download them)
  live view     {base}/live

Try it from another terminal (after installing the CLI, see README):
  bawabu scan react-datepickr --local                 a made-up name: blocked, with a suggestion
  bawabu scan left-pad --local                        an established package: allowed
  bawabu scan ci-build-cache-helper --local --lab     a practice attack: Muse Spark investigates
  bawabu demo                                         a project for Muse Code, wired to this service
""", flush=True)
    logging.basicConfig(level=logging.WARNING)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
