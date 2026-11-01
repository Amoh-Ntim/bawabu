"""Local mode: the test lab served from testlab/packages, and the whole service in one process with your own keys."""

import asyncio

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_investigator import FakeModel, verdict

from bawabu_service import diff, lab_registry, registry
from bawabu_service.local import PACKAGES, Settings, build, describe

LAB = "http://127.0.0.1:8787/lab"
TOKEN = "t0ken"


def lab_app() -> FastAPI:
    app = FastAPI()
    app.include_router(lab_registry.router(PACKAGES, LAB, TOKEN))
    return app


def test_every_practice_package_is_served_with_its_versions():
    packages = lab_registry.load(PACKAGES)
    assert {"env-loader-plus", "ci-build-cache-helper", "markdown-tiny-render", "pretty-log-kit"} <= set(packages)
    assert set(packages["docs-gen-postinstall"]) == {"1.0.0", "2.0.0"}  # two folders, one package


def test_only_bawabu_can_download_the_samples():
    client = TestClient(lab_app())
    assert client.get("/lab/env-loader-plus").status_code == 401  # npm sends no token
    assert client.get("/lab/env-loader-plus", headers={"authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/lab/env-loader-plus/-/env-loader-plus-1.0.0.tgz").status_code == 401
    auth = {"authorization": f"Bearer {TOKEN}"}
    doc = client.get("/lab/docs-gen-postinstall", headers=auth).json()
    assert doc["dist-tags"]["latest"] == "2.0.0" and doc["time"]["1.0.0"] < doc["time"]["2.0.0"]
    assert doc["versions"]["2.0.0"]["scripts"]["postinstall"] == "node scripts/postinstall.js"
    blob = client.get("/lab/env-loader-plus/-/env-loader-plus-1.0.0.tgz", headers=auth).content
    assert {"package.json", "scripts/setup.js"} <= set(diff.unpack(blob))
    assert blob == client.get("/lab/env-loader-plus/-/env-loader-plus-1.0.0.tgz", headers=auth).content  # reproducible
    assert client.get("/lab/no-such-package", headers=auth).status_code == 404


def test_bawabus_own_readers_work_against_the_lab():
    source = registry.Source(LAB, (("authorization", f"Bearer {TOKEN}"),))

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=lab_app())) as http:
            facts = await registry.npm_lookup(http, "ci-build-cache-helper", "", source)
            report = await diff.analyze(http, "docs-gen-postinstall", "2.0.0", source)
            return facts, report

    facts, report = asyncio.run(go())
    assert facts.version == "1.0.0" and facts.install_scripts == {"postinstall": "node scripts/cache.js"}
    assert report.previous == "1.0.0" and report.risk == "high"


def test_local_service_investigates_a_practice_attack_end_to_end():
    spark = FakeModel([
        [("read_file", {"path": "scripts/cache.js"})],
        [verdict("block", [{"type": "code", "file": "scripts/cache.js", "line": 17, "detail": "reads the npm token",
                            "quote": 'path.join(os.homedir(), ".npmrc")'}], reason="Steals the npm token when CI=true.")],
    ])
    app = build(Settings(clients={"meta": spark}))
    client = TestClient(app)
    r = client.post("/check", json={"client_version": "t", "packages": [{"ecosystem": "npm", "name": "ci-build-cache-helper", "registry": LAB + "/"}]}).json()
    result = r["results"][0]
    assert r["verdict"] == "block" and result["reason"] == "Steals the npm token when CI=true."
    assert result["signals"] == ["scripts/cache.js:17: reads the npm token"]
    report = client.get(f"/investigations/{result['report_id']}").json()
    assert report["code_hidden"] is False and report["result"]["snippets"]  # the lab may show its own code
    assert any(e["kind"] == "tool" for e in report["events"])
    assert client.get("/lab/ci-build-cache-helper").status_code == 401  # and npm still can't fetch it
    assert client.get("/health").json()["investigations"] is True


def test_open_weights_requests_use_the_open_model():
    meta, opened = FakeModel([]), FakeModel([[verdict("block", [], reason="open model says no")]])
    client = TestClient(build(Settings(clients={"meta": meta, "open": opened})))
    r = client.post("/check", json={"client_version": "t", "open_weights": True,
                                    "packages": [{"ecosystem": "npm", "name": "env-loader-plus", "registry": LAB}]}).json()
    assert opened.requests and not meta.requests  # the screener skipped it (install script), the open model investigated
    assert r["results"][0]["report_id"]


def test_settings_say_what_is_on():
    assert describe(Settings(meta_key="m"))["investigator"].startswith("Muse Spark (")
    assert describe(Settings(meta_key="m"))["screener"].startswith("off")
    assert describe(Settings(baseten_key="b"))["investigator"].startswith("Muse Spark Open")
    assert describe(Settings(meta_key="m", baseten_key="b", open_weights=True))["investigator"].startswith("Muse Spark Open")
    assert "off" in describe(Settings(meta_key="m"))["sandbox"]
