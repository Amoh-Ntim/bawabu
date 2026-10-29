/**
 * Works out what a shell command would install, following it into the scripts it runs:
 * `bash setup.sh`, `./setup.sh`, `source x.sh`, heredocs fed to a shell, and package.json
 * scripts (`npm run x`, `yarn x`, ...). Deliberately conservative: anything that runs code we
 * can't see (a script piped into a shell, a missing script file, a package name in a variable)
 * is reported in `unreadable` with a reason, so the hook can block it instead of guessing.
 */

import { isAbsolute, join, resolve } from "node:path";
import { detect, type Install } from "./managers.js";
import { lex, type Command } from "./shell.js";

export type { Install, PackageSpec } from "./managers.js";

export interface Unreadable {
  command: string;
  reason: string;
}

export interface Analysis {
  installs: Install[];
  unreadable: Unreadable[];
}

export type FileRead = { kind: "missing" } | { kind: "binary" } | { kind: "text"; content: string };

export interface Context {
  cwd: string;
  home: string;
  readFile: (path: string) => FileRead;
}

export const REASONS = {
  parse: "the command couldn't be parsed",
  dynamicName: "a package name comes from a variable or another command",
  xargs: "package names come from another command's output (xargs)",
  pipedShell: "it pipes a script into a shell, so Bawabu can't see what runs",
  missingScript: "it runs a script file that doesn't exist yet or can't be read",
  nested: "scripts call each other too deeply to follow",
  mcpShellEdit: "it edits an MCP server config from the shell instead of the file tools",
} as const;

const MANAGER_WORD = /(^|[^\w-])(npm|npx|pnpm|pnpx|yarn|bun|bunx|pip\d?(\.\d+)?|pipx|uv|uvx)([^\w-]|$)/;
const MAX_DEPTH = 6;
/** Lifecycle scripts the project's own package.json runs on a whole-project install. */
const LIFECYCLE = ["preinstall", "install", "postinstall", "prepublish", "preprepare", "prepare", "postprepare"];
const JS_MANAGERS = new Set(["npm", "pnpm", "yarn", "bun"]);
/** Programs under these run as installed tools, not project scripts. */
const SYSTEM_DIRS = /^\/(usr|bin|sbin|opt|System|Library|nix)\//;

export function analyze(command: string, ctx: Context, depth = 0): Analysis {
  const result: Analysis = { installs: [], unreadable: [] };
  if (depth > MAX_DEPTH) {
    result.unreadable.push({ command: brief(command), reason: REASONS.nested });
    return result;
  }
  const lexed = lex(command);
  if (!lexed) {
    if (MANAGER_WORD.test(command)) result.unreadable.push({ command: brief(command), reason: REASONS.parse });
    return result;
  }
  for (const sub of lexed.substitutions) merge(result, analyze(sub, ctx, depth + 1));
  let cwd = ctx.cwd;
  for (const cmd of lexed.commands) cwd = analyzeCommand(cmd, { ...ctx, cwd }, depth, result) ?? cwd;
  return result;
}

export function merge(into: Analysis, from: Analysis): void {
  into.installs.push(...from.installs);
  into.unreadable.push(...from.unreadable);
}

export function resolvePath(ctx: Pick<Context, "cwd" | "home">, path: string): string {
  const expanded = path === "~" ? ctx.home : path.replace(/^~(?=\/)/, ctx.home).replace(/^\$\{?HOME\}?(?=\/|$)/, ctx.home);
  return isAbsolute(expanded) ? resolve(expanded) : resolve(ctx.cwd, expanded);
}

/** Muse's settings, Claude Code's user config, and project .mcp.json files all hold MCP servers. */
export const isMcpConfig = (path: string) => /(^|\/)(\.mcp\.json|\.claude\.json)$|\/muse\/settings\.json$/.test(path);

const brief = (command: string) => {
  const line = command.trim().split("\n")[0];
  return line.length > 160 ? `${line.slice(0, 157)}...` : line;
};
const basename = (path: string) => path.slice(path.lastIndexOf("/") + 1);

/** Returns the new working directory when the command is `cd`. */
function analyzeCommand(cmd: Command, ctx: Context, depth: number, result: Analysis): string | undefined {
  const shown = brief(cmd.words.join(" "));
  const words = stripPrefixes(cmd.words);
  if (cmd.writes.some((w) => isMcpConfig(resolvePath(ctx, w))) || editsMcpConfig(words, ctx)) {
    result.unreadable.push({ command: shown, reason: REASONS.mcpShellEdit });
  }
  if (!words.length) return undefined;
  const prog = basename(words[0]);
  const args = words.slice(1);

  if (prog === "cd" || prog === "pushd") return resolvePath(ctx, args.find((a) => !a.startsWith("-")) ?? "~");
  if (SHELLS.has(prog)) analyzeShell(cmd, args, ctx, depth, result, shown);
  else if (prog === "source" || prog === ".") {
    if (args[0]) analyzeScript(args[0], ctx, depth, result, shown, false);
  } else if (prog === "eval") merge(result, analyze(args.join(" "), ctx, depth + 1));
  else if (prog === "xargs" || prog === "parallel") {
    if (MANAGER_WORD.test(shown)) result.unreadable.push({ command: shown, reason: REASONS.xargs });
  } else {
    const found = detect(prog, args, brief(words.join(" ")));
    if (found?.kind === "install") {
      result.installs.push(found.install);
      if (found.install.action === "manifest" && JS_MANAGERS.has(found.install.manager)) runScripts(ctx.cwd, LIFECYCLE, ctx, depth, result);
    } else if (found?.kind === "unreadable") result.unreadable.push({ command: shown, reason: REASONS.dynamicName });
    else if (found?.kind === "scripts") runScripts(found.dir ? resolvePath(ctx, found.dir) : ctx.cwd, found.names, ctx, depth, result);
    else if (words[0].includes("/")) analyzeScript(words[0], ctx, depth, result, shown, true);
  }
  return undefined;
}

// ---------------------------------------------------------------------------
// Prefixes: sudo, env, VAR=value, if/then/do, ...

const SHELL_KEYWORDS = new Set(["if", "then", "else", "elif", "do", "while", "until", "!", "{", "}"]);
const ASSIGNMENT = /^[A-Za-z_][A-Za-z0-9_]*=/;
const WRAPPERS: Record<string, { valueFlags?: string[]; positional?: number }> = {
  sudo: { valueFlags: ["-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U"] },
  doas: { valueFlags: ["-u", "-C"] },
  env: { valueFlags: ["-u", "-C", "--unset", "--chdir"] },
  nice: { valueFlags: ["-n"] },
  timeout: { valueFlags: ["-s", "-k", "--signal", "--kill-after"], positional: 1 },
  time: {},
  nohup: {},
  command: {},
  exec: {},
  caffeinate: {},
  stdbuf: {},
  corepack: {},
};

function stripPrefixes(words: string[]): string[] {
  let i = 0;
  while (i < words.length) {
    if (SHELL_KEYWORDS.has(words[i]) || ASSIGNMENT.test(words[i])) {
      i++;
      continue;
    }
    const wrapper = Object.hasOwn(WRAPPERS, basename(words[i])) ? WRAPPERS[basename(words[i])] : undefined;
    if (!wrapper) break;
    i++;
    let positional = wrapper.positional ?? 0;
    while (i < words.length) {
      const a = words[i];
      if (a.startsWith("-")) i += wrapper.valueFlags?.includes(a) ? 2 : 1;
      else if (ASSIGNMENT.test(a)) i++;
      else if (positional-- > 0) i++;
      else break;
    }
  }
  return words.slice(i);
}

// ---------------------------------------------------------------------------
// Scripts

const SHELLS = new Set(["sh", "bash", "zsh", "dash", "ksh"]);

/** `bash -c "..."`, `bash script.sh`, or a shell reading commands from stdin. */
function analyzeShell(cmd: Command, args: string[], ctx: Context, depth: number, result: Analysis, shown: string): void {
  let i = 0;
  let fromStdin = false;
  for (; i < args.length; i++) {
    const a = args[i];
    if (/^-[a-zA-Z]*c[a-zA-Z]*$/.test(a)) {
      if (args[i + 1] !== undefined) merge(result, analyze(args[i + 1], ctx, depth + 1));
      return;
    }
    if (a === "-o" || a === "+o") i++;
    else if (/^[-+][a-zA-Z]*s[a-zA-Z]*$/.test(a)) fromStdin = true;
    else if (a === "--") {
      i++;
      break;
    } else if (!a.startsWith("-") && !a.startsWith("+")) break;
  }
  if (!fromStdin && i < args.length) return analyzeScript(args[i], ctx, depth, result, shown, false);

  // Commands come from stdin: a heredoc or file we can read, or a pipe we can't (curl ... | sh).
  if (!cmd.stdin.length && !cmd.inputs.length) {
    result.unreadable.push({ command: shown, reason: REASONS.pipedShell });
    return;
  }
  for (const body of cmd.stdin) merge(result, analyze(body, ctx, depth + 1));
  for (const file of cmd.inputs) analyzeScript(file, ctx, depth, result, shown, false);
}

/** `direct` means the file is executed by path (./setup.sh), so its shebang decides the interpreter. */
function analyzeScript(path: string, ctx: Context, depth: number, result: Analysis, shown: string, direct: boolean): void {
  const full = resolvePath(ctx, path);
  if (direct && SYSTEM_DIRS.test(full)) return;
  const file = ctx.readFile(full);
  if (file.kind === "binary") return;
  if (file.kind === "missing") {
    result.unreadable.push({ command: shown, reason: REASONS.missingScript });
    return;
  }
  const firstLine = file.content.split("\n", 1)[0];
  if (direct && firstLine.startsWith("#!") && !/\b(sh|bash|zsh|dash|ksh)\b/.test(firstLine)) return; // node/python scripts aren't shell
  merge(result, analyze(file.content, ctx, depth + 1));
}

/** Runs package.json scripts by name, in the package's own directory. */
function runScripts(dir: string, names: string[], ctx: Context, depth: number, result: Analysis): void {
  const file = ctx.readFile(join(dir, "package.json"));
  if (file.kind !== "text") return;
  let scripts: unknown;
  try {
    scripts = JSON.parse(file.content)?.scripts;
  } catch {
    return; // npm would fail on it too
  }
  if (typeof scripts !== "object" || scripts === null) return;
  for (const name of names) {
    const script = (scripts as Record<string, unknown>)[name];
    if (typeof script === "string") merge(result, analyze(script, { ...ctx, cwd: dir }, depth + 1));
  }
}

// ---------------------------------------------------------------------------
// MCP configs edited from the shell (the agent should use edit_file, which the hook can inspect)

function editsMcpConfig(words: string[], ctx: Context): boolean {
  if (!words.length) return false;
  const prog = basename(words[0]);
  const args = words.slice(1);
  const isTarget = (w: string) => w.endsWith(".json") && isMcpConfig(resolvePath(ctx, w));
  if (prog === "tee" || prog === "truncate") return args.some(isTarget);
  if (prog === "dd") return args.some((a) => a.startsWith("of=") && isTarget(a.slice(3)));
  if (["cp", "mv", "install", "ln", "rsync"].includes(prog)) return isTarget(args.at(-1) ?? "");
  if (prog === "sed" || prog === "gsed" || prog === "perl") return args.some((a) => /^-\w*i|^--in-place/.test(a)) && args.some(isTarget);
  if (/^(python\d?(\.\d+)?|node|ruby|php|deno|bun|osascript)$/.test(prog)) {
    return args.some(isTarget) || args.some((a) => /mcp(Servers|_servers)|muse\/settings\.json|\.mcp\.json|\.claude\.json/.test(a));
  }
  return false;
}
