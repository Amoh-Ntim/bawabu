"""Step 6: the diff engine. Reads a package's code without running it and compares it with the version
published just before, so the signals point at what *changed*.

Hijacks rarely touch the public API: the clean 1.0.0 becomes a 2.0.0 that quietly adds an install script,
a new file for that script to run, and code that reads secrets or calls out. Scanning one version in
isolation flags every package that legitimately downloads a binary; comparing with the previous version
separates "has always done this" from "started doing this today".

Everything here is static: tarballs are unpacked in memory (never to disk) and only read as text. Each
signal carries the file, line and excerpt it came from, so the investigator's citations can be checked
against it (Step 7).
"""

from __future__ import annotations

import asyncio
import difflib
import hashlib
import io
import math
import posixpath
import re
import tarfile
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote, urlsplit

import httpx
import semantic_version

from . import registry

MAX_TARBALL = 64 * 1024 * 1024  # next is ~30 MB
MAX_FILES = 20_000
MAX_UNPACKED = 500 * 1024 * 1024  # decompression-bomb guard on the raw bytes read
MAX_KEPT = 150 * 1024 * 1024  # what is actually held in memory (big files are kept as a hash)
MAX_SCAN_FILE = 1024 * 1024  # bigger files are kept as a hash: compared and listed, not scanned
MAX_DIFF_LINES = 400
TEXT_EXTENSIONS = (".js", ".cjs", ".mjs", ".ts", ".cts", ".mts", ".jsx", ".tsx", ".json", ".sh", ".py", ".gyp", ".yml", ".yaml", ".md", "")

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


@dataclass(frozen=True)
class Source:
    """Where to fetch packages from. The public npm by default; the test lab passes its URL and login."""

    url: str = registry.NPM
    headers: tuple[tuple[str, str], ...] = ()


@dataclass
class Signal:
    kind: str
    severity: str  # low | medium | high
    detail: str
    file: str | None = None
    line: int | None = None
    excerpt: str | None = None
    new: bool = True  # False when the previous version already did this

    def key(self) -> tuple[str, str]:
        """What counts as "the same behaviour" across versions: the kind plus the matched pattern."""
        return (self.kind, self.detail)

    def cite(self) -> str:
        where = f" ({self.file}:{self.line})" if self.file and self.line else f" ({self.file})" if self.file else ""
        return f"{self.detail}{where}"


@dataclass
class DiffReport:
    name: str
    version: str
    previous: str | None
    files: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    diffs: dict[str, str] = field(default_factory=dict)  # file -> unified diff against the previous version
    notes: list[str] = field(default_factory=list)

    @property
    def risk(self) -> str:
        """The worst severity among the signals that matter: new ones, or all of them for a first release."""
        relevant = [s for s in self.signals if s.new or self.previous is None]
        best = max((SEVERITY_RANK[s.severity] for s in relevant), default=0)
        return {0: "none", 1: "low", 2: "medium", 3: "high"}[best]

    def headline(self, limit: int = 6) -> list[str]:
        """The most serious signals as short sentences, new ones first."""
        ordered = sorted(self.signals, key=lambda s: (not (s.new or self.previous is None), -SEVERITY_RANK[s.severity]))
        return [s.cite() + ("" if s.new or self.previous is None else " [also in the previous version]") for s in ordered[:limit]]


# ---------------------------------------------------------------------------------------------- unpacking


def unpack(tarball: bytes) -> dict[str, bytes]:
    """The package's files, keyed by path inside the package (the tarball's top folder, usually `package/`,
    is dropped). Only regular files; anything with an absolute or `..` path, links and devices are skipped."""
    files: dict[str, bytes] = {}
    total = kept = 0
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:*") as tar:
        for member in tar:
            if not member.isfile():
                continue
            parts = member.name.replace("\\", "/").split("/")
            path = posixpath.normpath("/".join(parts[1:] if len(parts) > 1 else parts))
            if path.startswith(("/", "..")) or path in (".", ""):
                continue
            if len(files) >= MAX_FILES or total + member.size > MAX_UNPACKED or kept > MAX_KEPT:
                raise ValueError("package is too large to inspect")
            handle = tar.extractfile(member)
            if handle is None:
                continue
            data = handle.read()
            total += len(data)
            # Keep big files (bundles, binaries) as a hash so they still count as added/changed without
            # holding them in memory; the leading NUL marks them as not-text for the scanner.
            files[path] = data if len(data) <= MAX_SCAN_FILE else b"\x00sha256:" + hashlib.sha256(data).hexdigest().encode()
            kept += len(files[path])
    return files


def _text(path: str, data: bytes) -> str | None:
    if len(data) > MAX_SCAN_FILE or b"\x00" in data[:4096]:
        return None
    if posixpath.splitext(path)[1].lower() not in TEXT_EXTENSIONS and not data[:2] == b"#!":
        return None
    return data.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------------------------- scanning

_BASE64_BLOB = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")
_HEX_BLOB = re.compile(r"(?:\\x[0-9a-fA-F]{2}){40,}|['\"][0-9a-fA-F]{200,}['\"]")
_DYNAMIC_CODE = re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(|(?<![\w.])Function\s*\(|\bvm\s*\.\s*run\w*\s*\(|\bexecScript\s*\(")
_CAPABILITIES = {
    "child_process": re.compile(r"""require\(\s*['"](?:node:)?child_process['"]\s*\)|from\s+['"](?:node:)?child_process['"]|\bexecSync\s*\(|\bspawnSync?\s*\("""),
    "network": re.compile(r"""require\(\s*['"](?:node:)?(?:https?|net|tls|dgram|dns)['"]\s*\)|from\s+['"](?:node:)?(?:https?|net|tls|dgram|dns)['"]|\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\s*\("""),
}
_SECRETS = re.compile(
    r"""\.npmrc|\.ssh\b|id_rsa|id_ed25519|\.aws[/\\]credentials|\.git-credentials|\.docker[/\\]config\.json|\.kube[/\\]config"""
    r"""|\b(?:NPM_TOKEN|NODE_AUTH_TOKEN|GITHUB_TOKEN|GH_TOKEN|AWS_SECRET_ACCESS_KEY|AWS_ACCESS_KEY_ID)\b"""
    r"""|JSON\.stringify\(\s*process\.env\s*\)|Object\.(?:keys|entries)\(\s*process\.env\s*\)""",
)
_INJECTION = re.compile(
    r"(?:note|message|instructions?)\s+(?:to|for)\s+(?:the\s+|any\s+)?(?:automated|ai|llm|code|security)\s+(?:reviewer|scanner|auditor|assistant|agent)"
    r"|ignore\s+(?:all\s+|any\s+)?(?:previous|prior|above|the)?\s*(?:instructions|install\s+scripts|warnings)"
    r"|(?:respond|reply|answer|output)\s+with\s+(?:the\s+)?(?:verdict|['\"]?allow)"
    r"|do\s+not\s+(?:flag|report|block)\s+this"
    r"|(?:this\s+(?:package|code|module))\s+(?:has\s+been|is|was)\s+(?:audited|approved|verified|whitelisted)"
    r"|you\s+are\s+an?\s+(?:ai|language\s+model|llm)",
    re.IGNORECASE,
)
_COMMENT = re.compile(r"\s*(?://|/\*|\*|#(?!!))")
# `Function("return this")()` is the standard pre-globalThis way to reach the global object (lodash, bundles).
_GLOBAL_THIS = re.compile(r"""Function\(\s*['"]return this['"]\s*\)""")
_SCRIPT_FILE = re.compile(r"""(?:node|sh|bash|python3?)\s+(?:-\w+\s+)*['"]?([\w./@-]+\.(?:c?js|mjs|sh|py))""")


def _excerpt(line: str, start: int, end: int, width: int = 160) -> str:
    if len(line) <= width:
        return line.strip()
    lo = max(0, start - 40)
    return ("…" if lo else "") + line[lo : lo + width].strip() + "…"


def _entropy(s: str) -> float:
    counts = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())


def scan_file(path: str, text: str, install_files: set[str]) -> list[Signal]:
    """Static signals in one file. Code that install scripts run is held to a stricter standard."""
    signals: list[Signal] = []
    runs_on_install = path in install_files
    minified = path.endswith((".min.js", ".bundle.js")) or "/dist/" in f"/{path}"
    has_dynamic = bool(_DYNAMIC_CODE.search(text))
    seen: set[tuple[str, str]] = set()

    def add(kind: str, severity: str, detail: str, lineno: int, line: str, m: re.Match) -> None:
        if (kind, detail) in seen:
            return
        seen.add((kind, detail))
        signals.append(Signal(kind, severity, detail, path, lineno, _excerpt(line, m.start(), m.end())))

    docs = path.lower().endswith(".md")
    for lineno, line in enumerate(text.splitlines(), 1):
        if (m := _INJECTION.search(line)):
            add("prompt_injection", "high", "Text aimed at AI reviewers, telling them to approve the package", lineno, line, m)
        if docs or _COMMENT.match(line):
            continue  # injection text lives in comments and READMEs; code signals only count in code
        if (m := _BASE64_BLOB.search(line)) and _entropy(m.group(0)[:400]) > 4.5:
            sev = "high" if (has_dynamic or runs_on_install) else "medium"
            add("obfuscation", sev, "A long base64-encoded blob" + (" that is decoded and run" if has_dynamic else ""), lineno, line, m)
        if (m := _HEX_BLOB.search(line)):
            add("obfuscation", "high" if has_dynamic else "medium", "A long hex-encoded string", lineno, line, m)
        if (m := _DYNAMIC_CODE.search(line)) and not minified and not _GLOBAL_THIS.search(line):
            add("dynamic_code", "high" if runs_on_install else "medium",
                f"Builds and runs code at runtime ({m.group(0).strip().rstrip('(').strip()})", lineno, line, m)
        for cap, pattern in _CAPABILITIES.items():
            if (m := pattern.search(line)):
                label = {"child_process": "Starts other programs (child_process)", "network": "Makes network requests"}[cap]
                # Downloading on install is normal for binary packages (esbuild, sharp): medium, not high.
                add("capability", "medium" if runs_on_install else "low",
                    label + (" in code that runs on install" if runs_on_install else ""), lineno, line, m)
        if (m := _SECRETS.search(line)):
            add("secret_access", "high" if runs_on_install else "medium",
                f"Refers to credentials ({m.group(0)})" + (" in code that runs on install" if runs_on_install else ""), lineno, line, m)
        if len(line) > 2000 and not minified and path.endswith((".js", ".cjs", ".mjs")):
            signals.append(Signal("obfuscation", "low", "A single line over 2,000 characters long", path, lineno, line[:120] + "…"))

    # The exfiltration shape: install-time code that both touches credentials and talks to the network.
    secret = next((s for s in signals if s.kind == "secret_access"), None)
    network = next((s for s in signals if s.kind == "capability" and s.detail.startswith("Makes network")), None)
    if runs_on_install and secret and network:
        signals.insert(0, Signal("exfiltration_pattern", "high",
                                 "Install-time code reads credentials and makes network requests in the same file",
                                 path, secret.line, secret.excerpt))
    return signals


def _install_files(manifest: dict, files: dict[str, bytes]) -> set[str]:
    """Files the install scripts run (`node scripts/setup.js`), so their contents get the strict rules."""
    found: set[str] = set()
    scripts = manifest.get("scripts") or {}
    for key in registry.NPM_INSTALL_SCRIPTS:
        for ref in _SCRIPT_FILE.findall(str(scripts.get(key, ""))):
            path = posixpath.normpath(ref)
            if path in files:
                found.add(path)
    if manifest.get("gypfile") or "binding.gyp" in files:
        found.add("binding.gyp")
    return found


def _manifest(files: dict[str, bytes]) -> dict:
    import json

    try:
        return json.loads(files.get("package.json", b"{}").decode("utf-8", errors="replace"))
    except ValueError:
        return {}


def scan(files: dict[str, bytes], paths: set[str] | None = None) -> list[Signal]:
    """Signals in `files` (or just `paths` among them)."""
    manifest = _manifest(files)
    install = _install_files(manifest, files)
    out: list[Signal] = []
    for path in sorted(files if paths is None else paths):
        text = _text(path, files[path])
        if text is not None:
            out.extend(scan_file(path, text, install))
    return out


# ---------------------------------------------------------------------------------------------- diffing


def compare(name: str, version: str, new: dict[str, bytes], previous: str | None = None, old: dict[str, bytes] | None = None,
            provenance: bool | None = None, previous_provenance: bool | None = None) -> DiffReport:
    """Signals for `new`, each marked new or not by comparing with `old` (the previous version), plus the
    package-level changes: install scripts, the files they run, dependencies, provenance."""
    report = DiffReport(name, version, previous, files=sorted(new))
    new_manifest, old_manifest = _manifest(new), _manifest(old or {})
    new_install = _install_files(new_manifest, new)

    if old is None:
        signals = scan(new)
    else:
        # A file that is byte-identical (and equally install-time) in both versions is scanned once: its
        # signals can't be new. Big packages (next, core-js) are mostly unchanged files, so this halves the work.
        old_install = _install_files(old_manifest, old)
        same = {p for p in set(new) & set(old) if new[p] == old[p] and (p in new_install) == (p in old_install)}
        shared, fresh = scan(new, same), scan(new, set(new) - same)
        # Behaviour the previous version already had, in any file, isn't new: a binary downloader that has
        # always made network calls on install stays quiet; one that just started doing so doesn't.
        old_keys = {s.key() for s in shared + scan(old, set(old) - same)}
        for s in shared:
            s.new = False
        for s in fresh:
            s.new = s.key() not in old_keys
        signals = sorted(shared + fresh, key=lambda s: (s.file or "", s.line or 0))
        report.added = sorted(set(new) - set(old))
        report.removed = sorted(set(old) - set(new))
        report.changed = sorted(p for p in set(new) & set(old) if new[p] != old[p])
        for path in report.added + report.changed:
            a, b = _text(path, old.get(path, b"")), _text(path, new[path])
            if b is None:
                continue
            lines = list(difflib.unified_diff((a or "").splitlines(), b.splitlines(), f"{previous}/{path}", f"{version}/{path}", lineterm="", n=2))
            report.diffs[path] = "\n".join(lines[:MAX_DIFF_LINES]) + ("\n… (diff truncated)" if len(lines) > MAX_DIFF_LINES else "")

    new_scripts = registry._npm_install_scripts(new_manifest)
    old_scripts = registry._npm_install_scripts(old_manifest) if old is not None else None
    for key, cmd in new_scripts.items():
        if old_scripts is None:
            report.signals.append(Signal("install_script", "medium", f"Runs code on install ({key}: {cmd})", "package.json", new=True))
        elif key not in old_scripts:
            report.signals.append(Signal("install_script", "high", f"Adds code that runs on install ({key}: {cmd}); {previous} had none", "package.json"))
        elif old_scripts[key] != cmd:
            # Packages switch build tools (node-pre-gyp → node-gyp-build); a changed command is worth a look,
            # but the hijack tell is a new file for it to run, which is flagged high separately below.
            report.signals.append(Signal("install_script", "medium", f"Changes what runs on install ({key}: {old_scripts[key]} → {cmd})", "package.json"))
        else:
            report.signals.append(Signal("install_script", "low", f"Runs code on install ({key}: {cmd}), unchanged since {previous}", "package.json", new=False))
    if old is not None:
        for path in sorted(new_install & set(report.added)):
            report.signals.append(Signal("install_script", "high", f"The install script runs a file that is new in this version ({path})", path))
        old_deps = set((old_manifest.get("dependencies") or {}))
        for dep in sorted(set(new_manifest.get("dependencies") or {}) - old_deps):
            report.signals.append(Signal("new_dependency", "medium" if new_install else "low", f"Adds a dependency: {dep}", "package.json"))
    if previous_provenance and provenance is False:
        report.signals.append(Signal("provenance_lost", "high",
                                     f"{previous} was published with provenance (built and signed by CI); this version wasn't"))

    report.signals.extend(signals)
    if old is None and previous is None:
        report.notes.append("First release, so there is nothing to compare with; every signal is shown.")
        # A clean package can still pull in a bad one; list what it depends on so the investigator can follow.
        for dep, wanted in sorted((new_manifest.get("dependencies") or {}).items()):
            report.signals.append(Signal("dependency", "low", f"Depends on {dep}@{wanted}", "package.json"))
    return report


# ---------------------------------------------------------------------------------------------- fetching


async def _get(client: httpx.AsyncClient, url: str, source: Source) -> httpx.Response:
    response = await client.get(url, headers=dict(source.headers))
    response.raise_for_status()
    return response


async def _tarball(client: httpx.AsyncClient, url: str, source: Source, name: str) -> bytes:
    # A registry behind a proxy may advertise tarball links on another host; fetch from the source instead.
    if urlsplit(url).netloc != urlsplit(source.url).netloc:
        url = f"{source.url.rstrip('/')}/{quote(name, safe='@')}/-/{url.rsplit('/', 1)[-1]}"
    async with client.stream("GET", url, headers=dict(source.headers)) as response:
        response.raise_for_status()
        chunks, size = [], 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_TARBALL:
                raise ValueError("tarball is too large to inspect")
            chunks.append(chunk)
    return b"".join(chunks)


def previous_version(version: str, versions: dict[str, dict], when) -> str | None:
    """The version to compare against: the nearest lower version by semver, skipping prereleases unless the
    target is one. Publish time alone misleads: nightlies and backports to old lines land in between."""
    try:
        target = semantic_version.Version(version)
    except ValueError:
        target = None
    if target is not None:
        lower = []
        for v in versions:
            try:
                parsed = semantic_version.Version(v)
            except ValueError:
                continue
            if parsed < target and (target.prerelease or not parsed.prerelease):
                lower.append((parsed, v))
        return max(lower)[1] if lower else None
    published = when(version)  # not semver: fall back to publish order
    earlier = sorted((v for v in versions if v != version and published and (t := when(v)) and t < published), key=when)
    return earlier[-1] if earlier else None


async def analyze(client: httpx.AsyncClient, name: str, requested: str, source: Source = Source()) -> DiffReport:
    """Fetch the resolved version and the one published before it, and compare them."""
    doc = (await _get(client, f"{source.url.rstrip('/')}/{quote(name, safe='@')}", source)).json()
    versions: dict[str, dict] = doc.get("versions") or {}
    version = registry.resolve_npm(requested, doc.get("dist-tags") or {}, versions)
    if version is None:
        raise LookupError(f"no version of {name} matches {requested!r}")
    times = doc.get("time") or {}

    def when(v: str) -> datetime | None:
        return registry._time(times.get(v))

    previous = previous_version(version, versions, when)
    meta = versions[version]

    jobs = [_tarball(client, meta["dist"]["tarball"], source, name)]
    if previous:
        jobs.append(_tarball(client, versions[previous]["dist"]["tarball"], source, name))
    blobs = await asyncio.gather(*jobs)
    new = unpack(blobs[0])
    old = unpack(blobs[1]) if previous else None
    has_prov = lambda m: "attestations" in (m.get("dist") or {})  # noqa: E731
    return compare(name, version, new, previous, old,
                   provenance=has_prov(meta), previous_provenance=has_prov(versions[previous]) if previous else None)
