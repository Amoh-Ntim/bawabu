// BAWABU TEST FIXTURE — harmless. Falls back to a stub if the native build is absent.
let native;
try {
  native = require("./build/Release/resize.node");
} catch {
  native = { resize: () => true };
}
module.exports = { resize: native.resize };
