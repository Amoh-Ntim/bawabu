/**
 * `bawabu scan <package>`: ask the Bawabu service about one npm package from the terminal, without an agent.
 *
 * It sends what the hook sends (the name, the version and the registry the project installs from, nothing else) and
 * prints the verdict, the evidence and the report link. A first check of a suspicious package can outlast one request;
 * asking again joins the running investigation instead of starting another.
 */

import { existsSync } from "node:fs";
import { join } from "node:path";
import { loadConfig } from "./config.js";
import { CONFIG_RELATIVE_PATH, DEFAULT_SERVICE_URL, LOCAL_LAB_URL, LOCAL_SERVICE_URL, SERVICE_TIMEOUT_SECONDS, VERSION } from "./constants.js";
import { parseNpmSpec } from "./managers.js";
import { cleanRegistry, npmRegistries } from "./npmrc.js";
import type { FileRead } from "./parse.js";
import { parseCheckResponse, type PackageResult, type Post } from "./service.js";

export interface ScanEnv {
  cwd: string;
  home: string;
  readFile: (path: string) => FileRead;
  post: Post;
  log: (line: string) => void;
}

export const SCAN_USAGE = "bawabu scan <package>[@version] [--local] [--lab] [--open-weights] [--service <url>] [--registry <url>]";
/** Each request already waits up to ~110 s on the service, so this is several minutes in all. */
const MAX_ROUNDS = 4;
const VALUE_FLAGS = new Set(["--service", "--registry"]);

/** Exit code: 0 allowed, 1 blocked, 2 a human should decide, it's still being investigated, or something failed. */
export async function scan(args: string[], env: ScanEnv): Promise<number> {
  const value = (flag: string) => {
    const i = args.indexOf(flag);
    return i >= 0 ? args[i + 1] : undefined;
  };
  const spec = args.find((a, i) => !a.startsWith("-") && !VALUE_FLAGS.has(args[i - 1] ?? ""));
  if (!spec) {
    env.log(`Usage: ${SCAN_USAGE}`);
    return 2;
  }
  const pkg = parseNpmSpec(spec);
  if (!pkg || pkg.source !== "registry") {
    env.log(`✖ "${spec}" isn't an npm package name; scan checks packages that come from a registry.`);
    return 2;
  }

  const base = (value("--service") ?? (args.includes("--local") ? LOCAL_SERVICE_URL : configuredService(env) ?? DEFAULT_SERVICE_URL)).replace(/\/+$/, "");
  const rawRegistry = value("--registry") ?? (args.includes("--lab") ? LOCAL_LAB_URL : null);
  const registry = rawRegistry ? cleanRegistry(rawRegistry) : npmRegistries(env.cwd, env.home, env.readFile)(pkg.name);
  if (rawRegistry && !registry) {
    env.log(`✖ --registry must be an http(s) URL, got ${rawRegistry}`);
    return 2;
  }
  const body = {
    client_version: VERSION,
    ...(args.includes("--open-weights") ? { open_weights: true } : {}),
    packages: [{ ecosystem: "npm", name: pkg.name, version: pkg.version, ...(registry ? { registry } : {}) }],
    manifests: [],
  };

  env.log(`Checking ${pkg.name}${pkg.version ? `@${pkg.version}` : ""}${registry ? ` from ${registry}` : ""} with ${base}`);
  env.log(`(investigations can be watched live at ${base}/live)`);
  for (let round = 1; ; round++) {
    let result: PackageResult;
    try {
      result = parseCheckResponse(await env.post(`${base}/check`, body, SERVICE_TIMEOUT_SECONDS * 1000)).results[0];
    } catch (e) {
      env.log(`✖ Couldn't get a verdict from ${base}: ${(e as Error).message}`);
      if (base === LOCAL_SERVICE_URL) env.log("  Is the local service running? Start it with: uv run service/run_local.py");
      return 2;
    }
    if (result.pending && round < MAX_ROUNDS) {
      env.log(`⏳ Still investigating${result.report_id ? `: ${base}/r/${result.report_id}` : ""}. Waiting for the verdict…`);
      continue;
    }
    report(result, base, env.log);
    return result.verdict === "allow" ? 0 : result.verdict === "block" ? 1 : 2;
  }
}

function configuredService(env: ScanEnv): string | null {
  const path = join(env.cwd, CONFIG_RELATIVE_PATH);
  try {
    return existsSync(path) ? loadConfig(path).serviceUrl : null;
  } catch {
    return null;
  }
}

function report(r: PackageResult, base: string, log: (line: string) => void): void {
  const label = r.verdict === "allow" ? "✅ ALLOWED" : r.verdict === "block" ? "⛔ BLOCKED" : r.pending ? "⏳ STILL INVESTIGATING" : "⏸ A HUMAN SHOULD DECIDE";
  log("");
  log(`${label}  ${r.name}${r.version ? `@${r.version}` : ""}`);
  log(`   ${r.reason}`);
  for (const s of r.signals ?? []) log(`   - ${s}`);
  if (r.suggestion) log(r.report_id ? `   A safer choice: ${r.suggestion}` : `   Did you mean ${r.suggestion}?`);
  if (r.report_id) log(`   Report: ${base}/r/${r.report_id}`);
}
