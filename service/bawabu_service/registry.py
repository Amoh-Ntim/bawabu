"""What npm and PyPI say about a package: does it exist, which exact version would be installed, and the facts
the quick checks use (age, publish time, install-time code, provenance, publisher).
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote

import httpx
import semantic_version
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

NPM = "https://registry.npmjs.org"
PYPI = "https://pypi.org/pypi"
# npm runs these on install; prepare only runs for git dependencies.
NPM_INSTALL_SCRIPTS = ("preinstall", "install", "postinstall")
SOURCE_BUILD = {"setup.py": "built from source on install (no wheel)"}


@dataclass
class Facts:
    ecosystem: str
    name: str
    version: str
    created: datetime | None
    published: datetime | None
    weekly_downloads: int | None = None
    # Code that runs on install: npm lifecycle scripts, or a Python source-only build.
    install_scripts: dict[str, str] = field(default_factory=dict)
    # The same for the version published just before this one; None when there's no earlier version.
    previous_install_scripts: dict[str, str] | None = None
    provenance: bool | None = None
    previous_provenance: bool | None = None
    publisher: str | None = None
    previous_publishers: frozenset[str] = frozenset()
    deprecated: str | None = None
    yanked: bool = False


@dataclass
class Missing:
    """No package by that name."""


@dataclass
class Placeholder:
    """npm's "security holding package": npm removed the package for malware."""


@dataclass
class NoMatch:
    """The package exists, but no version matches the request."""

    latest: str | None


Lookup = Facts | Missing | Placeholder | NoMatch


class RegistryError(Exception):
    pass


@dataclass(frozen=True)
class Source:
    """Where npm packages come from: the public npm by default, or a private registry the service has a login for."""

    url: str = NPM
    headers: tuple[tuple[str, str], ...] = ()
    # Reports for this private registry may show code (the test lab's own fixtures). Off for real private code.
    show_code: bool = False

    @property
    def public(self) -> bool:
        return self.url.rstrip("/") == NPM

    @property
    def key(self) -> str:
        """How verdicts for this registry are kept apart from the public npm's: "" for the public npm."""
        return "" if self.public else self.url.rstrip("/")


def clean_url(value: str) -> str | None:
    """scheme://host/path with credentials, query and trailing slash dropped (as the CLI does); None if not http(s)."""
    match = re.match(r"(https?)://(?:[^@/]*@)?([^/?#]+)([^?#]*)", value.strip())
    return f"{match.group(1)}://{match.group(2).lower()}{match.group(3)}".rstrip("/") if match else None


def sources_from_env() -> dict[str, Source]:
    """Private registries the service can read, by URL: the test lab's Verdaccio when LAB_REGISTRY_URL and
    LAB_REGISTRY_AUTH (its HTTP Basic login) are set. LAB_REGISTRY_SHOW_CODE=1 lets its reports show code."""
    url, auth = os.environ.get("LAB_REGISTRY_URL"), os.environ.get("LAB_REGISTRY_AUTH")
    key = clean_url(url) if url else None
    show = os.environ.get("LAB_REGISTRY_SHOW_CODE") == "1"
    return {key: Source(key, (("authorization", f"Basic {auth}"),), show_code=show)} if key and auth else {}


def source_for(ecosystem: str, registry: str | None, known: dict[str, Source]) -> Source | None:
    """Where to read this package from; None for a private registry the service has no login for."""
    if ecosystem != "npm" or not registry:
        return Source()
    url = clean_url(registry)
    if url == NPM:
        return Source()
    return known.get(url) if url else None


async def lookup(client: httpx.AsyncClient, ecosystem: str, name: str, requested: str, source: Source | None = None) -> Lookup:
    if ecosystem == "npm":
        return await npm_lookup(client, name, requested, source or Source())
    return await pypi_lookup(client, name, requested)


async def weekly_downloads(client: httpx.AsyncClient, ecosystem: str, name: str) -> int | None:
    try:
        if ecosystem == "npm":
            response = await client.get(f"https://api.npmjs.org/downloads/point/last-week/{name}")
            response.raise_for_status()
            return int(response.json()["downloads"])
        response = await client.get(f"https://pypistats.org/api/packages/{quote(name.lower())}/recent")
        response.raise_for_status()
        return int(response.json()["data"]["last_week"])
    except Exception:
        return None


def _time(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# npm


async def npm_lookup(client: httpx.AsyncClient, name: str, requested: str, source: Source = Source()) -> Lookup:
    # @scope/name -> @scope%2Fname
    response = await client.get(f"{source.url.rstrip('/')}/{quote(name, safe='@')}", headers=dict(source.headers))
    if response.status_code == 404:
        return Missing()
    if response.status_code != 200:
        raise RegistryError(f"the registry answered HTTP {response.status_code}")
    doc = response.json()
    tags = doc.get("dist-tags") or {}
    versions: dict[str, dict] = doc.get("versions") or {}
    if doc.get("description") == "security holding package" or str(tags.get("latest", "")).endswith("-security"):
        return Placeholder()
    version = resolve_npm(requested, tags, versions)
    if version is None:
        return NoMatch(tags.get("latest"))

    times = doc.get("time") or {}
    published = _time(times.get(version))
    earlier = sorted(
        (v for v in versions if v != version and published and (t := _time(times.get(v))) and t < published),
        key=lambda v: _time(times[v]),
    )
    meta, previous = versions[version], (versions[earlier[-1]] if earlier else None)
    publisher = lambda m: (m.get("_npmUser") or {}).get("name")  # noqa: E731
    return Facts(
        ecosystem="npm",
        name=name,
        version=version,
        created=_time(times.get("created")),
        published=published,
        install_scripts=_npm_install_scripts(meta),
        previous_install_scripts=_npm_install_scripts(previous) if previous else None,
        provenance="attestations" in (meta.get("dist") or {}),
        previous_provenance=("attestations" in (previous.get("dist") or {})) if previous else None,
        publisher=publisher(meta),
        previous_publishers=frozenset(p for v in earlier if (p := publisher(versions[v]))),
        deprecated=meta.get("deprecated") or None,
    )


def resolve_npm(requested: str, tags: dict[str, str], versions: dict[str, dict]) -> str | None:
    """The version `npm install name@requested` picks: a tag, an exact version, or the best match for a range
    (npm prefers the `latest` tag when it satisfies the range)."""
    spec = requested.strip()
    if not spec or spec == "*":
        return tags.get("latest")
    if spec in tags:
        return tags[spec]
    for exact in (spec, spec.lstrip("=v").strip()):
        if exact in versions:
            return exact
    try:
        npm_spec = semantic_version.NpmSpec(spec)
    except ValueError:
        return None
    parsed: dict[semantic_version.Version, str] = {}
    for v in versions:
        try:
            parsed[semantic_version.Version(v)] = v
        except ValueError:
            continue
    latest = tags.get("latest")
    if latest in versions:
        try:
            if semantic_version.Version(latest) in npm_spec:
                return latest
        except ValueError:
            pass
    matching = [pv for pv in parsed if pv in npm_spec]
    return parsed[max(matching)] if matching else None


def _npm_install_scripts(meta: dict) -> dict[str, str]:
    scripts = meta.get("scripts") or {}
    found = {k: str(scripts[k]) for k in NPM_INSTALL_SCRIPTS if scripts.get(k)}
    # With a binding.gyp and no install script of its own, npm runs node-gyp to compile native code.
    if meta.get("gypfile") and not ({"install", "preinstall"} & found.keys()):
        found["install"] = "node-gyp rebuild (binding.gyp)"
    return found


# ---------------------------------------------------------------------------
# PyPI


async def pypi_lookup(client: httpx.AsyncClient, name: str, requested: str) -> Lookup:
    response = await client.get(f"{PYPI}/{quote(name)}/json")
    if response.status_code == 404:
        return Missing()
    if response.status_code != 200:
        raise RegistryError(f"PyPI answered HTTP {response.status_code}")
    doc = response.json()
    latest = (doc.get("info") or {}).get("version")
    releases: dict[str, list[dict]] = {v: files for v, files in (doc.get("releases") or {}).items() if files}
    version = resolve_pypi(requested, latest, releases)
    if version is None:
        return NoMatch(latest)

    def uploaded(files: list[dict]) -> datetime | None:
        times = [t for f in files if (t := _time(f.get("upload_time_iso_8601")))]
        return min(times) if times else None

    def install_code(files: list[dict]) -> dict[str, str]:
        return {} if any(f.get("packagetype") == "bdist_wheel" for f in files) else dict(SOURCE_BUILD)

    published = uploaded(releases[version])
    first_uploads = [t for files in releases.values() if (t := uploaded(files))]
    earlier = sorted((v for v in releases if v != version and published and (t := uploaded(releases[v])) and t < published),
                     key=lambda v: uploaded(releases[v]))
    return Facts(
        ecosystem="pypi",
        name=name,
        version=version,
        created=min(first_uploads) if first_uploads else None,
        published=published,
        install_scripts=install_code(releases[version]),
        previous_install_scripts=install_code(releases[earlier[-1]]) if earlier else None,
        yanked=all(f.get("yanked") for f in releases[version]),
    )


def resolve_pypi(requested: str, latest: str | None, releases: dict[str, list[dict]]) -> str | None:
    """The version `pip install name<requested>` picks. Environment markers (; python_version < ...) are ignored."""
    spec = requested.split(";", 1)[0].strip()
    if not spec:
        return latest if latest in releases else _best(SpecifierSet(), releases)
    if re.fullmatch(r"[0-9][0-9A-Za-z.!+-]*", spec):  # uv-style name@1.2.3
        spec = f"=={spec}"
    if spec.startswith("==="):
        exact = spec[3:].strip()
        return exact if exact in releases else None
    if spec.startswith("==") and "*" not in spec and spec[2:].strip() in releases:
        return spec[2:].strip()  # an exact pin installs even a yanked release
    try:
        return _best(SpecifierSet(spec), releases)
    except InvalidSpecifier:
        return None


def _best(specifier: SpecifierSet, releases: dict[str, list[dict]]) -> str | None:
    parsed: dict[Version, str] = {}
    for v, files in releases.items():
        if all(f.get("yanked") for f in files):
            continue  # pip skips yanked releases unless pinned exactly
        try:
            parsed[Version(v)] = v
        except InvalidVersion:
            continue
    matching = list(specifier.filter(parsed))
    return parsed[max(matching)] if matching else None
