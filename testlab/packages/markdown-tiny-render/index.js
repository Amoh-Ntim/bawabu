// BAWABU TEST FIXTURE #5 — harmless. This package is itself completely clean: no install script,
// no secrets, no network. The danger is its dependency, console-logs-transport, which carries the
// payload. A checker that only looks at the named package would wave this through.
const t = require("console-logs-transport");
module.exports = function render(md) {
  return String(md).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
};
module.exports.transport = t;
