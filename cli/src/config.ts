import { readFileSync } from "node:fs";
import { DEFAULT_SERVICE_URL } from "./constants.js";

export interface Config {
  /** block: stop anything unchecked or unsafe. warn: never block (for trying Bawabu out). */
  mode: "block" | "warn";
  serviceUrl: string | null;
  /** Package names Bawabu never checks, e.g. private packages. "@myorg/*" covers a whole scope. */
  allowlist: string[];
  /** Investigate with Muse Spark Open (Meta's open-weights model) instead of Muse Spark on Meta's API. */
  openWeights: boolean;
}

export const DEFAULT_CONFIG: Config = { mode: "block", serviceUrl: DEFAULT_SERVICE_URL, allowlist: [], openWeights: false };

/** Package lists only travel over HTTPS, except to a service on this machine. */
export const isValidServiceUrl = (url: string) => /^https:\/\/[^\s/]+|^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/.test(url);

export function loadConfig(path: string): Config {
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    throw new Error(`can't read ${path}: ${(e as Error).message}`);
  }
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) throw new Error(`${path} must be a JSON object`);

  const { mode = DEFAULT_CONFIG.mode, serviceUrl = null, allowlist = [], openWeights = false } = raw as Partial<Config>;
  if (mode !== "block" && mode !== "warn") throw new Error(`"mode" must be "block" or "warn", got ${JSON.stringify(mode)}`);
  if (serviceUrl !== null && (typeof serviceUrl !== "string" || !isValidServiceUrl(serviceUrl))) {
    throw new Error(`"serviceUrl" must be an https:// URL (or http://localhost for development) or null`);
  }
  if (!Array.isArray(allowlist) || !allowlist.every((a) => typeof a === "string")) throw new Error(`"allowlist" must be a list of package names`);
  if (typeof openWeights !== "boolean") throw new Error(`"openWeights" must be true or false`);
  return { mode, serviceUrl, allowlist, openWeights };
}
