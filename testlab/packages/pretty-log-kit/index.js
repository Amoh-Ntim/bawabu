// BAWABU TEST FIXTURE — harmless. A small, real logging helper.
const COLORS = { info: "\x1b[36m", warn: "\x1b[33m", error: "\x1b[31m", reset: "\x1b[0m" };

function log(level, ...args) {
  const color = COLORS[level] || "";
  console.log(`${color}[${level}]${COLORS.reset}`, ...args);
}

module.exports = {
  info: (...a) => log("info", ...a),
  warn: (...a) => log("warn", ...a),
  error: (...a) => log("error", ...a),
};
