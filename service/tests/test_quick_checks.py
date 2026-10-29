from datetime import timedelta

from fakes import NOW

from bawabu_service.quick_checks import DAY, HOUR, ago, decide
from bawabu_service.registry import Facts, Missing, NoMatch, Placeholder


def facts(**overrides) -> Facts:
    """An established, popular package with nothing unusual about it."""
    base = dict(
        ecosystem="npm", name="pkg", version="2.0.0", created=NOW - timedelta(days=1000), published=NOW - timedelta(days=60),
        weekly_downloads=500_000, install_scripts={}, previous_install_scripts={}, provenance=True, previous_provenance=True,
        publisher="alice", previous_publishers=frozenset({"alice"}),
    )
    return Facts(**{**base, **overrides})


def check(lookup=None, malicious=(), lookalike=None, suggestion=None, requested=""):
    return decide("npm", "pkg", requested, lookup, None if malicious is None else list(malicious), lookalike, suggestion, NOW)


def test_an_established_package_is_allowed_and_cached_for_a_week():
    d = check(facts())
    assert d.verdict == "allow" and d.signals == ()
    assert "2 years old" in d.reason and "500,000 downloads last week" in d.reason and "no code runs on install" in d.reason
    assert d.ttl == 7 * DAY


def test_a_fresh_version_of_a_popular_package_is_allowed_but_rechecked_soon():
    d = check(facts(published=NOW - timedelta(hours=5)))
    assert d.verdict == "allow" and "this version is 5 hours old" in d.reason
    assert d.ttl == 6 * HOUR


def test_known_bad_is_blocked():
    assert check(facts(), malicious=["MAL-2025-1"]).verdict == "block"
    assert "MAL-2025-1" in check(Missing(), malicious=["MAL-2025-1"]).reason
    placeholder = check(Placeholder())
    assert placeholder.verdict == "block" and "security placeholder" in placeholder.reason and placeholder.ttl == 30 * DAY


def test_a_made_up_name_is_blocked_with_a_suggestion_and_not_cached():
    d = check(Missing(), suggestion="react-datepicker")
    assert d.verdict == "block" and "slopsquatting" in d.reason and d.suggestion == "react-datepicker" and d.ttl == 0


def test_a_version_that_does_not_exist_is_blocked():
    d = check(NoMatch(latest="2.0.0"), requested="^9")
    assert d.verdict == "block" and "No version of pkg matches '^9'" in d.reason and "2.0.0" in d.reason


def test_an_unreachable_registry_asks_and_is_not_cached():
    d = check(None)
    assert d.verdict == "ask" and d.ttl == 0


def signals(**overrides):
    return " | ".join(check(facts(**overrides)).signals)


def test_red_flags_ask_with_reasons():
    young = check(facts(created=NOW - timedelta(days=3), published=NOW - timedelta(days=3), weekly_downloads=12))
    assert young.verdict == "ask" and young.ttl == 6 * HOUR
    assert young.signals == ("The package is only 3 days old.", "It had only 12 downloads last week.")
    assert "adds code that runs on install (postinstall); the previous version had none" in signals(install_scripts={"postinstall": "node x.js"})
    assert "changes the code that runs on install" in signals(install_scripts={"postinstall": "b"}, previous_install_scripts={"postinstall": "a"})
    assert "provenance" in signals(provenance=False)
    assert "published by mallory, an account that hadn't published pkg before" in signals(publisher="mallory", published=NOW - timedelta(days=2))
    assert "yanked" in signals(yanked=True)
    assert "compromised" in signals(deprecated="This version was compromised, use 2.0.1")


def test_install_code_is_fine_for_a_popular_package_that_always_had_it():
    d = check(facts(install_scripts={"postinstall": "node install.js"}, previous_install_scripts={"postinstall": "node install.js"}))
    assert d.verdict == "allow" and "same install code (postinstall)" in d.reason
    unpopular = check(facts(weekly_downloads=3_000, install_scripts={"install": "x"}, previous_install_scripts={"install": "x"}))
    assert unpopular.verdict == "ask" and "It runs code on install (install)." in unpopular.signals


def test_old_publisher_changes_and_ordinary_deprecations_are_not_red_flags():
    assert check(facts(publisher="bob")).verdict == "allow"  # the version is two months old
    d = check(facts(deprecated="Use pkg2 instead"))
    assert d.verdict == "allow" and "deprecated" in d.reason


def test_a_lookalike_name_asks_and_suggests_the_real_package():
    d = check(facts(weekly_downloads=40), lookalike="react")
    assert d.verdict == "ask" and d.suggestion == "react"
    assert "Its name is one typo away from the popular package react." in d.signals


def test_without_osv_young_versions_ask_but_old_ones_pass():
    assert check(facts(published=NOW - timedelta(days=2)), malicious=None).verdict == "ask"
    assert check(facts(), malicious=None).verdict == "allow"


def test_freshness_is_mentioned_alongside_other_red_flags():
    d = check(facts(published=NOW - timedelta(hours=7), provenance=False))
    assert d.signals[-1] == "This version was published 7 hours ago."


def test_ago():
    assert [ago(timedelta(seconds=s)) for s in (5, 120, 3 * HOUR, 2 * DAY, 45 * DAY, 800 * DAY)] == [
        "under a minute", "2 minutes", "3 hours", "2 days", "1 month", "2 years",
    ]
