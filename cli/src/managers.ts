/** Package-manager command lines: which packages one would fetch, or which package.json scripts it would run. */

export type Ecosystem = "npm" | "pypi";
export type Source = "registry" | "git" | "url" | "path";

export interface PackageSpec {
  ecosystem: Ecosystem;
  /** Registry name, or the raw spec for git/url/path sources. */
  name: string;
  /** Requested version, range or tag; "" means whatever is latest. */
  version: string;
  source: Source;
  raw: string;
}

export interface Install {
  manager: string;
  /** add: named packages. manifest: from package.json/lockfile/requirements. exec: fetch and run (npx-style). */
  action: "add" | "manifest" | "exec";
  packages: PackageSpec[];
  command: string;
}

export type Detected =
  | { kind: "install"; install: Install }
  /** A package name we can't read, such as $PKG. */
  | { kind: "unreadable" }
  /** package.json scripts to run, in `dir` (default: the current directory). */
  | { kind: "scripts"; dir: string | undefined; names: string[] }
  | null;

export function detect(prog: string, args: string[], command: string): Detected {
  switch (prog) {
    case "npm":
      return detectNpm(args, command);
    case "npx":
    case "pnpx":
    case "bunx": {
      const { positional, values } = parseArgs(args, NPM_VALUE_FLAGS);
      return execInstall(prog, values, positional, command);
    }
    case "pnpm":
      return detectPnpm(args, command);
    case "yarn":
      return detectYarn(args, command);
    case "bun":
      return detectBun(args, command);
    case "uv":
      return detectUv(args, command);
    case "uvx":
      return detectUvx("uvx", args, command);
    case "pipx":
      return detectPipx(args, command);
  }
  if (/^pip\d?(\.\d+)?$/.test(prog)) return detectPip("pip", args, command);
  if (/^python\d?(\.\d+)?$/.test(prog) && args[0] === "-m" && /^pip\d?$/.test(args[1] ?? "")) return detectPip("pip", args.slice(2), command);
  return null;
}

interface Args {
  positional: string[];
  values: Map<string, string[]>;
}

function parseArgs(args: string[], valueFlags: ReadonlySet<string>): Args {
  const positional: string[] = [];
  const values = new Map<string, string[]>();
  const add = (flag: string, value: string) => values.set(flag, [...(values.get(flag) ?? []), value]);
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--") {
      positional.push(...args.slice(i + 1));
      break;
    }
    if (a.startsWith("--") && a.includes("=")) add(a.slice(0, a.indexOf("=")), a.slice(a.indexOf("=") + 1));
    else if (a.startsWith("-") && a.length > 1) add(a, valueFlags.has(a) && i + 1 < args.length ? args[++i] : "");
    else positional.push(a);
  }
  return { positional, values };
}

/** The first positional argument and the raw arguments after it (flags kept, for nested CLIs like `uv pip`). */
function subcommand(args: string[], valueFlags: ReadonlySet<string>): [string | undefined, string[]] {
  for (let i = 0; i < args.length; i++) {
    if (!args[i].startsWith("-")) return [args[i], args.slice(i + 1)];
    if (valueFlags.has(args[i])) i++;
  }
  return [undefined, []];
}

function makeInstall(manager: string, action: Install["action"], specs: string[], ecosystem: Ecosystem, command: string): Detected {
  const packages: PackageSpec[] = [];
  for (const raw of specs) {
    const spec = ecosystem === "npm" ? parseNpmSpec(raw) : parsePipSpec(raw);
    if (!spec) return { kind: "unreadable" };
    packages.push(spec);
  }
  return { kind: "install", install: { manager, action, packages, command } };
}

/** npm, yarn and bun also run pre<name> and post<name>; listing them for pnpm too errs on the safe side. */
const runScripts = (dir: string | undefined, ...names: string[]): Detected => ({
  kind: "scripts",
  dir,
  names: names.flatMap((n) => [`pre${n}`, n, `post${n}`]),
});

// ---------------------------------------------------------------------------
// npm family

const NPM_VALUE_FLAGS = new Set([
  "--registry", "--prefix", "-C", "--workspace", "-w", "--tag", "--cache", "--userconfig", "--globalconfig",
  "--omit", "--include", "--install-strategy", "--loglevel", "--before", "--package", "-p", "--call", "-c",
  "--otp", "--location", "-L", "--scope",
]);
const NPM_INSTALL = new Set(["install", "i", "in", "ins", "inst", "insta", "instal", "isnt", "isnta", "isntal", "isntall", "add"]);
const NPM_UPDATE = new Set(["update", "up", "upgrade", "udpate"]);
const NPM_CI = new Set(["ci", "clean-install", "ic", "install-clean", "isntall-clean", "install-test", "it", "install-ci-test", "cit"]);
const NPM_EXEC = new Set(["exec", "x"]);
const NPM_CREATE = new Set(["init", "create", "innit"]);
const NPM_RUN = new Set(["run", "run-script", "rum", "urn"]);
const NPM_LIFECYCLE = new Map([["start", "start"], ["stop", "stop"], ["restart", "restart"], ["test", "test"], ["t", "test"], ["tst", "test"]]);

function detectNpm(args: string[], command: string): Detected {
  const { positional, values } = parseArgs(args, NPM_VALUE_FLAGS);
  const [sub, ...rest] = positional;
  const dir = values.get("--prefix")?.[0];
  if (sub === undefined) return null;
  if (NPM_INSTALL.has(sub) || NPM_UPDATE.has(sub)) return makeInstall("npm", rest.length ? "add" : "manifest", rest, "npm", command);
  if (NPM_CI.has(sub)) return makeInstall("npm", "manifest", [], "npm", command);
  if (NPM_EXEC.has(sub)) return execInstall("npm", values, rest, command);
  if (NPM_CREATE.has(sub)) return createInstall("npm", rest, command);
  if (NPM_RUN.has(sub)) return rest[0] ? runScripts(dir, rest[0]) : null;
  const lifecycle = NPM_LIFECYCLE.get(sub);
  if (lifecycle === "restart") return runScripts(dir, "restart", "stop", "start");
  return lifecycle ? runScripts(dir, lifecycle) : null;
}

/** npx / npm exec / pnpm dlx / bunx: --package values if given, otherwise the command name is the package. */
function execInstall(manager: string, values: Map<string, string[]>, rest: string[], command: string): Detected {
  const named = [...(values.get("--package") ?? []), ...(values.get("-p") ?? [])];
  const specs = named.length ? named : rest.slice(0, 1);
  return specs.length ? makeInstall(manager, "exec", specs, "npm", command) : null;
}

/** `npm create vite` runs the package create-vite (and `@scope/foo` runs `@scope/create-foo`). */
function createInstall(manager: string, rest: string[], command: string): Detected {
  const initializer = rest[0];
  if (!initializer) return null;
  const at = initializer.indexOf("@", 1);
  const name = at > 0 ? initializer.slice(0, at) : initializer;
  const version = at > 0 ? initializer.slice(at) : "";
  const [scope, pkg] = name.split("/");
  const spec = name.startsWith("@") ? `${scope}/create${pkg ? `-${pkg}` : ""}${version}` : `create-${name}${version}`;
  return makeInstall(manager, "exec", [spec], "npm", command);
}

const PNPM_VALUE_FLAGS = new Set(["--filter", "-F", "--dir", "-C", "--workspace-dir", "--reporter", "--registry", "--store-dir", "--package", "--loglevel"]);
const PNPM_BUILTINS = new Set([
  "add", "install", "i", "update", "up", "upgrade", "remove", "rm", "uninstall", "un", "link", "ln", "unlink", "import",
  "rebuild", "rb", "prune", "fetch", "install-test", "it", "patch", "patch-commit", "audit", "list", "ls", "outdated",
  "why", "licenses", "exec", "run", "run-script", "test", "t", "start", "dlx", "create", "init", "publish", "pack", "store",
  "root", "bin", "setup", "server", "config", "c", "env", "deploy", "doctor", "help", "self-update", "recursive", "m",
  "multi", "approve-builds", "ignored-builds", "cat-file", "cat-index", "find-hash",
]);

function detectPnpm(args: string[], command: string): Detected {
  const { positional, values } = parseArgs(args, PNPM_VALUE_FLAGS);
  const [sub, ...rest] = positional;
  const dir = (values.get("--dir") ?? values.get("-C"))?.[0];
  if (sub === undefined) return null;
  if (["add", "install", "i", "update", "up", "upgrade"].includes(sub)) return makeInstall("pnpm", rest.length ? "add" : "manifest", rest, "npm", command);
  if (sub === "dlx") return execInstall("pnpm", values, rest, command);
  if (sub === "create") return createInstall("pnpm", rest, command);
  if (sub === "run" || sub === "run-script") return rest[0] ? runScripts(dir, rest[0]) : null;
  if (sub === "test" || sub === "t" || sub === "start") return runScripts(dir, sub === "t" ? "test" : sub);
  return PNPM_BUILTINS.has(sub) ? null : runScripts(dir, sub); // `pnpm build` runs the build script
}

const YARN_VALUE_FLAGS = new Set(["--cwd", "--registry", "--modules-folder", "--cache-folder", "--network-timeout", "--package", "-p"]);
const YARN_BUILTINS = new Set([
  "add", "install", "remove", "upgrade", "up", "upgrade-interactive", "dlx", "create", "global", "info", "init", "run",
  "why", "list", "cache", "config", "link", "unlink", "pack", "publish", "login", "logout", "outdated", "version",
  "versions", "workspaces", "workspace", "audit", "autoclean", "bin", "check", "help", "import", "licenses", "owner",
  "policies", "tag", "team", "node", "plugin", "set", "exec", "explain", "constraints", "dedupe", "npm", "patch",
  "patch-commit", "rebuild", "search", "stage", "unplug", "generate-lock-entry",
]);

function detectYarn(args: string[], command: string): Detected {
  const { positional, values } = parseArgs(args, YARN_VALUE_FLAGS);
  let [sub, ...rest] = positional;
  const dir = values.get("--cwd")?.[0];
  if (sub === "global") [sub, ...rest] = rest;
  if (sub === undefined) {
    // Bare `yarn` installs the project's dependencies; `yarn --version` doesn't.
    return args.some((a) => ["--version", "-v", "--help", "-h"].includes(a)) ? null : makeInstall("yarn", "manifest", [], "npm", command);
  }
  if (sub === "install") return makeInstall("yarn", "manifest", [], "npm", command);
  if (sub === "add" || sub === "up" || sub === "upgrade" || sub === "upgrade-interactive") {
    return makeInstall("yarn", rest.length ? "add" : "manifest", rest, "npm", command);
  }
  if (sub === "dlx") return execInstall("yarn", values, rest, command);
  if (sub === "create") return createInstall("yarn", rest, command);
  if (sub === "run") return rest[0] ? runScripts(dir, rest[0]) : null;
  return YARN_BUILTINS.has(sub) ? null : runScripts(dir, sub); // `yarn build` runs the build script
}

const BUN_VALUE_FLAGS = new Set(["--cwd", "--registry", "--cache-dir", "--backend", "--filter", "-F", "--config", "-c", "--cpu", "--os", "--package", "-p"]);
const BUN_BUILTINS = new Set([
  "run", "test", "x", "repl", "exec", "install", "i", "add", "a", "remove", "rm", "update", "outdated", "link", "unlink",
  "publish", "patch", "patch-commit", "pm", "build", "init", "create", "c", "upgrade", "completions", "discord", "help",
  "audit", "info", "why",
]);

function detectBun(args: string[], command: string): Detected {
  const { positional, values } = parseArgs(args, BUN_VALUE_FLAGS);
  const [sub, ...rest] = positional;
  const dir = values.get("--cwd")?.[0];
  if (sub === undefined) return null;
  if (sub === "add" || sub === "a") return rest.length ? makeInstall("bun", "add", rest, "npm", command) : null;
  if (sub === "install" || sub === "i" || sub === "update") return makeInstall("bun", rest.length ? "add" : "manifest", rest, "npm", command);
  if (sub === "x") return execInstall("bun", values, rest, command);
  if (sub === "create" || sub === "c") {
    // `bun create user/repo` clones a GitHub template; `bun create vite` runs create-vite.
    return rest[0] && /^[\w.-]+\/[\w.-]+$/.test(rest[0]) ? makeInstall("bun", "exec", [rest[0]], "npm", command) : createInstall("bun", rest, command);
  }
  if (sub === "run") return rest[0] ? runScripts(dir, rest[0]) : null;
  return BUN_BUILTINS.has(sub) ? null : runScripts(dir, sub); // `bun dev` runs the dev script
}

// ---------------------------------------------------------------------------
// Python

const PIP_VALUE_FLAGS = new Set([
  "-r", "--requirement", "-c", "--constraint", "-e", "--editable", "-i", "--index-url", "--extra-index-url",
  "-t", "--target", "--prefix", "--root", "-f", "--find-links", "--src", "--upgrade-strategy", "--python-version",
  "--platform", "--implementation", "--abi", "--only-binary", "--no-binary", "--progress-bar", "--log",
  "--cache-dir", "--trusted-host", "--proxy", "--retries", "--timeout", "--exists-action", "--report",
  "-p", "--python", "--group",
]);

function detectPip(manager: string, args: string[], command: string): Detected {
  const { positional, values } = parseArgs(args, PIP_VALUE_FLAGS);
  const [sub, ...rest] = positional;
  if (sub !== "install") return null;
  const editable = [...(values.get("-e") ?? []), ...(values.get("--editable") ?? [])];
  const fromFile = [...values.keys()].some((k) => /^(-r|-c|--requirement|--constraint)/.test(k));
  const specs = [...rest, ...editable];
  if (!specs.length) return fromFile ? makeInstall(manager, "manifest", [], "pypi", command) : null;
  return makeInstall(manager, fromFile ? "manifest" : "add", specs, "pypi", command);
}

const UV_VALUE_FLAGS = new Set([
  ...PIP_VALUE_FLAGS, "--with", "--from", "--directory", "--project", "--index", "--default-index",
  "--optional", "--extra", "--package", "--script", "--tag", "--branch", "--rev",
]);

function detectUv(args: string[], command: string): Detected {
  const [sub, rest] = subcommand(args, UV_VALUE_FLAGS);
  if (sub === "pip") return detectPip("uv", rest, command);
  const { positional, values } = parseArgs(rest, UV_VALUE_FLAGS);
  if (sub === "add") return positional.length ? makeInstall("uv", "add", positional, "pypi", command) : null;
  if (sub === "sync") return makeInstall("uv", "manifest", [], "pypi", command);
  if (sub === "tool" && positional[0] === "install") return positional[1] ? makeInstall("uv", "add", [positional[1]], "pypi", command) : null;
  if (sub === "tool" && positional[0] === "run") return detectUvx("uv", rest.slice(rest.indexOf("run") + 1), command);
  if (sub === "run") {
    const extra = (values.get("--with") ?? []).flatMap((w) => w.split(","));
    return extra.length ? makeInstall("uv", "add", extra, "pypi", command) : null;
  }
  return null;
}

function detectUvx(manager: string, args: string[], command: string): Detected {
  const { positional, values } = parseArgs(args, UV_VALUE_FLAGS);
  const from = values.get("--from") ?? [];
  const specs = from.length ? from : positional.slice(0, 1);
  return specs.length ? makeInstall(manager, "exec", specs, "pypi", command) : null;
}

const PIPX_VALUE_FLAGS = new Set(["--spec", "--python", "--index-url", "-i", "--pip-args", "--suffix"]);

function detectPipx(args: string[], command: string): Detected {
  const [sub, rest] = subcommand(args, PIPX_VALUE_FLAGS);
  if (sub === "runpip") {
    const [venv, pipArgs] = subcommand(rest, PIPX_VALUE_FLAGS);
    return venv ? detectPip("pipx", pipArgs, command) : null;
  }
  const { positional, values } = parseArgs(rest, PIPX_VALUE_FLAGS);
  if (sub === "install" || sub === "upgrade") return positional.length ? makeInstall("pipx", "add", positional, "pypi", command) : null;
  if (sub === "inject") return positional.length > 1 ? makeInstall("pipx", "add", positional.slice(1), "pypi", command) : null;
  if (sub === "run") {
    const spec = values.get("--spec") ?? positional.slice(0, 1);
    return spec.length ? makeInstall("pipx", "exec", spec, "pypi", command) : null;
  }
  if (sub === "install-all" || sub === "reinstall" || sub === "reinstall-all" || sub === "upgrade-all") {
    return makeInstall("pipx", "manifest", [], "pypi", command);
  }
  return null;
}

// ---------------------------------------------------------------------------
// Package specs

const NPM_NAME = /^(?:@[a-z0-9~][\w.~-]*\/)?[a-z0-9~][\w.~-]*$/i;
const PATH_LIKE = /^(\.{0,2}\/|~\/|file:)|^\.{1,2}$/;

/** Returns null when the spec isn't a readable package (e.g. a $VARIABLE), so the caller can block. */
export function parseNpmSpec(raw: string): PackageSpec | null {
  const pkg = (name: string, version: string, source: Source): PackageSpec => ({ ecosystem: "npm", name, version, source, raw });
  if (/^https?:\/\//.test(raw)) return pkg(raw, "", "url");
  if (PATH_LIKE.test(raw) || /\.(tgz|tar\.gz|tar)$/.test(raw)) return pkg(raw, "", "path");
  if (/^(git\+|git:\/\/|github:|gitlab:|bitbucket:|gist:)/.test(raw) || /^[\w.-]+\/[\w.-]+(#.*)?$/.test(raw)) return pkg(raw, "", "git");
  const alias = raw.match(/^(?:@[^@/]+\/)?[^@/]+@npm:(.+)$/);
  if (alias) {
    const real = parseNpmSpec(alias[1]);
    return real && { ...real, raw };
  }
  const at = raw.indexOf("@", 1);
  const name = at > 0 ? raw.slice(0, at) : raw;
  const version = at > 0 ? raw.slice(at + 1) : "";
  if (!NPM_NAME.test(name) || /[\s$`]/.test(version)) return null;
  return pkg(name, version, "registry");
}

const PEP508 = /^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?:\[[^\]]*\])?\s*(.*)$/;

export function parsePipSpec(raw: string): PackageSpec | null {
  const pkg = (name: string, version: string, source: Source): PackageSpec => ({ ecosystem: "pypi", name, version, source, raw });
  if (/^(git|hg|svn|bzr)\+/.test(raw)) return pkg(raw, "", "git");
  if (/^https?:\/\//.test(raw)) return pkg(raw, "", "url");
  if (PATH_LIKE.test(raw) || (/\.(whl|tar\.gz|zip)$/.test(raw) && !raw.includes("://"))) return pkg(raw, "", "path");
  const m = raw.match(PEP508);
  if (!m || /[$`]/.test(raw)) return null;
  const name = m[1].toLowerCase().replace(/[-_.]+/g, "-");
  const rest = m[2].trim();
  if (rest.startsWith("@") && !rest.includes("://")) return pkg(name, rest.slice(1).trim(), "registry"); // uv-style name@version
  if (rest.includes("@")) return pkg(raw, "", "url"); // PEP 508 direct reference: name @ https://...
  return pkg(name, rest, "registry");
}
