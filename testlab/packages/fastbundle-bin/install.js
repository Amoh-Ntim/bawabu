// BAWABU TEST FIXTURE — harmless.
// Downloads the prebuilt fastbundle binary for this platform from the registry the package
// was installed from, and falls back to a small shell stub when there's no network.
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
