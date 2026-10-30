"""The investigation path: /check starting, joining and waiting for investigations; private-registry routing;
and the investigation pipeline itself (diff + sandbox + Spark → events, verdict, cache)."""

import asyncio

from fakes import NOW, internet, npm_doc
from fastapi.testclient import TestClient
from test_diff import pkg, tarball
from test_investigator import GRAB, LEAKY_RUN, FakeModel, verdict

from bawabu_service import investigations
from bawabu_service.api import create_app
from bawabu_service.cache import MemoryCache
from bawabu_service.investigations import Investigations, MemoryStore
from bawabu_service.registry import Source

LAB = "https://lab.example"
LAB_SOURCES = {LAB: Source(LAB, (("authorization", "Basic bGFiOnB3"),))}
BLOCK_RESULT = {
    "verdict": "block", "confidence": "high", "reason": "Reads your npm token on install and posts it to an unknown server.",
    "evidence": [{"type": "code", "file": "setup.js", "line": 3, "detail": "reads ~/.npmrc"},
                 {"type": "sandbox", "file": None, "line": None, "detail": "Leaked canary: npm token → collector.bawabu-test.invalid"}],
    "safe_alternative": "dotenv",
}


class Spawner:
    """Stands in for investigate.spawn: records payloads, and optionally finishes the investigation at once."""

    def __init__(self, store: MemoryStore, result: dict | None = None, status: str = "done") -> None:
        self.store, self.result, self.status, self.calls = store, result, status, []

    async def __call__(self, inv_id: str, payload: dict) -> None:
        self.calls.append((inv_id, payload))
        if self.result is not None:
            await self.store.finish(inv_id, self.status, self.result)


def service(spawner_result=None, status="done", budget=5.0, net=None, sources=None):
    net = net or internet()
    store = MemoryStore()
    spawn = Spawner(store, spawner_result, status)
    inv = Investigations(store, spawn, budget_s=budget, poll_s=0.01)
    cache = MemoryCache()
    client = TestClient(create_app(cache, net.client(), investigations=inv, sources=sources if sources is not None else {}))
    return client, spawn, store, cache, net


def check(client, *packages):
    return client.post("/check", json={"client_version": "test", "packages": list(packages)}).json()


def test_suspicious_package_is_investigated_and_the_verdict_returned():
    client, spawn, store, cache, _ = service(BLOCK_RESULT)
    body = check(client, {"ecosystem": "npm", "name": "fresh-helper"})
    r = body["results"][0]
    assert body["verdict"] == "block" and r["verdict"] == "block"
    assert r["reason"].startswith("Reads your npm token")
    assert r["signals"][0] == "setup.js:3: reads ~/.npmrc" and "Leaked canary" in r["signals"][1]
    assert r["suggestion"] == "dotenv" and r["report_id"] == "inv-1"
    inv_id, payload = spawn.calls[0]
    assert payload["name"] == "fresh-helper" and payload["version"] == "0.1.0" and payload["registry_key"] == ""
    assert any("days old" in s for s in payload["signals"])  # the quick checks' red flags go along
    assert cache._items == {}  # the quick checks' "ask" isn't cached; the investigation caches its own verdict


def test_established_packages_never_reach_an_investigation():
    client, spawn, *_ = service(BLOCK_RESULT)
    assert check(client, {"ecosystem": "npm", "name": "react"})["verdict"] == "allow"
    assert spawn.calls == []


def test_slow_investigation_asks_to_retry_and_a_retry_joins_it():
    client, spawn, store, *_ = service(None, budget=0.05)
    first = check(client, {"ecosystem": "npm", "name": "fresh-helper"})["results"][0]
    assert first["verdict"] == "ask" and "still investigating" in first["reason"] and first["report_id"] == "inv-1"
    assert first["pending"] is True
    second = check(client, {"ecosystem": "npm", "name": "fresh-helper"})["results"][0]
    assert second["report_id"] == "inv-1" and len(spawn.calls) == 1  # joined, not started twice
    asyncio.run(store.finish("inv-1", "done", BLOCK_RESULT))
    assert check(client, {"ecosystem": "npm", "name": "fresh-helper"})["verdict"] == "block"


def test_dead_or_failed_investigations_are_started_again():
    client, spawn, store, *_ = service(None, budget=0.02)
    check(client, {"ecosystem": "npm", "name": "fresh-helper"})
    store.rows["inv-1"]["created_at"] = NOW - investigations.STALE * 2  # its worker died long ago
    assert check(client, {"ecosystem": "npm", "name": "fresh-helper"})["results"][0]["report_id"] == "inv-2"
    asyncio.run(store.finish("inv-2", "failed", {"error": "x"}))
    assert check(client, {"ecosystem": "npm", "name": "fresh-helper"})["results"][0]["report_id"] == "inv-3"
    assert len(spawn.calls) == 3


def test_failed_investigation_asks():
    client, *_ = service({"error": "boom"}, status="failed")
    r = check(client, {"ecosystem": "npm", "name": "fresh-helper"})["results"][0]
    assert r["verdict"] == "ask" and "failed" in r["reason"]


def test_unknown_private_registry_asks_without_touching_the_network():
    client, spawn, _, _, net = service(BLOCK_RESULT)
    r = check(client, {"ecosystem": "npm", "name": "internal-ui", "registry": "https://npm.corp.example/"})["results"][0]
    assert r["verdict"] == "ask" and "private registry" in r["reason"] and "allowlist" in r["reason"]
    assert not net.requests and not spawn.calls


def test_known_private_registry_is_read_with_its_login_and_skips_public_data():
    net = internet()
    net.lab["env-loader-plus"] = npm_doc("env-loader-plus", [{"version": "1.0.0", "days": 2, "scripts": {"postinstall": "node scripts/setup.js"}}])
    client, spawn, *_ = service(BLOCK_RESULT, net=net, sources=LAB_SOURCES)
    r = check(client, {"ecosystem": "npm", "name": "env-loader-plus", "registry": "https://lab.example/"})["results"][0]
    assert r["verdict"] == "block"
    assert net.lab_auth and set(net.lab_auth) == {"Basic bGFiOnB3"}
    assert net.hits("api.osv.dev") == 0 and net.hits("api.npmjs.org") == 0  # those describe the public package of that name
    payload = spawn.calls[0][1]
    assert payload["registry_url"] == LAB and payload["registry_key"] == LAB
    assert payload["headers"] == [["authorization", "Basic bGFiOnB3"]]


def test_a_public_package_and_a_private_one_never_share_a_verdict():
    net = internet()
    net.lab["left-pad"] = npm_doc("left-pad", [{"version": "1.3.0", "days": 2, "scripts": {"postinstall": "node x.js"}}])
    client, spawn, *_ = service(BLOCK_RESULT, net=net, sources=LAB_SOURCES)
    assert check(client, {"ecosystem": "npm", "name": "left-pad", "version": "1.3.0"})["verdict"] == "allow"
    assert check(client, {"ecosystem": "npm", "name": "left-pad", "version": "1.3.0", "registry": LAB})["verdict"] == "block"
    assert check(client, {"ecosystem": "npm", "name": "left-pad", "version": "1.3.0"})["verdict"] == "allow"


def test_report_endpoint():
    client, _, store, *_ = service(BLOCK_RESULT)
    check(client, {"ecosystem": "npm", "name": "fresh-helper"})
    asyncio.run(store.add_event("inv-1", 0, {"kind": "tool", "title": "Reading setup.js"}))
    body = client.get("/investigations/inv-1").json()
    assert body["status"] == "done" and body["result"]["verdict"] == "block"
    assert body["events"] == [{"seq": 0, "kind": "tool", "title": "Reading setup.js"}]
    assert body["package"] == {"ecosystem": "npm", "name": "fresh-helper", "version": "0.1.0"}
    assert client.get("/investigations/nope").status_code == 404


def test_pipeline_runs_diff_sandbox_and_spark_then_stores_and_caches():
    net = internet()
    net.lab["env-loader-plus"] = npm_doc("env-loader-plus", [{"version": "1.0.0", "days": 2}])
    net.lab["env-loader-plus"]["versions"]["1.0.0"]["dist"] = {"tarball": f"{LAB}/env-loader-plus/-/env-loader-plus-1.0.0.tgz"}
    net.blobs["/env-loader-plus/-/env-loader-plus-1.0.0.tgz"] = tarball(pkg("env-loader-plus", "1.0.0", scripts={"postinstall": "node setup.js"}, **{"setup.js": GRAB}))
    store, cache = MemoryStore(), MemoryCache()
    sandbox_calls = []

    def sandbox(name, version, registry_url, auth, env, date):
        sandbox_calls.append((name, version, registry_url, auth, env, date))
        return LEAKY_RUN

    spark = FakeModel([[("read_file", {"path": "setup.js"})],
                       [verdict("block", [{"type": "code", "file": "setup.js", "line": 3, "quote": 'fs.readFileSync(path.join(os.homedir(), ".npmrc"), "utf8")', "detail": "reads the npm token"}])]])
    payload = {"ecosystem": "npm", "name": "env-loader-plus", "version": "1.0.0", "registry_url": LAB, "registry_key": LAB,
               "headers": [["authorization", "Basic bGFiOnB3"]], "signals": ["The package is only 2 days old."]}

    async def go():
        inv_id = await store.create("npm", LAB, "env-loader-plus", "1.0.0")
        async with net.client() as http:
            return inv_id, await investigations.run(inv_id, payload, store=store, cache=cache, http=http, spark=spark,
                                                    model="muse-spark-1.3", sandbox=sandbox, engine=2)

    inv_id, result = asyncio.run(go())
    assert result["verdict"] == "block" and store.rows[inv_id]["status"] == "done"
    assert sandbox_calls == [("env-loader-plus", "1.0.0", LAB, "bGFiOnB3", None, None)]  # the login reaches the sandbox's npm
    events = asyncio.run(store.events(inv_id))
    assert [e["seq"] for e in events] == list(range(len(events)))  # written in order
    kinds = [e["kind"] for e in events]
    assert kinds[0] == "stage" and "tool" in kinds and kinds[-1] == "verdict"
    hit = asyncio.run(cache.get("npm", "env-loader-plus", "1.0.0", 2, registry=LAB))
    assert hit and hit.verdict == "block" and hit.signals[0].startswith("Leaked canary")
    assert asyncio.run(cache.get("npm", "env-loader-plus", "1.0.0", 2)) is None  # not under the public name


def test_pipeline_failure_marks_the_investigation_failed():
    store, cache = MemoryStore(), MemoryCache()
    net = internet()  # the lab has no such package, so the diff fails

    async def go():
        inv_id = await store.create("npm", LAB, "ghost", "1.0.0")
        async with net.client() as http:
            await investigations.run(inv_id, {"ecosystem": "npm", "name": "ghost", "version": "1.0.0", "registry_url": LAB,
                                              "registry_key": LAB, "headers": []},
                                     store=store, cache=cache, http=http, spark=FakeModel([]), model="x", sandbox=None, engine=2)
        return inv_id

    inv_id = asyncio.run(go())
    assert store.rows[inv_id]["status"] == "failed"
    assert asyncio.run(store.events(inv_id))[-1]["kind"] == "error"
    _ = NOW
