import { readFileSync } from "node:fs";

export interface Config {
  /** block: stop anything unchecked or unsafe. warn: never block (for trying Bawabu out). */
  mode: "block" | "warn";
  serviceUrl: string | null;
  /** Package names Bawabu never checks, e.g. private packages. "@myorg/*" covers a whole scope. */
  allowlist: string[];
}

export const DEFAULT_CONFIG: Config = { mode: "block", serviceUrl: null, allowlist: [] };

export function loadConfig(path: string): Config {
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    throw new Error(`can't read ${path}: ${(e as Error).message}`);
  }
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) throw new Error(`${path} must be a JSON object`);

  const { mode = DEFAULT_CONFIG.mode, serviceUrl = null, allowlist = [] } = raw as Partial<Config>;
  if (mode !== "block" && mode !== "warn") throw new Error(`"mode" must be "block" or "warn", got ${JSON.stringify(mode)}`);
  if (serviceUrl !== null && typeof serviceUrl !== "string") throw new Error(`"serviceUrl" must be a string or null`);
  if (!Array.isArray(allowlist) || !allowlist.every((a) => typeof a === "string")) throw new Error(`"allowlist" must be a list of package names`);
  return { mode, serviceUrl, allowlist };
}
