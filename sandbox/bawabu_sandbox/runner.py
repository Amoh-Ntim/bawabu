"""The X-ray: run one package in a locked Modal sandbox and watch what it does.

Nothing from the package ever runs on anyone's real machine, and it can never reach the internet.

Two phases, because a network-blocked sandbox can't download anything:
  1. Stage (network on): `npm install <pkg> --ignore-scripts` into a throwaway sandbox so NONE of the
     package's own code runs — we only fetch files. Snapshot that filesystem.
  2. Trigger (network blocked): boot a fresh sandbox from the snapshot, plant canary secrets, start the
     fake-internet sink, point DNS at it, then deliberately run the package's code under `strace`
     (`npm rebuild` runs install scripts; `require()` runs load-time code). Collect the strace log and
     everything the package tried to send, and turn it into an evidence report.

Run one package by hand:
    uv run sandbox/scripts/run_sandbox.py env-loader-plus 1.0.0 --registry <verdaccio-url>
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import modal

log = logging.getLogger(__name__)

from . import honeypots
from .evidence import Evidence, build

_HERE = Path(__file__).resolve()
TRACE_PATH = "/tmp/trace.txt"
SINK_LOG = "/var/log/bawabu-sink.jsonl"
CA_PATH = "/opt/bawabu/ca.pem"
PROJECT = "/work/project"
# CA env vars so the package's HTTPS calls trust the sink and we capture their plaintext bodies.
CA_ENV = {"NODE_EXTRA_CA_CERTS": CA_PATH, "CURL_CA_BUNDLE": CA_PATH, "SSL_CERT_FILE": CA_PATH, "REQUESTS_CA_BUNDLE": CA_PATH}


@dataclass
class SandboxRun:
    ecosystem: str
    name: str
    version: str
    evidence: Evidence = field(default_factory=Evidence)
    install_scripts: dict[str, str] = field(default_factory=dict)
    trigger_output: str = ""
    sink_ready: bool = False
    sink_log_raw: str = ""
    error: str | None = None

    def ok(self) -> bool:
        return self.error is None


RESOLVE_LOG = "/var/log/bawabu-resolve.log"
SHIM_PATH = "/opt/bawabu/dnsshim.so"
FAKETIME_LIB = "/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1"


def build_image() -> modal.Image:
    return (
        modal.Image.debian_slim(python_version="3.13")
        .apt_install("nodejs", "npm", "strace", "ca-certificates", "faketime", "curl", "gcc", "libc6-dev")
        .pip_install("cryptography>=43")
        .add_local_file(str(_HERE.parent / "dnsshim.c"), "/opt/bawabu/dnsshim.c", copy=True)
        .run_commands(f"gcc -shared -fPIC -o {SHIM_PATH} /opt/bawabu/dnsshim.c -ldl")
        .add_local_file(str(_HERE.parent / "sink.py"), "/opt/bawabu/sink.py")
    )


def _run(sb: modal.Sandbox, *cmd: str, timeout: int = 60, env: dict | None = None) -> tuple[int, str, str]:
    proc = sb.exec(*cmd, timeout=timeout, env=env or {})
    out, err = proc.stdout.read(), proc.stderr.read()
    proc.wait()
    return proc.returncode, out, err


def _read_file(sb: modal.Sandbox, path: str) -> str:
    try:
        return sb.filesystem.read_text(path)
    except Exception:
        return ""


def _warm_registry(registry: str, auth: str | None, name: str) -> bool:
    """The test-lab Verdaccio scales to zero; its first (cold) request can return an empty packument
    that npm caches as ENOVERSIONS. Wake it from here (we have network) until it serves versions."""
    import json
    import urllib.request

    headers = {"Authorization": f"Basic {auth}"} if auth else {}
    req = urllib.request.Request(f"{registry.rstrip('/')}/{name}", headers=headers)
    for _ in range(8):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if json.load(resp).get("versions"):
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def _stage(app: modal.App, image: modal.Image, name: str, spec: str, registry: str | None, registry_auth: str | None) -> modal.Image:
    """Phase 1: fetch the package (and deps) with scripts disabled, then snapshot the filesystem."""
    sb = modal.Sandbox.create(app=app, image=image, block_network=False, timeout=240)
    try:
        sb.filesystem.write_text("", f"{PROJECT}/.keep")
        npmrc = f"registry={registry}\n" if registry else ""
        if registry and registry_auth:
            host = registry.split("://", 1)[-1].rstrip("/")
            npmrc += f'//{host}/:_auth="{registry_auth}"\nalways-auth=true\n'
        if npmrc:
            sb.filesystem.write_text(npmrc, f"{PROJECT}/.npmrc")
        _run(sb, "sh", "-c", f"cd {PROJECT} && npm init -y >/dev/null 2>&1", timeout=60)

        # Verdaccio (the test lab) answers /-/ping before its storage is ready, so a cold first hit
        # returns an empty packument that npm would cache as ENOVERSIONS. Wake it from THIS container
        # (where npm will run) with curl until it serves versions, so npm's first fetch is good.
        if registry:
            auth_h = f'-H "Authorization: Basic {registry_auth}"' if registry_auth else ""
            warm = (f'for i in $(seq 1 20); do curl -s {auth_h} '
                    f'-H "Accept: application/vnd.npm.install-v1+json" {registry.rstrip("/")}/{name} '
                    f'| grep -q \'"versions"\' && break; sleep 2; done')
            _run(sb, "sh", "-c", warm, timeout=60)

        reg = f"--registry {registry}" if registry else ""
        install = (f"cd {PROJECT} && npm install {spec} --ignore-scripts --no-audit --no-fund "
                   f"--prefer-online --fetch-retries=3 --fetch-retry-mintimeout=1000 {reg} 2>&1")
        for _ in range(3):  # retry with a clean cache in case a bad packument was cached anyway
            code, out, err = _run(sb, "sh", "-c", install, timeout=180)
            if code == 0:
                break
            _run(sb, "npm", "cache", "clean", "--force", timeout=30)
            time.sleep(2)
        if code != 0:
            reg_cfg = _run(sb, "sh", "-c", f"cd {PROJECT} && npm config get registry")[1].strip()
            raise RuntimeError(f"staging install failed (exit {code}); registry={reg_cfg}\n{(out + err)[-1500:]}")
        return sb.snapshot_filesystem(timeout=120)
    finally:
        sb.terminate()


def _install_scripts(sb: modal.Sandbox, name: str) -> dict[str, str]:
    code, out, _ = _run(
        sb, "node", "-e",
        f'try{{const p=require("{PROJECT}/node_modules/{name}/package.json");'
        f'process.stdout.write(JSON.stringify(p.scripts||{{}}))}}catch(e){{process.stdout.write("{{}}")}}',
        timeout=30,
    )
    import json
    try:
        scripts = json.loads(out or "{}")
    except ValueError:
        return {}
    keep = ("preinstall", "install", "postinstall", "prepare", "prepublish")
    return {k: v for k, v in scripts.items() if k in keep}


def investigate(
    name: str,
    version: str,
    *,
    ecosystem: str = "npm",
    registry: str | None = None,
    registry_auth: str | None = None,
    env: dict[str, str] | None = None,
    fake_date: str | None = None,
    timeout: int = 90,
    app: modal.App | None = None,
) -> SandboxRun:
    if ecosystem != "npm":
        return SandboxRun(ecosystem, name, version, error="only npm is supported so far")
    spec = f"{name}@{version}" if version else name
    run = SandboxRun(ecosystem, name, version)
    app = app or modal.App.lookup("bawabu-sandbox", create_if_missing=True)
    image = build_image()

    if registry:
        _warm_registry(registry, registry_auth, name)
    try:
        staged = _stage(app, image, name, spec, registry, registry_auth)
    except Exception as exc:
        run.error = f"stage: {exc}"
        return run

    from modal.stream_type import StreamType
    sb = modal.Sandbox.create(app=app, image=staged, block_network=True, timeout=max(timeout + 120, 240), cpu=1.0, memory=1024)
    try:
        run.install_scripts = _install_scripts(sb, name)

        # Lived-in home + planted canaries, and send all DNS to the sink.
        for bait in honeypots.planted_files(project=PROJECT):
            sb.filesystem.write_text(bait.contents, bait.path)
        # DNS can't be repointed (Modal manages /etc/resolv.conf), so the trigger env LD_PRELOADs a
        # resolver shim that sends every hostname to the loopback sink. Nothing else needed here.

        sink = sb.exec(
            "sh", "-c", f"python3 /opt/bawabu/sink.py --log {SINK_LOG} --ca {CA_PATH} --ready /tmp/sink.ready 2>/var/log/sink.err",
            stdout=StreamType.DEVNULL, stderr=StreamType.DEVNULL,
        )
        for _ in range(60):  # wait up to ~15s for the sink to come up
            if _run(sb, "test", "-f", "/tmp/sink.ready")[0] == 0:
                run.sink_ready = True
                break
            time.sleep(0.25)
        if not run.sink_ready:
            run.evidence.notes.append("sink did not report ready: " + _read_file(sb, "/var/log/sink.err").strip()[-300:])

        preload = SHIM_PATH
        full_env = {**CA_ENV, **honeypots.env_canaries(), **(env or {}), "PKG": name, "BAWABU_RESOLVE_LOG": RESOLVE_LOG}
        if fake_date:
            # Preload libfaketime alongside the shim and shift the clock, so time-bomb payloads fire.
            preload = f"{FAKETIME_LIB}:{SHIM_PATH}"
            full_env["FAKETIME"] = f"{fake_date} 00:00:00" if len(fake_date) <= 10 else fake_date
        full_env["LD_PRELOAD"] = preload
        trigger = (
            f"cd {PROJECT}\n"
            "echo '=== npm rebuild (runs install scripts) ==='\n"
            "npm rebuild --foreground-scripts 2>&1 || true\n"
            "echo '=== require (runs load-time code) ==='\n"
            'node -e \'try{require(process.env.PKG)}catch(e){console.log("require error:",e.message)}\' 2>&1 || true\n'
            "sleep 1\n"
            "echo '=== done ==='\n"
        )
        straced = ["strace", "-f", "-e", "trace=openat,open,connect,execve", "-s", "300", "-o", TRACE_PATH, "sh", "-c", trigger]

        start = time.monotonic()
        code, out, err = _run(sb, *straced, timeout=timeout, env=full_env)
        duration = time.monotonic() - start
        run.trigger_output = (out + err)[-4000:]
        _ = sink  # the sink keeps running until the sandbox is torn down; it flushes every line

        time.sleep(0.5)
        trace_text = _read_file(sb, TRACE_PATH)
        sink_text = _read_file(sb, SINK_LOG)
        resolve_text = _read_file(sb, RESOLVE_LOG)
        run.sink_log_raw = sink_text
    except Exception as exc:
        log.exception("sandbox trigger phase failed for %s@%s", name, version)
        run.error = f"trigger: {type(exc).__name__}: {exc}"
        return run
    finally:
        sb.terminate()

    import json
    events = []
    for line in sink_text.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    # Names the package tried to resolve (captured by the shim) — the intended destinations, even
    # for requests that never completed. Add any not already seen via the sink's own DNS server.
    seen = {e.get("name") for e in events if e.get("kind") == "dns"}
    for name in dict.fromkeys(resolve_text.split()):
        if name and name not in seen:
            events.append({"kind": "dns", "name": name, "qtype": "A"})
    # The registry the package was installed from is a known-good destination (esbuild-style
    # installers fetch their own binary from it); don't count that as suspicious contact.
    benign = (registry.split("://", 1)[-1].rstrip("/").split("/")[0],) if registry else ()
    ev = build(trace_text, events, duration, benign_hosts=benign)
    ev.notes = run.evidence.notes + ev.notes  # keep any notes gathered during the run
    run.evidence = ev
    return run
