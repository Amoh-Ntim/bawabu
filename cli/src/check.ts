import { appendFileSync, existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { loadConfig, type Config } from "./config.js";
import { CHECK_DEADLINE_SECONDS, SERVICE_TIMEOUT_SECONDS } from "./constants.js";
import { addedServers, analyzeServer } from "./mcp.js";
import { analyze, merge, resolvePath, type Analysis, type Context, type FileRead, type Install, type PackageSpec } from "./parse.js";
import { checkRequest, httpPost, parseCheckResponse, type CheckResponse, type Post } from "./service.js";

/**
 * Muse runs the hook before every tool call. Exit 2 blocks the call and shows stderr to the agent.
 * Anything else, including a crash or a timeout, lets the call run, so every failure here must end in exit 2.
 */
export interface Decision {
  exitCode: 0 | 2;
  /** Shown to the agent when blocking. */
  message?: string;
  /** Logged to ~/.local/state/bawabu/checks.jsonl; absent for calls Bawabu ignores. */
  record?: Record<string, unknown>;
}

/** The machine-facing parts of a check, swappable in tests. */
export interface Env {
  home: string;
  readFile: (path: string) => FileRead;
  binExists: (cwd: string, bin: string) => boolean;
  post: Post;
}

interface HookPayload {
  tool_name?: unknown;
  tool_input?: { command?: unknown; workdir?: unknown; path?: unknown; content?: unknown; find?: unknown; replace?: unknown };
  cwd?: unknown;
  bawabu_selftest?: unknown;
}

/** What a tool call would do: run a shell command, or add MCP servers by editing a config file. */
type Subject = { kind: "command"; command: string; analysis: Analysis } | { kind: "mcp"; path: string; servers: string[]; analysis: Analysis };

const ALLOW: Decision = { exitCode: 0 };
const MCP_KEY = /"mcp(Servers|_servers)"/;

const block = (message: string, record?: Record<string, unknown>): Decision => ({ exitCode: 2, message, record });

export async function decide(input: string, getConfig: () => Config, envOverrides: Partial<Env> = {}): Promise<Decision> {
  const env: Env = { ...nodeEnv(), ...envOverrides };
  let payload: HookPayload;
  try {
    payload = JSON.parse(input);
  } catch {
    return block("⛔ Blocked by Bawabu: it couldn't read the hook input from Muse Code, so it blocked this to be safe. Ask the user to run `bawabu init` again.");
  }
  const tool = payload?.tool_name;
  const cwd = asString(payload.tool_input?.workdir) ?? asString(payload.cwd) ?? process.cwd();
  const ctx: Context = { cwd, home: env.home, readFile: env.readFile };

  let subject: Subject;
  if (tool === "bash") {
    const command = payload.tool_input?.command;
    if (typeof command !== "string") return block("⛔ Blocked by Bawabu: it couldn't read this shell command, so it blocked it to be safe.");
    subject = { kind: "command", command, analysis: analyze(command, ctx) };
  } else if (tool === "write_file" || tool === "edit_file") {
    const edit = mcpEdit(tool, payload.tool_input ?? {}, ctx);
    if (!edit) return ALLOW;
    subject = edit;
  } else {
    return ALLOW; // reads and Muse's own internal tools
  }
  const { analysis } = subject;
  if (!analysis.installs.length && !analysis.unreadable.length) return ALLOW;

  let config: Config;
  try {
    config = getConfig();
  } catch (e) {
    return block(`⛔ Blocked by Bawabu: its config couldn't be loaded (${(e as Error).message}), so this was blocked. Ask the user to fix .muse/bawabu.json or run \`bawabu init\`.`);
  }
  if (payload.bawabu_selftest === true) return block("Bawabu self-test: install detected and stopped.");

  const record = {
    tool,
    ...(subject.kind === "command" ? { command: subject.command } : { file: subject.path, mcpServers: subject.servers }),
    installs: analysis.installs,
    unreadable: analysis.unreadable,
    mode: config.mode,
  };
  if (config.mode === "warn") return { exitCode: 0, record: { ...record, decision: "allow", reason: "warn mode" } };
  if (analysis.unreadable.length) return block(unreadableMessage(subject), { ...record, decision: "block", reason: "unreadable" });

  const toCheck = analysis.installs
    .map((install) => ({ ...install, packages: install.packages.filter((p) => needsCheck(p, install, config, cwd, env)) }))
    .filter((install) => install.action === "manifest" || install.packages.length);
  if (!toCheck.length) return { exitCode: 0, record: { ...record, decision: "allow", reason: "allowlisted or local" } };
  if (!config.serviceUrl) return block(noServiceMessage(subject, toCheck), { ...record, decision: "block", reason: "no service" });

  const unsupported = toCheck.flatMap((i) => i.packages.filter((p) => p.source !== "registry"));
  if (unsupported.length) return block(unsupportedMessage(unsupported), { ...record, decision: "block", reason: "git or url source" });

  let response: CheckResponse;
  try {
    const answer = await env.post(`${config.serviceUrl.replace(/\/+$/, "")}/check`, checkRequest(toCheck), SERVICE_TIMEOUT_SECONDS * 1000);
    response = parseCheckResponse(answer);
  } catch (e) {
    const error = (e as Error).message;
    return block(
      `⛔ Blocked by Bawabu: it couldn't get a verdict from its service (${error}), so it blocked this to be safe. Try again in a minute; if it keeps happening, tell the user.`,
      { ...record, decision: "block", reason: "service error", error },
    );
  }
  const outcome = { ...record, decision: response.verdict, reason: "service", service: response };
  return response.verdict === "allow" ? { exitCode: 0, record: outcome } : block(verdictMessage(subject, response), outcome);
}

/** An edit that adds MCP servers, worked out from the file as it would be after the edit; null for any other edit. */
function mcpEdit(tool: "write_file" | "edit_file", input: NonNullable<HookPayload["tool_input"]>, ctx: Context): Subject | null {
  const path = asString(input.path);
  if (!path?.endsWith(".json")) return null;
  const full = resolvePath(ctx, path);
  const before = ctx.readFile(full);
  const beforeText = before.kind === "text" ? before.content : "";
  let afterText: string | undefined;
  if (tool === "write_file") afterText = typeof input.content === "string" ? input.content : undefined;
  else if (typeof input.find === "string" && typeof input.replace === "string" && beforeText.includes(input.find)) {
    const replacement = input.replace;
    afterText = beforeText.replace(input.find, () => replacement);
  }
  if (afterText === undefined || (!MCP_KEY.test(afterText) && !MCP_KEY.test(beforeText))) return null;

  const after = parseJson(afterText);
  if (after === undefined) {
    const analysis = { installs: [], unreadable: [{ command: `${tool} ${path}`, reason: "it writes an MCP server config Bawabu can't parse" }] };
    return { kind: "mcp", path: full, servers: [], analysis };
  }
  const added = addedServers(parseJson(beforeText), after);
  if (!added.length) return null;
  const analysis: Analysis = { installs: [], unreadable: [] };
  for (const [, def] of added) merge(analysis, analyzeServer(def, ctx));
  return { kind: "mcp", path: full, servers: added.map(([name]) => name), analysis };
}

function needsCheck(p: PackageSpec, install: Install, config: Config, cwd: string, env: Env): boolean {
  if (p.source === "path") return false; // the user's own code on disk
  if (config.allowlist.some((entry) => entry === p.name || (entry.endsWith("/*") && p.name.startsWith(entry.slice(0, -1))))) return false;
  // `npx eslint` runs the project's own copy when it's installed; nothing is fetched.
  if (install.action === "exec" && p.ecosystem === "npm" && p.source === "registry" && !p.version && env.binExists(cwd, p.name.split("/").pop()!)) return false;
  return true;
}

function unreadableMessage(subject: Subject): string {
  const reasons = [...new Set(subject.analysis.unreadable.map((u) => `- ${u.reason}: \`${u.command}\``))];
  const lead =
    subject.kind === "mcp"
      ? `this edit adds an MCP server Bawabu can't check safely${subject.servers.length ? ` (${subject.servers.join(", ")})` : ""}, so it wasn't saved:`
      : "this command runs code Bawabu can't check safely, so it wasn't run:";
  return [
    `⛔ Blocked by Bawabu: ${lead}`,
    ...reasons,
    "Run installs as plain commands (like `npm install <package>`) and edit MCP settings with the file tools, so Bawabu can check them. Otherwise, ask the user.",
  ].join("\n");
}

function noServiceMessage(subject: Subject, installs: Install[]): string {
  const what = installs
    .flatMap((i) => (i.action === "manifest" ? [`the dependencies from \`${i.command}\``] : i.packages.map((p) => `${p.name}${p.version ? `@${p.version}` : ""} (${p.ecosystem})`)))
    .join(", ");
  const lead =
    subject.kind === "mcp"
      ? `the MCP server ${subject.servers.map((s) => `"${s}"`).join(", ")} wasn't added. It would download and run ${what} every time Muse starts`
      : `${what} wasn't installed`;
  return [
    `⛔ Blocked by Bawabu: ${lead}. Bawabu can't check packages yet because no Bawabu service is connected, and it doesn't let unchecked packages through.`,
    `Don't try to ${subject.kind === "mcp" ? "add it" : "install it"} another way. Tell the user; if they trust it, they can allowlist it in .muse/bawabu.json.`,
  ].join("\n");
}

function verdictMessage(subject: Subject, response: CheckResponse): string {
  const icon = (verdict: string) => (verdict === "block" ? "⛔" : "⏸");
  const lines = [
    ...response.results
      .filter((r) => r.verdict !== "allow")
      .flatMap((r) => [
        `${icon(r.verdict)} ${r.name}${r.version || r.requested ? `@${r.version ?? r.requested}` : ""} (${r.ecosystem}): ${r.reason}`,
        ...(r.signals ?? []).map((s) => `   - ${s}`),
        ...(r.suggestion ? [`   Did you mean ${r.suggestion}?`] : []),
      ]),
    ...response.manifests.filter((m) => m.verdict !== "allow").map((m) => `${icon(m.verdict)} the project's ${m.manager} dependencies: ${m.reason}`),
  ];
  const what = subject.kind === "mcp" ? `the MCP server ${subject.servers.map((s) => `"${s}"`).join(", ")} wasn't added` : "this wasn't installed";
  if (response.verdict === "block") {
    return [`⛔ Blocked by Bawabu: ${what}.`, ...lines, `Don't try to ${subject.kind === "mcp" ? "add" : "install"} it another way. Tell the user what Bawabu found.`].join("\n");
  }
  return [`⏸ Bawabu needs the user's OK first: ${what}.`, ...lines, "Ask the user whether to go ahead; if they trust it, they can allowlist it in .muse/bawabu.json."].join("\n");
}

function unsupportedMessage(packages: PackageSpec[]): string {
  return [
    `⛔ Blocked by Bawabu: ${packages.map((p) => `\`${p.raw}\``).join(", ")} ${packages.length > 1 ? "come" : "comes"} from a git repo or URL, which Bawabu can't check yet.`,
    "Install from the registry instead, or ask the user; if they trust it, they can allowlist it in .muse/bawabu.json.",
  ].join("\n");
}

const asString = (v: unknown): string | undefined => (typeof v === "string" && v ? v : undefined);

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

export function nodeEnv(): Env {
  return {
    home: process.env.HOME ?? homedir(),
    readFile: readFileForAnalysis,
    binExists: (cwd, bin) => existsSync(join(cwd, "node_modules", ".bin", bin)),
    post: httpPost,
  };
}

/** Text files only, up to 2 MB; binaries and huge files are treated as "not a script". */
function readFileForAnalysis(path: string): FileRead {
  try {
    const stat = statSync(path);
    if (!stat.isFile()) return { kind: "missing" };
    if (stat.size > 2_000_000) return { kind: "binary" };
    const buffer = readFileSync(path);
    return buffer.includes(0) ? { kind: "binary" } : { kind: "text", content: buffer.toString("utf8") };
  } catch {
    return { kind: "missing" };
  }
}

/** Entry point for `bawabu check`: the hook command Muse runs. */
export async function runCheck(configPath: string): Promise<void> {
  const failClosed = (why: string) => {
    process.stderr.write(`⛔ Blocked by Bawabu: ${why}, so this was blocked to be safe.\n`);
    process.exit(2);
  };
  process.on("uncaughtException", (e) => failClosed(`it hit an internal error (${e.message})`));
  process.on("unhandledRejection", (e) => failClosed(`it hit an internal error (${String(e)})`));
  setTimeout(() => failClosed(`the check took longer than ${CHECK_DEADLINE_SECONDS}s`), CHECK_DEADLINE_SECONDS * 1000).unref();

  const decision = await decide(await readStdin(), () => loadConfig(configPath));
  if (decision.record) appendLog(decision.record);
  if (decision.message) process.stderr.write(decision.message + "\n");
  process.exitCode = decision.exitCode;
}

async function readStdin(): Promise<string> {
  if (process.stdin.isTTY) return "";
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(chunk as Buffer);
  return Buffer.concat(chunks).toString("utf8");
}

function appendLog(record: Record<string, unknown>): void {
  try {
    const dir = join(process.env.HOME ?? homedir(), ".local", "state", "bawabu");
    mkdirSync(dir, { recursive: true });
    appendFileSync(join(dir, "checks.jsonl"), JSON.stringify({ at: new Date().toISOString(), ...record }) + "\n");
  } catch {
    // Logging must never change the decision.
  }
}
