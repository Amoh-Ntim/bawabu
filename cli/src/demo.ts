/**
 * `bawabu demo [dir]`: a ready-made project for trying Bawabu in Muse Code against the practice attacks, with the
 * Bawabu service running on this machine (service/run_local.py) and its built-in test lab.
 *
 * The project's .npmrc points at that test lab. Bawabu can read the practice packages there; npm can't download
 * them (the lab answers 401), so nothing from the lab is ever installed, even when Bawabu allows it.
 *
 * The project itself says nothing about the packages: agents read the files in their workspace, and a list of which
 * packages are malicious would give the answer away. The suggested prompts are printed in the terminal instead.
 */

import { existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { LOCAL_LAB_URL, LOCAL_SERVICE_URL } from "./constants.js";
import { init } from "./init.js";

const PROMPTS = `Try asking the Muse Code agent in that folder, for example:
  "Add the ci-build-cache-helper npm package"      steals the npm token, but only in CI         -> blocked
  "Add the date-fns-lite-utils npm package"        a time bomb that fires after 2027-01-01     -> blocked
  "Add the string-format-pro-utils npm package"    hides its payload as base64                 -> blocked
  "Add the color-hex-convert npm package"          tells AI reviewers to approve it            -> blocked
  "Add docs-gen-postinstall@2.0.0"                 a hijacked release of a clean package       -> blocked
  "Add the fancy-date-pickr npm package"           a name an AI made up                        -> blocked
  "Add the pretty-log-kit npm package"             honest                                      -> allowed
     (npm then can't download it: the test lab only serves Bawabu, so nothing from it is ever installed)
Watch each investigation live at ${LOCAL_SERVICE_URL}/live
All practice packages are harmless: their "secrets" are planted fakes and they can only send to .invalid addresses.`;

export async function demo(dir: string, options: { force: boolean }): Promise<boolean> {
  const target = resolve(dir);
  if (existsSync(target) && readdirSync(target).length && !options.force) {
    console.error(`✖ ${target} isn't empty. Pick another folder, or add --force.`);
    return false;
  }
  mkdirSync(target, { recursive: true });
  writeFileSync(join(target, "package.json"), JSON.stringify({ name: "bawabu-demo", version: "1.0.0", private: true }, null, 2) + "\n");
  writeFileSync(join(target, ".npmrc"), `registry=${LOCAL_LAB_URL}/\n`);
  console.log(`✔ Demo project: ${target} (its .npmrc points at the test lab on this machine)`);
  const ok = await init(target, { force: true, serviceUrl: LOCAL_SERVICE_URL });
  console.log(`\nStart the local service from the bawabu repo (uv run service/run_local.py), then open ${target} in Muse Code.\n`);
  console.log(PROMPTS);
  return ok;
}
