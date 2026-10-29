/**
 * MCP servers added through a config file edit. Muse starts these itself (not through the agent's
 * shell), so a server like `npx -y some-mcp-server` would download and run a package the hook never
 * sees. We catch it at the edit instead.
 */

import { analyze, type Analysis, type Context } from "./parse.js";
import { shellQuote } from "./shell.js";

/** Server definitions by name, from any config that uses mcpServers: Muse settings, Claude Code, .mcp.json. */
function servers(config: unknown): Map<string, unknown> {
  const found = new Map<string, unknown>();
  const add = (prefix: string, block: unknown) => {
    if (typeof block === "object" && block !== null) for (const [name, def] of Object.entries(block)) found.set(prefix + name, def);
  };
  if (typeof config !== "object" || config === null) return found;
  const c = config as Record<string, unknown>;
  add("", c.mcpServers);
  add("", c.mcp_servers);
  if (typeof c.projects === "object" && c.projects !== null) {
    for (const [path, project] of Object.entries(c.projects)) add(`${path}:`, (project as Record<string, unknown> | null)?.mcpServers);
  }
  return found;
}

/** What a server runs; changing only env or headers (say, a new token) doesn't count as a new server. */
const launch = (def: unknown) => {
  const d = (typeof def === "object" && def !== null ? def : {}) as Record<string, unknown>;
  return JSON.stringify([d.command, d.args, d.url]);
};

/** Servers in `after` that are new or run something different than in `before`. */
export function addedServers(before: unknown, after: unknown): Array<[string, unknown]> {
  const old = servers(before);
  return [...servers(after)].filter(([name, def]) => !old.has(name) || launch(old.get(name)) !== launch(def));
}

export function analyzeServer(def: unknown, ctx: Context): Analysis {
  const result: Analysis = { installs: [], unreadable: [] };
  const { command, args } = (typeof def === "object" && def !== null ? def : {}) as { command?: unknown; args?: unknown };
  if (typeof command !== "string") return result; // a remote (URL) server: nothing runs on this machine
  const argv = Array.isArray(args) ? args.map(String) : [];
  if (/(^|\/)(docker|podman|nerdctl)$/.test(command)) {
    result.unreadable.push({ command: [command, ...argv].join(" "), reason: "it runs a container image, which Bawabu can't check" });
    return result;
  }
  // Some configs put the whole command line in `command`.
  return analyze(argv.length ? [command, ...argv].map(shellQuote).join(" ") : command, ctx);
}
