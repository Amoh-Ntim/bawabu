#!/usr/bin/env node
import { nodeEnv, runCheck } from "./check.js";
import { CONFIG_RELATIVE_PATH, VERSION } from "./constants.js";
import { init } from "./init.js";
import { analyze } from "./parse.js";

const USAGE = `bawabu ${VERSION}: a gatekeeper between AI coding agents and the packages they install.

Usage:
  bawabu init [dir] [--force]     Install the Muse Code hook and config in a project (default: this folder)
  bawabu check --config <path>    Run by the hook: reads Muse's hook input on stdin
  bawabu explain "<command>"      Show which installs Bawabu sees in a shell command
`;

const [cmd, ...args] = process.argv.slice(2);
const flagValue = (name: string) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};

switch (cmd) {
  case "check":
    await runCheck(flagValue("--config") ?? CONFIG_RELATIVE_PATH);
    break;
  case "init":
    try {
      if (!init(args.find((a) => !a.startsWith("-")) ?? ".", args.includes("--force"))) process.exitCode = 1;
    } catch (e) {
      console.error(`✖ ${(e as Error).message}`);
      process.exitCode = 1;
    }
    break;
  case "explain":
    console.log(JSON.stringify(analyze(args.join(" "), { cwd: process.cwd(), ...nodeEnv() }), null, 2));
    break;
  case "--version":
  case "-v":
    console.log(VERSION);
    break;
  default:
    process.stdout.write(USAGE);
    if (cmd && cmd !== "--help" && cmd !== "-h") process.exitCode = 1;
}
