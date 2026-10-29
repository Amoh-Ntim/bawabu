// BAWABU TEST FIXTURE — harmless. A plausible-looking .env loader so the package has a real main.
const fs = require("fs");
module.exports = function load(file = ".env") {
  try {
    return Object.fromEntries(
      fs.readFileSync(file, "utf8").split("\n").filter(Boolean).map((l) => l.split("=")),
    );
  } catch {
    return {};
  }
};
