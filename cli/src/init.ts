import { spawnSync } from "node:child_process";
import { accessSync, constants, existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { delimiter, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { DEFAULT_CONFIG, isValidServiceUrl, loadConfig, type Config } from "./config.js";
import { CONFIG_RELATIVE_PATH, HOOK_TIMEOUT_SECONDS } from "./constants.js";
import { serviceHealth } from "./service.js";
import { shellQuote } from "./shell.js";

interface HookEntry {
  type?: string;
  command?: string;
  timeout?: number;
}
interface MatcherGroup {
  matcher?: string;
  hooks?: HookEntry[];
}
interface HooksFile {
  hooks?: Record<string, MatcherGroup[]>;
}

/** Installs the Muse Code hook and config in a project. Returns false if the self-test fails. */
export async function init(dir: string, options: { force: boolean; serviceUrl?: string; openWeights?: boolean }): Promise<boolean> {
  const projectDir = resolve(dir);
  const hooksPath = join(projectDir, ".muse", "hooks.json");
  const configPath = join(projectDir, CONFIG_RELATIVE_PATH);

  if (options.serviceUrl && !isValidServiceUrl(options.serviceUrl)) {
    throw new Error(`--service must be an https:// URL (or http://localhost for development), got ${options.serviceUrl}`);
  }
  // An existing config is kept (allowlist and all); --service only changes the service URL.
  const existing = existsSync(configPath) && !options.force ? loadConfig(configPath) : null;
  const config: Config = {
    ...(existing ?? DEFAULT_CONFIG),
    ...(options.serviceUrl ? { serviceUrl: options.serviceUrl } : {}),
    ...(options.openWeights ? { openWeights: true } : {}),
  };

  if (!findExecutable("muse") && !existsSync(join(homedir(), ".local", "bin", "muse"))) {
    console.warn("! Muse Code wasn't found. Install it from https://dev.meta.ai, then open this folder in it.");
  }

  // Muse runs hooks with a near-empty PATH, so the hook command uses absolute paths only.
  const node = findExecutable("node") ?? process.execPath;
  const cli = realpathSync(fileURLToPath(new URL("./cli.js", import.meta.url)));
  const command = [node, cli, "check", "--config", configPath].map(shellQuote).join(" ");

  const hooks = withBawabuHook(readHooks(hooksPath), command);
  mkdirSync(join(projectDir, ".muse"), { recursive: true });
  writeFileSync(hooksPath, JSON.stringify(hooks, null, 2) + "\n");
  console.log(`✔ Hook installed: ${hooksPath} (PreToolUse, timeout ${HOOK_TIMEOUT_SECONDS}s)`);

  if (existing && !options.serviceUrl && !options.openWeights) {
    console.log(`✔ Config kept: ${configPath}`);
  } else {
    writeFileSync(configPath, JSON.stringify(config, null, 2) + "\n");
    console.log(`✔ Config ${existing ? "updated" : "written"}: ${configPath} (mode: ${config.mode}, service: ${config.serviceUrl ?? "none"}` +
      `${config.openWeights ? ", investigator: Muse Spark Open (open weights)" : ""})`);
  }

  const failure = selfTest(command, projectDir);
  if (failure) {
    console.error(`✖ Self-test failed: ${failure}`);
    console.error("  The hook is installed but isn't working, and Muse lets commands through when a hook fails. Fix this before relying on Bawabu.");
    return false;
  }
  console.log("✔ Self-test passed: installs are stopped, other commands run.");

  if (!config.serviceUrl) {
    console.log("! No service configured: every install will be blocked until you run `bawabu init --service <url>`.");
  } else {
    try {
      console.log(`✔ Service reachable: ${config.serviceUrl} (${await serviceHealth(config.serviceUrl)})`);
    } catch (e) {
      console.warn(`! Service not reachable at ${config.serviceUrl} (${(e as Error).message}). Installs will be blocked until it is.`);
    }
  }
  console.log("\nNext: open this folder in Muse Code and trust the workspace when asked, so the hook loads.");
  return true;
}

function readHooks(path: string): HooksFile {
  if (!existsSync(path)) return {};
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8"));
    if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) return parsed;
  } catch {
    // Reported below.
  }
  throw new Error(`${path} isn't a valid hooks file. Fix it or move it aside, then run bawabu init again.`);
}

/** Adds our hook, replacing any earlier Bawabu hook so re-running init doesn't stack duplicates. Other hooks are kept. */
function withBawabuHook(file: HooksFile, command: string): HooksFile {
  const isOurs = (group: MatcherGroup) =>
    (group.hooks ?? []).some((h) => typeof h.command === "string" && h.command.includes(" 'check' '--config' ") && h.command.includes("bawabu"));
  const existing = Array.isArray(file.hooks?.PreToolUse) ? file.hooks.PreToolUse : [];
  const ours: MatcherGroup = { hooks: [{ type: "command", command, timeout: HOOK_TIMEOUT_SECONDS }] };
  return { ...file, hooks: { ...file.hooks, PreToolUse: [...existing.filter((g) => !isOurs(g)), ours] } };
}

/** Runs the hook command the way Muse does: through the shell, with a near-empty environment. */
function selfTest(command: string, cwd: string): string | null {
  const cases: Array<{ name: string; payload: object; exit: number; stderr?: string }> = [
    { name: "an install is stopped", payload: { tool_name: "bash", tool_input: { command: "npm install left-pad" }, bawabu_selftest: true }, exit: 2, stderr: "self-test" },
    { name: "a normal command runs", payload: { tool_name: "bash", tool_input: { command: "git status" } }, exit: 0 },
    { name: "Muse's own tools run", payload: { tool_name: "submit_reminder_decision", tool_input: {} }, exit: 0 },
  ];
  for (const c of cases) {
    const run = spawnSync("/bin/sh", ["-c", command], {
      cwd,
      input: JSON.stringify({ hook_event_name: "PreToolUse", cwd, ...c.payload }),
      env: { HOME: homedir(), PATH: "/usr/bin:/bin:/usr/sbin:/sbin" },
      encoding: "utf8",
      timeout: 20_000,
    });
    if (run.status !== c.exit || (c.stderr && !run.stderr.includes(c.stderr))) {
      return `${c.name}: expected exit ${c.exit}, got ${run.status ?? run.signal}. ${run.stderr?.trim() ?? ""}`;
    }
  }
  return null;
}

function findExecutable(name: string): string | null {
  for (const dir of (process.env.PATH ?? "").split(delimiter)) {
    if (!dir) continue;
    try {
      accessSync(join(dir, name), constants.X_OK);
      return join(dir, name);
    } catch {
      // Keep looking.
    }
  }
  return null;
}
