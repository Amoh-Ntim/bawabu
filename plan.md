# Bawabu — Build Plan

> **Bawabu** (Swahili for *"gatekeeper"*): a security layer that sits between AI coding agents and the packages they install.

Meta Global AI Developer Hackathon · Indie Developer track · Theme: **Push the Frontier**
Builder: Samuel Amoh Ntim (solo)

---

## 1. The problem

AI coding agents now run `npm install` and `pip install` on their own, mid-task, with no human checking what comes in. Attackers have noticed:

- Malicious open-source packages rose **1,444%** from 2024 to 2025 (OpenSSF, cited by Google Threat Intelligence).
- In May 2026, a self-spreading npm/PyPI worm (Mini Shai-Hulud) compromised **172 packages**, reaching Mistral AI, UiPath and TanStack ecosystems.
- Coding agents pull roughly **50% more** open-source dependencies than humans (Socket CEO).
- Models invent package names that don't exist (4.6–6.1% for 2026 frontier models), and attackers register those names (**"slopsquatting"**).
- Most defenses are **blocklists**: they only stop a package after someone has flagged it, which leaves the first hours of an attack wide open.

## 2. What Bawabu does (one paragraph)

Bawabu hooks into Muse Code and intercepts every install command and every new MCP server the agent tries to add. Cheap checks clear most installs instantly. For anything new or suspicious, it runs the package in an isolated cloud sandbox baited with fake credentials, diffs it against the previous version, and lets **Muse Spark investigate as an agent**: reading the code, decoding hidden payloads, and re-running the sandbox under the conditions the malware is waiting for. The verdict (allow / block / ask) goes back to the agent with a plain-English reason, the evidence, and a safe alternative.

## 3. How we stand out

Existing tools: Socket Firewall, Aikido Safe Chain, NpmGuard (ETHGlobal winner), Agentinel, Dep Bouncer, airlock-cli, Lazaretto, Air (Sequoia-backed).

Our differentiators:
1. **Spark as investigator, not a classifier**: tool-calling agent that follows leads.
2. **Trigger-aware re-runs**: Spark reads the code, spots how malware hides (CI-only, date-gated), and re-tests under those conditions.
3. **Task-aware judgment**: "a date picker has no reason to read your npm token."
4. **Native Muse Code integration** (hook + skill + MCP server).
5. **Verifiable verdicts**: every claim cites evidence Bawabu checks exists.
6. **Measured results**: catch rate and false-positive rate, published.

---

## 4. Hackathon facts

### Key times (Accra time)

| What | When |
|---|---|
| Kickoff | Mon Oct 26, 4:00 PM |
| Building period | Oct 27 – Nov 4 |
| Agents 101: Build a Multimodal AI Agent | Tue Oct 27, 4:00 PM |
| Agents 102: Best Practices for Verifiable Agents (**attend**) | Wed Oct 28, 4:00 PM |
| Fireworks: Specialized Intelligence with Muse Open Models | Fri Oct 30, 4:00 PM |
| Discord office hours (weekdays, #office-hours) | 2–3 PM until Oct 30, then 3–4 PM from Nov 2 |
| Last day for submission help | Tue Nov 3 |
| **Submission deadline** | **Thu Nov 5, 2:00 AM** (Wed Nov 4, 9 PM ET) |
| **Our target** | **Submit by Wed Nov 4 evening** |
| Judging | Nov 5 – 8 |
| Closing ceremony (top 5 per track, finals live) | Mon Nov 9, 5:00 PM |
| Most Viral engagement counted until | Nov 8 end of day |
| Community vote winner | Mon Nov 16 |

### Rules that matter
- Repo must be **public**.
- **New work only**: everything shown must be built during the event. Create the repo after kickoff; commit often.
- Demo must only highlight features built during the hackathon, and make that clear, or risk disqualification.
- Solo is allowed (max team size 4).
- Must use Meta's models (Meta Model API and/or open weights).
- Submission: **public repo + 3-minute demo video + live product**, on the Cerebral Valley platform.

### Judging
- **Stage 1 (pass/fail):** fits a theme and genuinely uses Meta models.
- **Stage 2 (0–10 per category):**

| Category | Weight | What Bawabu needs |
|---|---|---|
| Impact | 30% | Real users could install it today; eval numbers; fits Push the Frontier |
| Use of Meta AI tooling | 25% | Spark investigator with tools, trigger-aware re-runs, Muse Code native, open-weights screener |
| Technical depth & execution | 20% | Hardened sandbox, verified evidence, caching, clean code, README |
| Demo | 25% | Live investigation streaming on screen; works every time |

- **Stage 3:** top 5 per track; finalists' videos watched live by final judges.

### Prizes
- **Indie track:** $150K / $100K / $75K / $50K / $25K
- **Startup track:** $250K / $150K / $75K / $50K / $25K
- **Bonus (Meta, $50K):**

| Bonus | Prize | How Bawabu targets it |
|---|---|---|
| Most Viral (X engagement) | $20K | Post the demo clip on X right after submitting |
| Best Build on Meta Open Weight Models | $10K | Screener + `--open-weights` mode on Muse Spark Open |
| Community Vote | $10K | Share the gallery link |
| Best Agentic Use-Case | $5K | Spark investigator agent |
| Best Creative Build | $5K | Not targeting |

---

## 5. Accounts & credits checklist

- [ ] **Meta Model API ($150, guaranteed):** account at dev.meta.ai → add card under Billing → set spend limit → copy Team ID from URL → submit claim form by Nov 4. Credits land within 2 business days.
- [ ] **Modal ($100, reviewed):** create account first; request for Sandboxes + open-weights inference.
- [ ] **Baseten ($100 + 2M TPM, reviewed):** no signup needed. Model ID: `meta-models/muse-spark-open-1026`.
- [ ] Fireworks ($25, shortlist): optional, skip.
- [ ] Discord joined, intro posted in #intros.
- [ ] Muse Code installed locally (sign in with Meta account to save API credits).
- [ ] GitHub repo `bawabu` created (public, **after kickoff**).
- [ ] npm package name `bawabu` claimed.
- [ ] Neon or Supabase Postgres project.

**Team name on all forms:** Samuel Amoh Ntim · **Email:** the one used to apply.

**Saving credits:** use `muse-spark-1.3-contributor` (cheaper; Meta may use requests to improve models, fine for public packages) during development, regular model for the final demo. Let the funnel and cache keep Spark calls rare.

---

## 6. Architecture

```
DEVELOPER'S MACHINE                          BAWABU CLOUD (Modal)
┌───────────────────────┐                   ┌──────────────────────────────────────┐
│ Muse Code agent        │                   │ FastAPI service                       │
│   runs: npm install x  │                   │  1. Quick checks (registry, OSV)      │
│          │             │   POST /check     │  2. Open-weights screener             │
│          ▼             │ ────────────────▶ │     (Muse Spark Open)                 │
│ Bawabu hook            │                   │  3. Sandbox run (honeypots, strace,   │
│  (pauses install)      │ ◀──────────────── │     fake DNS/HTTP sink)               │
│          │             │   verdict         │  4. Version diff + signals            │
│          ▼             │                   │  5. Muse Spark investigator (tools)   │
│ allow / block / ask    │                   │  6. Evidence check + hard rules       │
└───────────────────────┘                   │  7. Cache + report                    │
                                            └──────────────────────────────────────┘
                                                     │
                                                     ▼
                                            Postgres ──▶ Next.js report page (/r/[id])
```

Nothing from the package ever runs on the developer's machine.

### The funnel (cheap first, expensive only when needed)

| Layer | Time | Cost | Ends here when |
|---|---|---|---|
| Quick checks | ~1 s | Free | Package doesn't exist (block) or is old/popular/no install scripts (allow) |
| Open-weights screener | seconds | Partner credits | Signals look benign (allow) |
| Sandbox + diff + Spark | 20–60 s | Meta credits | Everything suspicious |
| Cache | instant | Free | Same `package@version` already judged |

---

## 7. How each part works

### 7.1 Hook & CLI (local)
- `npm i -g bawabu` installs the CLI only (no install scripts; publish with npm provenance).
- `bawabu init` checks Muse Code is installed, registers the hook, creates `.bawabu.json` (mode: block/warn/ask, allowlist for private packages, service URL). Optional: wrap `npm`/`pip`/`npx` so other agents are covered.
- `bawabu check` receives each command from the hook:
  - Not an install (`git status`, `npm test`) → allow instantly.
  - Install → resolve exact package names + versions (including what `latest` means now) → cache hit? → else send to service with the agent's task.
- Covers: `npm`/`pnpm`/`yarn` install/add, `npx`, `pip install`, adding MCP servers.
- Check the full dependency tree for packages with install scripts, not just the top-level name.
- Note to verify: Muse Code runs hooks **outside its sandbox with a cleared environment**, so the hook must read config from a file, not env vars. Hooks may need user approval to be trusted.

### 7.2 Quick checks
- Exists? If not → hallucinated name → block + suggest the real package.
- Age, weekly downloads, maintainers (recent change?), install scripts, provenance attestation.
- Known malicious? (OSV.dev `MAL-` entries.)

### 7.3 Sandbox (the X-ray)
1. **Download without running:** service runs `npm install <pkg> --ignore-scripts` (no package code executes).
2. **Run in a locked room:** copy into a Modal Sandbox with **real internet blocked**, then trigger code deliberately: `npm rebuild` (runs install scripts) and `node -e "require('<pkg>')"`.
3. **Bait:** fake `~/.npmrc`, `~/.ssh/id_rsa`, `.env`, plus env vars with **unique canary values** (e.g. `NPM_TOKEN=npm_canary_7f3k9q`).
4. **Look lived-in:** normal username/hostname, `.gitconfig`, shell history, fake project folder.
5. **Record:** `strace -f` for files opened and processes spawned; fake DNS + catch-all HTTP(S) server log every domain and request (custom CA via `NODE_EXTRA_CA_CERTS` + system store).
6. **Output:** evidence report (files read, processes, network attempts, canaries leaked, duration).

A network call alone isn't guilt (e.g. `esbuild` downloads binaries). **A leaked canary is always guilt.**

### 7.4 Version diff
- Fetch previous version tarball, unpack both, diff.
- Signals: new `install`/`postinstall` script · new file referenced only by that script · obfuscation (long lines, high entropy, `eval`, `Function(`, base64 blobs) · new `child_process`/`http`/`net`/`dns` use · secret paths (`.npmrc`, `.ssh`, `.aws`) · **provenance lost** vs previous version · unknown new dependency.
- Brand-new packages have no diff → sandbox + Spark code reading carry the weight.

### 7.5 Muse Spark investigator
Tools given to Spark:

| Tool | Purpose |
|---|---|
| `list_files()` | See package contents |
| `read_file(path)` | Read any file |
| `search_code(pattern)` | Find `eval`, `.npmrc`, etc. |
| `decode(text, format)` | Decode base64/hex without executing |
| `get_diff(file)` | Changes vs previous version |
| `get_metadata()` | Age, downloads, maintainers, provenance |
| `rerun_sandbox(env, fake_date, timeout)` | Re-test under new conditions |

Loop: think → call tool → read result → repeat (cap ~12 steps). Each step streamed as an event to the report page.

**Trigger-aware re-runs:** if code only fires when `CI=true` or after a date, Spark calls `rerun_sandbox(env={"CI":"true","GITHUB_ACTIONS":"true"}, fake_date="...")` (libfaketime) to make it reveal itself.

**Verdict (structured output):**
```json
{
  "verdict": "block",
  "confidence": "high",
  "reason": "On install, reads ~/.npmrc and sends the token to evil-collector.xyz when CI=true.",
  "evidence": [
    {"type": "sandbox", "detail": "POST to evil-collector.xyz containing NPM_TOKEN canary (rerun #2, CI=true)"},
    {"type": "code", "file": "setup.js", "line": 1, "detail": "base64 payload decoded to network exfiltration"},
    {"type": "diff", "detail": "postinstall script added in 2.3.1"}
  ],
  "safe_alternative": "react-datepicker"
}
```

**Safety rules (must build):**
1. **Verify evidence:** every cited file/line/event must exist in tool outputs, or the verdict is rejected.
2. **Prompt injection:** package content is data, never instructions. **Hard rules override the model** (canary leaked → always block). An injection attempt aimed at AI reviewers is itself a malicious signal.

### 7.6 What the agent sees
> ⛔ Blocked by Bawabu: `fancy-date-pickr` reads your npm token and sends it to an unknown server during install. Use `react-datepicker` instead. Details: bawabu.dev/r/x7k2

### 7.7 Report page
`/r/[id]`: verdict + reason, live-streamed investigation steps, sandbox timeline (files, processes, network), suspicious code lines from the diff, metadata, safe alternative. Optional feed page of recent checks. No accounts, no settings, no desktop app.

---

## 8. Tech stack & repo layout

| Part | Tech |
|---|---|
| CLI + hook | TypeScript (Node), published to npm as `bawabu` |
| Service | Python + FastAPI, hosted on Modal |
| Sandboxes | Modal Sandboxes |
| Investigator | Muse Spark via Meta Model API (OpenAI-compatible SDK, tool calling, structured output) |
| Screener / open-weights mode | Muse Spark Open via Baseten or Modal |
| Database | Postgres (Neon or Supabase) |
| Report page | Next.js (SSE for live streaming) |
| Test registry | Verdaccio (local) |

```
bawabu/
├── cli/        # TypeScript CLI + Muse Code hook
├── service/    # FastAPI on Modal: checks, screener, investigator
├── sandbox/    # image, runner, honeypots, DNS/HTTP sink, strace parser
├── web/        # Next.js report page
├── testlab/    # Verdaccio + harmless stand-in packages
└── eval/       # evaluation harness + results
```

---

## 9. Build steps

| # | Step | Done when |
|---|---|---|
| 0 | **Setup:** credits, accounts, repo (after kickoff). Prove: Muse Code hook can **block** + message the agent; one Muse Spark call; one Modal sandbox command | All three proven |
| 1 | **CLI & hook:** `bawabu init`, `bawabu check`, install-command parsing | Agent's `npm install x` can be stopped with a message |
| 2 | **Service skeleton:** `POST /check`, cache table, CLI → service | Hook → service → allow → install runs, end to end |
| 3 | **Quick checks:** registry metadata, OSV, fast-path rules, hallucinated-name suggestions | Fake names blocked; `react` allowed instantly |
| 4 | **Test lab:** Verdaccio + ~8 harmless stand-ins + 2–3 tricky legit packages | Test packages installable from local registry |
| 5 | **Sandbox runner:** staged download, locked sandbox, honeypots, canaries, strace, DNS/HTTP sink, evidence parser | Token-stealer stand-in caught in evidence report |
| 6 | **Diff engine:** previous-version fetch, diff, signal extraction | Injected postinstall flagged with signals |
| 7 | **Spark investigator:** tools, loop, structured verdict, evidence verification, hard rules, injection handling, event streaming | Correct verdicts with verified evidence on test lab |
| 8 | **Trigger-aware re-runs:** env vars, libfaketime, longer runtime | CI-gated and date-gated stand-ins caught |
| 9 | **Open-weights layer:** Spark Open screener + `--open-weights` mode | Screener allows benign, escalates suspicious |
| 10 | **Report page:** `/r/[id]` with live stream | Investigation visibly streams during a block |
| 11 | **Evaluation:** test lab (catch rate, time) + top 500–1,000 npm packages (false positives, latency) | Results table in README |
| 12 | **Live scan (stretch):** watch new npm publishes, escalate suspicious, report real finds to npm security | Scanner running |
| 13 | **Ship:** README (architecture diagram, "built during hackathon"), publish to npm, record video, post on X, submit | Submitted |

### Test lab stand-ins (all harmless; fake data only, "exfiltrate" only to our own sink; **never publish to public npm**)
1. Token grab on postinstall
2. Only triggers when `CI=true`
3. Only triggers after a date
4. Obfuscated base64 payload
5. Malware hidden in a dependency
6. Hallucinated package name
7. Prompt-injection comment aimed at AI reviewers
8. Hijacked version (clean v1, malicious v2 with lost provenance)
- Tricky legit: binary downloader (esbuild-style), native build (sharp-style), heavy postinstall

---

## 10. Schedule

| Day | Work | Also |
|---|---|---|
| Mon Oct 26 | Step 0 | Kickoff 4 PM |
| Tue Oct 27 | Steps 1–2 | Agents 101, 4 PM |
| Wed Oct 28 | Steps 3–4 | **Agents 102, 4 PM** |
| Thu Oct 29 | Step 5 | |
| Fri Oct 30 | Finish 5, Step 6 | Fireworks workshop (optional) |
| Sat Oct 31 | Step 7 | |
| Sun Nov 1 | Steps 8–9 | US clocks change |
| Mon Nov 2 | Step 10 | |
| Tue Nov 3 | Step 11 (+12 if time) | Last day for help in Discord |
| Wed Nov 4 | Step 13 | **Submit in the evening** |

**Cut order if behind:** live scan → full open-weights mode (keep screener) → PyPI support → feed page.
**Never cut:** test lab, sandbox, Spark investigator, report page.

---

## 11. Demo video (3 minutes)

| Time | Content |
|---|---|
| 0:00–0:15 | Hook: an AI agent about to install malware, and nobody's watching |
| 0:15–0:40 | The problem in numbers (1,444%, worms, slopsquatting); blocklists are too slow |
| 0:40–1:50 | **Live split screen:** Muse Code builds a feature (left); Bawabu report page streams Spark's investigation (right): reads code, decodes payload, re-runs with `CI=true`, catches the canary leaving, blocks, agent installs the safe alternative |
| 1:50–2:20 | Under the hood: funnel, sandbox honeypots, verified evidence, open-weights mode |
| 2:20–2:45 | Results: catch rate, false-positive rate on top npm packages, average delay |
| 2:45–3:00 | One-command install, open source, "everything shown was built during the hackathon" |

Demo must run from the local Verdaccio registry so it works every time. Record a backup take.

---

## 12. Risks & open questions

| Risk | Plan |
|---|---|
| Muse Code hook can't block commands | Fall back to wrapping `npm`/`pip`/`npx` (works with any agent) |
| Meta API access / card declined | Virtual USD card; confirm access day 0 |
| Modal/Baseten credits not granted | Use whichever arrives; small paid top-up if needed |
| False positives on legit packages | Tricky-legit test packages, eval on top npm packages, "ask" verdict for gray areas |
| Sandbox-evasive malware | Lived-in sandbox, trigger-aware re-runs, diff + code reading; state limits openly |
| Slow checks annoy users | Funnel + cache; only suspicious packages get the full investigation |
| Scope creep | npm only; PyPI only if time remains |

---

## 13. Resources

- Event: https://cerebralvalley.ai/e/meta-ai-developer-hackathon
- Participant guide: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details
- Livestream: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/live
- Discord: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/discord
- Submission: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit
- Meta docs: https://dev.meta.ai/docs/overview · Quickstart: https://dev.meta.ai/docs/quickstart · Models: https://dev.meta.ai/docs/models
- Cookbooks: https://github.com/meta-models/meta-model-cookbook (Muse Code recipes in `04_muse_code`) · https://github.com/meta-models/meta-oss-cookbook
- Modal Sandboxes: https://modal.com/docs/guide/sandboxes
- Baseten quickstart: https://docs.baseten.co/quickstart
- Credit forms:
  - Meta: https://docs.google.com/forms/d/e/1FAIpQLScam78z7tHsNYibiFyJQVFzEgr0coyBTiY568SxxNbsPa3jiw/viewform
  - Modal: https://docs.google.com/forms/d/e/1FAIpQLSe_GDPtLZsdA57xPhFcOCi_yLjPf8HRxMIQJ5V7ystoKSqWCQ/viewform
  - Baseten: https://docs.google.com/forms/d/e/1FAIpQLSfM7gcK8yMZEmAGq6DbTyiuv2c71IH7CKCy0fXGIfUED1qxVQ/viewform