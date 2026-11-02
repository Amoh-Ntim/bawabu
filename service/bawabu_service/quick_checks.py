"""Step 3: the quick checks. Turns registry facts into a verdict in about a second, without running anything.

Known-bad (malware listing, npm security placeholder, a name that doesn't exist) is blocked. Established packages
with nothing unusual are allowed. Anything with a red flag gets "ask" for now; later steps send these to the
sandbox and the Spark investigator instead.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import Verdict
from .registry import Facts, Lookup, Missing, NoMatch, Placeholder

POPULAR_WEEKLY_DOWNLOADS = 10_000
LOW_WEEKLY_DOWNLOADS = 1_000
NEW_PACKAGE = timedelta(days=90)
ESTABLISHED_PACKAGE = timedelta(days=180)
FRESH_VERSION = timedelta(hours=72)
RECENT_VERSION = timedelta(days=30)

HOUR = 3600
DAY = 24 * HOUR
# Verdicts for young versions are re-checked sooner, so a malware report that arrives later is picked up.
YOUNG_VERSION = timedelta(days=7)

_ALARMING_DEPRECATION = re.compile(r"compromis|malicious|malware|hacked|backdoor|do not (use|install)", re.IGNORECASE)


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str
    signals: tuple[str, ...] = ()
    suggestion: str | None = None
    # How long the verdict may be cached, in seconds; 0 means don't cache.
    ttl: int = 0


def decide(
    ecosystem: str,
    name: str,
    requested: str,
    lookup: Lookup | None,
    malicious: list[str] | None,
    lookalike_of: str | None,
    suggestion: str | None,
    now: datetime,
) -> Decision:
    """`lookup` is None when the registry couldn't be reached; `malicious` is None when OSV couldn't be."""
    registry = "npm" if ecosystem == "npm" else "PyPI"
    if malicious:
        return Decision("block", f"Listed as malicious by OSV ({', '.join(malicious)}).", ttl=30 * DAY)
    if lookup is None:
        return Decision("ask", f"Bawabu couldn't reach {registry} to check this package. Try again shortly.")
    if isinstance(lookup, Missing):
        return Decision(
            "block",
            f"There is no package called {name} on {registry}. AI agents sometimes make up package names, "
            "and attackers register those names to catch them (slopsquatting).",
            suggestion=suggestion,
        )
    if isinstance(lookup, Placeholder):
        return Decision("block", f"npm took {name} down for being malicious and left a security placeholder in its place.", ttl=30 * DAY)
    if isinstance(lookup, NoMatch):
        latest = f" The latest version is {lookup.latest}." if lookup.latest else ""
        return Decision("block", f"No version of {name} matches '{requested}'.{latest}")
    return _judge_facts(lookup, malicious, lookalike_of, now)


def _judge_facts(f: Facts, malicious: list[str] | None, lookalike_of: str | None, now: datetime) -> Decision:
    age = now - f.created if f.created else None
    version_age = now - f.published if f.published else None
    downloads = f.weekly_downloads
    popular = downloads is not None and downloads >= POPULAR_WEEKLY_DOWNLOADS and age is not None and age >= ESTABLISHED_PACKAGE
    scripts = ", ".join(f.install_scripts)

    signals: list[str] = []
    if f.yanked:
        signals.append("The author withdrew (yanked) this version.")
    if f.deprecated and _ALARMING_DEPRECATION.search(f.deprecated):
        signals.append(f'The author marked this version deprecated: "{f.deprecated[:160]}"')
    if age is not None and age < NEW_PACKAGE:
        signals.append(f"The package is only {ago(age)} old.")
    if downloads is not None and downloads < LOW_WEEKLY_DOWNLOADS:
        signals.append(f"It had only {downloads:,} downloads last week.")
    if f.install_scripts:
        if f.previous_install_scripts == {}:
            signals.append(f"This version adds code that runs on install ({scripts}); the previous version had none.")
        elif f.previous_install_scripts is not None and f.previous_install_scripts != f.install_scripts:
            signals.append(f"This version changes the code that runs on install ({scripts}).")
        elif not popular:
            signals.append(f"It runs code on install ({scripts}).")
    if f.previous_provenance and f.provenance is False:
        signals.append("Earlier versions were published with provenance (built and signed by CI); this one wasn't.")
    if (f.publisher and f.previous_publishers and f.publisher not in f.previous_publishers
            and version_age is not None and version_age < RECENT_VERSION):
        signals.append(f"It was published by {f.publisher}, an account that hadn't published {f.name} before.")
    if lookalike_of:
        signals.append(f"Its name is one typo away from the popular package {lookalike_of}.")
    if malicious is None and (version_age is None or version_age < YOUNG_VERSION):
        signals.append("Bawabu couldn't check OSV's list of known malware.")
    if signals and version_age is not None and version_age < FRESH_VERSION:
        signals.append(f"This version was published {ago(version_age)} ago.")

    if signals:
        return Decision("ask", "Bawabu wants a closer look before this is installed.", tuple(signals), suggestion=lookalike_of, ttl=6 * HOUR)

    facts = []
    if age is not None:
        facts.append(f"{ago(age)} old")
    if downloads is not None:
        facts.append(f"{downloads:,} downloads last week")
    facts.append(f"same install command ({scripts}) as the previous version" if f.install_scripts else "no code runs on install")
    if version_age is not None and version_age < FRESH_VERSION:
        facts.append(f"this version is {ago(version_age)} old")
    if f.deprecated:
        facts.append("deprecated")
    young = version_age is None or version_age < YOUNG_VERSION
    return Decision("allow", f"Established package: {', '.join(facts)}.", ttl=6 * HOUR if young else 7 * DAY)


def ago(delta: timedelta) -> str:
    """A short human duration: 5 minutes, 3 hours, 12 days, 4 months, 6 years."""
    seconds = max(int(delta.total_seconds()), 0)
    for unit, size in (("year", 365 * DAY), ("month", 30 * DAY), ("day", DAY), ("hour", HOUR), ("minute", 60)):
        if seconds >= size:
            n = seconds // size
            return f"{n} {unit}{'s' if n != 1 else ''}"
    return "under a minute"
