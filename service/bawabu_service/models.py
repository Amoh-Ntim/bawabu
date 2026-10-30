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
    # The registry the project installs from (npm only), as the CLI read it from .npmrc; absent = the public npm.
    registry: str | None = Field(default=None, max_length=512)


class Manifest(BaseModel):
    """A whole-project install (npm ci, pip install -r ...): the packages come from files on the user's machine."""

    ecosystem: Ecosystem
    manager: str = Field(max_length=32)


class CheckRequest(BaseModel):
    client_version: str = Field(max_length=32)
    # Investigate with Muse Spark Open (open weights, on Baseten) instead of Muse Spark on Meta's API.
    open_weights: bool = False
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
    # The red flags behind an "ask" or "block", one sentence each.
    signals: list[str] = Field(default_factory=list)
    # A real package the agent probably meant (for made-up or lookalike names), or a safe alternative.
    suggestion: str | None = None
    cached: bool
    # The investigation behind this verdict, for the report page (GET /investigations/{id}).
    report_id: str | None = None
    # True when the investigation is still running: the agent should wait a minute and retry.
    pending: bool = False


class ManifestResult(BaseModel):
    ecosystem: Ecosystem
    manager: str
    verdict: Verdict
    reason: str


class CheckResponse(BaseModel):
    verdict: Verdict
    results: list[PackageResult]
    manifests: list[ManifestResult]
