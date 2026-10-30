"""How a package gets its verdict: the cache first, then the quick checks (Step 3), and for anything they find
suspicious, an investigation (sandbox + diff + Muse Spark, Step 7).

ENGINE identifies the checks that made a verdict. Lookups only trust verdicts from MIN_ENGINE or later, so older
verdicts are judged again when the checks improve: engine 1's "ask" verdicts now get investigated.
"""

import asyncio
import dataclasses
import logging
import re
from datetime import datetime, timezone

import httpx

from . import osv, popular, quick_checks, registry
from .cache import Cache, CachedVerdict
from .investigations import Investigations
from .models import Manifest, ManifestResult, Package, PackageResult, Verdict
from .registry import Source
from .screener import Screener

# How long a screener clearance is trusted: short, because it skipped the sandbox.
SCREENED_TTL = 24 * 3600

log = logging.getLogger(__name__)

ENGINE = 2
MIN_ENGINE = 2

_NPM_EXACT = re.compile(r"[=v]?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]*)?)")
_PYPI_EXACT = re.compile(r"(?:===?\s*)?([0-9][0-9A-Za-z.!+-]*)")


def exact_version(package: Package) -> str | None:
    """The exact version requested, or None for "latest", a tag or a range (those are resolved first)."""
    match = (_NPM_EXACT if package.ecosystem == "npm" else _PYPI_EXACT).fullmatch(package.version.strip())
    return match.group(1) if match else None


async def judge(package: Package, cache: Cache, client: httpx.AsyncClient, now: datetime | None = None, *,
                sources: dict[str, Source] | None = None, investigations: Investigations | None = None,
                screener: Screener | None = None, open_weights: bool = False, cache_asks: bool = True) -> PackageResult:
    """`cache_asks=False` for dependency checks: a dependency's quick "ask" must not be cached, or a later direct
    install of it would get that "ask" back instead of an investigation."""
    now = now or datetime.now(timezone.utc)
    source = registry.source_for(package.ecosystem, package.registry, sources or {})
    if source is None:
        host = registry.clean_url(package.registry or "") or package.registry
        return _result(package, None, CachedVerdict(
            "ask", f"{package.name} comes from {host}, a private registry Bawabu can't read. If the user trusts this "
            "registry, they can add the package (or its @scope/*) to the allowlist in .muse/bawabu.json.", ENGINE), cached=False)
    reg = source.key
    exact = exact_version(package)
    if exact and (hit := await _cached(cache, package, exact, reg)):
        return _result(package, exact, hit, cached=True)

    try:
        lookup: registry.Lookup | None = await registry.lookup(client, package.ecosystem, package.name, package.version, source)
    except Exception:
        log.exception("registry lookup failed for %s %s", package.ecosystem, package.name)
        lookup = None
    facts = lookup if isinstance(lookup, registry.Facts) else None
    version = facts.version if facts else None
    if version and version != exact and (hit := await _cached(cache, package, version, reg)):
        return _result(package, version, hit, cached=True)

    # Ask OSV about this exact version; ask about the whole package only when it (or the version) is gone,
    # since a deleted malicious package is exactly what OSV remembers and the registry no longer shows.
    # OSV and download counts describe the *public* package of that name, so a private one skips them.
    osv_version = version or exact
    gone = isinstance(lookup, (registry.Missing, registry.Placeholder, registry.NoMatch))
    malicious, downloads, names = await asyncio.gather(
        _malicious(client, package, osv_version) if source.public and (osv_version or gone) else _no_ids(),
        registry.weekly_downloads(client, package.ecosystem, package.name) if facts and source.public else _nothing(),
        popular.for_ecosystem(client, package.ecosystem),
    )
    if facts:
        facts = dataclasses.replace(facts, weekly_downloads=downloads)
    lookalike = names.lookalike(package.name) if (facts and names) else None
    missing = isinstance(lookup, registry.Missing)
    suggestion = await popular.suggest(client, package.ecosystem, package.name, names) if missing and source.public else None

    decision = quick_checks.decide(package.ecosystem, package.name, package.version, facts or lookup, malicious, lookalike, suggestion, now)
    signals = list(decision.signals)
    if decision.verdict == "ask" and facts and screener and package.ecosystem == "npm":
        async def dependency(name: str, wanted: str) -> str:
            dep = Package(ecosystem="npm", name=name, version=wanted, registry=package.registry)
            return (await judge(dep, cache, client, now, sources=sources, cache_asks=False)).verdict

        screen = await screener.screen(package.name, facts, signals, source, client, dependency)
        log.info("screener: %s@%s -> %s (%s, %ss): %s", package.name, facts.version, screen.decision, screen.by, screen.duration_s, screen.reason)
        if screen.allow:
            cleared = CachedVerdict("allow", f"Cleared by Bawabu's open-weights screener (Muse Spark Open): {screen.reason}",
                                    ENGINE, decision.signals)
            try:
                await cache.put(package.ecosystem, package.name, facts.version, cleared, SCREENED_TTL, registry=reg)
            except Exception:
                log.exception("cache write failed for %s@%s", package.name, facts.version)
            return _result(package, facts.version, cleared, cached=False)
        if screen.by == "model":
            signals.append(f"The open-weights screener wanted a closer look: {screen.reason}")

    if decision.verdict == "ask" and facts and investigations and package.ecosystem == "npm":
        # Suspicious: the investigation decides (and caches its own verdict), not the quick checks.
        try:
            outcome = await investigations.verdict("npm", package.name, facts.version, source, signals, open_weights=open_weights)
        except Exception:
            log.exception("couldn't run the investigation for %s@%s", package.name, facts.version)
        else:
            return PackageResult(
                ecosystem=package.ecosystem, name=package.name, requested=package.version, version=facts.version,
                verdict=outcome.verdict, reason=outcome.reason, signals=list(outcome.signals or decision.signals),
                suggestion=outcome.suggestion or decision.suggestion, cached=False, report_id=outcome.report_id,
                pending=outcome.pending)

    verdict = CachedVerdict(decision.verdict, decision.reason, ENGINE, decision.signals, decision.suggestion)
    if version and decision.ttl and (cache_asks or decision.verdict != "ask"):
        try:
            await cache.put(package.ecosystem, package.name, version, verdict, decision.ttl, registry=reg)
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


async def _cached(cache: Cache, package: Package, version: str, reg: str = "") -> CachedVerdict | None:
    try:
        return await cache.get(package.ecosystem, package.name, version, MIN_ENGINE, registry=reg)
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
