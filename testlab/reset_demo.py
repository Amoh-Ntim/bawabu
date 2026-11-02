"""Makes the hosted Bawabu service forget the test lab's practice packages, so a demo can be recorded more than once.

Bawabu remembers each verdict (a block for 30 days) and reuses a finished investigation for 24 hours, so asking about
the same practice package again returns the stored answer instantly: right for users, but a second take of the demo
would show no investigation. For test-lab packages only, this deletes:
  * their cached verdicts, and
  * their investigations from the last 24 hours (the window in which one would be reused),
except investigations linked from the README, and any still running (unless --force). Verdicts for packages from the
public npm can't be touched: everything is filtered on the test lab's registry address.

Dry run by default. From the repo root (needs SUPABASE_URL, SUPABASE_SECRET_KEY and BAWABU_REGISTRY in .env):

    uv run testlab/reset_demo.py                                   # all practice packages: shows what would go
    uv run testlab/reset_demo.py ci-build-cache-helper --yes       # forget one package
    uv run testlab/reset_demo.py --yes --warm                      # forget all, then wake the service and the registry

The local service (service/run_local.py) keeps everything in memory: restarting it already resets it.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "service"))

from bawabu_service.investigations import REUSE  # noqa: E402
from bawabu_service.registry import clean_url  # noqa: E402

SERVICE = "https://amohntim123--bawabu.us-east.modal.run"


def dotenv() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def lab_packages() -> list[str]:
    manifest = json.loads((ROOT / "testlab" / "manifest.json").read_text())
    return [p["name"] for p in manifest["packages"] if p["versions"]]


def protected_ids() -> set[str]:
    """Investigations the README links to: never deleted."""
    return set(re.findall(r"/r/([0-9a-f-]{36})", (ROOT / "README.md").read_text()))


def main() -> None:
    ap = argparse.ArgumentParser(description="Make the hosted service forget test-lab packages, for demo retakes.")
    ap.add_argument("packages", nargs="*", help="practice package names (default: all of them)")
    ap.add_argument("--yes", action="store_true", help="really delete (without it, a dry run)")
    ap.add_argument("--force", action="store_true", help="also delete investigations that are still running")
    ap.add_argument("--warm", action="store_true", help="afterwards, wake the hosted service and the practice registry")
    args = ap.parse_args()

    env = dotenv()
    for key in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "BAWABU_REGISTRY"):
        if not env.get(key):
            sys.exit(f"{key} is missing from .env")
    known = lab_packages()
    names = args.packages or known
    unknown = [n for n in names if n not in known]
    if unknown:
        sys.exit(f"Not test-lab packages: {', '.join(unknown)}. This script only resets the practice packages.")

    registry = clean_url(env["BAWABU_REGISTRY"])
    key = env["SUPABASE_SECRET_KEY"]
    headers = {"apikey": key} if key.startswith("sb_") else {"apikey": key, "Authorization": f"Bearer {key}"}
    rest = f"{env['SUPABASE_URL'].rstrip('/')}/rest/v1"
    in_names = "in.(" + ",".join(f'"{n}"' for n in names) + ")"
    since = (datetime.now(timezone.utc) - REUSE).isoformat()
    keep = protected_ids()

    with httpx.Client(timeout=30, headers=headers) as http:
        verdict_filter = {"ecosystem": "eq.npm", "registry": f"eq.{registry}", "name": in_names}
        verdicts = http.get(f"{rest}/verdicts", params={**verdict_filter, "select": "name,version,verdict"}).raise_for_status().json()
        recent = http.get(f"{rest}/investigations", params={
            "select": "id,name,version,status,created_at", "registry": f"eq.{registry}", "name": in_names,
            "created_at": f"gt.{since}", "order": "created_at.desc"}).raise_for_status().json()

        doomed, spared = [], []
        for row in recent:
            why = "linked from the README" if row["id"] in keep else "still running" if row["status"] == "running" and not args.force else None
            (spared if why else doomed).append((row, why))

        print(f"Test lab registry: {registry}")
        print(f"Cached verdicts to forget ({len(verdicts)}):")
        for v in verdicts:
            print(f"  - {v['name']}@{v['version']}: {v['verdict']}")
        print(f"Investigations from the last {int(REUSE.total_seconds() // 3600)} h to delete ({len(doomed)}):")
        for row, _ in doomed:
            print(f"  - {row['name']}@{row['version']} {row['status']} {row['created_at'][:16]} ({row['id'][:8]})")
        for row, why in spared:
            print(f"  · kept {row['name']}@{row['version']} ({row['id'][:8]}): {why}")

        if not args.yes:
            print("\nDry run: nothing deleted. Add --yes to delete.")
            return
        prefer = {"Prefer": "return=representation"}
        gone_v = http.delete(f"{rest}/verdicts", params=verdict_filter, headers=prefer).raise_for_status().json() if verdicts else []
        ids = [row["id"] for row, _ in doomed]
        gone_i = http.delete(f"{rest}/investigations", params={"id": "in.(" + ",".join(ids) + ")"},
                             headers=prefer).raise_for_status().json() if ids else []
        print(f"\nDeleted {len(gone_v)} verdict(s) and {len(gone_i)} investigation(s) (their steps go with them).")
        print("The next install of these packages starts a fresh, live investigation; watch it at " + f"{SERVICE}/live")

    if args.warm:
        with httpx.Client(timeout=120) as http:
            health = http.get(f"{SERVICE}/health").json()
            print(f"Service awake: version {health.get('version')}, investigations {health.get('investigations')}")
            auth = {"Authorization": f"Basic {env['VERDACCIO_AUTH_BASIC']}"} if env.get("VERDACCIO_AUTH_BASIC") else {}
            r = http.get(f"{registry}/{names[0]}", headers=auth)
            print(f"Practice registry awake: HTTP {r.status_code}")


if __name__ == "__main__":
    main()
