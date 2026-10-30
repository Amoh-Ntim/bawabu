"""Test-lab evaluation: every practice package (testlab/manifest.json) through the real decision path, compared with
the verdict it should get. Reports catch rate, false positives, which layer decided, and time.

    uv run eval/run_lab.py --model meta     # investigator: Muse Spark on Meta's Model API
    uv run eval/run_lab.py --model open     # investigator: Muse Spark Open (open weights) on Baseten
"""

import argparse
import asyncio
import json

from harness import ROOT, Engine, new_client, save, timing


def cases() -> list[dict]:
    manifest = json.loads((ROOT / "testlab" / "manifest.json").read_text())
    out = []
    for p in manifest["packages"]:
        versions = p["versions"] or [""]
        for v in versions:
            expect = p["expect"][v] if isinstance(p["expect"], dict) else p["expect"]
            out.append({"id": str(p["id"]), "name": p["name"], "version": v, "expect": expect,
                        "malicious": expect == "block", "technique": p["technique"]})
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["meta", "open"], default="meta")
    ap.add_argument("--parallel", type=int, default=4)
    args = ap.parse_args()

    engine = Engine(args.model, lab=True, max_investigations=args.parallel)
    todo = cases()
    limit = asyncio.Semaphore(args.parallel)
    print(f"Test lab: {len(todo)} cases, investigator {engine.model_label}\n")

    async with new_client() as http:
        async def one(case):
            async with limit:
                o = await engine.judge(http, case["name"], case["version"])
                mark = "✅" if o.verdict == case["expect"] else "❌"
                print(f"{mark} {case['name']}@{o.version or case['version'] or '-'}: {o.verdict} (expected {case['expect']}) "
                      f"by {o.decided_by} in {o.seconds}s", flush=True)
                return case, o

        pairs = await asyncio.gather(*(one(c) for c in todo))

    malicious = [(c, o) for c, o in pairs if c["malicious"]]
    benign = [(c, o) for c, o in pairs if not c["malicious"]]
    caught = sum(1 for _, o in malicious if o.verdict == "block")
    false_pos = sum(1 for _, o in benign if o.verdict != "allow")
    correct = sum(1 for c, o in pairs if o.verdict == c["expect"])
    t = timing([o for _, o in pairs])
    summary = {"model": engine.model_label, "cases": len(pairs), "correct": correct, "malicious": len(malicious), "caught": caught,
               "benign": len(benign), "false_positives": false_pos, **t}

    print("\n| # | Package | Expected | Bawabu | Decided by | Time | Spark tool calls | Re-runs | Verified evidence |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c, o in pairs:
        ok = "✅" if o.verdict == c["expect"] else "❌"
        print(f"| {c['id']} | `{c['name']}{'@' + c['version'] if c['version'] else ''}` | {c['expect']} | {ok} {o.verdict} | "
              f"{o.decided_by} | {o.seconds} s | {o.steps if o.steps is not None else '-'} | {o.reruns if o.reruns is not None else '-'} | "
              f"{o.verified_evidence if o.verified_evidence is not None else '-'} |")
    print(f"\nCaught {caught}/{len(malicious)} malicious · {false_pos}/{len(benign)} false positives · "
          f"{correct}/{len(pairs)} correct · median {t['median_s']} s, max {t['max_s']} s")
    path = save("lab", args.model, summary, [o for _, o in pairs])
    print(f"saved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
