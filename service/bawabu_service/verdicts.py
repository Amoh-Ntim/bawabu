"""How a package gets its verdict: the cache first, then the quick checks (Step 3).

ENGINE identifies the checks that made a verdict. Lookups only trust verdicts from MIN_ENGINE or later, so the
Step 2 skeleton's blanket "allow" verdicts (engine 0) are never reused.
"""

import asyncio
import dataclasses
import logging
import re
from datetime import datetime, timezone

import httpx

from . import osv, popular, quick_checks, registry
from .cache import Cache, CachedVerdict
from .models import Manifest, ManifestResult, Package, PackageResult, Verdict

log = logging.getLogger(__name__)

ENGINE = 1
MIN_ENGINE = 1

_NPM_EXACT = re.compile(r"[=v]?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]*)?)")
_PYPI_EXACT = re.compile(r"(?:===?\s*)?([0-9][0-9A-Za-z.!+-]*)")


def exact_version(package: Package) -> str | None:
    """The exact version requested, or None for "latest", a tag or a range (those are resolved first)."""
    match = (_NPM_EXACT if package.ecosystem == "npm" else _PYPI_EXACT).fullmatch(package.version.strip())
    return match.group(1) if match else None


async def judge(package: Package, cache: Cache, client: httpx.AsyncClient, now: datetime | None = None) -> PackageResult:
    now = now or datetime.now(timezone.utc)
    exact = exact_version(package)
    if exact and (hit := await _cached(cache, package, exact)):
        return _result(package, exact, hit, cached=True)

    try:
        lookup: registry.Lookup | None = await registry.lookup(client, package.ecosystem, package.name, package.version)
    except Exception:
        log.exception("registry lookup failed for %s %s", package.ecosystem, package.name)
        lookup = None
    facts = lookup if isinstance(lookup, registry.Facts) else None
    version = facts.version if facts else None
    if version and version != exact and (hit := await _cached(cache, package, version)):
        return _result(package, version, hit, cached=True)

    # Ask OSV about this exact version; ask about the whole package only when it (or the version) is gone,
    # since a deleted malicious package is exactly what OSV remembers and the registry no longer shows.
    osv_version = version or exact
    gone = isinstance(lookup, (registry.Missing, registry.Placeholder, registry.NoMatch))
    malicious, downloads, names = await asyncio.gather(
        _malicious(client, package, osv_version) if (osv_version or gone) else _no_ids(),
        registry.weekly_downloads(client, package.ecosystem, package.name) if facts else _nothing(),
        popular.for_ecosystem(client, package.ecosystem),
    )
    if facts:
        facts = dataclasses.replace(facts, weekly_downloads=downloads)
    lookalike = names.lookalike(package.name) if (facts and names) else None
    suggestion = await popular.suggest(client, package.ecosystem, package.name, names) if isinstance(lookup, registry.Missing) else None

    decision = quick_checks.decide(package.ecosystem, package.name, package.version, facts or lookup, malicious, lookalike, suggestion, now)
    verdict = CachedVerdict(decision.verdict, decision.reason, ENGINE, decision.signals, decision.suggestion)
    if version and decision.ttl:
        try:
            await cache.put(package.ecosystem, package.name, version, verdict, decision.ttl)
        except Exception:
            log.exception("cache write failed for %s@%s", package.name, version)
    return _result(package, version, verdict, cached=False)


def judge_manifest(manifest: Manifest) -> ManifestResult:
    return ManifestResult(
        ecosystem=manifest.ecosystem,
        manager=manifest.manager,
        verdict="allow",
        reason="Whole-project installs aren't checked yet.",
    )


def overall(verdicts: list[Verdict]) -> Verdict:
    """Any block blocks; otherwise any ask asks."""
    return "block" if "block" in verdicts else "ask" if "ask" in verdicts else "allow"


async def _cached(cache: Cache, package: Package, version: str) -> CachedVerdict | None:
    try:
        return await cache.get(package.ecosystem, package.name, version, MIN_ENGINE)
    except Exception:
        log.exception("cache lookup failed; judging %s@%s fresh", package.name, version)
        return None


async def _malicious(client: httpx.AsyncClient, package: Package, version: str | None) -> list[str] | None:
    try:
        return await osv.malicious_ids(client, package.ecosystem, package.name, version)
    except Exception:
        log.warning("OSV lookup failed for %s", package.name, exc_info=True)
        return None


async def _nothing() -> None:
    return None


async def _no_ids() -> list[str]:
    return []


def _result(package: Package, version: str | None, verdict: CachedVerdict, cached: bool) -> PackageResult:
    return PackageResult(
        ecosystem=package.ecosystem,
        name=package.name,
        requested=package.version,
        version=version,
        verdict=verdict.verdict,
        reason=verdict.reason,
        signals=list(verdict.signals),
        suggestion=verdict.suggestion,
        cached=cached,
    )
