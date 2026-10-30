"""Turn `strace -f` output into the few facts we care about: which files were opened, which
processes were spawned, and which network connections were attempted.

We run strace with a narrow trace set (openat/open, execve, connect) so the output stays small and
parseable. strace splits a syscall across two lines when another thread interrupts it
(`<unfinished ...>` / `<... resumed>`); we stitch those back together before matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A line is optionally prefixed by a PID (from -f): "1234 openat(...".
_PID = r"(?:\[pid\s+\d+\]\s*|\d+\s+)?"
_OPEN = re.compile(_PID + r'openat?\([^,]*,\s*"((?:[^"\\]|\\.)*)"(?:\s*,\s*([A-Z_|]+))?')
_EXECVE = re.compile(_PID + r'execve\("((?:[^"\\]|\\.)*)",\s*\[(.*?)\]')
_CONNECT = re.compile(_PID + r"connect\(")
_CONN_FAMILY = re.compile(r"sa_family=(AF_INET6?)")
_CONN_PORT = re.compile(r"sin6?_port=htons\((\d+)\)")
_CONN_ADDR = re.compile(r'inet_addr\("([^"]+)"\)|inet_pton\([^,]+,\s*"([^"]+)"')
_UNFINISHED = re.compile(_PID + r"(\w+)\(.*<unfinished \.\.\.>$")
_RESUMED = re.compile(_PID + r"<\.\.\. (\w+) resumed>(.*)$")
_ARG = re.compile(r'"((?:[^"\\]|\\.)*)"')


@dataclass
class StraceFacts:
    opened: list[tuple[str, str]] = field(default_factory=list)  # (path, flags)
    execs: list[list[str]] = field(default_factory=list)  # argv per execve
    connects: list[tuple[str, int]] = field(default_factory=list)  # (addr, port); addr "" = unix

    def read_opens(self) -> list[str]:
        """Paths opened for reading (or with no flags captured)."""
        return [p for p, flags in self.opened if "O_WRONLY" not in flags and "O_RDWR" not in flags]


def _stitch(text: str) -> list[str]:
    """Rejoin strace lines that were split by <unfinished>/<resumed>."""
    lines: list[str] = []
    pending: dict[str, str] = {}  # syscall name -> head of an unfinished line
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        m = _UNFINISHED.search(line)
        if m:
            pending[m.group(1)] = line[: line.rindex("<unfinished")]
            continue
        r = _RESUMED.search(line)
        if r and r.group(1) in pending:
            lines.append(pending.pop(r.group(1)) + r.group(2))
            continue
        lines.append(line)
    lines.extend(pending.values())
    return lines


def parse(text: str) -> StraceFacts:
    facts = StraceFacts()
    for line in _stitch(text):
        if (m := _OPEN.search(line)):
            facts.opened.append((m.group(1), m.group(2) or ""))
        elif (m := _EXECVE.search(line)):
            if line.rstrip().endswith("ENOENT") or "= -1" in line:
                continue  # a failed PATH-search attempt, not a real spawn
            argv = [a.encode().decode("unicode_escape") for a in _ARG.findall(m.group(2))]
            facts.execs.append([m.group(1)] + argv[1:] if argv else [m.group(1)])
        elif _CONNECT.search(line):
            if not _CONN_FAMILY.search(line):
                continue  # AF_UNIX or anything not IP: local IPC, not network
            port = _CONN_PORT.search(line)
            addr = _CONN_ADDR.search(line)
            facts.connects.append((
                (addr.group(1) or addr.group(2)) if addr else "",
                int(port.group(1)) if port else 0,
            ))
    return facts
