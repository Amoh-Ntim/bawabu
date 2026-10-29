# Bawabu: Results Log

A running record of what we tested, what we found, and how it changes the build. The newest day comes first. Step numbers refer to [plan.md](plan.md).

## Status

| Step 0 item | Status | Notes |
|---|---|---|
| Meta Model API credits | ✅ **$150 received** | Oct 27 |
| Baseten credits | ✅ **Received** | Oct 27 |
| **Baseten open weights (`muse-spark-open-1026`): chat, tool calling, structured output** | ✅ **Proven** | Oct 27. All 4 checks pass, faster than the Meta API. See below |
| Modal credits | 🟡 Approved | Oct 28: approved, credits being processed |
| **Modal sandbox: node runs, network blocked, strace works** | ✅ **Proven** | Oct 28. All 3 checks pass. **Step 0 complete** |
| **Step 1: CLI and hook** (`bawabu init`, `bawabu check`) | ✅ **Done** | Oct 29. A real Muse agent's `npm install left-pad` was blocked, and allowed once allowlisted |
| **Coverage: bun, pipx, script files, package.json scripts, MCP servers** | ✅ **Done** | Oct 29. 39 unit tests pass. Real agents blocked on `./setup.sh`, `bun run setup` and `pipx install`. MCP edits blocked at the hook |
| **Step 2: service skeleton** (`POST /check` on Modal, verdict cache, CLI to service) | ✅ **Done** | Oct 29. A real agent's install went from the hook to the service, got `allow`, and ran. Deployed at `https://amohntim123--bawabu.us-east.modal.run` with the Supabase verdict cache. `bawabu init` uses it by default |
| Muse Code installed and signed in | ✅ Done | v1.4.13, at `~/.local/bin/muse` |
| **Muse Code hook can block and message the agent** | ✅ **Proven** | Oct 27. See below |
| **Muse Spark API: chat, tool calling, structured output** | ✅ **Proven** | Oct 27. All 3 checks pass. See below |
| One Modal sandbox command | ⏳ Waiting | Needs a Modal account and credits |
| Public GitHub repo | ✅ Done | `Amoh-Ntim/bawabu`, created after kickoff |

---

## 2026-10-29 (Thu): Hook timeout and failure test, Step 1 CLI

### Result

- **A hook can take at least 90 s by default.** Muse waits for it, and an exit-2 block still works after the wait.
- **The limit can be set per hook** with `"timeout": <seconds>` in `.muse/hooks.json`. Setting it to 5 got the hook killed after about 5 s.
- ⚠️ **Muse fails open.** If a hook **times out** or **exits with anything other than 2**, the command **runs anyway, and the agent sees no warning.** Only exit code 2 blocks.

### How we tested it

Each run used a probe hook in a throwaway workspace and a real `muse exec` session (approvals and sandbox on, `--trust-workspace`). The agent was asked to run `touch ran-marker.txt && echo done`. If the marker file exists afterwards, the command ran.

| Run | Hook behaviour | Hook config | What happened | Command ran? |
|---|---|---|---|---|
| A | Waits 90 s, then exits 2 | Default (no `timeout`) | Hook survived all 90 s. Agent got `tool blocked by hook: Blocked by Bawabu (timeout probe) after 90s`. Session took 146 s | ❌ No (blocked ✅) |
| B | Waits 20 s, then exits 2 | `"timeout": 5` | Hook killed after about 4–5 s (last heartbeat: second 4). Agent got `done`, exit code 0, "No error message." | ⚠️ **Yes** |
| C | Exits 1 immediately (simulated crash) | `"timeout": 30` | Agent got `done`, exit code 0, "No error message." | ⚠️ **Yes** |

The agent tried the command once in each run and didn't retry.

### What this changes in the build

This is the most important hook finding so far. **Any slow path or bug in `bawabu check` would silently let packages through.** So:

1. **`bawabu init` always writes an explicit `"timeout"`** (for example 180 s). We know the default is longer than 90 s, but not what it is.
2. **`bawabu check` enforces its own deadline, well inside that limit** (for example 150 s). When the deadline is reached without a verdict, it **exits 2** with "Bawabu is still checking `<pkg>`, watch at /r/[id], retry in about a minute." The investigation keeps running in the cloud, and the retry gets the cached verdict. The "retry later" fallback is still needed, now as our own safety deadline, not because Muse's limit is short.
3. **Every error in `bawabu check` ends in exit 2** in `block` mode: the whole check is wrapped in error handling, and a crash or unreachable service means "block, Bawabu couldn't check this". In `warn` mode, letting the command through is intended.
4. **A missing or broken hook command fails open too** (for example if node moves or Bawabu is uninstalled, the shell returns 127, which isn't 2). `bawabu init` should run the hook once to confirm it works. A `bawabu doctor` command could recheck it later.

### Step 1: CLI and hook

**Result:** done. `bawabu init` installs the hook. In a real Muse session, the agent's `npm install left-pad` was **blocked with a Bawabu message, and the agent didn't try another way.** Once the package was allowlisted, the same request installed it.

**What was built** (`cli/`, TypeScript, **no runtime dependencies**; `cli/.npmrc` sets `ignore-scripts=true` for our own dev dependencies):
- **`parse.ts`:** reads a shell command the way a shell would (quotes, `&&`/`;`/`|`, redirections, `$(...)` and backticks, `sudo`/`env`/`VAR=` prefixes, `bash -c "..."`, `if/then`) and lists the installs it would run.
  - Covered: npm (install/i/add/update/ci/exec/create/init), npx, pnpm (add/install/update/dlx/create), pnpx, yarn (bare/install/add/global add/up/dlx/create), pip/pip3/`python -m pip`, uv (pip install/add/sync/tool/run --with), uvx.
  - Package specs: registry name and version, scoped names, `alias@npm:real`, git, URL and local path.
  - **Flags what it can't read safely** (package name in a variable, `$(cat list)`, xargs, heredocs, unbalanced quotes) rather than guessing.
- **`check.ts`:** the hook handler. It ignores Muse's internal tools and only looks at `bash`. Ordinary commands are allowed instantly.
  - **Every failure exits 2:** unreadable input, a broken config, a crash, unreadable installs, and a 150 s deadline.
  - Allowed without checking: allowlisted names and scopes (`@myorg/*`), local path installs, and `npx <bin>` when the project already has that binary.
  - Everything else is blocked, for now, as "no service connected". Step 2 replaces this with the service's verdict.
  - Every decision is logged to `~/.local/state/bawabu/checks.jsonl`.
- **`init.ts`:** writes `.muse/hooks.json` with absolute `node` and CLI paths and `"timeout": 180`. Existing hooks are kept, and re-running replaces our hook instead of duplicating it. It writes `.muse/bawabu.json` (mode, serviceUrl, allowlist) and then **runs the hook three times the way Muse does** (`/bin/sh -c`, `PATH=/usr/bin:/bin…`): an install must exit 2, `git status` must exit 0, and a Muse internal tool must exit 0.
- **`bawabu explain "<command>"`** shows what Bawabu sees in a command, for debugging.

**Change from the plan: the config lives in `.muse/bawabu.json`, not `.bawabu.json`.** The agent can't write to `.muse/` without a human approving each write (Meta's guardrails recipe), so a prompt-injected agent can't turn Bawabu off or allowlist its own malware.

**Tests:** 23 unit tests (`cd cli && npm test`), all passing. They include false positives that must **not** block: `echo "npm install foo"`, `git commit -m 'npm install foo'`, `echo $(npm --version)`. Writing them caught one real bug: `pkg @ https://…/x.whl` was labelled a local path (allowed) instead of a URL (checked). Fixed.

**End-to-end with a real Muse agent** (fresh project, `bawabu init`, then `muse exec --trust-workspace "Add the left-pad npm package to this project."`):

| Run | Config | What the agent did | Bawabu decision | Result |
|---|---|---|---|---|
| 1 | Default (block, no service) | `npm install left-pad --save` → got the Bawabu message → read `.muse/bawabu.json` → told the user how to allowlist it. **Didn't try another install method** | block (no service) | Nothing installed ✅ |
| 2 | `"allowlist": ["left-pad"]` | Same install, retried once with a different npm cache | allow (allowlisted), twice | `left-pad@^1.3.0` installed ✅ |

The agent's other commands in these runs (`ls`, `cat package.json`, `git status`) ran normally.

**Not covered at this point:** bun, pipx, script files, package.json scripts and MCP servers. All of these were added later the same day; see the next section.

### Coverage: bun, pipx, scripts and MCP servers

**Result:** all four are covered. In real Muse sessions, agents were blocked when they ran `./setup.sh` (which runs `npm install left-pad`), `bun run setup` (a package.json script that runs `bun add is-odd`) and `pipx install httpie`. Each time the agent explained the block and **didn't try another way**. Adding an MCP server is blocked at the hook, tested with Muse's real input format against the real settings file.

**What changed in `cli/`:** the parser is now three files.
- **`shell.ts`:** the shell lexer. It now handles **heredocs** (`<<EOF`, `<<-`, `<<'EOF'`, `<<<`) and records what each command reads from stdin and which files it writes.
- **`managers.ts`:** package managers. Added:
  - **bun:** `add`/`a`, `install`/`i`, `update`, `x`, `bunx`, and `create` (both npm initializers and GitHub templates).
  - **pipx:** `install`, `upgrade`, `inject`, `run` (`--spec`), `runpip`, and `install-all`/`reinstall`/`upgrade-all`.
  - **Script detection:** `npm run`/`run-script`/`start`/`test`/`restart`, `pnpm run`/`pnpm <script>`, `yarn run`/`yarn <script>`, `bun run`/`bun <script>`.
- **`parse.ts`:** follows commands into the code they run:
  - **Script files:** `bash x.sh`, `sh -e x.sh`, `./x.sh` (by shebang; node/python scripts are skipped), `source`/`.`, `bash < file`, and heredocs or here-strings fed to a shell. A script file that doesn't exist or can't be read is blocked, which catches `curl -o x.sh … && sh x.sh`.
  - **package.json scripts:** the named script plus its `pre`/`post` scripts, run in the package's own folder (`cd web &&`, `--prefix`, `--cwd`). A whole-project install (`npm install`, `npm ci`, `bun install`, …) also checks the project's own lifecycle scripts (`preinstall`, `postinstall`, `prepare`, …).
  - **`cd` is tracked** across a command chain.
  - **Scripts piped into a shell** (`curl … | sh`, `bash <(curl …)`, `cat <<EOF | sh`) are blocked, because Bawabu can't see what runs.
  - Scripts that call each other in a loop stop at depth 6 and block.
- **`mcp.ts` and `check.ts`:** MCP servers (details below).

**MCP servers: how they're covered.** Muse starts MCP servers itself, not through the agent's shell, so a server like `npx -y some-mcp-server` would download and run a package the hook never sees. Bawabu catches it **when the server is added to a config file**:
- **Where Muse keeps them:** `mcpServers` in `~/.config/muse/settings.json`, according to Muse's built-in `manage-settings` and `migrate` skills. Muse doesn't support MCP servers per project. Changes take effect at the next launch.
- **How the agent adds one:** with its file tools. A probe captured the input the hook receives: `edit_file` sends `{"path", "find", "replace"}` and `write_file` sends `{"path", "content"}`. A shell edit is used only in YOLO mode.
- **What Bawabu does:** for any `write_file`/`edit_file` on a `.json` file mentioning `mcpServers`/`mcp_servers`, it works out the file **as it would be after the edit**, compares the servers before and after, and checks every new server, or any server whose `command`/`args`/`url` changed, the same way as an install.
  - Only changing `env` or `headers`, such as a new token, isn't treated as a new server.
  - Covers Muse's `settings.json`, Claude Code's `~/.claude.json` (including `projects[...]`) and project `.mcp.json` files.
  - A remote URL server is allowed, since nothing is installed locally.
  - `docker`/`podman` servers are blocked, because Bawabu can't check container images.
  - An MCP config Bawabu can't parse is blocked.
- **Shell edits of MCP configs are blocked:** `> settings.json`, `tee`, `sed -i`, `cp`/`mv` onto the file, and `python`/`node` scripts that touch it. The message tells the agent to use the file tools instead, which Bawabu can inspect.

**Hook-level test (MCP):** we sent the installed hook command (`/bin/sh`, cleared environment, as Muse runs it) the exact `edit_file`/`write_file` input Muse produces, targeting the real `~/.config/muse/settings.json`. Results:

| Edit | Hook result |
|---|---|
| `edit_file` adds `github` (`npx -y @modelcontextprotocol/server-github`) to settings.json | ⛔ exit 2: "the MCP server "github" wasn't added. It would download and run @modelcontextprotocol/server-github (npm) every time Muse starts…" |
| `write_file` creates `.mcp.json` with `fetch` (`uvx mcp-server-fetch`) | ⛔ exit 2, names `mcp-server-fetch (pypi)` |
| `edit_file` adds a remote server (`streamable-http`, URL only) | ✅ exit 0 |

The real settings file was unchanged afterwards (checksum compared). We **didn't** run a live agent against the real settings: Claude Code's safety classifier refused a probe that had an agent try to add an MCP server to the user's real Muse settings, even though the probe hook blocked every write. The live-agent MCP test is left for the user to run themselves.

**Tests:** 39 unit tests, all passing. New cases cover bun, pipx, script files (a fake filesystem), heredocs (code fed to a shell versus data written to a file), package.json scripts and lifecycle scripts, the depth limit, `curl | sh`, shell edits of MCP configs, and MCP file edits (added versus changed versus token-only, remote, local, docker, allowlisted, unparseable).

**Still not covered:**
- **Node and Python scripts** that install from inside their code (for example `node setup.js` calling `execSync('npm install …')`). Bawabu only reads shell scripts.
- **Makefiles** (`make setup`).
- **Commands passed as data to other tools**, such as `find -exec`, `watch` and `nodemon --exec`.
- **Remote URL MCP servers** pass, because nothing is installed locally. They aren't vetted beyond that.
- Muse auto-updated from 1.4.13 to 1.4.14 during the day. The hook format still worked, but these tests should be re-run after Muse updates.

### Step 2: service skeleton

**Result:** the hook now asks a cloud service for a verdict. In a real Muse session, the agent's `npm install left-pad --save` went from the hook to the service, got `allow`, and the **install ran** (`left-pad@^1.3.0` in package.json and node_modules). The service is deployed on Modal at **`https://amohntim123--bawabu.us-east.modal.run`**.

**Service** (`service/bawabu_service/`, FastAPI; `service/modal_app.py` deploys it):
- `GET /health` reports the version, engine and cache.
- `POST /check` takes `{client_version, packages: [{ecosystem, name, version}], manifests: [{ecosystem, manager}]}` and returns an overall verdict (`allow`/`block`/`ask`; any block blocks) plus one result per package or manifest, with its reason and whether it was cached.
- **Privacy rule:** the CLI sends only package names and versions, **never the command line**, which can hold tokens and paths. A test checks that `NPM_TOKEN=secret npm install …` sends no `secret`, `NPM_TOKEN` or `install`.
- **The cache stores verdicts per exact version** (`left-pad@1.3.0`). "latest", tags and ranges aren't cached yet; Step 3 resolves them to exact versions.
- **Each verdict records the engine that made it.** A lookup only trusts verdicts from engine ≥ `MIN_ENGINE`. The skeleton is engine 0 (it allows everything); Step 3 raises it to 1, so **none of the skeleton's "allow" verdicts are ever reused.**
- A broken cache never breaks a check; it's treated as a cache miss.
- Two cache backends: in-memory (the current deployment, per container) and **Supabase** through its REST API with the secret key (written and tested against a mock, not yet connected).

**CLI** (`cli/src/service.ts`, `check.ts`, `init.ts`):
- `bawabu check` sends the packages that still need checking to `serviceUrl/check` (140 s timeout, inside the 150 s deadline). Allowlisted and local packages aren't sent.
- `allow` lets the command run. `block` stops it with the service's reason per package. `ask` stops it and tells the agent to ask the user. This also works for MCP servers.
- **Still fail-closed:** an unreachable service, a timeout, a non-200 answer or an unexpected response body all block, with the error in the message.
- Git and URL installs are blocked locally ("can't check yet") without asking the service.
- `bawabu init --service <url>` sets the service URL (keeping an existing allowlist) and checks `/health`. **Only `https://` is accepted** (or `http://localhost` for development), both in `init` and when the config loads.

**Tests:** CLI 49/49 (`cd cli && npm test`), service 10/10 (`uv run pytest`).

**Live measurements:**

| What | Result |
|---|---|
| Deployed `/health`, cold start | 4.7 s |
| Deployed `/health`, warm | 0.9 s |
| Deployed `/check` (left-pad@1.3.0), then repeated | 0.9 s, then `cached: true` |
| Real hook command (Muse input format, cleared env) to the cloud service: `npm install is-odd@3.0.1` | allow, **1.6 s** end to end |
| Real Muse agent, local service | 2 checks, both allow, install ran |

**Open question #11 answered: Muse honours a 180 s hook timeout.** A probe hook that ran for 150 s with `"timeout": 180` survived to the end and blocked, and the command never ran. Bawabu's own 150 s deadline inside the 180 s timeout is therefore safe.

**Not done yet in Step 2:**
- **Permanent cache:** the Supabase **Bawabu** organization and project (`ruwvannqkvunasynlowz`, eu-west-1) exist, and the `verdicts` table has been created through the Supabase MCP:
  - `unique (ecosystem, name, version)` for upserts, `engine` and `updated_at` columns, and check constraints on every field.
  - **RLS is on with no policies**, so the publishable key can't read or write it. Only the service's secret key can.
  - The security advisor shows two expected items: "RLS enabled, no policy" (intended), and a warning about Supabase's own `rls_auto_enable()` event-trigger function being callable. That warning is harmless, because Postgres won't run an event-trigger function called directly.
  - **Tested locally** (the service on this machine, reading `.env`): `/health` reported `cache: supabase`.
    - The first `/check` for `left-pad@1.3.0` and `requests==2.31.0` wrote both verdicts (1.5 s).
    - The second came back `cached` from Supabase (0.2 s).
    - Both rows are in `public.verdicts` (engine 0).
  - **The lock holds:** with the publishable key, reading the table returns `[]`, and writing a forged `allow` verdict is refused (HTTP 401, "new row violates row-level security policy"). Only the service's secret key can write verdicts.
  - Where each key lives: `SUPABASE_SECRET_KEY` in `.env` and the Modal secret `bawabu-supabase`. `META_API_KEY` and `BASETEN_API_KEY` go in their own Modal secrets once the service uses them (Steps 7 and 9). No key is ever stored in the database.
  - **Connected in the cloud (done).** The user created the Modal secret `bawabu-supabase` (type Custom). Claude Code's safety system doesn't allow it to write to secret stores. Results after redeploying:

    | What | Result |
    |---|---|
    | Cloud `/health` | `cache: supabase` (5.1 s cold start) |
    | Cloud `/check` with `is-odd@3.0.1` and `left-pad@1.3.0` | Call 1: is-odd fresh, **left-pad cached** (written by the local test, so verdicts are shared across machines and restarts), 2.5 s. Later calls: both cached, about 3 s |
    | Real hook command (Muse input format, cleared env) to the cloud: `npm install is-even@1.0.0`, twice | allow, **2.19 s** (fresh), then **2.02 s** (cached) |
    | Rows in `public.verdicts` | 4: left-pad, requests, is-odd, is-even (all engine 0) |

    Compared with the in-memory deployment (1.6 s), Supabase adds roughly 0.4–0.6 s per hook call, which includes the Modal (us-east) to Supabase (eu-west-1) round trips. That's acceptable for now.
  - ⚠️ **One outlier: a single `/check` took 76.6 s.** That's almost exactly macOS's 75 s TCP connection timeout plus a normal reply, the same pattern as the user's GitHub push error ("Failed to connect … after 75003 ms"). So it was **this network failing to connect once, not the service**: every other request took 2–3 s. For the demo, record on a stable network (see open question #13).
- ~~**Default service URL**~~ **Done:** `bawabu init` now uses `https://amohntim123--bawabu.us-east.modal.run` by default, so `--service` is only needed to point somewhere else. A fresh `bawabu init` with no flags reported "Service reachable … cache supabase". Unit tests never touch the network: the test config sets the service to `null` unless a test supplies a fake one.
- **No auth or rate limit** on the public endpoint yet. That matters before the endpoint starts spending Spark credits (Step 7).

---

## 2026-10-28 (Wed): Modal sandbox test, Step 0 complete

### Result

**Modal Sandboxes can do everything the plan's sandbox design (section 7.3) needs:** run Node, block the real internet, and trace what package code does with `strace -f`. With this, **all Step 0 proofs are done.**

Ran `uv run sandbox/scripts/smoke_modal.py`: one sandbox (Debian slim with nodejs, strace and curl), created with `block_network=True`.

| Check | Result | Time | Detail |
|---|---|---|---|
| Sandbox created | ✅ | 2.7 s | Image already built (the first run built it) |
| Node runs | ✅ PASS | 3.2 s | `node v18.20.4` |
| Network blocked | ✅ PASS | 1.3 s | `curl: (6) Could not resolve host: registry.npmjs.org`. Even DNS is blocked |
| strace works | ✅ PASS | 4.2 s | A Node script started `/bin/sh` and read a planted `.npmrc` containing a canary token. `strace -f` recorded both the `execve /bin/sh` and the open of `/root/.npmrc` (71 trace lines) |

The test ran twice. The first run happened by accident during an import check, because `modal setup` was already done. Both runs passed, and each cost a fraction of a cent.

**What we learned:**
- **The biggest Step 5 risk is cleared: `strace -f` works inside Modal's gVisor sandbox.** It catches spawned processes and file reads, including in child processes. That's what the evidence report is built on (files read, processes spawned).
- **`block_network=True` blocks DNS as well, not just connections.** For the plan's fake DNS and catch-all HTTP sink, both have to run **inside** the sandbox (for example a local DNS server or `/etc/hosts` pointing every domain at a local HTTP server). Nothing can reach an outside sink.
- **The sandbox is ready in about 4–6 s** (create plus first command). That's small next to Spark's investigation time.
- **Debian's Node is old (v18).** For Step 5, use a current Node image (20 or 22) so packages behave as they do on a developer's machine.

### Other findings today

- **Modal approved.** Credits are being processed. `modal setup` is done (token in `~/.modal.toml`, outside the repo).
- **Python project for the repo:** the root `pyproject.toml` (deps `modal`, `openai`), Python pinned to 3.13 (`.python-version`), `uv sync` created `.venv` and `uv.lock`. This fixed VS Code's "import could not be resolved" warning on `import modal`, which happened because the editor's Python didn't have the libraries installed. The scripts no longer carry their own dependency headers. `.vscode/settings.json` (local only, gitignored) points the editor at `.venv`.
- **Install Modal with `uv`, not `pip`.** Modal's instructions say `pip install modal` and `python3 -m modal setup`, but Homebrew's Python blocks `pip install` (`externally-managed-environment`). Use **`uvx modal setup`** for the login, and `uv run sandbox/scripts/smoke_modal.py`, which installs `modal` from the script header automatically. Modal client version: 1.6.3.
- **PATH fixed:** Homebrew (`/opt/homebrew/bin`) is now on PATH, and `python3`, `node`, `npm` and `uv` resolve normally. Yesterday's workaround of using full paths is no longer needed.

---

## 2026-10-27 (Tue): Muse Code hook proof and Muse Spark API test

### Result

**A Muse Code hook can stop an `npm install` before it runs, and the agent sees our message.** The plan's riskiest assumption holds, so we don't need the fallback of wrapping `npm`/`pip`/`npx`.

### How we tested it

- We made a throwaway folder with a `PreToolUse` hook that logs everything Muse sends it and blocks any `npm install`.
- We ran a real headless session (`muse exec --trust-workspace`) with approvals and the sandbox **on** and asked the agent to run `npm install left-pad`.
- The hook fired before the command ran and exited with code 2. Nothing was installed.
- What the agent received:
  ```
  tool blocked by hook: Blocked by Bawabu (probe): npm install is not allowed in this test workspace.
  ```
  The agent passed that text on to the user word for word.
- Model used: `muse-spark-1.3-contributor`. That run succeeded, so the cheaper contributor tier works on this account.

### How Muse Code hooks work (verified by testing)

Meta's docs list the hook events but not the config format or how blocking works. We worked these out from the strings in the Muse binary and then confirmed them with the live test.

**Config file:** `<project>/.muse/hooks.json`. The layout is the same as Claude Code's, and `matcher` is optional:

```json
{
  "hooks": {
    "PreToolUse": [
      { "hooks": [ { "type": "command", "command": "/absolute/path/to/hook" } ] }
    ]
  }
}
```

**What the hook receives on stdin** for a shell command (IDs and paths shortened):

```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "bash",
  "tool_input": {
    "command": "npm install left-pad",
    "description": "Install left-pad with npm",
    "workdir": "<workspace>"
  },
  "tool_use_id": "call_…",
  "session_id": "…",
  "turn_id": "…",
  "cwd": "<workspace>",
  "transcript_path": null,
  "model": "muse-spark-1.3-contributor",
  "permission_mode": "default",
  "model_provider": "meta"
}
```

**Results:**
- Exit 0 lets the command run.
- Exit 2 blocks it, and whatever the hook wrote to stderr goes to the agent. That's where Bawabu's verdict, reason and safe alternative will go.

**Environment:** the hook runs outside Muse's sandbox with a cleared environment. It gets only these variables: `HOME`, `USER`, `LOGNAME`, `SHELL`, `PATH`, `PWD`, `TMPDIR`, `MUSE_SESSION_ID`, `MUSE_THREAD_ID`, `TRACEPARENT`. Its working directory is the project root.

**Trust:**
- Project hooks load only in a trusted folder (`--trust-workspace`, or a saved decision in `~/.config/muse/trust.json`). The `bawabu` folder is already trusted.
- User hooks in `~/.config/muse/settings.json` run in every project with no trust step.
- Plugin hooks use a different format: `{id, event, command: [argv], timeoutMs}`, with no `matcher`.

### What this changes in the build

1. **Look only at `tool_name: "bash"`.** `PreToolUse` also fires for Muse's internal background helpers (`submit_reminder_decision`). Their notes can quote the user's request, and our quick test blocked two of those calls by mistake. `bawabu check` has to read `tool_input.command` from bash calls only, never search the whole payload for text.
2. **Use absolute paths in the hook command.** `PATH` inside the hook didn't include `/opt/homebrew/bin`, so a plain `node` won't be found. `bawabu init` has to write the full path to node and the script, or we ship a single compiled binary.
3. **Settings come from a file, not environment variables.** The environment is cleared, so `bawabu check` reads `.bawabu.json`. This confirms what the plan expected.
4. **User-level vs project-level install.** A user hook covers every project without a trust prompt, which could make it the better default for `bawabu init`. Not tested yet.

### Muse Spark API test

We ran `uv run --env-file .env service/scripts/smoke_spark.py` on the model `muse-spark-1.3-contributor`, using the OpenAI Python SDK pointed at `https://api.meta.ai/v1`.

| Check | Result | Time | Tokens (in+out) | What Spark returned |
|---|---|---|---|---|
| Chat | ✅ PASS | 4.4 s | 15+316 | `bawabu ok` |
| Tool calling (decode round trip) | ✅ PASS | 7.7 s | 834+436 | Called `decode(format=base64)` on its own, then: "It exfiltrates the `NPM_TOKEN` environment variable to `https://evil-collector.xyz` via a fetch request." |
| Structured output (strict JSON schema) | ✅ PASS | 5.4 s | 31+573 | `{"verdict": "block", "confidence": "high", "reason": "Install-time read of ~/.npmrc … credential exfiltration with no legitimate function for a date-picker."}` |

**What we learned:**
- **The investigator design works with this API.** Spark chooses to call a tool, sends correct arguments, uses the result we return, and can be forced into a strict verdict format. These are the three pieces in plan section 7.5.
- **Spark judges against the task without being told to.** Its reason ("no legitimate function for a date-picker") is the "task-aware judgment" the plan lists as a differentiator.
- **Calls are slow and use a lot of output tokens.** Each call took 4–8 s, and a two-word reply used 316 output tokens, probably hidden reasoning. A 12-step investigation at this speed would take about **1–1.5 minutes**, which is longer than the plan's estimate of 20–60 s. That makes the hook timeout question (#1) more urgent, and it makes it worth testing lower reasoning effort for simple steps (#7).
- The credits easily cover development: the whole test used about 2.2k tokens.
- **Models available on our Meta key** (from `GET /v1/models`, which the script now checks first): `muse-spark-1.3`, `muse-spark-1.3-contributor`, `muse-spark-1.2`, `muse-spark-1.2-contributor`, `muse-spark-1.1`, `muse-wonder-1.0`, `muse-image-1.0`, `muse-voice-transcribe-1.0`. A second run passed all 4 checks.

### Baseten open-weights test (Muse Spark Open)

Ran `uv run --env-file .env service/scripts/smoke_spark.py --provider baseten`. Baseten's hackathon instructions confirmed the base URL `https://inference.baseten.co/v1` and the model ID **`meta-models/muse-spark-open-1026`**. Use that exact ID: the hackathon key only works with it, and Baseten's docs show `meta-models/muse-spark-open`, which is the wrong one for us.

| Check | Baseten (open weights) | Meta API (contributor) |
|---|---|---|
| Model listed | ✅ 3.3 s. Lists `muse-spark-open` and `muse-spark-open-1026` (20 models in total) | ✅ 0.7 s |
| Chat | ✅ **1.5 s** (152+186 tok) | 2.2–4.4 s |
| Tool calling (decode round trip) | ✅ **4.2 s** (1025+708 tok). Called `decode` itself, explained the payload correctly | 7.6–7.7 s |
| Structured output (strict JSON schema) | ✅ 3.8 s (168+841 tok). `block`/`high`, reason: "credential exfiltration - no legitimate use" | 3.8–5.4 s |

**What we learned:**
- **The open-weights model can run the full investigator loop** (tool calls plus a strict verdict format), so the plan's `--open-weights` mode is viable. This supports our entry for the "Best Build on Meta Open Weight Models" prize.
- **It's faster: about 2 times quicker on chat and tool calling.** It generates at about 125–220 tokens/s against Meta's 60–115. That makes it a good fit for the **screener** (funnel layer 2), where speed matters most.
- **It always reasons** (per Baseten), but the reasoning came back separately: `content` held only the answer, and the JSON parsed cleanly. It adds about 140 tokens of overhead to each prompt (152 input tokens against Meta's 15 for the same message).
- **Its reasons were shorter** ("credential exfiltration - no legitimate use"), where Meta's named the date-picker mismatch. This is a single sample. Compare quality on the test lab before deciding which model gives the final verdict.

### Why Spark is slow: reasoning effort test

Same prompt ("date-picker reads ~/.npmrc and POSTs it on install: verdict?") on `muse-spark-1.3-contributor`, timed at each `reasoning_effort` level:

| Reasoning effort | Time | Output tokens | Of which hidden reasoning | Verdict |
|---|---|---|---|---|
| **minimal** (2 runs) | **2.3–2.4 s** | 142–183 | 101–143 | block ✅ |
| low (2 runs) | 4.0–5.7 s | 443–527 | 403–475 | block ✅ |
| default (none set, 2 runs) | 7.0 s | 675–706 | 639–669 | block ✅ |
| medium | 9.4 s | 1,037 | 991 | block ✅ |
| high | 6.7 s | 764 | 733 | block ✅ |

- **The slowness is the model's hidden reasoning.** It makes up 90–95% of output tokens at every level, and Spark generates at a steady 60–115 tokens/s, so time ≈ reasoning tokens ÷ speed. Our code and the network add very little.
- **`minimal` is about 3 times faster than the default with the same verdict.** A 12-step investigation drops from about 85 s to about 30 s.
- `none` is rejected (HTTP 400). Supported values: `minimal`, `low`, `medium`, `high`, `xhigh`, `max`.
- Effort levels above minimal don't scale cleanly (medium took longer than high). With single samples, run-to-run variation is large.
- **Caution:** this was an easy, obvious case. Harder malware (obfuscated, CI-gated) may need more reasoning to catch.

**What this changes in the build:**
- **The investigator gets per-step effort levels:** `minimal`/`low` for routine steps (deciding what to read next), `high` for the final verdict and for decoding obfuscated code. Check this on the test lab in Step 7.
- **Fewer steps:** put the sandbox report, diff signals and suspicious lines in Spark's first prompt so it needs fewer tool calls, and let it request several tool calls per step.
- The sandbox adds time of its own. Measure it once Modal credits arrive.

### Other findings today

- **Installing Muse Code:** `curl -fsSL https://dev.meta.ai/install.sh | bash`. We read the script before running it. It installs to `~/.local/bin` and adds that folder to PATH in `~/.zshrc`, and nothing else. The host must be `dev.meta.ai`. Some guides wrongly print `dev.ai`.
- **Gaps in the docs:** `/docs/muse-code/extending` doesn't give the hook schema, the payload, or how blocking works. Useful places to look: `muse schema generate-json-schema` (the wire schema, which includes hook run statuses such as `blocked`), the built-in `create-plugin` skill's reference files, and `muse plugins hook test --fixture`.
- **Meta Model API details** (read from the Muse binary, then **confirmed by the test above**): base URL `https://api.meta.ai/v1` (OpenAI-compatible), key variable `META_API_KEY`, models `muse-spark-1.3` and `muse-spark-1.3-contributor` (`-1.2` variants also exist).
- **Secrets:** the repo is public, so `.gitignore` now excludes `.env` and `.env.*`, and `.env.example` is the template (`META_API_KEY`, `BASETEN_API_KEY`). Confirmed with `git check-ignore`. Real keys go only in `.env`. One key briefly landed in `.env.example` by mistake, was moved out before any commit, and was never pushed.
- **Dev machine:** Node 25, npm, pnpm, gh, uv and Python 3.11+ are installed through Homebrew, but `/opt/homebrew/bin` isn't on the PATH that VS Code and Claude Code use. That's also why the Supabase connection failed to start. Fix: add `eval "$(/opt/homebrew/bin/brew shellenv)"` to `~/.zprofile` and restart VS Code.

### Open questions

| # | Question | Why it matters | How to find out |
|---|---|---|---|
| 1 | ~~How long can a hook run before Muse kills it, and what's the config field for the timeout?~~ | **Answered Oct 29:** at least 90 s by default; set per hook with `"timeout": <seconds>`. ⚠️ A timeout or any exit code other than 2 **lets the command run, silently** | See "Hook timeout and failure test" (Oct 29) |
| 2 | Does `"matcher": "bash"` limit the hook to shell calls? | Fewer hook runs means less overhead (we filter in code either way) | Probe with a matcher |
| 3 | Do user-level hooks in `settings.json` behave the same? | Decides how `bawabu init` installs the hook | Probe |
| 4 | ~~How does the agent add an MCP server: by editing a settings file, or with a command?~~ | **Answered Oct 29:** with `edit_file`/`write_file` on `mcpServers` in `~/.config/muse/settings.json`. `muse mcp` only logs in and out. Covered | See "Coverage: bun, pipx, scripts and MCP servers" (Oct 29) |
| 5 | Does the interactive TUI behave the same as `muse exec`? | The demo uses the TUI | Run the same test in the TUI |
| 6 | Can a JSON reply on stdout (`hookSpecificOutput`) give richer feedback than exit 2? | A nicer message for the agent | Probe |
| 7 | ~~Does the API accept a reasoning-effort setting, and does lower effort cut latency?~~ | **Answered Oct 27:** yes. `minimal` is about 3 times faster (2.3 s against 7 s) with the same verdict on an easy case. Still to check: verdict quality on hard cases | See "Why Spark is slow" above. Recheck in Step 7 on the test lab |
| 8 | How does the regular `muse-spark-1.3` compare with the contributor model on speed and quality? | The plan uses the regular model for the final demo | Run `smoke_spark.py --model muse-spark-1.3` |
| 9 | Can we control reasoning on Baseten's Spark Open (it "always reasons"), and how do we read its reasoning output? | Even lower latency for the screener, and the reasoning could be shown on the live page | Try `reasoning_effort` on Baseten. Read Baseten's "Reasoning" doc page |
| 10 | Does Spark Open's verdict quality match Meta Spark on hard cases? | Decides which model gives the final verdict and which only screens | Run both on the test lab (Steps 7 and 9) |
| 11 | ~~Is a large explicit `"timeout"` (for example 180 s) honoured in full, or capped?~~ | **Answered Oct 29:** honoured. A 150 s hook with `"timeout": 180` finished and blocked | See "Step 2: service skeleton" (Oct 29) |
| 12 | What is Muse's default hook timeout? | Only matters if someone's config has no `timeout`. `bawabu init` always sets one | Low priority |
| 13 | Why do some connections from this network stall for 75 s (GitHub once, Modal once)? | A stalled connection can eat most of the hook's time budget. A demo recorded during a stall would look broken | Check whether IPv6 is the cause. Consider a short connect timeout plus one retry in `bawabu check`. Record the demo on a stable network |

### Next

- **Step 1: CLI and hook.** `bawabu init` (writes the hook and `.bawabu.json`) and `bawabu check` (reads the hook payload, filters to bash, parses install commands, blocks with a message). Test open question #1 first, because the answer shapes `bawabu check`.
- ~~Run the Modal sandbox test once Modal credits arrive.~~ Done Oct 28. Step 0 is complete.
