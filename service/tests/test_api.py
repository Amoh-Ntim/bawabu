import asyncio
import json
from datetime import timedelta

import httpx
from fakes import NOW, internet, npm_doc
from fastapi.testclient import TestClient

from bawabu_service import verdicts
from bawabu_service.api import create_app
from bawabu_service.cache import CachedVerdict, MemoryCache, SupabaseCache


def service(net=None, cache=None) -> tuple[TestClient, object, MemoryCache]:
    net = net or internet()
    cache = cache or MemoryCache()
    return TestClient(create_app(cache, net.client())), net, cache


def check(c: TestClient, *packages: dict, manifests: list | None = None) -> dict:
    response = c.post("/check", json={"client_version": "0.1.0", "packages": list(packages), "manifests": manifests or []})
    assert response.status_code == 200, response.text
    return response.json()


def npm(name: str, version: str = "") -> dict:
    return {"ecosystem": "npm", "name": name, "version": version}


def test_health():
    c, _, _ = service()
    assert c.get("/health").json() == {"ok": True, "version": "0.3.0", "engine": verdicts.ENGINE, "cache": "memory",
                                       "investigations": False, "private_registries": 0}


def test_react_is_allowed_with_its_resolved_version_and_then_cached():
    c, net, _ = service()
    first = check(c, npm("react"))
    assert first["verdict"] == "allow"
    result = first["results"][0]
    assert result["version"] == "19.2.0" and result["requested"] == "" and result["cached"] is False
    assert result["reason"].startswith("Established package:")
    second = check(c, npm("react"))["results"][0]
    assert second["cached"] is True and second["version"] == "19.2.0"
    # An exact version that's cached skips the registry entirely.
    registry_calls = net.hits("registry.npmjs.org")
    assert check(c, npm("react", "19.2.0"))["results"][0]["cached"] is True
    assert net.hits("registry.npmjs.org") == registry_calls


def test_a_made_up_name_is_blocked_with_a_suggestion():
    c, _, cache = service()
    result = check(c, npm("fancy-date-pickr"))["results"][0]
    assert result["verdict"] == "block" and "There is no package called fancy-date-pickr on npm" in result["reason"]
    assert result["suggestion"] == "react-datepicker"
    assert cache._items == {}  # made-up names aren't cached: someone could register the name later


def test_a_deleted_malicious_version_is_blocked_by_osv():
    c, _, _ = service()
    result = check(c, npm("@ctrl/tinycolor", "4.1.1"))["results"][0]
    assert result["verdict"] == "block" and "MAL-2025-47141" in result["reason"]
    assert check(c, npm("@ctrl/tinycolor", "4.1.0"))["verdict"] == "allow"


def test_an_npm_security_placeholder_is_blocked():
    c, _, _ = service()
    assert "security placeholder" in check(c, npm("crossenv"))["results"][0]["reason"]


def test_a_risky_new_package_asks_with_its_red_flags():
    c, _, _ = service()
    body = check(c, npm("fresh-helper"))
    result = body["results"][0]
    assert body["verdict"] == "ask" and result["verdict"] == "ask"
    assert "The package is only 3 days old." in result["signals"]
    assert "It had only 12 downloads last week." in result["signals"]
    assert any("adds code that runs on install (postinstall)" in s or "runs code on install" in s for s in result["signals"])


def test_lookalike_names_ask_and_suggest_the_real_package():
    net = internet()
    net.npm["raect"] = npm_doc("raect", [{"version": "1.0.0", "days": 400}])
    net.downloads[("npm", "raect")] = 50_000
    c, _, _ = service(net)
    result = check(c, npm("raect"))["results"][0]
    assert result["verdict"] == "ask" and result["suggestion"] == "react"


def test_pypi():
    c, _, _ = service()
    allowed = check(c, {"ecosystem": "pypi", "name": "requests", "version": "==2.31.0"})["results"][0]
    assert allowed["verdict"] == "allow" and allowed["version"] == "2.31.0"
    made_up = check(c, {"ecosystem": "pypi", "name": "reqeusts", "version": ""})["results"][0]
    assert made_up["verdict"] == "block" and made_up["suggestion"] == "requests"


def test_an_unreachable_registry_asks_and_nothing_is_cached():
    net = internet()
    net.down.add("registry.npmjs.org")
    c, _, cache = service(net)
    result = check(c, npm("react"))["results"][0]
    assert result["verdict"] == "ask" and "couldn't reach npm" in result["reason"]
    assert cache._items == {}


def test_skeleton_verdicts_and_expired_verdicts_are_judged_again():
    clock = [NOW]
    cache = MemoryCache(clock=lambda: clock[0])
    asyncio.run(cache.put("npm", "left-pad", "1.3.0", CachedVerdict("block", "skeleton said so", 0), 3600))
    c, _, _ = service(cache=cache)
    result = check(c, npm("left-pad", "1.3.0"))["results"][0]
    assert result["cached"] is False and result["verdict"] == "allow"  # the engine-0 verdict was ignored
    assert check(c, npm("left-pad", "1.3.0"))["results"][0]["cached"] is True
    clock[0] = NOW + timedelta(days=8)  # past the one-week lifetime of an old version's verdict
    assert check(c, npm("left-pad", "1.3.0"))["results"][0]["cached"] is False


def test_block_wins_and_duplicates_are_judged_once():
    c, _, _ = service()
    body = check(c, npm("left-pad"), npm("crossenv"), npm("crossenv"))
    assert body["verdict"] == "block"
    assert [r["name"] for r in body["results"]] == ["left-pad", "crossenv"]


def test_manifests_still_pass_with_a_note():
    c, _, _ = service()
    body = check(c, manifests=[{"ecosystem": "npm", "manager": "npm"}])
    assert body["verdict"] == "allow" and "aren't checked yet" in body["manifests"][0]["reason"]


def test_bad_input_is_rejected():
    c, _, _ = service()
    for package in [{"ecosystem": "maven", "name": "x"}, {"ecosystem": "npm", "name": ""}]:
        assert c.post("/check", json={"client_version": "0.1.0", "packages": [package]}).status_code == 422


def test_a_broken_cache_does_not_break_checks():
    class BrokenCache(MemoryCache):
        name = "broken"

        async def get(self, *args):
            raise RuntimeError("database down")

        async def put(self, *args):
            raise RuntimeError("database down")

    c, _, _ = service(cache=BrokenCache())
    assert check(c, npm("left-pad", "1.3.0"))["verdict"] == "allow"


def test_supabase_cache_requests():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"verdict": "ask", "reason": "r", "engine": 3, "signals": ["new"], "suggestion": "react"}])
        return httpx.Response(201)

    cache = SupabaseCache("https://p.supabase.co/", "sb_secret_abc", httpx.AsyncClient(transport=httpx.MockTransport(handler)), clock=lambda: NOW)
    hit = asyncio.run(cache.get("npm", "@scope/pkg", "1.0.0", 2))
    asyncio.run(cache.put("npm", "@scope/pkg", "1.0.0", CachedVerdict("allow", "ok", 2, ("a",), None), 3600))

    get, post = seen
    assert hit == CachedVerdict("ask", "r", 3, ("new",), "react")
    assert get.url.path == "/rest/v1/verdicts"
    assert dict(get.url.params) == {
        "select": "verdict,reason,engine,signals,suggestion", "ecosystem": "eq.npm", "registry": "eq.", "name": "eq.@scope/pkg",
        "version": "eq.1.0.0", "engine": "gte.2", "expires_at": f"gt.{NOW.isoformat()}", "limit": "1",
    }
    assert get.headers["apikey"] == "sb_secret_abc" and "authorization" not in get.headers
    assert post.url.params["on_conflict"] == "ecosystem,registry,name,version"
    assert "resolution=merge-duplicates" in post.headers["prefer"]
    assert json.loads(post.content) == {
        "ecosystem": "npm", "registry": "", "name": "@scope/pkg", "version": "1.0.0", "verdict": "allow", "reason": "ok", "engine": 2,
        "signals": ["a"], "suggestion": None, "expires_at": (NOW + timedelta(seconds=3600)).isoformat(),
    }
    # A private registry's verdicts are filed under its URL, apart from the public package of the same name.
    asyncio.run(cache.get("npm", "@scope/pkg", "1.0.0", 2, registry="https://lab.example"))
    assert seen[-1].url.params["registry"] == "eq.https://lab.example"


def test_memory_cache_keeps_registries_apart():
    cache = MemoryCache()
    asyncio.run(cache.put("npm", "foo", "1.0.0", CachedVerdict("block", "private foo is bad", 2), 3600, registry="https://lab.example"))
    assert asyncio.run(cache.get("npm", "foo", "1.0.0", 2)) is None
    assert asyncio.run(cache.get("npm", "foo", "1.0.0", 2, registry="https://lab.example")).verdict == "block"
