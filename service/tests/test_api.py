import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from bawabu_service import verdicts
from bawabu_service.api import create_app
from bawabu_service.cache import CachedVerdict, MemoryCache, SupabaseCache
from bawabu_service.models import Package


def client(cache=None) -> TestClient:
    return TestClient(create_app(cache or MemoryCache()))


def check(c: TestClient, *packages: dict, manifests: list | None = None) -> dict:
    response = c.post("/check", json={"client_version": "0.1.0", "packages": list(packages), "manifests": manifests or []})
    assert response.status_code == 200, response.text
    return response.json()


def test_health():
    assert client().get("/health").json() == {"ok": True, "version": "0.1.0", "engine": verdicts.ENGINE, "cache": "memory"}


def test_skeleton_allows_and_caches_exact_versions():
    c = client()
    first = check(c, {"ecosystem": "npm", "name": "left-pad", "version": "1.3.0"})
    assert first["verdict"] == "allow"
    assert first["results"][0] | {"reason": None} == {
        "ecosystem": "npm", "name": "left-pad", "requested": "1.3.0", "version": "1.3.0", "verdict": "allow", "reason": None, "cached": False,
    }
    assert check(c, {"ecosystem": "npm", "name": "left-pad", "version": "1.3.0"})["results"][0]["cached"] is True


def test_latest_tags_and_ranges_are_not_cached_until_resolved():
    c = client()
    for version in ["", "latest", "^1.2.0", ">=2,<3"]:
        check(c, {"ecosystem": "npm", "name": "x", "version": version})
        assert check(c, {"ecosystem": "npm", "name": "x", "version": version})["results"][0]["cached"] is False


def test_exact_versions():
    def exact(ecosystem: str, version: str):
        return verdicts.exact_version(Package(ecosystem=ecosystem, name="x", version=version))

    assert exact("npm", "1.2.3") == "1.2.3"
    assert exact("npm", "v1.2.3-beta.1") == "1.2.3-beta.1"
    assert exact("npm", "^1.2.3") is None
    assert exact("pypi", "==2.31.0") == "2.31.0"
    assert exact("pypi", ">=2") is None


def test_block_wins_and_duplicates_are_judged_once():
    cache = MemoryCache()
    asyncio.run(cache.put("npm", "evil", "1.0.0", CachedVerdict("block", "steals tokens", verdicts.MIN_ENGINE)))
    body = check(
        client(cache),
        {"ecosystem": "npm", "name": "left-pad", "version": "1.3.0"},
        {"ecosystem": "npm", "name": "evil", "version": "1.0.0"},
        {"ecosystem": "npm", "name": "evil", "version": "1.0.0"},
    )
    assert body["verdict"] == "block"
    assert [r["name"] for r in body["results"]] == ["left-pad", "evil"]
    assert body["results"][1]["reason"] == "steals tokens"


def test_verdicts_from_older_engines_are_judged_again(monkeypatch):
    cache = MemoryCache()
    asyncio.run(cache.put("npm", "old", "1.0.0", CachedVerdict("allow", "skeleton", 0)))
    monkeypatch.setattr(verdicts, "MIN_ENGINE", 1)
    monkeypatch.setattr(verdicts, "ENGINE", 1)
    assert check(client(cache), {"ecosystem": "npm", "name": "old", "version": "1.0.0"})["results"][0]["cached"] is False


def test_manifests_get_a_verdict():
    body = check(client(), manifests=[{"ecosystem": "npm", "manager": "npm"}])
    assert body["verdict"] == "allow" and body["manifests"][0]["manager"] == "npm"


def test_bad_input_is_rejected():
    c = client()
    bad = [{"ecosystem": "maven", "name": "x"}, {"ecosystem": "npm", "name": ""}]
    for package in bad:
        assert c.post("/check", json={"client_version": "0.1.0", "packages": [package]}).status_code == 422


def test_a_broken_cache_does_not_break_checks():
    class BrokenCache(MemoryCache):
        name = "broken"

        async def get(self, *args):
            raise RuntimeError("database down")

        async def put(self, *args):
            raise RuntimeError("database down")

    assert check(client(BrokenCache()), {"ecosystem": "npm", "name": "x", "version": "1.0.0"})["verdict"] == "allow"


def test_supabase_cache_requests():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"verdict": "block", "reason": "r", "engine": 3}])
        return httpx.Response(201)

    cache = SupabaseCache("https://p.supabase.co/", "sb_secret_abc", httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    hit = asyncio.run(cache.get("npm", "@scope/pkg", "1.0.0", 2))
    asyncio.run(cache.put("npm", "@scope/pkg", "1.0.0", CachedVerdict("allow", "ok", 2)))

    get, post = seen
    assert hit == CachedVerdict("block", "r", 3)
    assert get.url.path == "/rest/v1/verdicts"
    assert dict(get.url.params) | {} == {
        "select": "verdict,reason,engine", "ecosystem": "eq.npm", "name": "eq.@scope/pkg", "version": "eq.1.0.0", "engine": "gte.2", "limit": "1",
    }
    assert get.headers["apikey"] == "sb_secret_abc" and "authorization" not in get.headers
    assert post.url.params["on_conflict"] == "ecosystem,name,version"
    assert "resolution=merge-duplicates" in post.headers["prefer"]
    assert json.loads(post.content) == {"ecosystem": "npm", "name": "@scope/pkg", "version": "1.0.0", "verdict": "allow", "reason": "ok", "engine": 2}
