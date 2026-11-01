"""The test lab as a tiny npm registry, built straight from testlab/packages, for running Bawabu on your own machine.

The local service (service/run_local.py) serves the practice packages at /lab so anyone can test Bawabu against the
real attack samples with their own API key, without our hosted registry or its password.

Only Bawabu itself can download from it: every request must carry a token that only the running service holds. So
`npm install` (and with it the samples' install scripts) can never fetch a sample onto the machine; npm gets a 401.
"""

from __future__ import annotations

import gzip
import io
import json
import secrets
import tarfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import semantic_version
from fastapi import APIRouter, Header, HTTPException, Response

# Never packed: build output and caches a fixture might have produced if someone ran it by hand.
SKIP_DIRS = {"node_modules", ".cache", "build"}
PUBLISHER = "bawabu-testlab"


@dataclass(frozen=True)
class LabPackage:
    name: str
    version: str
    folder: Path
    manifest: dict


def load(packages_dir: Path) -> dict[str, dict[str, LabPackage]]:
    """name -> version -> package, from every folder holding a package.json (a name may span folders:
    docs-gen-postinstall and docs-gen-postinstall-2 are two versions of one package)."""
    out: dict[str, dict[str, LabPackage]] = {}
    for manifest_path in sorted(packages_dir.glob("*/package.json")):
        manifest = json.loads(manifest_path.read_text())
        pkg = LabPackage(manifest["name"], manifest["version"], manifest_path.parent, manifest)
        out.setdefault(pkg.name, {})[pkg.version] = pkg
    return out


def tarball(folder: Path) -> bytes:
    """The folder as an npm tarball (files under package/), byte-for-byte reproducible."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for path in sorted(folder.rglob("*")):
            rel = path.relative_to(folder)
            if not path.is_file() or SKIP_DIRS & set(rel.parts[:-1]) or path.name == ".DS_Store":
                continue
            data = path.read_bytes()
            info = tarfile.TarInfo(f"package/{rel.as_posix()}")
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            tar.addfile(info, io.BytesIO(data))
    return gzip.compress(raw.getvalue(), mtime=0)


def _ordered(versions: dict[str, LabPackage]) -> list[str]:
    return sorted(versions, key=semantic_version.Version)


def packument(name: str, versions: dict[str, LabPackage], base_url: str, now: datetime) -> dict:
    """What a registry answers for GET /<name>. The newest version looks a day old and earlier ones a month older,
    which is what the samples are meant to look like: brand new, or a fresh release of an older package."""
    order = _ordered(versions)
    times = {v: now - timedelta(days=1 if i == len(order) - 1 else 31 + (len(order) - i)) for i, v in enumerate(order)}
    keep = ("name", "version", "description", "main", "scripts", "dependencies", "gypfile", "license")
    return {
        "name": name,
        "dist-tags": {"latest": order[-1]},
        "versions": {v: {**{k: versions[v].manifest[k] for k in keep if k in versions[v].manifest},
                         "dist": {"tarball": f"{base_url}/{name}/-/{name}-{v}.tgz"},
                         "_npmUser": {"name": PUBLISHER}} for v in order},
        "time": {"created": times[order[0]].isoformat(), "modified": times[order[-1]].isoformat(),
                 **{v: t.isoformat() for v, t in times.items()}},
    }


def router(packages_dir: Path, base_url: str, token: str, prefix: str = "/lab") -> APIRouter:
    packages = load(packages_dir)
    now = datetime.now(timezone.utc)
    api = APIRouter(prefix=prefix, include_in_schema=False)

    def allowed(authorization: str | None) -> None:
        if not authorization or not secrets.compare_digest(authorization, f"Bearer {token}"):
            raise HTTPException(401, "The Bawabu test lab only serves Bawabu itself, never npm: its samples mimic malware.")

    @api.get("/{name}")
    async def doc(name: str, authorization: str | None = Header(default=None)) -> dict:
        allowed(authorization)
        if name not in packages:
            raise HTTPException(404, "Not found")
        return packument(name, packages[name], base_url, now)

    @api.get("/{name}/-/{filename}")
    async def file(name: str, filename: str, authorization: str | None = Header(default=None)) -> Response:
        allowed(authorization)
        for version, pkg in packages.get(name, {}).items():
            if filename == f"{name}-{version}.tgz":
                return Response(tarball(pkg.folder), media_type="application/octet-stream")
        raise HTTPException(404, "Not found")

    return api
