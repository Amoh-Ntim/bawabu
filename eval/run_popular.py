"""False-positive and latency evaluation on the most popular real npm packages (latest versions), through the real
decision path. Anything not allowed is a false positive to explain.

    uv run eval/run_popular.py --top 500
"""

import argparse
import asyncio
from collections import Counter

from harness import ROOT, Engine, new_client, percentile, save, timing

from bawabu_service import registry
from bawabu_service.popular_npm import NAMES


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=500)
    ap.add_argument("--model", choices=["meta", "open"], default="meta")
    ap.add_argument("--parallel", type=int, default=6)
    args = ap.parse_args()

    names = list(NAMES)[: args.top]
    engine = Engine(args.model, lab=False, max_investigations=3)
    limit = asyncio.Semaphore(args.parallel)
    done = 0
    print(f"Top {len(names)} npm packages (most popular first), investigator {engine.model_label}")

    async with new_client() as http:
        async def one(name):
            nonlocal done
            async with limit:
                o = await engine.judge(http, name)
            done += 1
            if o.verdict != "allow" or done % 50 == 0:
                print(f"[{done}/{len(names)}] {name}@{o.version}: {o.verdict} by {o.decided_by} in {o.seconds}s", flush=True)
            return o

        outcomes = await asyncio.gather(*(one(n) for n in names))
        flagged = [o for o in outcomes if o.verdict != "allow"]
        # Re-check download counts for anything flagged: a rate-limited stats API would look like "not popular".
        downloads = {o.name: await registry.weekly_downloads(http, "npm", o.name) for o in flagged}

    verdicts = Counter(o.verdict for o in outcomes)
    layers = Counter(o.decided_by for o in outcomes)
    t = timing(outcomes)
    quick = [o.seconds for o in outcomes if o.decided_by == "quick checks"]
    summary = {"model": engine.model_label, "packages": len(outcomes), "verdicts": dict(verdicts), "decided_by": dict(layers),
               "false_positives": len(flagged), **t, "quick_median_s": percentile(quick, 50), "quick_p95_s": percentile(quick, 95)}

    print(f"\nVerdicts: {dict(verdicts)} · decided by: {dict(layers)}")
    print(f"Time: median {t['median_s']} s, p95 {t['p95_s']} s, max {t['max_s']} s "
          f"(quick checks alone: median {summary['quick_median_s']} s, p95 {summary['quick_p95_s']} s)")
    if flagged:
        print("\n| Package | Bawabu | Decided by | Weekly downloads | Why |\n|---|---|---|---|---|")
        for o in flagged:
            why = "; ".join(o.signals[:3]) or o.reason
            print(f"| `{o.name}@{o.version}` | {o.verdict} | {o.decided_by} | {downloads.get(o.name)} | {why[:220]} |")
    path = save("popular", f"top{len(outcomes)}-{args.model}", summary, list(outcomes))
    print(f"\nsaved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
