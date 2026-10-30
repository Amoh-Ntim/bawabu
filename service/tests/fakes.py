"""A fake internet for the service tests: npm, PyPI, OSV, download counts and npm search, from plain dicts."""

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

import httpx

NOW = datetime.now(timezone.utc)


def iso(days: float) -> str:
    return (NOW - timedelta(days=days)).isoformat().replace("+00:00", "Z")


def npm_doc(name: str, versions: list[dict], latest: str | None = None, description: str | None = None) -> dict:
    """versions: [{"version", "days" (age), "scripts", "provenance", "publisher", "deprecated", "gypfile"}], oldest first."""
    doc: dict = {
        "name": name,
        "dist-tags": {"latest": latest or versions[-1]["version"]},
        "versions": {},
        "time": {"created": iso(max(v["days"] for v in versions))},
    }
    if description:
        doc["description"] = description
    for v in versions:
        meta = {
            "name": name,
            "version": v["version"],
            "scripts": v.get("scripts", {}),
            "dist": {"attestations": {"provenance": {}}} if v.get("provenance") else {},
            "_npmUser": {"name": v.get("publisher", "alice")},
        }
        for key in ("deprecated", "gypfile"):
            if v.get(key):
                meta[key] = v[key]
        doc["versions"][v["version"]] = meta
        doc["time"][v["version"]] = iso(v["days"])
    return doc


def pypi_doc(name: str, releases: dict[str, dict], latest: str) -> dict:
    """releases: {version: {"days", "wheel" (default True), "yanked"}}."""
    files = {}
    for version, r in releases.items():
        kinds = ["sdist"] + (["bdist_wheel"] if r.get("wheel", True) else [])
        files[version] = [{"packagetype": k, "upload_time_iso_8601": iso(r["days"]), "yanked": r.get("yanked", False)} for k in kinds]
    return {"info": {"name": name, "version": latest}, "releases": files}


class FakeNet:
    def __init__(self) -> None:
        self.npm: dict[str, dict] = {}
        self.pypi: dict[str, dict] = {}
        self.downloads: dict[tuple[str, str], int] = {}
        # (OSV ecosystem, name) -> [(id, affected versions; empty = all versions)]
        self.osv: dict[tuple[str, str], list[tuple[str, list[str]]]] = {}
        self.search: dict[str, list[tuple[str, int]]] = {}
        self.pypi_top = ["boto3", "requests", "numpy", "django"]
        self.down: set[str] = set()
        self.requests: list[httpx.Request] = []
        # A private registry at https://lab.example: packuments by name, plus raw files (tarballs) by path.
        self.lab: dict[str, dict] = {}
        self.blobs: dict[str, bytes] = {}
        self.lab_auth: list[str | None] = []

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle))

    def hits(self, host: str) -> int:
        return sum(1 for r in self.requests if r.url.host == host)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host, path = request.url.host, unquote(request.url.raw_path.decode().split("?")[0])
        if host in self.down:
            return httpx.Response(503)
        if host == "lab.example":
            self.lab_auth.append(request.headers.get("authorization"))
            if path in self.blobs:
                return httpx.Response(200, content=self.blobs[path])
            doc = self.lab.get(path[1:])
            return httpx.Response(200, json=doc) if doc else httpx.Response(404, json={"error": "Not found"})
        if host == "registry.npmjs.org" and path == "/-/v1/search":
            found = self.search.get(request.url.params["text"], [])
            return httpx.Response(200, json={"objects": [{"package": {"name": n}, "downloads": {"weekly": w}} for n, w in found]})
        if host == "registry.npmjs.org":
            doc = self.npm.get(path[1:])
            return httpx.Response(200, json=doc) if doc else httpx.Response(404, json={"error": "Not found"})
        if host == "api.npmjs.org":
            name = path.removeprefix("/downloads/point/last-week/")
            count = self.downloads.get(("npm", name))
            return httpx.Response(200, json={"downloads": count}) if count is not None else httpx.Response(404)
        if host == "pypi.org":
            doc = self.pypi.get(path.split("/")[2])
            return httpx.Response(200, json=doc) if doc else httpx.Response(404)
        if host == "pypistats.org":
            count = self.downloads.get(("pypi", path.split("/")[3]))
            return httpx.Response(200, json={"data": {"last_week": count}}) if count is not None else httpx.Response(404)
        if host == "api.osv.dev":
            body = json.loads(request.content)
            entries = self.osv.get((body["package"]["ecosystem"], body["package"]["name"]), [])
            version = body.get("version")
            ids = [i for i, versions in entries if not version or not versions or version in versions]
            return httpx.Response(200, json={"vulns": [{"id": i} for i in ids]} if ids else {})
        if host == "hugovk.github.io":
            return httpx.Response(200, json={"rows": [{"project": p} for p in self.pypi_top]})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")


def internet() -> FakeNet:
    """A small world with the packages the tests talk about."""
    net = FakeNet()
    net.npm["react"] = npm_doc("react", [{"version": "18.3.1", "days": 900}, {"version": "19.2.0", "days": 40, "provenance": True}])
    net.downloads[("npm", "react")] = 60_000_000
    net.npm["left-pad"] = npm_doc("left-pad", [{"version": "1.3.0", "days": 2900}])
    net.downloads[("npm", "left-pad")] = 1_200_000
    net.npm["@ctrl/tinycolor"] = npm_doc("@ctrl/tinycolor", [{"version": "4.1.0", "days": 500}, {"version": "4.2.0", "days": 20}])
    net.downloads[("npm", "@ctrl/tinycolor")] = 2_000_000
    net.osv[("npm", "@ctrl/tinycolor")] = [("MAL-2025-47141", ["4.1.1", "4.1.2"])]
    net.npm["crossenv"] = npm_doc("crossenv", [{"version": "0.0.2-security", "days": 3000}], description="security holding package")
    net.npm["fresh-helper"] = npm_doc("fresh-helper", [{"version": "0.1.0", "days": 3, "scripts": {"postinstall": "node setup.js"}}])
    net.downloads[("npm", "fresh-helper")] = 12
    net.search["fancy date pickr"] = [("fancy-datepicker", 900), ("react-datepicker", 1_500_000), ("datepicker", 400_000)]
    net.pypi["requests"] = pypi_doc("requests", {"2.31.0": {"days": 900}, "2.32.3": {"days": 400}}, latest="2.32.3")
    net.downloads[("pypi", "requests")] = 330_000_000
    return net
