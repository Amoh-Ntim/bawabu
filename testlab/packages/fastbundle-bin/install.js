// BAWABU TEST FIXTURE — harmless. Mirrors a LEGITIMATE pattern: packages like esbuild
// download a prebuilt binary for the host platform on install. This does the benign
// shape of that (a network fetch on install) but must NOT be flagged as malware — it
// touches no secrets, and it only talks to the package registry it was installed from.
const fs = require("fs");
const path = require("path");

const registry = process.env.npm_config_registry || "https://registry.npmjs.org/";
const url = `${registry.replace(/\/$/, "")}/fastbundle-bin/-/placeholder-binary`;

console.log(`fastbundle-bin: fetching prebuilt binary for ${process.platform}-${process.arch}…`);

async function main() {
  try {
    const res = await fetch(url).catch(() => null);
    const bytes = res && res.ok ? Buffer.from(await res.arrayBuffer()) : Buffer.from("#!/bin/sh\necho fastbundle\n");
    fs.writeFileSync(path.join(__dirname, "fastbundle"), bytes);
    console.log("fastbundle-bin: binary ready.");
  } catch {
    // No network at install time is tolerable for the fixture.
  }
}
main();
