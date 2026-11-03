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
        assert "img-src 'self'" in csp
        assert r.headers["x-content-type-options"] == "nosniff"
    assert client.get("/r/a").headers["content-security-policy"] != client.get("/r/a").headers["content-security-policy"]


def test_mascot_is_served_by_the_service():
    client, _ = service()
    r = client.get("/mascot.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.content.startswith(b"\x89PNG") and r.headers["x-content-type-options"] == "nosniff"


def test_page_never_inserts_package_text_as_html():
    assert "innerHTML" not in report_page.PAGE and "insertAdjacentHTML" not in report_page.PAGE and "document.write" not in report_page.PAGE


def test_report_has_no_external_assets_and_all_scripts_use_the_nonce():
    page = report_page.PAGE
    # The only thing it loads is the mascot, from this service.
    assert re.findall(r'<(?:script|img|link|iframe)\b[^>]*?(?:src|href)\s*=\s*"([^"]*)"', page, re.I) == ["/mascot.png"] * 2
    assert "@import" not in page and "url(" not in page
    assert re.findall(r"<script[^>]*>", page) == ['<script nonce="__NONCE__">'] * 2
    assert page.index('localStorage.getItem("bawabu-theme")') < page.index("<style>")


def test_both_themes_define_all_colors_with_accessible_contrast():
    page = report_page.PAGE
    themes = [re.search(r':root\[data-theme="' + theme + r'"\]\s*\{([^}]+)\}', page).group(1)
              for theme in ("light", "dark")]
    colors = [dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", theme)) for theme in themes]
    tokens = [set(re.findall(r"--([\w-]+):", theme)) - {"mono"} for theme in themes]
    assert tokens[0] == tokens[1]
    used = set(re.findall(r"var\(--([\w-]+)", page)) - {"mono", "shadow", "tone", "tint", "progress", "ring-tone"}
    assert used <= tokens[0]

    def luminance(color):
        channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        return sum(weight * (c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4)
                   for c, weight in zip(channels, (.2126, .7152, .0722)))

    for theme in colors:
        pairs = [(name, name + "-bg") for name in ("danger", "caution", "low", "safe", "brand", "spark")]
        pairs += [("text", bg) for bg in ("bg", "card", "surface", "code", "code-hit")]
        pairs += [("muted", bg) for bg in ("bg", "card", "surface", "code", "code-hit")]
        for fg, bg in pairs:
            a, b = sorted([luminance(theme[fg]), luminance(theme[bg])])
            assert (b + .05) / (a + .05) >= 4.5, (fg, bg, theme[fg], theme[bg])


def test_risk_mapping_legacy_fallback_and_unverified_state_are_present():
    page = report_page.PAGE
    for level in ("none", "low", "medium", "high"):
        assert f'.risk-{level}' in page and f'{level}: "risk-{level}"' in page
    assert 'Array.isArray(d.signal_items)' in page
    assert 'for (const text of d.signals)' in page
    assert '.unverified { color: var(--caution); background: var(--caution-bg); }' in page
    assert 'e.verified ? "verified" : "unverified"' in page
    assert 'prefers-reduced-motion: reduce' in page
    assert '[hidden] { display: none !important; }' in page


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


def test_a_failed_sandbox_run_is_never_shown_as_clean():
    assert "!rep.error && !(rep.network || []).length" in report_page.PAGE


def test_live_can_leave_out_earlier_checks_for_a_recording():
    page = report_page.PAGE
    assert 'new URLSearchParams(location.search).has("fresh")' in page
    assert "onlyNew ? all.filter(" in page
