"""The report page (/r/{id}, /live), the opt-in live feed, and what private-registry reports hide."""

import asyncio
import re

from fakes import internet
from fastapi.testclient import TestClient

from bawabu_service import report_page
from bawabu_service.api import create_app
from bawabu_service.cache import MemoryCache
from bawabu_service.investigations import Investigations, MemoryStore
from bawabu_service.registry import Source

RESULT = {
    "verdict": "block", "confidence": "high", "reason": "Reads your npm token on install and posts it away.",
    "evidence": [{"type": "code", "file": "setup.js", "line": 3, "quote": 'fs.readFileSync(".npmrc")', "detail": "reads the token", "verified": True}],
    "rejected": [{"type": "code", "file": "x.js", "line": 1, "quote": "secret stuff", "detail": "made up", "why_rejected": "no such file"}],
    "snippets": {"setup.js:3": {"start": 1, "lines": ["const fs = require('fs');", "", 'fs.readFileSync(".npmrc")']}},
    "sandbox": {"summary": "Exfiltration confirmed", "output": "postinstall printed the token"},
    "reruns": [{"summary": "x", "output": "more output", "conditions": {"env": {"CI": "true"}}}],
    "rules": ["Canary secret left the sandbox"],
}


def service(public_feed=False, sources=None):
    store = MemoryStore()

    async def spawn(inv_id, payload):
        pass

    app = create_app(MemoryCache(), internet().client(), investigations=Investigations(store, spawn), sources=sources or {}, public_feed=public_feed)
    return TestClient(app), store


def seed(store, registry=""):
    async def go():
        inv_id = await store.create("npm", registry, "env-loader-plus", "1.0.0")
        await store.add_event(inv_id, 0, {"kind": "tool", "title": "Reading setup.js", "t": 1.0})
        await store.add_event(inv_id, 1, {"kind": "result", "title": 'fs.readFileSync(".npmrc")', "t": 1.2})
        await store.finish(inv_id, "done", RESULT)
        return inv_id
    return asyncio.run(go())


def test_report_page_is_served_with_a_strict_policy_and_a_matching_nonce():
    client, _ = service()
    for path in ("/r/some-id", "/live"):
        r = client.get(path)
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
        csp = r.headers["content-security-policy"]
        nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
        assert f'<script nonce="{nonce}">' in r.text and "__NONCE__" not in r.text
        assert "default-src 'none'" in csp and "connect-src 'self'" in csp and "frame-ancestors 'none'" in csp
        assert r.headers["x-content-type-options"] == "nosniff"
    assert client.get("/r/a").headers["content-security-policy"] != client.get("/r/a").headers["content-security-policy"]


def test_page_never_inserts_package_text_as_html():
    assert "innerHTML" not in report_page.PAGE and "insertAdjacentHTML" not in report_page.PAGE and "document.write" not in report_page.PAGE


def test_public_report_shows_code_and_story():
    client, store = service()
    inv_id = seed(store)
    body = client.get(f"/investigations/{inv_id}").json()
    assert body["private_registry"] is False
    assert body["result"]["evidence"][0]["quote"] == 'fs.readFileSync(".npmrc")'
    assert body["result"]["snippets"]["setup.js:3"]["lines"][2] == 'fs.readFileSync(".npmrc")'
    assert body["events"][1]["title"] == 'fs.readFileSync(".npmrc")'


def test_private_registry_report_hides_code_but_keeps_the_verdict():
    client, store = service()
    inv_id = seed(store, registry="https://lab.example")
    body = client.get(f"/investigations/{inv_id}").json()
    r = body["result"]
    assert body["private_registry"] is True and r["verdict"] == "block" and r["reason"].startswith("Reads your npm token")
    assert r["snippets"] == {} and r["evidence"][0]["quote"] is None and r["rejected"][0]["quote"] is None
    assert r["sandbox"]["output"] is None and r["reruns"][0]["output"] is None
    assert r["evidence"][0]["file"] == "setup.js" and r["evidence"][0]["line"] == 3  # where, not what
    assert body["events"][0]["title"] == "Reading setup.js" and body["events"][1]["title"].startswith("(hidden")
    assert ".npmrc\")" not in str(body)


def test_a_registry_marked_show_code_keeps_its_code():
    """The test lab's reports may show code (our own fixtures); other private registries never do."""
    lab = "https://lab.example"
    client, store = service(sources={lab: Source(lab, (), show_code=True)})
    body = client.get(f"/investigations/{seed(store, registry=lab)}").json()
    assert body["private_registry"] is True and body["code_hidden"] is False
    assert body["result"]["snippets"]["setup.js:3"] and body["result"]["evidence"][0]["quote"]
    other = seed(store, registry="https://npm.corp.example")
    assert client.get(f"/investigations/{other}").json()["code_hidden"] is True


def test_live_feed_is_off_unless_turned_on():
    client, store = service(public_feed=False)
    seed(store)
    assert client.get("/investigations").status_code == 404
    client, store = service(public_feed=True)
    inv_id = seed(store, registry="https://lab.example")
    rows = client.get("/investigations?limit=5").json()
    assert rows[0]["id"] == inv_id and rows[0]["name"] == "env-loader-plus" and rows[0]["verdict"] == "block"
    assert rows[0]["private_registry"] is True and "registry" not in rows[0]  # never the registry's address
