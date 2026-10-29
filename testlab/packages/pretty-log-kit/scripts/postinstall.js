// BAWABU TEST FIXTURE — harmless. A "heavy but benign" postinstall: the kind of
// legitimate work (banner + a local cache file) that must NOT be mistaken for an attack.
// It touches no secrets and makes no network request.
const fs = require("fs");
const path = require("path");

console.log("pretty-log-kit: building colour tables…");
const cacheDir = path.join(__dirname, "..", ".cache");
try {
  fs.mkdirSync(cacheDir, { recursive: true });
  fs.writeFileSync(path.join(cacheDir, "theme.json"), JSON.stringify({ built: true }));
  console.log("pretty-log-kit: ready.");
} catch {
  // A read-only install location is fine; the package still works.
}
