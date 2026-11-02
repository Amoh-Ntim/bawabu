# bawabu

**The gatekeeper between AI coding agents and the packages they install.**

When an AI coding agent ([Muse Code](https://dev.meta.ai/docs/overview)) runs `npm install`, Bawabu stops the install,
checks the package, and lets it in only when it finds no evidence of harm. Most packages are cleared in about a second.
Suspicious ones are run in a locked cloud sandbox baited with fake secrets and investigated by **Muse Spark**, which
reads the code, decodes what's hidden, re-runs the sandbox under the conditions the malware is waiting for, and has to
quote its evidence, which Bawabu checks against what the tools saw.

Full story, results and design: **[github.com/Amoh-Ntim/bawabu](https://github.com/Amoh-Ntim/bawabu#readme)**

## Install

```bash
npm i -g bawabu        # Node.js 20+; no runtime dependencies
```

## Check a package from the terminal

```bash
bawabu scan react-datepickr     # a name an AI made up: blocked, "did you mean react-datepicker?"
bawabu scan left-pad            # an established package: allowed in about a second
```

It prints the verdict, the evidence and a link to the report page. Exit code: `0` allowed, `1` blocked, `2` a human
should decide (or the check failed).

## Protect a Muse Code project

```bash
cd your-project
bawabu init                     # installs the Muse Code hook and .muse/bawabu.json
```

Then open the project in Muse Code and trust the workspace. The installs the agent runs (npm, npx, pnpm, yarn, bun,
pip, uv, pipx, including ones hidden in scripts, whole-project installs with their direct dependencies, and new MCP
servers) are checked first; installs it can't see into are blocked. The agent gets the verdict with the evidence, and
is told not to try another way. It protects a well-meaning agent from bad packages; it isn't a sandbox around a
hostile one (see [Limits](https://github.com/Amoh-Ntim/bawabu#limits)).

## Use your own API key

By default the CLI uses the hosted demo service. To run everything on your own machine with your own Meta Model API key,
including a built-in test lab of harmless practice attacks:

```bash
git clone https://github.com/Amoh-Ntim/bawabu.git && cd bawabu && uv sync
export META_API_KEY=...
uv run service/run_local.py

bawabu scan ci-build-cache-helper --local --lab    # a practice attack: Muse Spark investigates
bawabu demo                                        # a project for Muse Code, wired to your local service
```

See [Try it with your own API key](https://github.com/Amoh-Ntim/bawabu#try-it-with-your-own-api-key).

## Commands

| Command | What it does |
|---|---|
| `bawabu init [dir] [--local \| --service <url>] [--open-weights] [--force]` | Install the hook and settings in a project, test the hook the way Muse runs it, and check the service answers |
| `bawabu scan <pkg>[@version] [--local] [--lab] [--open-weights]` | Check one package and print the verdict and evidence |
| `bawabu demo [dir]` | Create a project for trying Bawabu in Muse Code with the local service |
| `bawabu explain "<command>"` | Show which installs Bawabu sees in a shell command |
| `bawabu check` | Run by the hook (reads Muse's hook input on stdin) |

## Privacy and safety

- Only package names, versions and the registry's address leave your machine: never the command line, your code,
  your files, or credentials from `.npmrc`.
- It fails closed: if the service can't be reached or a check takes too long, the install is blocked, not waved through.
- Its settings live in `.muse/`, which the agent can't change without your approval.

The hosted service is a hackathon deployment: it may be slow, rate-limited or switched off later.

## License

MIT. Built for the Meta Global AI Developer Hackathon (Indie track) by Samuel Amoh Ntim.
