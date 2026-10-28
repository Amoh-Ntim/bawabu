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
| Muse Code installed and signed in | ✅ Done | v1.4.13, at `~/.local/bin/muse` |
| **Muse Code hook can block and message the agent** | ✅ **Proven** | Oct 27. See below |
| **Muse Spark API: chat, tool calling, structured output** | ✅ **Proven** | Oct 27. All 3 checks pass. See below |
| One Modal sandbox command | ⏳ Waiting | Needs a Modal account and credits |
| Public GitHub repo | ✅ Done | `Amoh-Ntim/bawabu`, created after kickoff |

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
| 1 | **How long can a hook run before Muse kills it, and what's the config field for the timeout?** | A full investigation takes about 1–1.5 min (measured Spark speed). If hooks time out sooner, the hook replies quickly ("checking, watch live at /r/[id], retry in about a minute"), the investigation keeps running in the cloud, the live report page shows progress, and the agent's retry hits the cached verdict | Run a hook that sleeps for 90 s |
| 2 | Does `"matcher": "bash"` limit the hook to shell calls? | Fewer hook runs means less overhead (we filter in code either way) | Probe with a matcher |
| 3 | Do user-level hooks in `settings.json` behave the same? | Decides how `bawabu init` installs the hook | Probe |
| 4 | How does the agent add an MCP server: by editing a settings file, or with a command? | The plan says we intercept new MCP servers too | Ask the agent to add one and watch the hook log |
| 5 | Does the interactive TUI behave the same as `muse exec`? | The demo uses the TUI | Run the same test in the TUI |
| 6 | Can a JSON reply on stdout (`hookSpecificOutput`) give richer feedback than exit 2? | A nicer message for the agent | Probe |
| 7 | ~~Does the API accept a reasoning-effort setting, and does lower effort cut latency?~~ | **Answered Oct 27:** yes. `minimal` is about 3 times faster (2.3 s against 7 s) with the same verdict on an easy case. Still to check: verdict quality on hard cases | See "Why Spark is slow" above. Recheck in Step 7 on the test lab |
| 8 | How does the regular `muse-spark-1.3` compare with the contributor model on speed and quality? | The plan uses the regular model for the final demo | Run `smoke_spark.py --model muse-spark-1.3` |
| 9 | Can we control reasoning on Baseten's Spark Open (it "always reasons"), and how do we read its reasoning output? | Even lower latency for the screener, and the reasoning could be shown on the live page | Try `reasoning_effort` on Baseten. Read Baseten's "Reasoning" doc page |
| 10 | Does Spark Open's verdict quality match Meta Spark on hard cases? | Decides which model gives the final verdict and which only screens | Run both on the test lab (Steps 7 and 9) |

### Next

- **Step 1: CLI and hook.** `bawabu init` (writes the hook and `.bawabu.json`) and `bawabu check` (reads the hook payload, filters to bash, parses install commands, blocks with a message). Test open question #1 first, because the answer shapes `bawabu check`.
- ~~Run the Modal sandbox test once Modal credits arrive.~~ Done Oct 28. Step 0 is complete.
