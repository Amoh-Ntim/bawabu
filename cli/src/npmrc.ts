/**
 * Which npm registry a package would be installed from, read from .npmrc files the way npm does: the
 * project's (nearest first, walking up), then the user's. A `@scope:registry=` line wins for that scope.
 *
 * Only `registry` lines are read, and any credentials embedded in the URL are dropped, so nothing secret
 * from .npmrc ever reaches the service. The hook runs with a cleared environment, so npm_config_* variables
 * aren't visible; a `--registry` flag on the command itself isn't followed yet either.
 */

import { dirname, join } from "node:path";
import type { FileRead } from "./parse.js";

export const PUBLIC_NPM = "https://registry.npmjs.org";

/** The registry URL with credentials, query and trailing slash removed; null if it isn't an http(s) URL. */
export function cleanRegistry(value: string): string | null {
  let url: URL;
  try {
    url = new URL(value.trim());
  } catch {
    return null;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return null;
  return `${url.protocol}//${url.host}${url.pathname}`.replace(/\/+$/, "");
}

function parse(content: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const raw of content.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith(";") || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq < 0) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim().replace(/^["']|["']$/g, "");
    if ((key === "registry" || /^@[^:]+:registry$/.test(key)) && !value.includes("${")) {
      const clean = cleanRegistry(value);
      if (clean && !out.has(key)) out.set(key, clean);
    }
  }
  return out;
}

/** A lookup: package name -> the registry it comes from, or null for the public npm. */
export function npmRegistries(cwd: string, home: string, readFile: (path: string) => FileRead): (name: string) => string | null {
  const files: string[] = [];
  for (let dir = cwd; ; dir = dirname(dir)) {
    files.push(join(dir, ".npmrc"));
    if (dirname(dir) === dir) break;
  }
  files.push(join(home, ".npmrc"));
  const settings = new Map<string, string>();
  for (const path of [...new Set(files)]) {
    const read = readFile(path);
    if (read.kind !== "text") continue;
    for (const [key, value] of parse(read.content)) if (!settings.has(key)) settings.set(key, value);
  }
  return (name) => {
    const scope = name.startsWith("@") ? name.split("/")[0] : null;
    const registry = (scope && settings.get(`${scope}:registry`)) || settings.get("registry") || null;
    return registry && registry !== PUBLIC_NPM ? registry : null;
  };
}
