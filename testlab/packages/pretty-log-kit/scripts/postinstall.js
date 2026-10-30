// BAWABU TEST FIXTURE — harmless.
// Prints a banner and writes the default colour theme to a local cache file.
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
