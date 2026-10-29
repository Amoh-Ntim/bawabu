/**
 * The Bawabu service's /check API (service/bawabu_service/models.py).
 * Only package names and versions are sent, never the command line, which can hold tokens and paths.
 */

import { VERSION } from "./constants.js";
import type { Install } from "./parse.js";

export type Verdict = "allow" | "block" | "ask";

export interface PackageResult {
  ecosystem: string;
  name: string;
  requested: string;
  version: string | null;
  verdict: Verdict;
  reason: string;
  cached: boolean;
}

export interface ManifestResult {
  ecosystem: string;
  manager: string;
  verdict: Verdict;
  reason: string;
}

export interface CheckResponse {
  verdict: Verdict;
  results: PackageResult[];
  manifests: ManifestResult[];
}

/** POSTs JSON and returns the parsed body; throws on network errors, timeouts and non-2xx answers. */
export type Post = (url: string, body: unknown, timeoutMs: number) => Promise<unknown>;

const PYPI_MANAGERS = new Set(["pip", "uv", "uvx", "pipx"]);
const VERDICTS = new Set(["allow", "block", "ask"]);

export function checkRequest(installs: Install[]) {
  const packages = new Map<string, { ecosystem: string; name: string; version: string }>();
  for (const p of installs.flatMap((i) => i.packages)) {
    packages.set(`${p.ecosystem}:${p.name}@${p.version}`, { ecosystem: p.ecosystem, name: p.name, version: p.version });
  }
  return {
    client_version: VERSION,
    packages: [...packages.values()],
    manifests: installs
      .filter((i) => i.action === "manifest")
      .map((i) => ({ ecosystem: PYPI_MANAGERS.has(i.manager) ? "pypi" : "npm", manager: i.manager })),
  };
}

export function parseCheckResponse(body: unknown): CheckResponse {
  const r = body as Partial<CheckResponse> | null;
  if (!r || !VERDICTS.has(r.verdict as string) || !Array.isArray(r.results) || !Array.isArray(r.manifests)) {
    throw new Error("the service sent an unexpected answer");
  }
  return r as CheckResponse;
}

export const httpPost: Post = async (url, body, timeoutMs) => {
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json", "user-agent": `bawabu-cli/${VERSION}` },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    throw new Error((e as Error).name === "TimeoutError" ? `no answer within ${Math.round(timeoutMs / 1000)}s` : `couldn't connect to ${new URL(url).host}`);
  }
  if (!response.ok) throw new Error(`the service answered HTTP ${response.status}`);
  return response.json();
};

/** A one-line description of the service for `bawabu init`; throws if it isn't reachable. */
export async function serviceHealth(serviceUrl: string): Promise<string> {
  const response = await fetch(`${serviceUrl.replace(/\/+$/, "")}/health`, { signal: AbortSignal.timeout(15_000) });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const body = (await response.json()) as { version?: string; engine?: number; cache?: string };
  return `version ${body.version}, engine ${body.engine}, cache ${body.cache}`;
}
