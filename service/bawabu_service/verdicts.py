"""How a package gets its verdict.

Step 2 is a skeleton: every package is allowed, by engine 0. Step 3 replaces `_decide` with real quick
checks and bumps ENGINE and MIN_ENGINE to 1, so the skeleton's cached "allow" verdicts are never trusted.
"""

import logging
import re

from .cache import Cache, CachedVerdict
from .models import Manifest, ManifestResult, Package, PackageResult, Verdict

log = logging.getLogger(__name__)

ENGINE = 0
MIN_ENGINE = 0

_NPM_EXACT = re.compile(r"[=v]?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]*)?)")
_PYPI_EXACT = re.compile(r"===?\s*([0-9A-Za-z.!+-]+)")


def exact_version(package: Package) -> str | None:
    """The exact version requested, or None for "latest", a tag or a range (Step 3 resolves those)."""
    match = (_NPM_EXACT if package.ecosystem == "npm" else _PYPI_EXACT).fullmatch(package.version.strip())
    return match.group(1) if match else None


async def judge(package: Package, cache: Cache) -> PackageResult:
    version = exact_version(package)
    if version:
        try:
            hit = await cache.get(package.ecosystem, package.name, version, MIN_ENGINE)
        except Exception:
            log.exception("cache lookup failed; judging %s@%s fresh", package.name, version)
            hit = None
        if hit:
            return _result(package, version, hit, cached=True)

    verdict = _decide(package, version)
    if version:
        try:
            await cache.put(package.ecosystem, package.name, version, verdict)
        except Exception:
            log.exception("cache write failed for %s@%s", package.name, version)
    return _result(package, version, verdict, cached=False)


def judge_manifest(manifest: Manifest) -> ManifestResult:
    return ManifestResult(
        ecosystem=manifest.ecosystem,
        manager=manifest.manager,
        verdict="allow",
        reason="Whole-project installs aren't checked yet (Bawabu service skeleton).",
    )


def overall(verdicts: list[Verdict]) -> Verdict:
    """Any block blocks; otherwise any ask asks."""
    return "block" if "block" in verdicts else "ask" if "ask" in verdicts else "allow"


def _decide(package: Package, version: str | None) -> CachedVerdict:
    return CachedVerdict(verdict="allow", reason="No checks run yet (Bawabu service skeleton).", engine=ENGINE)


def _result(package: Package, version: str | None, verdict: CachedVerdict, cached: bool) -> PackageResult:
    return PackageResult(
        ecosystem=package.ecosystem,
        name=package.name,
        requested=package.version,
        version=version,
        verdict=verdict.verdict,
        reason=verdict.reason,
        cached=cached,
    )
