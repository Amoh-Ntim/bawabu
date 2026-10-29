"""Step 3 smoke test: real packages through the deployed (or a local) service's quick checks.

    uv run python service/scripts/smoke_checks.py [service-url]

Each package is checked twice: the first answer is judged fresh, the second should come from the cache
(unless it's a made-up name or the verdict isn't cacheable).
"""

import sys
import time

import httpx

URL = (sys.argv[1] if len(sys.argv) > 1 else "https://amohntim123--bawabu.us-east.modal.run").rstrip("/")

CASES = [
    # (ecosystem, name, requested version, expected verdict, why it's here)
    ("npm", "react", "", "allow", "hugely popular"),
    ("npm", "express", "^4", "allow", "a range, resolved like npm does"),
    ("npm", "esbuild", "", "allow", "popular, has always had an install script"),
    ("npm", "@types/node", "", "allow", "one of the largest packuments on npm"),
    ("npm", "fancy-date-pickr", "", "block", "made-up name (the plan's example)"),
    ("npm", "react-datepickr", "", "block", "made-up name, one typo from a real one: suggest react-datepicker"),
    ("npm", "prisma-clinet", "", "block", "made-up name: suggest @prisma/client"),
    ("npm", "crossenv", "", "block", "npm security placeholder (2017 typosquat)"),
    ("npm", "@ctrl/tinycolor", "4.1.1", "block", "Shai-Hulud worm version, deleted from npm, MAL in OSV"),
    ("npm", "@ctrl/tinycolor", "", "allow", "same package, current clean version"),
    ("npm", "react", "^99", "block", "a version that doesn't exist"),
    ("pypi", "requests", "", "allow", "hugely popular"),
    ("pypi", "requests", "==2.31.0", "allow", "exact pin"),
    ("pypi", "reqeusts-fake-zz", "", "block", "made-up name"),
]


def main() -> None:
    print(f"service: {URL}\n{httpx.get(f'{URL}/health', timeout=60).json()}\n")
    failures = 0
    with httpx.Client(timeout=120) as client:
        for ecosystem, name, version, expected, why in CASES:
            timings, result = [], None
            for _ in range(2):
                start = time.monotonic()
                body = client.post(f"{URL}/check", json={"client_version": "smoke", "packages": [{"ecosystem": ecosystem, "name": name, "version": version}]}).json()
                timings.append(time.monotonic() - start)
                result = body["results"][0]
            ok = result["verdict"] == expected
            failures += not ok
            label = f"{name}@{version}" if version else name
            print(f"[{'PASS' if ok else 'FAIL'}] {ecosystem:4} {label:28} -> {result['verdict']:5} (expected {expected})  "
                  f"{timings[0]:.2f}s fresh, {timings[1]:.2f}s {'cached' if result['cached'] else 'not cached'}   # {why}")
            print(f"       version={result['version']}  reason: {result['reason']}")
            for signal in result.get("signals", []):
                print(f"         - {signal}")
            if result.get("suggestion"):
                print(f"         did you mean: {result['suggestion']}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} as expected")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
