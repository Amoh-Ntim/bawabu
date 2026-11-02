"""Build the evidence report from a sandbox run: what the package read, ran, and tried to send.

Two raw inputs: the `strace -f` output (files/processes/connections) and the sink's JSONL log
(every DNS query and HTTP(S) request the package made, since all traffic is routed to our sink).
We cross-reference them into a small, human-readable report that the investigator and the hard
rules both consume.

The decisive signal is a **leaked canary**: a planted secret's value turning up in a request body
(even base64-encoded or nested) can only mean the package read the bait and tried to send it out.
A plain network call is not guilt on its own — legitimate installers fetch binaries.
"""

from __future__ import annotations

import base64
import binascii
import gzip
import json
import re
from dataclasses import dataclass, field

from . import honeypots, strace_parse

_B64_RUN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
# Hosts that are part of the harness or ordinary installer traffic, not exfiltration.
_BENIGN_HOSTS = ("registry.npmjs.org", "localhost", "127.0.0.1", "::1")


@dataclass
class NetworkAttempt:
    host: str
    scheme: str  # "https" | "http" | "dns"
    method: str = ""
    path: str = ""
    had_body: bool = False
    canaries: list[str] = field(default_factory=list)  # labels of canaries found in this request
    benign_destination: bool = False  # the install registry or loopback — not exfiltration


@dataclass
class Evidence:
    duration_s: float = 0.0
    secret_reads: list[str] = field(default_factory=list)
    processes: list[str] = field(default_factory=list)
    dns_queries: list[str] = field(default_factory=list)
    network: list[NetworkAttempt] = field(default_factory=list)
    canaries_leaked: list[str] = field(default_factory=list)  # "<label> → <host>"
    notes: list[str] = field(default_factory=list)

    @property
    def exfiltration(self) -> bool:
        """A planted secret left the box. This is the hard-rule 'always block' trigger."""
        return bool(self.canaries_leaked)

    def summary(self) -> str:
        if self.exfiltration:
            return "Exfiltration confirmed: " + "; ".join(self.canaries_leaked)
        unknown = [n for n in self.network if not n.benign_destination and n.scheme != "dns"]
        if self.secret_reads and unknown:
            return f"Read {len(self.secret_reads)} secret file(s) and contacted {len(unknown)} unknown host(s)."
        if self.secret_reads:
            return f"Read {len(self.secret_reads)} secret file(s); no outbound leak observed."
        if unknown:
            return f"Contacted {len(unknown)} unknown host(s); no secret read."
        return "No secret reads or unknown network contact observed."


def _candidates(text: str) -> list[str]:
    """`text` plus anything we can base64-decode out of it (malware often encodes before sending)."""
    out = [text]
    for run in _B64_RUN.findall(text):
        try:
            decoded = base64.b64decode(run + "=" * (-len(run) % 4), validate=True)
        except (binascii.Error, ValueError):
            continue
        try:
            out.append(decoded.decode("utf-8"))
        except UnicodeDecodeError:
            out.append(decoded.decode("latin-1"))
    return out


def _scan(blob: str, canaries: dict[str, str]) -> list[str]:
    """Labels of any canaries present in `blob` (checking base64-decoded forms too)."""
    cands = _candidates(blob)
    return [label for label, value in canaries.items() if any(value in c for c in cands)]


def _is_benign_host(host: str, extra: tuple[str, ...]) -> bool:
    hosts = _BENIGN_HOSTS + extra
    return any(host == h or host.endswith("." + h) for h in hosts)


def build(
    strace_text: str,
    sink_events: list[dict],
    duration_s: float,
    canaries: dict[str, str] | None = None,
    benign_hosts: tuple[str, ...] = (),
) -> Evidence:
    canaries = canaries or honeypots.ALL_CANARIES
    ev = Evidence(duration_s=round(duration_s, 1))

    facts = strace_parse.parse(strace_text)
    seen_secret: set[str] = set()
    for path in facts.read_opens():
        clean = path.rstrip("\x00")
        # npm reads ~/.npmrc and the project .npmrc for its own config on every run, so an .npmrc
        # read is not a signal by itself — a leaked npm-token canary (below) is what proves theft.
        if clean.endswith(".npmrc"):
            continue
        if honeypots.is_secret_path(clean) and clean not in seen_secret:
            seen_secret.add(clean)
            ev.secret_reads.append(clean)

    notable = {"sh", "bash", "dash", "curl", "wget", "nc", "ncat", "python", "python3", "perl", "ruby"}
    seen_proc: set[tuple[str, str]] = set()
    for argv in facts.execs:
        prog = argv[0].rsplit("/", 1)[-1]
        if prog not in notable:
            continue
        cmd = " ".join(argv[1:])[:200]
        # Skip Bawabu's own trigger wrapper and the bare rebuild/require shells it spawns.
        if "=== npm rebuild" in cmd or cmd.startswith("rebuild") or "process.env.PKG" in cmd:
            continue
        key = (prog, cmd)
        if key in seen_proc:
            continue
        seen_proc.add(key)
        ev.processes.append(f"{prog} {cmd}".strip())

    for ev_row in sink_events:
        kind = ev_row.get("kind")
        if kind == "dns":
            name = ev_row.get("name", "")
            if name and name not in ev.dns_queries:
                ev.dns_queries.append(name)
        elif kind == "http":
            host = ev_row.get("host", "") or ""
            body = _body(ev_row)
            blob = " ".join([host, ev_row.get("path", ""), json.dumps(ev_row.get("headers", {})), body])
            hits = _scan(blob, canaries)
            attempt = NetworkAttempt(
                host=host,
                scheme=ev_row.get("scheme", "http"),
                method=ev_row.get("method", ""),
                path=ev_row.get("path", ""),
                had_body=bool(body),
                canaries=hits,
                benign_destination=_is_benign_host(host, benign_hosts),
            )
            ev.network.append(attempt)
            for label in hits:
                ev.canaries_leaked.append(f"{label} → {host or 'unknown host'}")

    # Also treat a canary that shows up in a DNS name as a leak (DNS-tunnel exfiltration).
    for name in ev.dns_queries:
        for label in _scan(name, canaries):
            entry = f"{label} → DNS {name}"
            if entry not in ev.canaries_leaked:
                ev.canaries_leaked.append(entry)

    if ev.exfiltration:
        ev.notes.append("A planted canary secret was found leaving the sandbox. This is conclusive.")
    elif ev.secret_reads and any(not n.benign_destination and n.scheme != "dns" for n in ev.network):
        ev.notes.append("The package read a secret file and also made outbound requests; inspect the payloads.")
    return ev


def _body(row: dict) -> str:
    """A request body as text. The sink keeps non-UTF-8 bodies as base64: decode those byte for byte (and un-gzip them),
    so a canary sent in a binary or compressed body is still found."""
    if row.get("body_text"):
        return row["body_text"]
    try:
        raw = base64.b64decode(row.get("body_b64") or "")
    except (binascii.Error, ValueError):
        return ""
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except (OSError, EOFError):
            pass
    return raw.decode("latin-1")
