import asyncio

import pytest
from fakes import FakeNet, internet, npm_doc, pypi_doc

from bawabu_service import osv, registry
from bawabu_service.registry import SOURCE_BUILD, Facts, Missing, NoMatch, Placeholder, RegistryError


def run(coro):
    return asyncio.run(coro)


VERSIONS = {v: {} for v in ["1.2.3", "1.3.0", "1.10.1", "2.0.0-beta.1", "2.0.0", "2.1.0"]}


@pytest.mark.parametrize("requested, expected", [
    ("", "2.0.0"),            # the latest tag, even though 2.1.0 is higher
    ("latest", "2.0.0"),
    ("next", "2.1.0"),
    ("1.3.0", "1.3.0"),
    ("v1.3.0", "1.3.0"),
    ("^1.2.3", "1.10.1"),
    ("~1.2", "1.2.3"),
    ("^2", "2.0.0"),          # latest satisfies the range, so npm picks it over 2.1.0
    (">=2.1", "2.1.0"),
    ("^9", None),
    ("not a range!", None),
])
def test_npm_resolution(requested, expected):
    assert registry.resolve_npm(requested, {"latest": "2.0.0", "next": "2.1.0"}, VERSIONS) == expected


RELEASES = {v: [{"packagetype": "bdist_wheel", "yanked": v == "2.31.1"}] for v in ["2.30.0", "2.31.0", "2.31.1", "2.32.0rc1", "2.32.3"]}


@pytest.mark.parametrize("requested, expected", [
    ("", "2.32.3"),
    ("==2.31.0", "2.31.0"),
    ("2.31.0", "2.31.0"),                    # uv-style name@2.31.0
    (">=2.31,<2.32", "2.31.0"),              # 2.31.1 is yanked, so pip skips it
    ("==2.31.1", "2.31.1"),                  # ...unless it's pinned exactly
    ("~=2.30", "2.32.3"),                    # no prereleases
    ('==2.31.0; python_version < "3.10"', "2.31.0"),
    ("==9.9", None),
])
def test_pypi_resolution(requested, expected):
    assert registry.resolve_pypi(requested, "2.32.3", RELEASES) == expected


def test_npm_facts_compare_with_the_previous_version():
    net = FakeNet()
    net.npm["@acme/widget"] = npm_doc("@acme/widget", [
        {"version": "1.0.0", "days": 400, "provenance": True, "publisher": "alice"},
        {"version": "1.1.0", "days": 100, "provenance": True, "publisher": "bob"},
        {"version": "1.2.0", "days": 1, "scripts": {"postinstall": "node x.js", "test": "jest"}, "publisher": "mallory"},
    ])
    f = run(registry.lookup(net.client(), "npm", "@acme/widget", ""))
    assert isinstance(f, Facts) and f.version == "1.2.0"
    assert f.install_scripts == {"postinstall": "node x.js"} and f.previous_install_scripts == {}
    assert f.provenance is False and f.previous_provenance is True
    assert f.publisher == "mallory" and f.previous_publishers == {"alice", "bob"}
    assert net.requests[0].url.raw_path == b"/@acme%2Fwidget"


def test_npm_native_builds_count_as_install_code():
    net = FakeNet()
    net.npm["native"] = npm_doc("native", [{"version": "1.0.0", "days": 10, "gypfile": True}])
    assert run(registry.lookup(net.client(), "npm", "native", "")).install_scripts == {"install": "node-gyp rebuild (binding.gyp)"}


def test_npm_missing_placeholder_nomatch_and_errors():
    net = internet()
    assert isinstance(run(registry.lookup(net.client(), "npm", "no-such-pkg", "")), Missing)
    assert isinstance(run(registry.lookup(net.client(), "npm", "crossenv", "")), Placeholder)
    assert run(registry.lookup(net.client(), "npm", "react", "^99")) == NoMatch(latest="19.2.0")
    net.down.add("registry.npmjs.org")
    with pytest.raises(RegistryError):
        run(registry.lookup(net.client(), "npm", "react", ""))


def test_pypi_facts_and_source_only_builds():
    net = FakeNet()
    net.pypi["sneaky"] = pypi_doc("sneaky", {"1.0": {"days": 300}, "1.1": {"days": 2, "wheel": False}}, latest="1.1")
    f = run(registry.lookup(net.client(), "pypi", "sneaky", ""))
    assert f.version == "1.1" and f.install_scripts == SOURCE_BUILD and f.previous_install_scripts == {}
    assert round((f.published - f.created).days) == 298
    assert isinstance(run(registry.lookup(net.client(), "pypi", "nope", "")), Missing)


def test_weekly_downloads():
    net = internet()
    client = net.client()
    assert run(registry.weekly_downloads(client, "npm", "react")) == 60_000_000
    assert run(registry.weekly_downloads(client, "pypi", "requests")) == 330_000_000
    assert run(registry.weekly_downloads(client, "npm", "unknown")) is None


def test_osv_reports_only_malicious_entries_for_the_version():
    net = internet()
    net.osv[("npm", "@ctrl/tinycolor")].append(("GHSA-xxxx", []))
    client = net.client()
    assert run(osv.malicious_ids(client, "npm", "@ctrl/tinycolor", "4.1.1")) == ["MAL-2025-47141"]
    assert run(osv.malicious_ids(client, "npm", "@ctrl/tinycolor", "4.1.0")) == []
    assert run(osv.malicious_ids(client, "npm", "@ctrl/tinycolor", None)) == ["MAL-2025-47141"]
