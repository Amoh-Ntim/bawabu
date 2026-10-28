"""Step 0 smoke test: prove Modal Sandboxes can do what the Bawabu X-ray needs.

Checks: (1) a sandbox starts and runs node, (2) outbound network is blocked,
(3) strace -f sees the files opened and processes spawned by package code.

Needs Modal auth in ~/.modal.toml (from `modal setup`). Run from the repo root:
    uv run sandbox/scripts/smoke_modal.py
"""

import sys
import time

import modal

CANARY = "npm_canary_7f3k9q"
# What a malicious postinstall does: spawn a shell that reads a secret file.
BAIT_SCRIPT = "require('child_process').execSync('cat /root/.npmrc')"


def run(sb, *cmd, timeout=60):
    proc = sb.exec(*cmd, timeout=timeout)
    out, err = proc.stdout.read(), proc.stderr.read()
    proc.wait()
    return proc.returncode, out, err


def check_node(sb):
    code, out, err = run(sb, "node", "--version")
    return code == 0, f"node {out.strip()}" if code == 0 else err.strip()[:200]


def check_network_blocked(sb):
    code, _, err = run(sb, "curl", "-sS", "-m", "5", "-o", "/dev/null", "https://registry.npmjs.org/")
    return code != 0, f"curl exit {code}: {err.strip()[:150] or '(no stderr)'}"


def check_strace(sb):
    run(sb, "sh", "-c", f"echo '//registry.npmjs.org/:_authToken={CANARY}' > /root/.npmrc")
    code, _, err = run(sb, "strace", "-f", "-e", "trace=openat,execve", "-o", "/tmp/trace.txt", "node", "-e", BAIT_SCRIPT)
    if code != 0:
        return False, f"strace exit {code}: {err.strip()[:200]}"
    _, trace, _ = run(sb, "cat", "/tmp/trace.txt")
    saw_exec = 'execve("/bin/sh"' in trace
    saw_open = "/root/.npmrc" in trace
    detail = f"execve /bin/sh seen: {saw_exec}, open /root/.npmrc seen: {saw_open}, {len(trace.splitlines())} trace lines"
    return saw_exec and saw_open, detail


def main():
    image = modal.Image.debian_slim().apt_install("nodejs", "strace", "curl")
    app = modal.App.lookup("bawabu-smoke", create_if_missing=True)

    start = time.monotonic()
    sb = modal.Sandbox.create(app=app, image=image, block_network=True, timeout=300)
    print(f"sandbox created in {time.monotonic() - start:.1f}s (first run includes the image build)\n")

    failed = 0
    try:
        for name, check in [("node runs", check_node), ("network blocked", check_network_blocked), ("strace works", check_strace)]:
            t = time.monotonic()
            try:
                ok, detail = check(sb)
            except Exception as exc:  # report every check, even if one blows up
                ok, detail = False, f"{type(exc).__name__}: {exc}"
            print(f"[{'PASS' if ok else 'FAIL'}] {name:16} {time.monotonic() - t:5.1f}s\n       {detail}\n")
            failed += not ok
    finally:
        sb.terminate()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
