"""The /check wire format, shared with the CLI (cli/src/service.ts).

The CLI sends only package names and versions, never the command line, which can hold tokens and paths.
"""

from typing import Literal

from pydantic import BaseModel, Field

Ecosystem = Literal["npm", "pypi"]
Verdict = Literal["allow", "block", "ask"]


class Package(BaseModel):
    ecosystem: Ecosystem
    name: str = Field(min_length=1, max_length=214)
    # Requested version, range or tag; "" means whatever is latest.
    version: str = Field(default="", max_length=256)


class Manifest(BaseModel):
    """A whole-project install (npm ci, pip install -r ...): the packages come from files on the user's machine."""

    ecosystem: Ecosystem
    manager: str = Field(max_length=32)


class CheckRequest(BaseModel):
    client_version: str = Field(max_length=32)
    packages: list[Package] = Field(default_factory=list, max_length=200)
    manifests: list[Manifest] = Field(default_factory=list, max_length=20)


class PackageResult(BaseModel):
    ecosystem: Ecosystem
    name: str
    requested: str
    # The exact version judged, when known.
    version: str | None
    verdict: Verdict
    reason: str
    cached: bool


class ManifestResult(BaseModel):
    ecosystem: Ecosystem
    manager: str
    verdict: Verdict
    reason: str


class CheckResponse(BaseModel):
    verdict: Verdict
    results: list[PackageResult]
    manifests: list[ManifestResult]
