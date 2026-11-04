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
| **Step 13: ship** (README, npm publish, video, X post, submission) | 🟡 **In progress** | Nov 1: **on npm** (`npm i -g bawabu`), MIT license, verified statistics, PDF covers Steps 0–13, try-it-with-your-own-key. Left: public repo, video, submit. Oct 30: README written (`README.md`), schema for self-hosting (`service/schema.sql`), report screenshot. Still to do: license, demo video, npm publish, X post, submit |
| **Step 11: evaluation** (test lab with both investigators; top 500 npm) | ✅ **Done** | Oct 30. **9/9 malicious caught in all 7 runs**; final engine **13/13** with Muse Spark (2 runs) and Muse Spark Open (1 run), 0 false positives. **Top 500 npm: 500/500 allowed**, 0.7 s median (493 by quick checks; 7 investigated and cleared by Spark). Found and fixed: unreadable C/C++ sources, native builds failing in the sandbox, reviewer-directed wording in our honest fixtures. See `eval/RESULTS.md` |
| **Step 10: report page** (`/r/<id>` live report, `/live` follow mode) | ✅ **Done** | Oct 30. Served by the Modal service, no new app. Verdict, Spark's steps live, verified evidence with the cited code highlighted, sandbox runs (STOLEN rows), diff, hard rules, discarded claims. Strict CSP + text-only rendering of package content. A real Muse agent's block message linked to the report |
| **Step 9: open-weights layer** (Muse Spark Open screener on Baseten + `--open-weights` investigator) | ✅ **Done** | Oct 30. Screener clears benign flagged packages in ~5–7 s and sends risky ones on in ~1.3 s by rule. Test lab: the clean one cleared, every risky one escalated (incl. the malicious-dependency one). Real little-used npm packages: 4/7 cleared, 3 escalated by the dependency gate. Open-weights investigator: CI-gated caught via its own re-run, legit allowed. **Deployed:** live `/check` cleared docs-gen-postinstall 1.0.0 via the screener, and an `open_weights` request blocked color-hex-convert (injection + leak) |
| **Step 7: Muse Spark investigator** (tools, loop, verified evidence, hard rules, events, registry routing, service wiring) | ✅ **Done** | Oct 30. Test lab **7/7 correct** (5 blocked incl. CI-gated and date-gated via Spark's own sandbox re-runs and an obfuscated payload Spark decoded itself; 2 legit allowed). **Deployed**; a real Muse agent's `npm install date-fns-lite-utils` was blocked after a live in-hook investigation (126 s session), with line-cited evidence and a report link; the agent didn't retry another way |
| **Step 6: diff engine** (previous-version fetch, in-memory unpack, static signals, what's new) | ✅ **Done** | Oct 30. Hijacked docs-gen-postinstall 2.0.0 flagged HIGH with the exact story; catches the base64 fixture the sandbox missed. 12 popular npm packages (esbuild, sharp, next, core-js, puppeteer, …): all NONE except bcrypt 6.0.0 MEDIUM |
| **Step 5: sandbox X-ray** (locked Modal sandbox, canaries, strace, fake-internet sink, evidence) | ✅ **Done** | Oct 30. Token-stealer caught (canary POST intercepted over HTTPS); transitive-dep, CI-gated and date-gated variants caught; 3 legit packages not flagged. Trigger-aware re-runs (env + faketime) also working |
| **Step 1: CLI and hook** (`bawabu init`, `bawabu check`) | ✅ **Done** | Oct 29. A real Muse agent's `npm install left-pad` was blocked, and allowed once allowlisted |
| **Coverage: bun, pipx, script files, package.json scripts, MCP servers** | ✅ **Done** | Oct 29. 39 unit tests pass. Real agents blocked on `./setup.sh`, `bun run setup` and `pipx install`. MCP edits blocked at the hook |
| **Step 4: test lab** (harmless practice packages on a private registry) | ✅ **Done** | Oct 29. 11 practice packages (12 versions) on a password-locked Verdaccio on Modal, which passes everything else through to the real npm. All install; no password means `E401` |
| **Step 3: quick checks** (registry facts, OSV malware, made-up names and suggestions, exact versions) | ✅ **Done** | Oct 29. 14/14 real packages judged as expected. Made-up names blocked with "did you mean"; `react` allowed in about 1 s. Service 60/60 tests, CLI 50/50 |
| **Step 2: service skeleton** (`POST /check` on Modal, verdict cache, CLI to service) | ✅ **Done** | Oct 29. A real agent's install went from the hook to the service, got `allow`, and ran. Deployed at `https://amohntim123--bawabu.us-east.modal.run` with the Supabase verdict cache. `bawabu init` uses it by default |
| Muse Code installed and signed in | ✅ Done | v1.4.13, at `~/.local/bin/muse` |
| **Muse Code hook can block and message the agent** | ✅ **Proven** | Oct 27. See below |
| **Muse Spark API: chat, tool calling, structured output** | ✅ **Proven** | Oct 27. All 3 checks pass. See below |
| One Modal sandbox command | ✅ **Proven** | Oct 28 (smoke) and Oct 30 (full X-ray runs) |
| Public GitHub repo | ✅ Done | `Amoh-Ntim/bawabu`, created after kickoff |

---

## 2026-11-04 (Wed): README setup followed from a fresh public clone

Followed the README as a judge would, after the organisers confirmed judges work from the README and the video. Public
clone of `main` at `6cc2383`, CLI 0.1.1 from npm (in a private folder, not with `-g`).

| Check | Result |
|---|---|
| Hosted, no keys: `bawabu scan react-datepickr` | ⛔ blocked, "did you mean react-datepicker?", 6 s (first call) |
| Hosted, no keys: `bawabu scan left-pad` | ✅ allowed, 2 s |
| `uv sync`, `uv run service/run_local.py` | Clean; the service answered in about 6 s |
| `--local`: `react-datepickr` / `left-pad` | ⛔ 1 s / ✅ 2 s |
| `--local --lab`: `ci-build-cache-helper` / `color-hex-convert` | ⛔ 18 s / ⛔ 10 s, with evidence and report links |
| `--local --lab`: `pretty-log-kit` (honest) | ✅ allowed, 16 s |
| `bawabu demo` | Project created, hook installed, self-test passed, service reachable |

Not run in this check: a Muse Code session in `bawabu-demo` and a sandbox investigation on the hosted service.

### Local practice cases, sandbox off, both models

All 13 cases on the local service from the fresh clone, three at a time, then repeats of the case that went wrong.

| Model | Result | Time per case |
|---|---|---|
| Muse Spark | **12 / 13**: `markdown-tiny-render` came back "ask" (it couldn't examine the dependency), not blocked | 14–38 s for investigations |
| Muse Spark Open | **13 / 13** | 8–28 s for investigations |

**A wrong "allow".** In the log check, run before these passes, `bawabu scan string-format-pro-utils --local --lab
--open-weights` **allowed the malicious package**, with a reason that described the credential theft and evidence
calling the address a "dead sink". The sample only sends to a `.invalid` address, which may be why; a later run's reason
says "even though sink domain is a test *.invalid, the behavior is credential theft". The repeats:

| `string-format-pro-utils`, sandbox off | Blocked | Allowed |
|---|---|---|
| Muse Spark Open, 5 runs | 4 | **1** |
| Muse Spark, 3 runs | 3 | 0 |

No hard rule catches this locally, because the leaked-canary rule needs a sandbox run. With the sandbox on, the 9
evaluation runs caught every malicious package. **Not fixed**: a guard against an "allow" whose own reason describes theft
would be a code change, so it's the user's decision. Earlier local testing (13 / 13 with Muse Spark, 0–18 s) was one run,
so the README now reports these results and has a new Limits entry.

### Logs, each one produced and found for real

| Log | Check | Result |
|---|---|---|
| `/investigations` and `/investigations/<id>` | Local and hosted | `model` shows `muse-spark-1.3` or `meta-models/muse-spark-open-1026`, with every tool call and result |
| `/r/<id>`, `/live` | Hosted | 200 |
| Screener | `docs-gen-postinstall@1.0.0` local; `string-format-js` hosted, no keys | "Cleared by Bawabu's open-weights screener (Muse Spark Open)" |
| `~/.local/state/bawabu/checks.jsonl` | The hook called as Muse calls it, with a separate `HOME` | Exit 2, one line with the command, decision, verdicts and reasons; `bawabu scan` doesn't write here |
| Muse session logs | A real 30 Oct session | `hook_run_terminal`, status `blocked`, exit code 2, stderr "Blocked by Bawabu"; `model_id` `muse-spark-1.3-contributor` |

The README gained an Architecture section and a Logs section, following the organisers' list, and a section on how
Modal and Baseten are used, written from `service/modal_app.py`, `runner.py`, `screener.py` and the results above.

## 2026-11-03 (Tue): demo video on YouTube

- Posted: https://youtu.be/poZY6OTK4-U, titled "Bawabu: a gatekeeper for the packages AI coding agents install |
  Meta Global AI Developer Hackathon". YouTube's oEmbed returns it without signing in (HTTP 200), so judges can open it.
- README's "Demo video" line now links to it.
- Repo made **public** (default branch `main` = `ad1dc59`). Commit `47b0c34` had removed `docs/` (including the README's
  two images) and `title cards/`; `docs/` is back, `title cards/` stays out (nothing links to it). Every README link and
  image checked signed-out: all load (npmjs.com answers 403 to scripts only; the registry shows `bawabu` 0.1.1).
- Still to do: submit on Cerebral Valley, post on X.

---

## 2026-11-03 (Tue): first cut of the demo video, reviewed frame by frame

- `bawabu meta ai.mp4`: 2:57, 1080p, 29.97 fps, AAC stereo. Audio −18.2 LUFS integrated, true peak −3.5 dBFS, no
  silence over 1.5 s. Order: title card, card 1, hook, cards 2a–2c, live demo (1:09–2:26), report B-roll, card 4,
  B7, card 5. Card 3b, B1 and B9 left out. Split-screen text is readable at 1080p; no secrets on screen.
- **What the agent actually did in Take A** (Muse session `01a1a05e…`, before the registry login): it read
  `.muse/*`, saw a "package gatekeeper configured for this project", read Bawabu's own `dist/cli.js`, and ran
  `bawabu scan ci-build-cache-helper` itself. The service investigated and blocked; the agent didn't install. The hook
  never had to stop an `npm install`, so a voiceover saying "the agent runs npm install and Bawabu stops it" doesn't
  match the picture.
- **After the registry login** (session `01a1a0b0…`), the agent `npm pack`ed the tarball to `/tmp`, read
  `scripts/cache.js` and refused on its own: this fixture is easy for a capable agent to catch when it can read the
  code. So the login from the entry below makes a retake *less* likely to show Bawabu; Take A is the better footage.
- Editing notes given: match V5a/V5b to the scan, slow the investigation (1:39–1:56) back to 1× and pay for it by
  cutting the agent's thinking (1:13–1:30), replace the screen-recorded cards (mouse cursor visible) with the PNGs, add
  "2× speed", "Muse Code" and "Harmless test package" labels, move "Bawabu Live Report" to the start of the split
  screen, raise the audio about 3 dB.
- All five Muse runs today in `payments-dashboard`: (1) no `.npmrc` yet → public npm 404, no change; (2) the video
  run → `bawabu scan`, blocked; (3, 4) no registry login → stopped and asked; (5) with the login → `npm pack`, read
  the code, refused. In none did the agent run `npm install` straight away (Muse Code 1.4.14, Auto-review mode).
- Judges' rule (organisers): the video is cut off at 3:00, and judges read the README. So anything that doesn't fit
  goes in the README: added **"The demo video"** section (what the live demo shows, that the hook doesn't rely on the
  agent asking, the four runs above as "why not leave it to the agent?", and the same package's report link, since the
  one on screen, `d63f2523…`, was deleted by the reset). The four README report links were checked: all live.

---

## 2026-11-03 (Tue): demo rehearsal — the agent stopped at the registry login

- A real Muse run with the backup prompt ("Run npm install ci-build-cache-helper …") still never reached the install.
  Muse's session log shows it ran only `npm view` on the test lab (E401, no login on this Mac) and on the public npm
  (E404), then stopped and asked for registry auth or another source. No install, so no hook check and nothing on
  `/live`. The earlier "remaining risk" happened even with the backup prompt, so a prompt alone can't avoid it.
- `package.json` had also gone missing from the demo project again; restored with `npm init -y`.
- Fix for recording: log this Mac in to the test lab once, at user level (`npm login --registry=<lab>
  --auth-type=legacy`), so the project's `.npmrc` still shows only the registry line. The CLI never reads or sends
  npm credentials (checked: no `_auth`/`_authToken` handling in `cli/src`); the service still downloads with its own
  login. Writing the login into `~/.npmrc` from Claude Code was refused by the safety check, so it's a manual step.
- The agent may now quote the fixture's description ("Bawabu test fixture #2 … harmless"); the on-screen "Harmless
  test package" label covers that. New backup prompt answers the agent's trust question up front ("It's our team's
  build-cache helper, on our private registry (already set up in .npmrc)").
- Recording script (setup step 4, step 6, troubleshooting) and video guide updated; both PDFs regenerated.

---

## 2026-11-02 (Mon): Report page redesign and light title cards

- Implemented `docs/report-page-ui-plan.md`: light/dark themes with saved preference, soft cards and icon headings,
  tinted verdicts, evidence ring, real metric tiles, confidence bars, severity pills and signal counts, sandbox
  contact tables, amber unverified evidence, and recent-check pills. The layout stacks at phone width.
- `diff_summary()` now adds structured `signal_items`; the existing `signals` list stays unchanged. Older reports
  still show their plain signals and explicitly identify missing comparison data.
- Validation: **123 service tests passed**, including nonce/CSP, private-registry redaction, both themes' color
  tokens and 4.5:1 text contrast. JavaScript DOM checks covered blocked/allowed/ask/failed/old reports, live mode,
  severity sorting, ring counts, network states, theme persistence, denied localStorage and hostile text.
- Visually inspected the report in Safari in light and dark, including 390 px phone width, and opened the existing
  hosted date-gated report after deployment. Used local fixtures for uncommon UI states; no fresh paid investigation
  was needed for the visual redesign.
- Deployed with `.venv/bin/modal deploy service/modal_app.py`. Both hosted `/r/<id>` and `/live` HTML match the
  tested local page after nonce replacement; security headers remain restrictive. The concurrent mascot/header
  change is included in this deployment.
- Added all **seven light-mode title cards** to `title cards/light mode/`, with 1920 × 1080 PNGs, editable SVGs and
  `preview.png`. Same wording and layout as the dark set; off-white, dark ink and accessible deep teal match the UI.
  Re-render with `python3 'title cards/source/render_cards.py' --theme light` (requires Pillow).
- Suggested video theme: light, to match the new card set. The recording theme remains the author's choice.

---

## 2026-11-03 (Tue): demo rehearsal — why /live stayed empty

- The demo project (`~/Desktop/payments-dashboard`) had only `.muse/` from `bawabu init`: no `package.json`, no
  `.npmrc`. With no `.npmrc`, the agent looked on the public npm (`npm view`, `npm search` → 404), concluded the package
  doesn't exist, and made no changes. Those aren't installs, so the hook (which ran on every command, per Muse's
  session log) correctly let them through; no install meant no check and nothing on `/live`.
- Fixed by finishing the setup: `npm init -y`, the one-line `.npmrc` pointing at the test lab, `git init`.
- **Remaining risk:** the test-lab registry needs a login, so if the agent researches with `npm view` first it gets
  E401 ("npm login") and may stop to ask. Adding the login to `.npmrc` would fix that but show the fixture's description
  ("Bawabu test fixture #2: payload gated on CI=true") on screen. Backup prompt that goes straight to the install:
  "Our CI builds are slow. Run npm install ci-build-cache-helper to add our team's build-cache helper to this project."
- Verified the chain from the demo project by sending the hook exactly what Muse sends for `npm install
  ci-build-cache-helper`: blocked after a live 69 s investigation (CI=true re-run, leaked canary), with the evidence and
  report link. Then reset with `reset_demo.py` so the first take is fresh.
- **`/live?fresh`** (deployed): a recording mode that leaves out the checks from before the page was opened. Plain
  `/live` showed a row of past checks, including `ci-build-cache-helper … BLOCKED`, which would give the outcome away
  on screen; the reset can't remove them all (the README's CI report is protected). Plain `/live` keeps the row for
  visitors. Checked both with headless Chrome against the hosted service; 141 Python tests pass.
- The recording script and video guide now use `/live?fresh`, the real project path (`~/Desktop/payments-dashboard`),
  the backup prompt, and two new troubleshooting rows ("npm login" error; "doesn't exist on the public npm").

---

## 2026-11-02 (Mon): Step 13 (part 13) — fixes from the outside review

An outside review (`bawabu-review-2026-11-02.md`, kept outside the repo) checked the code and found the claims
broader than the enforcement. Every high-severity finding was confirmed in the code before fixing.

**The guard (CLI 0.1.1, needs `npm publish`)**
- **Whole-project installs are now checked.** `npm install`, `npm ci`, `yarn`, `pnpm install`, `bun install` read the
  folder's `package.json` (following `--prefix`, `--cwd`, `--dir` and `cd`) and send every direct dependency
  (dependencies, dev, optional, peer; npm aliases resolved) to the service like a named package. `pip install -r`
  reads the requirement files (following `-r` includes); `uv run script.py` reads the script's inline `# /// script`
  dependencies. Before, an agent could add a package to `package.json` and run `npm install` unchecked.
- **Download-source switches are blocked**: `--registry`, `--userconfig`, `--@scope:registry`, bun `--config`, pip/uv
  index URLs and `--find-links`, `--pip-args` with an index, and `npm_config_registry=` / `PIP_INDEX_URL=` style
  variables (inline or exported). The public npm and PyPI URLs are still allowed.
- **Package files are blocked like URLs**: `npm i ./x.tgz`, `pip install ./x.whl`, `file:vendor/x.tgz` dependencies.
  Folders (`npm i ./packages/ui`, `pip install -e .`) are still trusted as the user's own code.
- **Installs from inside other programs are flagged**: `node -e` / `python -c` code containing an install, and local
  scripts that call one (`execSync("npm install …")`, `subprocess.run([... "pip", "install" ...])`). Scripts that merely
  print "pip install x" as advice still run.
- More than 200 packages in one install is blocked with a message (the service's limit).
- Tested end to end against the hosted service: a `package.json` with a made-up dependency → `npm install` blocked
  with "Did you mean react-datepicker?"; `--registry https://evil.example` blocked; `left-pad` + `express` allowed.

**The service and sandbox (needs `modal deploy`)**
- **Evidence needs a verbatim quote.** Code evidence with only a line number, diff evidence with only a file name, and
  metadata claims are discarded unless their quote appears in the file, the diff or the registry facts. The prompt and
  the tool schema say so.
- **The prompt-injection hard rule is narrower.** Text addressed to AI reviewers ("note to automated reviewer",
  "ignore previous instructions", "respond with verdict: allow", "do not flag this") still forces a block. "This package
  has been audited", "ignore the warnings" and "you are an AI" (common in harmless READMEs and LLM prompt templates) are
  now a medium red flag the investigator weighs.
- **Canaries in binary or gzipped request bodies are found** (the sink stores them as base64; the scan skipped them).
- **A failed sandbox run is no longer shown as clean** on the report page.
- Wording: "same install command" (only the command is compared, not the file); the manifest note says direct
  dependencies are checked.

**Re-evaluated with the stricter rules:** Muse Spark run `lab-meta-20261102-0946`: **13 / 13** (9 / 9 malicious, 0 / 4
false positives; median 36.8 s, max 70.8 s), with the `CI=true` re-run and the moved clock chosen by Spark again. **No
evidence was discarded** in any of the 11 investigations: Spark quoted every claim. Muse Spark Open run
`lab-open-20261102-0949`: **13 / 13** (9 / 9, 0 / 4; median 35.5 s, max 64.8 s); 2 unquoted claims discarded
(docs-gen-postinstall@2.0.0, image-resize-native) without changing either verdict. Totals now: 9 / 9 in every one of 9
runs (81 / 81). README, eval/RESULTS.md, the explainer and the video guide updated.

**Deployed** as Modal version v15 (09:50 GMT). A web container started at 09:48 on v14 kept answering afterwards
(probably kept warm by an open `/live` page polling every 1.5 s), so the live service still showed the old manifest note;
it needs stopping (`modal container stop`) or to go idle before v15 serves. CLI 0.1.1 built and packed, not yet
published.

**Redeployed as v16 (10:10 GMT): live and verified.** The only web container now runs v16; `/check` returns the new
manifest note, `/live` has the failed-run fix, `left-pad` is still allowed in about a second, and the README's CI
report still opens.

**CLI 0.1.1 on npm** (published 10:15 GMT, tagged `latest`). The registry's checksum (`9050143…`) matches the tested
local build byte for byte. It took about 20 minutes to show up in the public registry.

**Claims narrowed everywhere** (README, npm page, explainer PDF, title cards 3b/3c/4, video guide, recording script):
"only if it's safe" → "only when it finds no evidence of harm"; "every install" → "the installs it can see";
"prove every claim" → "show its evidence"; "9 / 9 attack samples" → "9 / 9 in our test lab". The README's "most
defences are blocklists" became a fair comparison (Socket Firewall, Aikido Safe Chain) leading with Bawabu's
difference: the experiment loop. The voiceover's "blocklists only help after…" became "And the agent installs it in
seconds, before any human looks." (394 words now). README Limits now states the threat model, direct-dependency scope,
command-not-file quick checks, citations-not-conclusions evidence checks, coverage, fixed canaries, and private code on
the hosted service.

Tests: **140 Python** (was 134) and **74 CLI** (was 66), all passing.

---

## 2026-11-02 (Mon): Step 13 (part 12) — the recording and voiceover script

**`docs/demo-recording-script.pdf`** (13 pages, from `demo-recording-script.md`): the rehearsal script, in three parts.
- **Part 1, the screen recording:** one-time setup (Mac, terminal, Chrome, the demo project, trusting the workspace),
  then every clip step by step: Take A (pre-flight, reload, prompt, and a timed table of what appears on each side),
  B1, B3–B5 as one scroll, B7, B9 and the spares, with the exact commands, URLs, expected output and file names.
- **Part 2, the voiceover:** recording tips, pause and stress marks, pronunciations, and the lines V1–V8 (V5 in eight
  parts tied to on-screen moments), with markers where the picture changes; then the 390-word script in large type for
  reading aloud.
- **Part 3:** the edit timeline, second by second: picture, added text and voice.
- Checked against the live system: the event sequence and timings come from the latest hosted ci-build-cache-helper
  run (blocked in 23 s, with the CI=true re-run); B1 and B2 output from running `bawabu scan` against the hosted
  service; the labels from the redesigned report page, which is already deployed (with the mascot).
- `docs/make_video_guide.py` now builds any Markdown file given as an argument (default: the video guide).

---

## 2026-11-02 (Mon): Step 13 (part 11) — architecture title cards

- Two new cards, drawn by `title cards/source/render_cards.py` in the cards' own style, **dark and light**:
  - **3b "Every install goes through the gate"** (0:41–0:47): Muse Code → hook → quick checks (about 1 s) → screener
    (Muse Spark Open, a few seconds) → investigation (30–90 s), what each stage can answer, and the answer going back
    to the agent. Replaces the screenshot of the PDF diagram, which had too much detail for six seconds of video.
  - **3c "Muse Spark has to prove every claim"** (optional): diff engine and sandbox feed Spark, the re-run loop,
    evidence check, hard rules, verdict.
- The renderer checks that every line fits inside its box and the card margins. Re-rendering left the seven existing
  cards and the mascot exports byte-for-byte identical.
- Updated `title cards/README.md`, `docs/title-cards-plan.md` (cards 3b and 3c, both themes) and
  `docs/demo-video-guide.md` (0:37–0:47 uses card 3b; 3c optional at 1:57), and rebuilt `docs/demo-video-guide.pdf`.

---

## 2026-11-02 (Mon): Step 13 (part 10) — the mascot on the report page

- The report page header shows the **Bawabu mascot** instead of the building icon, on a light tile so its dark
  outlines stay visible in the dark theme. It's also the browser tab icon.
- The page's security policy blocked every image, so the service now serves the mascot itself at `/mascot.png` and the
  policy allows images from the service only (`img-src 'self'`). Nothing loads from outside.
- The image is a 96 × 96 PNG (13 KB) kept as base64 in `service/bawabu_service/brand.py`, because Modal ships only
  `.py` files from the package.
- Tests: the page loads exactly one thing (`/mascot.png`, as the image and the tab icon), the policy includes
  `img-src 'self'`, and `/mascot.png` is served as a PNG. **123 passed.** Checked by eye in both themes with headless
  Chrome.
- Deployed together with the report page redesign on 2 November; see the entry above.

---

## 2026-11-02 (Mon): Step 13 (part 9) — report page UI plan

**`docs/report-page-ui-plan.md`**: making the report page readable at a glance, mostly with colour, before the video is
recorded. Nothing changed in the code yet.
- One colour scale for the whole page: danger red, caution amber, a new "low" blue, safe green. Teal stays Bawabu's own
  colour, violet stays Spark's.
- Must do: coloured static-risk badge (none, low, medium, high: the code says "medium", not "moderate"), a severity
  dot on each signal, a tinted verdict banner with ✕ ✓ ?, coloured sandbox rows.
- **Found while planning:** "unverified" evidence shows in the same green as "✓ verified" (both use `.ok`). The plan
  fixes it.
- Signals reach the page without their severity, so `diff_summary()` gets a new `signal_items` list. Old reports in
  Supabase don't have it, so the page falls back to the plain list.
- Shipping needs only `modal deploy service/modal_app.py`: old report links get the new look, and npm needs no new
  version.
- **Update (same day):** the plan now covers a full new look, based on two reference dashboards: soft rounded cards,
  icon titles with subtitles, tinted pills, stat tiles, an evidence ring, a signals-by-severity bar, and **light and
  dark themes** (follows the system, sun / moon switch, remembered). Light and dark colour values for every level,
  AA contrast. Only real data on the page: no decorative charts. Sections and behaviour unchanged. Time box about 4 h,
  colour first.

---

## 2026-11-02 (Mon): Step 13 (part 8) — title cards plan and mascot

**`docs/title-cards-plan.md`**: the still images for the video, ready to make in Keynote, Slides or Canva.
- **Seven cards** (context, three problem numbers, the Bawabu title, results, end card). Text, layout and timing match
  `demo-video-guide.md` (checked against its plan at a glance). The context card's "first commit: 27 October" checked
  against `git log`.
- One shared style: 1920 × 1080, dark navy with white, grey and teal (the report page's colours), one sans-serif font.
- The overlays that are video-editor labels, not cards (hook caption, lower-thirds, "Harmless test package",
  "2× speed", captions).
- **Mascot:** a friendly gatekeeper (*bawabu* is Swahili for gatekeeper), flat and simple so it still reads small, on a
  transparent background, used only on the title card, the end card, the README header and the X post. Time-boxed to
  30–60 minutes **after** recording. The cards work without it.

---

## 2026-11-02 (Mon): Step 13 (part 7) — the demo video guide

**`docs/demo-video-guide.md`**: everything needed to record the 3-minute video.
- What the video must do (rules, honesty rules, which moment answers which judging category), and a plan at a glance.
- One-time setup (a hint-free demo project `~/payments-dashboard` whose `.npmrc` points at the test lab, the screen
  layout) and a pre-flight for every take (`reset_demo.py ci-build-cache-helper --yes --warm`, reload `/live`).
- The script, segment by segment: what's on screen, what to do, what to say. The live demo is a table matching each
  stage of the real investigation to its line. Plus a B-roll shot list with exact commands and report URLs (the
  open-weights color-hex-convert report for Muse Spark Open, the prompt injection and the hard rules), editing notes,
  voiceover tips, troubleshooting, the source of every spoken number, the submission text and an X post.
- **Voiceover trimmed from 426 to 387 words: 2:34–2:45 at a calm 140–150 words a minute**, leaving room for silent beats.
- Timings come from real hosted runs: about 23–45 s for ci-build-cache-helper's investigation on a warm service, CI
  re-run included.
- **Open risk:** all end-to-end tests used `muse exec`; the guide asks for one rehearsal in interactive Muse Code first,
  with `muse exec` as the fallback.
- **Update (same day):** following the organisers' guidance, the video now **opens with what existed before the event**
  (0:00–0:09): a context card (no Bawabu code, repo or service before the event, with the first commit on 27 October
  after the 26 October kickoff; the existing tools it builds on: Muse Code, Muse Spark, Muse Spark Open, Modal, Baseten,
  Supabase, Verdaccio, OSV) plus one spoken line. To make room, the hook was tightened and the closing "built during this
  hackathon" line dropped (the end card still says it). Voiceover: **390 words, 2:36–2:47**.
- **`docs/demo-video-guide.pdf`** (10 pages), built by `docs/make_video_guide.py` (Markdown, then styled HTML, then
  headless Chrome's print to PDF; the lines to say are highlighted in green). Checked page by page.

---

## 2026-11-01 (Sun): Step 13 (part 6) — demo reset for retakes

**Why:** verdicts are cached (block: 30 days) and a finished investigation is reused for 24 h, so a second take of the
same practice package would be an instant "BLOCKED" with nothing on `/live`.

**`testlab/reset_demo.py [pkg ...] [--yes] [--force] [--warm]`** (talks to Supabase's REST API with the secret key from `.env`):
- Deletes the **test-lab packages'** cached verdicts and their investigations from the last 24 h (the reuse window;
  imported from the service so they stay in sync). Their event streams go with them (cascade).
- **Safety:** filters on the test lab's registry address, so public-npm verdicts can't be touched, and refuses names
  that aren't practice packages; dry run unless `--yes`; never deletes investigations linked from the README, or running
  ones unless `--force`.
- `--warm` wakes the hosted service and the practice registry afterwards, so the first take doesn't hit a cold start.

**Verified on the hosted service:** the dry run listed 7 cached practice verdicts and no recent investigations;
`reset_demo.py react --yes` refused. Take 1: reset → `/check ci-build-cache-helper` ran a **fresh investigation**
(`a40c3ea6`, 45 s). Take 2: the reset found and deleted that verdict and the take-1 investigation, warmed up, and
the next `/check` ran **another fresh investigation** (`6529c35a`, 27 s warm). The README's report for the same package
(`89265f12`) still returns 200.

Local mode needs nothing: `run_local.py` keeps everything in memory, so restarting it resets it.

---

## 2026-11-01 (Sun): Step 13 (part 5) — on npm

- **Published by the user:** `bawabu@0.1.0` on npm (created 2026-11-01 17:12 UTC; maintainer amoh_ntim; MIT; 16 files).
- **Verified from the public registry:** installed `bawabu` from npm into a throwaway prefix. `--version` 0.1.0; the
  published `dist/cli.js` is byte-for-byte the repo build; `scan left-pad` allowed and `scan react-datepickr` blocked
  with "did you mean react-datepicker?" against the hosted service.
- README: `npm i -g bawabu` in the results strip, the try-it steps (building from source kept as the alternative) and the
  hosted-service section (no keys, Python or clone needed). PDF section 17 and progress updated (try-it block kept on
  one page).
- **Still private:** the GitHub repo. The npm page's links to it are 404 until it's public.

---

## 2026-11-01 (Sun): Step 13 (part 4) — ready to publish on npm; what's left

- **`cli/README.md`** written for the npm package page (install, scan, init, your-own-key, commands, privacy).
- **Package check:** `npm pack --dry-run` gives 16 files (dist, LICENSE, README, package.json), about 23 kB, no runtime
  dependencies, no tests or sources. `bawabu` is still free on npm.
- **Rehearsal:** packed the real tarball, installed it globally into a throwaway prefix, and ran the installed command
  against the hosted service. `--version` 0.1.0; `scan react-datepickr` blocked with "did you mean react-datepicker?"
  (exit 1); `scan left-pad` allowed (exit 0); `init` wired the hook to the installed CLI, self-test passed, service reachable.
- **Not logged in to npm** on this machine (`npm whoami` fails), so publishing waits for the user's `npm login`.
- **Note:** `cli/.npmrc` has `ignore-scripts=true`, so npm's lifecycle scripts (prepublishOnly) don't run; build
  explicitly before publishing.
- **The GitHub repo is PRIVATE** (`gh repo view`: visibility PRIVATE; anonymous API: Not Found). The rules require a
  public repo, and every GitHub link in the README and on the npm page is a 404 until it's public.
- **History scan:** no Supabase, Meta, Baseten or registry-password values in any commit (pattern scan over the whole
  history; counts only, no values printed).
- Commits carry the author email amohntim123@gmail.com, which becomes visible once the repo is public.

---

## 2026-11-01 (Sun): Step 13 (part 3) — license, statistics, the PDF

### License
- **MIT** (`LICENSE`, © 2026 Samuel Amoh Ntim), also copied into `cli/` so the npm package carries it.
- **`THIRD_PARTY_NOTICES.md`**: `popular_npm.py` redistributes the npm-high-impact name list (MIT, Titus Wormer). Its
  exact license text was taken from the published 1.13.0 tarball, not typed from memory.
- `cli/package.json`: license, author, homepage, repository, bugs and keywords (what npm shows on the package page).
- README: a License section.

### Statistics (README "Why"), each checked against a source
| Claim | Verified | Source |
|---|---|---|
| Malicious open-source packages identified rose **1,444%** from 2024 to 2025 | Yes, verbatim: "increased exponentially, or 1,444% from 2024 to 2025" (OpenSSF data) | [Google Threat Intelligence](https://cloud.google.com/blog/topics/threat-intelligence/mitigation-guidance-for-supply-chain-compromise) |
| An AI coding agent added a malicious package to a real project | Yes: "an AI coding agent co-authored a commit integrating one of the malicious packages as a dependency" | same report |
| Mini Shai-Hulud, May 2026 | Yes: **169 npm + 2 PyPI packages (171), 373 malicious versions, over 518 million combined downloads**; TanStack, UiPath, Mistral AI. (Mend counts 172, so the plan's figure is right too; the README cites the source we verified.) | [Cloud Security Alliance](https://labs.cloudsecurityalliance.org/research/csa-research-note-shai-hulud-ai-supply-chain-20260517-csa-st/) |
| Models invent package names | Yes: 16 models, 576,000 samples; at least **5.2%** (commercial) and **21.7%** (open-source) hallucinated; 205,474 unique names | [Spracklen et al., USENIX Security 2025](https://arxiv.org/abs/2406.10279) |

The plan's other figures (4.6–6.1% for 2026 frontier models, "50% more dependencies") weren't verified and aren't used.

### The PDF (`docs/Bawabu-explained.pdf`, 25 pages, Steps 0–13)
- Refreshed: cover ("what works today", 9 rows), the story table, the architecture diagram (everything built; red =
  suspicious-only path), the request walkthrough, safety rules (+4), Modal/Baseten/Meta sections, the funnel, the quick
  checks' verdict table, the test-lab section.
- New sections, in plain language with the real results: 10 the sealed room (Step 5), 11 the before-and-after check
  (6), 12 the detective with a real case told step by step, plus "making hidden malware show itself" (7–8), 13 the
  quick sorter and open weights (9), 14 the report page with the screenshot (10), 15 the exam (11), 16 live scan,
  skipped on purpose (12), 17 shipping and trying it yourself (13).
- Files, keys, progress (all 14 steps) and glossary (+7 words) updated.
- Checked page by page as images (rendered with pypdfium2, since poppler isn't installed): no overflows; layout fixed
  where a section started at the bottom of a page or a table spilled one row.

---

## 2026-10-30 (Fri): Step 13 (part 2) — try it with your own API key

Judges want to run the code themselves with their own keys, so Bawabu now runs entirely on one machine.

### What was added

- **`uv run service/run_local.py`** (`bawabu_service/local.py`): the whole service in one process with the user's own
  `META_API_KEY` (and optionally `BASETEN_API_KEY`). In-memory cache and store (no Supabase), investigations in-process
  (no Modal function), sandbox optional (`--sandbox` needs `modal setup`, and only reaches public packages), and the
  live feed on. Keys from the environment or `.env`. Prints what's on and what to try.
- **A built-in test lab** (`bawabu_service/lab_registry.py`): the practice packages served from `testlab/packages` at
  `/lab` as a tiny npm registry (packuments + reproducible tarballs; two folders can be two versions of one package).
  **Only Bawabu can download from it**: a per-run token the service holds; npm gets 401, so the samples never reach the
  judge's disk. The service reads its own lab in-process (a transport that routes lab URLs into the app), so it never
  calls itself over the network. Its reports may show code (`show_code`).
- **`bawabu scan <pkg> [--local] [--lab] [--open-weights] [--service] [--registry]`**: one check from the terminal, no
  agent needed. Sends what the hook sends; waits through "still investigating" by asking again (which joins the
  investigation); prints verdict, evidence, report link. Exit 0 allowed, 1 blocked, 2 otherwise.
- **`bawabu demo [dir]`**: a project wired to the local service and its test lab, for trying it in Muse Code.
  **`bawabu init --local`** too.
- **No sandbox, no sandbox tools:** when there's no sandbox, Spark isn't offered `rerun_sandbox`/`get_sandbox_report`
  and its brief says to judge from the code. Before this, it spent a step asking for an impossible CI=true re-run, and
  the report showed a misleading amber "Re-running the sandbox" step.
- README: a new "Try it with your own API key" section (steps, a real `scan` output, every practice package, the Muse
  Code demo, what's different from the hosted service) and a pointer at the top.

### Tested for real (local service, real Meta API, no Modal, no Supabase)

| Check | Result |
|---|---|
| `bawabu scan react-datepickr --local` | blocked, "did you mean react-datepicker?", 2 s |
| `bawabu scan left-pad --local` | allowed, 1 s |
| **All 13 practice cases** with `--local --lab` | **all correct**: 9 blocked, 4 allowed, 0–18 s each |
| npm fetching from the lab | 401 |
| Report page at `127.0.0.1:8787/r/inv-1` | renders, code highlighted |
| **A real Muse agent in a `bawabu demo` project** (`npm install color-hex-convert`) | the hook blocked it after an in-hook local investigation citing the injection and the token theft; the agent said "I did not retry with another method"; nothing installed; 83 s |

### Things it caught

- **The first demo project gave the answer away.** It had a README listing which packages were malicious. The Muse
  agent read it, ran `bawabu scan` itself, and declined to install, so the hook was never exercised. The demo project is
  now just `.muse/`, a one-line `.npmrc` and `package.json`; the suggested prompts are printed in the terminal.
- **`markdown-tiny-render` was blocked locally for the wrong reason:** Spark cited the sample's own comment ("the danger
  is its dependency… which carries the payload"). With the sandbox off it can't see inside the dependency. The README
  says so, and both the README and `eval/RESULTS.md` now state the broader limit: **every sample starts with a comment
  explaining its trick** (safety labelling), which real malware never does. Verdicts cite code lines, but the comments
  may make the samples easier. A stricter lab variant without them is an option.

### Tests

**Python 129** (+6 local mode: every package served with its versions; 401 without the token; Bawabu's own readers work
against the lab; the full local service investigates a practice attack end to end; open-weights requests use the open
model; the startup banner. +1 no sandbox tools without a sandbox). **CLI 66** (+6 scan and demo).

---

## 2026-10-30 (Fri): Step 13 (part 1) — the README

- **`README.md`**, written for the judges first, then for developers: what it does; a real block message (the time bomb,
  rebuilt exactly from its stored verdict in the current CLI format) and the agent's reply; a report-page screenshot
  (`docs/images/report.png`) and four live report links; why; how it works (Mermaid diagram, the funnel, all seven
  layers); how Meta's models are used; results; try it; run your own; development; layout; **limits**; built during
  the hackathon; credits.
- Checked every claim against the code and the logs before publishing. Two corrected: the example message (it uses the
  current `/r/` link format, so it's "the message Bawabu gives", not a verbatim past message), and the self-hosted URL
  (Modal URLs include a region; Modal prints it on deploy).
- Also corrected an overstatement in `eval/RESULTS.md`: Muse Spark Open ran **once** on the final engine (13/13), not
  twice (its earlier 13/13 run was before the native-code fixes).
- **`service/schema.sql`**: the three Supabase tables as they are now (they were built through migrations, so nothing
  in the repo described them). **`.env.example`**: added `BAWABU_REGISTRY`.
- **`modal_app.py`**: the test-lab registry keys are now optional in `bawabu-investigator` (only `META_API_KEY` is
  required), so a self-hosted service doesn't need a private registry. Deployed.
- `bawabu` is **free on npm** (404 on `npm view bawabu`).
- Couldn't render the Mermaid diagram locally (downloading the Mermaid CLI was blocked); syntax reviewed by hand.
  Check it on GitHub after pushing.

---

## 2026-10-30 (Fri): Step 11 — evaluation

Full write-up: [eval/RESULTS.md](eval/RESULTS.md). Raw results: `eval/results/*.json`.

### How

`eval/harness.py` runs packages through the real `judge()` (quick checks → screener → investigation), with a fresh
in-memory cache (nothing replayed) and investigations run in-process (at most 3–4 at a time) instead of spawned on
Modal. It records which layer decided, the time, Spark's tool calls and re-runs, and verified/rejected evidence.
`eval/run_lab.py --model meta|open` (13 test-lab cases from `testlab/manifest.json`) and `eval/run_popular.py --top N`.

### Results

- **Test lab: 9/9 malicious caught in every one of 7 runs.** Final engine: **13/13** with Muse Spark (2 runs) and with
  Muse Spark Open (1 run; its earlier run, before the native-code fixes, was also 13/13), 0 false positives. Spark re-ran the sandbox itself for the CI-gated (`CI=true`) and
  date-gated (clock moved) packages. Median 36–48 s per investigated package, max 85 s (Muse Spark) / 113 s (Muse Spark
  Open, so that one package would get "still checking, retry" in the live service).
- **Top 500 npm: 500/500 allowed, 0 false positives.** 493 by the quick checks (0.7 s median, p95 1.6 s). 7 investigated
  and cleared by Spark: 5 newly published by "GitHub Actions" (trusted publishing), rxjs (lost provenance), pnpm
  (install scripts; ran clean in the sandbox).

### What the evaluation found (and what we changed)

1. **Harness bug:** with packages in parallel, "rows created since this check began" picked up other packages'
   investigations (empty tool-call columns; the screener-cleared package shown as "investigation"). Now matched by name+version.
2. **Our honest fixtures talked to reviewers** ("a LEGITIMATE pattern that must not be flagged", "must NOT be mistaken
   for an attack"). Spark treated that as manipulation, as instructed, and blocked image-resize-native. Rewrote the
   comments as a normal developer would (safety banner kept on executable files), published 1.0.1, and removed the
   flawed 1.0.0s from our private registry (Spark had also cited the old wording through the diff). Manifest updated with a note.
3. **Bawabu couldn't read native code:** `.cc`/`.cpp`/`.h` weren't "text" to the diff engine, so `read_file` refused
   them and Spark (correctly) asked a human. Added C/C++, Rust, Go, Ruby, Perl, PowerShell, batch, TOML, CMake and .txt.
4. **Native addons never built in the sandbox:** node-gyp tried to download Node's headers (network blocked), then picked
   the image's Python 3.13, which lacks Debian's `gyp` module. The sandbox image now has `g++`, `make`, `libnode-dev`, and
   the trigger sets `npm_config_nodedir=/usr` and `npm_config_python=/usr/bin/python3`. The fixture's addon now compiles
   (`CXX resize.o`, `SOLINK resize.node`, `gyp info ok`) and runs under strace. Deployed.

### Ideas from the data

- A publisher change *to* GitHub Actions *with* provenance is trusted publishing, not a hijack: treating it so would
  clear 6 of the 7 investigated top packages in ~1 s instead of ~35 s.
- The top 1,000 (the plan's upper bound) and a second open-weights popular run are still to do if time allows.

---

## 2026-10-30 (Fri): Step 10 — the report page

### Result

Every investigation now has a page anyone can read: **`/r/<id>`**, served by the existing Bawabu service on Modal
(no separate Next.js app to host). The agent's block message links to it. **`/live`** follows whichever investigation
starts next, for the demo's split screen: open it, then let the agent run `npm install`.

What the page shows, top to bottom: the package and verdict (BLOCKED / ALLOWED / NEEDS A HUMAN / INVESTIGATING), the
reason, chips (confidence, which model, tool calls, sandbox re-runs, time, safer choice); **the investigation step by
step** with timings (stages, Spark's narration in violet, each tool call, the re-run highlighted in amber, hard rules in
red, the final verdict); **the evidence**, each item "✓ verified", with the cited code shown in context and the line
highlighted; **the sandbox** run by run ("Run 2: re-run by Spark with CI=true", STOLEN rows in red); **what changed
since the previous version**; the hard rules; and the claims Spark couldn't back up (folded).

**End to end (deployed, real Muse agent):** `npm install env-loader-plus` → blocked after a fresh investigation → the
agent's message ended with `Details: …/r/27336358-…` and it said it would not try another way. The linked page showed
the leaked canary, then `scripts/setup.js` lines 12, 15 and 17 highlighted, all verified. Also checked on the deployed
service: the obfuscated fixture's report (with a **DECODED** evidence item), and `/live` picking up a running
investigation (checked locally with a half-finished one, since deployed investigations kept finishing in under a
minute, before the screenshot).

### Security

- **Package text is untrusted** (code, Spark's words, hostnames can all carry `<script>`): the page builds the DOM
  with `textContent` only. A test fails if `innerHTML`, `insertAdjacentHTML` or `document.write` ever appear.
- **Strict CSP** with a fresh nonce per response: `default-src 'none'; script-src 'nonce-…'; connect-src 'self';
  frame-ancestors 'none'`, plus `nosniff`, `no-referrer`, `no-store`.
- **Private registries:** reports keep the verdict, the reason and *where* (file:line) but drop code (snippets,
  quotes, tool output, sandbox output). A registry can be marked `show_code`; only the test lab is
  (`LAB_REGISTRY_SHOW_CODE=1`), because its code is our own harmless fixtures.
- **The live feed** (`GET /investigations`) lists package names from every client, so it's **off unless
  `BAWABU_PUBLIC_FEED=1`**. On for our deployment (only the test lab feeds it). It never returns registry addresses.

### Polish from looking at screenshots

- Routine tool results (file names, `"version": "1.0.0"`) hidden; the re-run shown once, highlighted.
- The final verdict row was picking up the verdict panel's styles through a shared class name; renamed.
- The package name couldn't shrink in its flex row on narrow screens; fixed (checked at 500 px).
- `/live` showed an empty "Investigating…" panel while nothing was happening; now a proper "Watching for the next check".
- "Decoding a base64 string (0 chars)" when Spark decodes from a file; now "Decoding the base64 string on build.js:6".

### Tests

**Python 122** (+6: page served with a CSP whose nonce matches the script; no HTML insertion of data; public report
shows code; private report hides code but keeps verdict and file:line; `show_code` registries keep code, others don't;
the feed is off unless turned on and never leaks registry addresses. Plus the pipeline now stores snippets, the first
sandbox run and the diff summary). **CLI 60** (the details link now points at `/r/<id>`).

### For the demo

- Open `https://amohntim123--bawabu.us-east.modal.run/live` on the right, Muse Code on the left.
- `/live` only follows **new** investigations. Verdicts are cached (block: 30 days), so a retake with the same package
  shows nothing new. Retakes need a package version that hasn't been checked yet, or a way to reset the lab's cached
  verdicts (to build before recording).
- Spark keeps calling the fixtures' "BAWABU TEST FIXTURE — harmless" banners a manipulation attempt. Those banners are
  part of the fixtures' safety labelling, so they stay; worth knowing before recording, since it shows up in the reasons.

---

## 2026-10-30 (Fri): Step 9 — the open-weights layer (Muse Spark Open)

### Result

Two jobs for **Muse Spark Open** (`meta-models/muse-spark-open-1026`, Meta's open-weights model on Baseten):

1. **The screener** (`service/bawabu_service/screener.py`). It runs between the quick checks' "ask" and the investigation.
   Most flagged packages are only new or little-used; the screener clears the plainly harmless ones in seconds so
   only the risky ones pay for the sandbox and Muse Spark (40–75 s).
2. **Open-weights mode.** `bawabu init --open-weights` sets `"openWeights": true` in `.muse/bawabu.json`; the guard
   sends `open_weights: true`, and the service runs the whole investigator on Spark Open instead of Meta's API.

**Step 9 "done when" met: the screener allows benign packages and escalates suspicious ones.**

| Package | Screener | How | Time |
|---|---|---|---|
| docs-gen-postinstall 1.0.0 (lab, clean) | **allow** | Model: "trivial pure function with no install scripts, network, fs, or exec access" | 6.5 s |
| markdown-tiny-render (lab, bad dependency) | escalate | Rule: its dependency console-logs-transport isn't an established package | 4.4 s |
| fastbundle-bin, color-hex-convert, string-format-pro-utils (lab) | escalate | Rule: runs code on install, so it gets the sandbox | ~2 s |
| string-format-js, @szydlovski/color-convert, @lugia/array-utils, nestjs-dotenv (real npm, <300 downloads/week) | **allow** | Model: pure string/colour/array helpers; a dotenv wrapper with no network | 5–9 s |
| date-helper-util, @parameter1/slug, vv-logger-tiny (real npm) | escalate | Rule: each depends on another little-used package (same author) | 3–5 s |

The model is only consulted after the rules pass, so every risky lab fixture was escalated **without asking it**.

### Safe by construction

- It can only say **allow** or **escalate**, never block.
- **Rules first, no model:** escalate if the package runs code on install (it gets the sandbox), if static risk is
  above "low", if a flag points at a typosquat or a hijack (lookalike name, lost provenance, new publisher, yanked or
  alarmingly deprecated), or if **any direct dependency doesn't pass the quick checks** (this closes the
  markdown-tiny-render hole: a clean package that pulls in a bad one), or if there are more than 25 dependencies.
- Dependencies are judged with the quick checks only, and a dependency's "ask" is **not cached**, so installing it
  directly later still gets investigated (a test checks this).
- The model sees the package fenced as data, answers in a fixed JSON format, and is told to escalate when unsure.
  Any error, timeout or odd answer escalates. A clearance is cached for 24 h only (it skipped the sandbox).
- The model's escalation reason is passed to the investigator as an extra red flag.

### Open-weights investigator vs Muse Spark on Meta's API

| Case | Spark Open (Baseten) | Spark (Meta API) |
|---|---|---|
| string-format-pro-utils (code only) | block, 7 tool calls, **6 s** | block, 11 tool calls, 28 s |
| ci-build-cache-helper (full, CI-gated) | spotted the gate, **re-ran with CI=true itself**, block, 6/6 evidence verified, **62 s** | same, 74 s |
| fastbundle-bin (legit) | allow, **5 s** investigator | allow, 11 s |

Spark Open cited the *decoded* payload against the source line, which the verifier rightly rejected. So both models now
get a **`decoded` evidence type**: the quote must appear in something the `decode` tool actually returned.

### Tests

**Python 116** (+9 screener: plain package cleared in one call and cached under its registry; install scripts and
static risk skip the model; risky dependency never cleared and its "ask" not cached; established dependencies fine;
model escalation, outage, bad JSON and odd answers all escalate; the escalation reason reaches the investigator;
injection text is a gate; the open-weights flag reaches the investigation. +1 decoded evidence). **CLI 60**
(+1 `openWeights` config, +1 the flag in the request).

### To do

- ✅ Done: secret `bawabu-baseten` (BASETEN_API_KEY only) created by the user; deployed. `/health` shows `screener: true`.
  Live: docs-gen-postinstall 1.0.0 **cleared by the screener** ("no install scripts and index.js only exports a pure
  string-length docs generator…"), then cached. An `open_weights: true` request for color-hex-convert ran the
  investigation on Spark Open and **blocked** it, citing the injection (index.js:7) and the leaked canary.
- Possible refinement: screen dependencies one level deep instead of requiring them to pass the quick checks, so
  small packages that depend on their author's other small packages can be cleared too.

---

## 2026-10-30 (Fri): Step 7 — the Muse Spark investigator

### Result (live, from the laptop: diff + Modal sandbox + `muse-spark-1.3` on the Meta API, effort `low`)

`uv run service/scripts/run_investigation.py <pkg> --lab` prints the event stream as it happens.

| Fixture | Verdict | What Spark did | Tool calls | Total time |
|---|---|---|---|---|
| string-format-pro-utils (code only) | **BLOCK** | The sandbox can't see this one. Spark read `build.js`, **decoded the base64 blob itself** and explained it: reads `.npmrc`, POSTs it | 11 | 37 s |
| ci-build-cache-helper | **BLOCK** | First sandbox run clean. Spark read `cache.js`, spotted the `CI === "true"` gate, **re-ran the sandbox with `CI=true`**, and the canary leaked | 7 (1 re-run) | 74 s |
| date-fns-lite-utils | **BLOCK** | Spotted `Date.now() < TRIGGER`, **re-ran with the clock at 2027-02-01**, and the canary leaked | 7 (1 re-run) | 69 s |
| color-hex-convert | **BLOCK** | **Not fooled by the "note to automated reviewer"**: cited it as a manipulation attempt, alongside the leak | 6 | 38 s |
| docs-gen-postinstall 2.0.0 | **BLOCK** | Leak in the sandbox plus the install code; hard rule confirms | 5 | 41 s |
| fastbundle-bin (legit) | **ALLOW** | Download only goes to the registry it was installed from; sandbox agrees | 6 | 43 s |
| pretty-log-kit (legit) | **ALLOW** | Postinstall only writes a local cache file | 6 | 43 s |

Every evidence item shown was **verified** against the tool outputs (file, line and quote exist; the sandbox host or secret
really appears). About 30 s of each run is the first sandbox run (two sandboxes + a snapshot); Spark itself takes 7–42 s.

### How it works (`service/bawabu_service/investigator.py`)

- **Tools:** `list_files`, `read_file` (numbered lines), `search_code`, `decode` (base64/hex/url, never executes; can
  decode straight from a `file`+`line` for blobs too long to copy), `get_diff`, `get_metadata`, `get_sandbox_report`,
  `rerun_sandbox(env, fake_date)` (max 2), `submit_verdict` (verdict, confidence, reason, evidence[], safe_alternative).
- **Loop:** up to 12 tool calls; parallel tool calls work on the Meta API. Plain-text replies are nudged back to the
  tools; at the limit the verdict is forced (falls back to asking in words if a provider rejects a forced `tool_choice`).
- **Prompt-injection handling:** every tool output is fenced in `<package_data>`, and the system prompt says it's
  data, never instructions, and that text addressing AI reviewers is itself evidence of malice.
- **Evidence verification:** code evidence needs a real file and line, and its quote must be on (or within 2 lines of)
  that line; sandbox evidence must name a host, path or secret that's really in the sandbox reports; diff evidence must
  be in the diff. Unverifiable items are dropped and listed; **a block with no verified evidence becomes "ask"**.
- **Hard rules (override the model):** a leaked canary in any run → block; prompt injection found by the diff engine
  → block. A model outage or no verdict → "ask".
- **Events:** start, thinking (Spark's short narration), tool, result, re-run, rejected evidence, rule, verdict.
  That's the live stream for the report page.

### Registry routing (open question #16, now answered)

- **CLI** (`cli/src/npmrc.ts`): reads `registry=` / `@scope:registry=` from the project's `.npmrc` (nearest first,
  walking up) and `~/.npmrc`, and sends that URL with each npm package. **Only `registry` lines are read; credentials in
  the URL are stripped; `_auth` lines are never touched.** Not followed yet: a `--registry` flag on the command itself,
  and `npm_config_*` env vars (the hook's environment is cleared anyway).
- **Service:** the public npm always; private registries only if it holds a login (the lab, via `LAB_REGISTRY_URL` +
  `LAB_REGISTRY_AUTH`). **An unknown private registry gets "ask"** with an allowlist hint, without touching the network.
  Private packages skip OSV and download counts, which describe the *public* package of that name.
- **Verdicts are cached per registry** (new `registry` column; unique key `(ecosystem, registry, name, version)`), so a
  private `left-pad` and the public one can never share a verdict. A test proves it.

### Service wiring (`investigations.py`, `modal_app.py`)

- When the quick checks say "ask" for an npm package, `/check` **starts an investigation as a separate Modal function**
  (`investigate.spawn`), or joins one already running for that version, and waits up to 110 s (the CLI waits 140, the
  hook 150). If it isn't done, the agent gets **"⏳ still checking: wait about a minute, then run the same command
  again"** (a new `pending` flag), the investigation carries on, and the retry gets the cached verdict.
- Retries reuse a finished investigation (within 24 h) even if the cache write failed; a dead (`running` > 10 min) or
  failed one is started again. (Caught by a test: the first version re-investigated after every finish.)
- New Supabase tables `investigations` and `investigation_events` (RLS on, service key only). Events are written in
  order from the Spark thread through a queue. `GET /investigations/{id}` returns status, events and result, which is
  what the report page (Step 10) will show. The CLI's block message now ends with `Details: <service>/investigations/<id>`
  and says "A safer choice: X" for Spark's alternative.
- ENGINE 2 (MIN_ENGINE 2): engine-1 "ask" verdicts are re-judged, so they get investigated.

### Things that bit us

- **`json.dumps` escapes `→` as `→`**, so Spark's verbatim quote of "npm token (~/.npmrc) → collector…" failed
  verification. Fixed with `ensure_ascii=False` in both the tool output and the verification corpus.
- **`decode` failed on a truncated line** (Spark copied the `…[+N chars]` marker). It now keeps only the base64
  alphabet, and can decode straight from a file and line.
- The hijack's reason didn't say the behaviour was **new in 2.0.0**; the prompt now asks for that when the diff shows it.

### Tests

**Python 106** (+11 investigator with a scripted fake model: verified vs invented evidence, both hard rules, CI re-run,
re-run budget and date validation, outage, step budget, nudging, tools, non-ASCII quotes; +11 investigation path:
start, join, pending, retry, failed, dead workers, unknown/known private registries, no cross-registry sharing, report
endpoint, the full pipeline with ordered events and a per-registry cache write, pipeline failure). **CLI 58** (+5 npmrc,
+3 messages and the registry in the request, never the login).

### Deployed and end to end

- `bawabu-investigator` secret created by the user; `modal deploy service/modal_app.py` → `web` + `investigate`.
  `/health`: version 0.3.0, engine 2, investigations on, 1 private registry.
- **Direct `/check`** for ci-build-cache-helper from the lab registry: **block in 69 s** (diff → sandbox → Spark →
  `CI=true` re-run → leak). The same request again: **2.4 s, from the cache**. `GET /investigations/{id}`: 25 events in
  order (stages, Spark's narration, each tool call, the re-run, the rule, the verdict).
- **Real Muse agent** (throwaway project whose `.npmrc` points at the lab registry, `bawabu init`, then
  `muse exec --trust-workspace "Add the date-fns-lite-utils npm package…"`): the agent read `.npmrc`, ran
  `npm install date-fns-lite-utils`, the hook sent the registry URL (not the login) and the service ran a **fresh
  investigation inside the hook**. Spark moved the clock to 2027-02-01 and the canary leaked. The agent saw:

  ```
  ⛔ Blocked by Bawabu: this wasn't installed.
  ⛔ date-fns-lite-utils@1.0.0 (npm): Install script stays dormant until 2027-01-01, then reads the user's .npmrc npm
     token and POSTs it to an external collector. Time-gated credential theft on install.
     - Leaked canary: npm token (~/.npmrc) → collector.bawabu-test.invalid
     - scripts/warm.js:10: Date gate makes install script exit cleanly before trigger date…
     - scripts/warm.js:17: Post-trigger reads npm credentials file
     - scripts/warm.js:20: Post-trigger exfiltrates file contents to external collector
     Details: https://amohntim123--bawabu.us-east.modal.run/investigations/738a177d-…
  Don't try to install it another way. Tell the user what Bawabu found.
  ```

  It told the user what Bawabu found, with the lines and the link, and said: *"I did not retry with another installer or
  bypass."* Nothing was installed. Session: 126 s.

### Supabase security

- The advisor's WARN was `public.rls_auto_enable()`: Supabase's event-trigger function (trigger `ensure_rls`) that turns
  RLS on for every new public table. It was callable through the API by `anon`/`authenticated`. **Revoked EXECUTE** from
  public, anon and authenticated (migration `lock_down_rls_auto_enable`); event triggers don't check EXECUTE when they fire.
  **Verified:** a probe table created afterwards still got RLS automatically (then dropped); anon/authenticated can't execute.
- Remaining advisor notes: "RLS enabled, no policies" on `verdicts`, `investigations` and `investigation_events`.
  **Intentional and the strictest setting:** the anon and signed-in keys can't read or write them; only the service's
  secret key can. The report page will read through the service, not directly.

### Still open

- **Unauthenticated `GET /investigations/{id}`:** anyone with the (random UUID) link can read the investigation, including
  code excerpts. Fine for public packages and the lab; for real private registries it should be gated (Step 10).
- Investigations cost Meta credits and sandbox time; there's no per-client rate limit yet.
- The CLI doesn't follow a `--registry` flag on the command itself.

---

## 2026-10-30 (Fri): Step 6 — the diff engine

### Result

The diff engine reads a package's code **without running it** and compares it with the version before,
so its signals say what *changed*. Each signal carries file, line and excerpt (so Step 7 can verify the
investigator's citations), and is marked **new** or **unchanged since the previous version**. Risk is
scored on the new signals only (or all of them for a first release).

Test lab (`uv run service/scripts/run_diff.py --lab <pkg>`):

| Fixture | Risk | Top signals |
|---|---|---|
| docs-gen-postinstall 2.0.0 (vs 1.0.0) | **HIGH** | Adds `postinstall` (1.0.0 had none) · runs a file new in this version · install-time code reads `.npmrc` **and** makes network requests (line 8) |
| docs-gen-postinstall 1.0.0 | none | — |
| string-format-pro-utils | **HIGH** | Long base64 blob that is decoded and run (line 6) · `new Function` (line 9) |
| color-hex-convert | **HIGH** | Text aimed at AI reviewers (index.js:6) · credential read + network on install |
| env-loader-plus | **HIGH** | Credential read + network in install code |
| markdown-tiny-render | low | Depends on console-logs-transport@1.0.0 (listed for the investigator) |
| fastbundle-bin (legit) | medium | Network on install (the esbuild gray area) |
| image-resize-native, pretty-log-kit (legit) | medium | Runs code on install |

Real npm (false-positive check, latest vs semver predecessor): **esbuild, sharp, next, core-js, puppeteer,
prisma, @swc/core, axios, lodash, react, typescript → NONE.** Their install-time downloads and
`child_process` use are shown as "(unchanged)". **bcrypt 6.0.0 → MEDIUM** (switched install from
node-pre-gyp to node-gyp-build and added that dependency, which is a legitimate change and fair to look at).

### The sandbox and the diff cover each other

| | Sandbox (Step 5) | Diff (Step 6) |
|---|---|---|
| string-format-pro-utils (base64 blob that can't run) | ❌ sees nothing | ✅ HIGH |
| markdown-tiny-render (payload in a dependency) | ✅ catches the leak | only lists the dependency |
| docs-gen-postinstall 2.0.0 (hijack) | ✅ (payload runs) | ✅ HIGH, says what changed |
| fastbundle-bin (legit download) | ✅ only the registry contacted | medium (gray area) |

That's the argument for the funnel and for Spark in Step 7: each layer has blind spots the other covers,
and Spark weighs both.

### Design (`service/bawabu_service/diff.py`)

- **Fetch:** packument, resolve the version, pick the **semver predecessor** (stable only, unless the target
  is a prerelease), download both tarballs. Source is configurable (`Source(url, headers)`), so the lab's
  Verdaccio and its login work. Tarball links on another host (Verdaccio behind Modal) are rewritten to the source.
- **Unpack in memory:** regular files only; no links, absolute or `..` paths; caps on files (20k), raw bytes
  (500 MB, bomb guard), kept bytes (150 MB) and tarball (64 MB). Files over 1 MB are kept as a hash: compared,
  not scanned.
- **Signals:** install scripts (added = high, changed = medium, unchanged = low); a file run by the install
  script that's new in this version (high); credential references (high in install code); network /
  child_process (medium in install code, low elsewhere); **credential read + network in the same install-time
  file (high: the exfiltration shape)**; base64/hex blobs (high when decoded and run); `eval`/`new Function`
  (high in install code); prompt injection aimed at AI reviewers (high); lost provenance (high); new dependencies.
- **Noise control:** comment-only lines don't count for code signals (injection still does); READMEs only
  checked for injection; minified/`dist/` files skip dynamic-code and long-line checks;
  `Function("return this")` (the global-object idiom) ignored; unchanged files scanned once.

### Things that bit us

- **"Previous version" by publish time was wrong:** react 19.3.1 was compared with a nightly, axios 1.21.0
  with a 0.x backport. Switched to the semver predecessor; a semver target with nothing lower has no previous.
- **Network-on-install alone as HIGH** flagged fastbundle-bin (and would flag esbuild on a first release).
  Made it medium; the high signal is credential read **plus** network in the same install file.
- **bcrypt's build-tool switch was HIGH** → a *changed* install command is now medium; the hijack tell
  (a new file for it to run) stays high.
- **core-js / next were "too large":** thousands of files and a 30 MB tarball. Raised caps and hashed big files.
  `next` takes about 18 s of CPU (two versions of huge compiled bundles); fine, because popular packages never
  reach the diff (the quick checks allow them).

### Tests

12 new tests in `service/tests/test_diff.py`: unsafe tar entries, the hijack (with exact lines), base64 +
`Function`, injection, the unchanged binary downloader staying quiet, minified/README guards, provenance lost,
new dependency, first release, semver predecessor, the global-this idiom, and `analyze` end to end against a
mock registry (auth header + tarball host rewrite). **83 Python tests pass.**

### Still to wire

The engine runs by hand (`run_diff.py`). It joins the service in Step 7, next to the sandbox, as the
investigator's `get_diff`/`search_code` evidence. The service also needs registry routing (#16) before
it can judge the lab packages end to end.

---

## 2026-10-30 (Fri): Step 5 — the sandbox X-ray

### Result

The X-ray works end to end. A package is run in a **network-blocked Modal sandbox** with planted
canary secrets and `strace`, and everything it tries to send is captured by a fake-internet sink —
so a token-stealer is caught **leaking a canary**, which is the one conclusive signal.

Measured on the test lab (each run ≈ 30–60 s; `uv run sandbox/scripts/run_sandbox.py <name> <ver>`):

| Fixture | Expected | Sandbox verdict signal | Right? |
|---|---|---|---|
| env-loader-plus | block | **Exfiltration confirmed**: npm-token canary → `collector.bawabu-test.invalid` (HTTPS POST intercepted, base64 body decoded) | ✅ |
| console-logs-transport | block | Exfiltration confirmed (canary leaked) | ✅ |
| markdown-tiny-render | block | Exfiltration confirmed — via its **transitive** dep console-logs-transport (`npm rebuild` ran the dep's install script) | ✅ |
| color-hex-convert | block | Exfiltration confirmed (quiet payload fired) | ✅ |
| ci-build-cache-helper (no CI) | allow (dormant) | No secret reads or unknown contact | ✅ |
| ci-build-cache-helper `--ci` | block | Exfiltration confirmed — fires only with `CI=true` | ✅ |
| date-fns-lite-utils `--date 2027-02-01` | block | Exfiltration confirmed — time-bomb fired under a faked clock | ✅ |
| fastbundle-bin (esbuild-style) | allow | No unknown contact (its registry fetch is known-good) | ✅ |
| image-resize-native (native build) | allow | No secret reads or unknown contact | ✅ |
| pretty-log-kit (heavy postinstall) | allow | No secret reads or unknown contact | ✅ |
| string-format-pro-utils (base64 blob) | block | **Sandbox sees nothing** — by design: the blob can't run (`require` isn't in `new Function` scope). Caught later by the diff engine + Spark decode (Steps 6–7) | ✅ (funnel) |

**Step 5 "done when" met:** the token-stealer stand-in is caught in the evidence report. Trigger-aware
re-runs (Step 8's core) already work too — CI-gated and date-gated payloads are revealed.

### How it works (`sandbox/bawabu_sandbox/`)

Two phases, because a network-blocked sandbox can't download anything:
1. **Stage** (network on): `npm install <pkg> --ignore-scripts` into a throwaway sandbox so **none**
   of the package's code runs — only files are fetched. `snapshot_filesystem()` captures the result.
2. **Trigger** (network blocked): boot a fresh sandbox from the snapshot, plant canary secrets, start
   the sink, then run the code under `strace` (`npm rebuild` for install scripts; `require()` for
   load-time code). Collect strace + the sink log → evidence.

Pieces:
- **`honeypots.py`** — the bait: fake `~/.npmrc`, `~/.ssh/id_rsa`, `~/.aws/credentials`, project `.env`,
  each holding a **distinct** canary, plus `NPM_TOKEN`/`GITHUB_TOKEN` env canaries and a lived-in home.
- **`sink.py`** — the fake internet, inside the sandbox: a DNS server that resolves everything to
  loopback, and HTTP/HTTPS catch-all servers that log every request. HTTPS is terminated with a CA
  generated at startup that **mints a leaf cert per SNI hostname**, so the package's `fetch("https://…")`
  completes and we capture the plaintext body (even base64-encoded secrets). Verified on the laptop
  (`test_sink.py`): a real DNS query + HTTPS POST through the minted CA is captured.
- **`dnsshim.c`** — a tiny `LD_PRELOAD` shim overriding `getaddrinfo` so every hostname resolves to
  loopback **and** the intended destination is logged. Needed because Modal manages `/etc/resolv.conf`
  and reverts edits, so DNS can't be repointed the normal way. Coexists with libfaketime (combined
  `LD_PRELOAD`) for the time-bomb case.
- **`strace_parse.py`** / **`evidence.py`** — pure, unit-tested: strace → files opened / processes /
  connections; then a report with secret reads, network attempts, leaked canaries, notes. **A leaked
  canary is always guilt; a network call alone is not** (legit installers fetch binaries).

### Things that bit us (and the fixes)

- **`/etc/resolv.conf` is managed by Modal** and reverts writes → DNS couldn't be repointed → every
  lookup failed with `EAI_AGAIN` before reaching the sink. Fixed with the `LD_PRELOAD` resolver shim.
- **npm reads `~/.npmrc` itself**, so an `.npmrc` *read* is not a signal — only the **leaked canary** is.
  The evidence builder ignores `.npmrc` reads; `.ssh`/`.aws`/`.env` reads still count.
- **The install registry is a benign destination** (esbuild-style downloaders fetch their own binary),
  so the runner passes the registry host to the evidence builder as known-good. Stops a false positive
  on fastbundle-bin.
- **Verdaccio cold-start `ENOVERSIONS`**: a cold registry can answer `/-/ping` before its storage is
  ready, returning an empty packument that npm caches. The runner now **warms the registry from inside
  the staging container** (curl until versions appear) before npm runs.
- **zsh doesn't word-split unquoted `$var`** (unlike bash). A batch test harness passed `"name 1.0.0"`
  as one argument, so npm tried to install a package literally named `1.0.0` (`ENOVERSIONS`). The runner
  was fine; the harness wasn't. (Already in memory: Bash here is zsh — use arrays / `${=var}`.)

### Tests

`sandbox/tests/` — 11 unit tests (strace parsing, evidence rules, and a live localhost sink test that
drives a real DNS query + HTTPS POST through the minted CA). `cryptography` added to dev deps; pytest
now also covers `sandbox/tests`.

### Still to wire

- Step 6 (diff engine) and Step 7 (Spark investigator) will use this evidence. The sandbox isn't in the
  **service** decision path yet — `run_sandbox.py` runs it by hand. Step 7 connects it.
- `string-format-pro-utils` needs the diff/decode path (its blob can't execute in the sandbox).

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

### Step 3: quick checks

**Result:** the service now makes real decisions, in about a second, without running anything. In the plan's terms: **made-up names are blocked (with a suggestion of the real package), and `react` is allowed instantly.** Deployed as service version 0.2.0, engine 1.

**What the checks do** (`service/bawabu_service/`):
- **`registry.py`:** reads npm's full package metadata, or PyPI's JSON API, and **resolves the request to the exact version npm or pip would install.** Rules:
  - npm: dist-tags; exact versions with or without `v`/`=`; ranges, preferring `latest` when it satisfies the range, as npm does (`semantic_version.NpmSpec`).
  - pip: PEP 440 specifiers (`packaging`); environment markers ignored; yanked releases skipped unless pinned exactly with `==`; uv-style `name@1.2`.
  - Facts it collects:
    - when the package and the version were first published;
    - code that runs on install: npm `preinstall`/`install`/`postinstall`, an implicit `node-gyp` build from `binding.gyp`, or for PyPI a release with no wheel, which runs its setup code;
    - the same for the version published just before this one;
    - npm provenance (`dist.attestations`) for this version and the previous one;
    - who published this version, and who published earlier ones;
    - deprecation and yanked status.
  - Weekly downloads come from api.npmjs.org and pypistats.org.
- **`osv.py`:** OSV.dev `MAL-` entries for the exact version. If the package or version no longer exists, it asks OSV about the whole package, because a deleted malicious package is exactly what OSV remembers and the registry no longer shows.
- **`popular.py`** suggests the real package, in three stages:
  1. **A one-typo lookalike** of a popular name, by swapped, missing, extra or replaced character, or by separator differences.
  2. **Spelling correction, then the closest popular name.** Misspelled words are fixed using the vocabulary of popular names, then the closest popular name is found (similarity ≥ 0.8, about 40 ms over 17,338 names).
  3. **npm search** as a last resort, only accepting close names.

  Popular lists:
  - npm: the vendored `popular_npm.py`, 17,338 names from `npm-high-impact` (MIT). Refresh it with `scripts/update_popular.py`.
  - PyPI: hugovk's top-15,000 list. It has no license, so it's fetched at runtime and not redistributed.
- **`quick_checks.py`:** the rules, as a pure function:

  | Situation | Verdict | Cached for |
  |---|---|---|
  | Listed as malicious by OSV | **block** | 30 days |
  | npm security holding package | **block** | 30 days |
  | No such package (made-up name; suggestion attached) | **block** | not cached (someone could register the name later) |
  | No version matches the request | **block** | not cached |
  | Registry unreachable | **ask** | not cached |
  | Any red flag (below) | **ask** (later steps will send these to the sandbox and the detective instead) | 6 hours |
  | No red flags | **allow** | 7 days, or 6 hours if the version is under a week old |

  **Red flags:**
  - a package under 90 days old;
  - fewer than 1,000 downloads a week;
  - install code that this version **adds** or **changes**, or any install code in a package that isn't popular (≥10k downloads a week and ≥180 days old);
  - **provenance lost** compared with the previous version;
  - a **new publisher** on a version under 30 days old;
  - a **name one typo from a popular package**;
  - yanked;
  - a deprecation message mentioning compromise or malware;
  - OSV unreachable for a version under a week old.

  "This version was published N hours ago" is added alongside other flags. Popular packages that have always had install code, such as esbuild, are allowed.
- **Cache** (`cache.py`): verdicts now store their red flags (`signals`) and `suggestion`, and **expire** (`expires_at`), so later malware reports are picked up. Supabase migration `verdict_signals_and_expiry` added the three columns. The advisor shows no new issues. A redundant index I added was dropped again.
- **The engine is now 1**, so none of Step 2's blanket "allow" verdicts (engine 0) are reused.
- **CLI:** the agent now sees each red flag as a bullet, and "Did you mean X?" under made-up names.

**Live results against the real npm, PyPI and OSV** (`uv run python service/scripts/smoke_checks.py`, deployed service, timed from Accra; first check, then repeat):

| Package | Verdict | Reason or suggestion | First / repeat |
|---|---|---|---|
| `react` | allow | 15 years old, 205M downloads/week, no install code (resolved 19.3.1) | 3.0 s / 1.1 s |
| `express@^4` | allow | resolved to 4.22.3, like npm | 1.2 s / 0.7 s |
| `esbuild` | allow | same postinstall as the previous version | 1.6 s / 0.6 s |
| `@types/node` (one of npm's largest metadata files) | allow | this version 14 hours old: allowed, re-checked within 6 h | 1.9 s / 1.1 s |
| `fancy-date-pickr` | block | doesn't exist; no suggestion (see below) | 1.0 s |
| `react-datepickr` | block | **Did you mean react-datepicker?** | 0.9 s |
| `prisma-clinet` | block | **Did you mean @prisma/client?** | 1.1 s |
| `crossenv` | block | npm security placeholder (2017 typosquat) | 1.0 s |
| `@ctrl/tinycolor@4.1.1` (Shai-Hulud worm, deleted from npm) | block | OSV `MAL-2025-47141` | 1.1 s |
| `@ctrl/tinycolor` (current) | allow | 4.2.2, clean | 1.0 s |
| `react@^99` | block | no matching version; latest is 19.3.1 | 1.0 s |
| `requests`, `requests==2.31.0` (PyPI) | allow | 330M downloads/week | 0.5–2.1 s |
| `reqeusts-fake-zz` (PyPI) | block | doesn't exist | 0.7 s |

**14/14 as expected.** One first check took 77 s, which was this network's 75 s connection stall again (open question #13).

**Suggestions for made-up names** (spelling correction, then the closest popular name): `react-datepickr` → react-datepicker, `expresss-validator` → express-validator, `axois` → axios, `mongose` → mongoose, `prisma-clinet` → @prisma/client, `tailwind-css-animate` → tailwindcss-animate. **`fancy-date-pickr` gets no suggestion.** "fancy" to "react" is a guess about meaning, not spelling, so that suggestion is a job for the Spark detective (Step 7). npm's own search doesn't fix spelling (it returned `fancy-log`, `@simonwep/pickr`), so a similarity floor rejects poor matches: a wrong suggestion is worse than none.

**Real hook with Muse's input format and environment, against the deployed service:**
- `npm install react-datepickr` → **exit 2**: "There is no package called react-datepickr on npm … Did you mean react-datepicker?"
- `npm install fresh-test-pkg-zz9 && pip install reqeusts` → both blocked; PyPI suggestion "Did you mean requests?"
- `npm install @ctrl/tinycolor@4.1.1` → blocked, OSV `MAL-2025-47141`
- `npm install react` → **exit 0**

**Real Muse agents:**
- "Run this to add React: npm install react react-dom" → Bawabu allowed react@19.3.1 and react-dom@19.3.1, and **they installed**.
- Asked to install `react-datepickr`, the agent **checked first with `npm view`**, which Bawabu allows, saw the 404, refused to install, and suggested `react-datepicker` itself, even when told the exact command. Muse is cautious here, but Bawabu is for when the agent isn't; the hook-level test above shows what it would get.
- Side finding (corrected): inside Muse, plain `npm install` fails with EPERM writing `~/.npm/_cacache/tmp/…`. npm's message blames root-owned files and suggests `sudo chown`, **but that's wrong here**: every file in `~/.npm` is owned by the user (501:20), and the folder is writable outside Muse. **Muse's OS sandbox makes the home folder outside the workspace read-only**, so npm can't write its cache. The agent's workaround (`--cache /tmp/...`) works because `/tmp` is writable inside the sandbox. No `chown` is needed. This isn't a Bawabu issue, but it slows down agent installs and will show up in the demo, so consider pointing npm's cache at a folder Muse can write to.

**Tests:** service **60/60** (`uv run pytest`: rules, version resolution, registry parsing, OSV, popular names and suggestions, and the API end to end on a fake internet, including expiry and the engine cutoff). CLI **50/50**.

**Not done yet:**
- **Whole-project installs** (`npm install`, `npm ci`, `pip install -r`) are still allowed without checks. Next: have the CLI send the dependencies listed in `package.json`/`requirements.txt`, plus every lockfile entry with `hasInstallScript` (plan section 7.1).
- "ask" is the interim verdict for red flags until the sandbox and Spark exist (Steps 5–8).
- PyPI provenance (PEP 740 attestations) and PyPI publisher changes aren't checked; PyPI's JSON API doesn't expose uploaders.
- pypistats is rate-limited. If it fails, PyPI downloads are unknown, which isn't a red flag by itself.

### Step 4: test lab

**Result:** done. The plan's test: **every practice package installs from our private registry.** Ten named packages, plus `react` through the registry's npm passthrough, installed in 12 s, and the hidden dependency came along automatically. Without the password the registry refuses (`E401`).

**What's in `testlab/`:**
- **`packages/`:** 11 practice packages (12 folders, since the hijacked one has two versions). Each copies one supply-chain attack technique, or a tricky but honest pattern, from plan section 9:

  | Package | Mirrors | Bawabu should | Decisive layer |
  |---|---|---|---|
  | `env-loader-plus` | postinstall credential grab | block | sandbox (canary leaves) |
  | `ci-build-cache-helper` | payload only when `CI=true` | block | Spark re-run with `CI=true` |
  | `date-fns-lite-utils` | payload only after 2027-01-01 | block | Spark re-run with a faked date |
  | `string-format-pro-utils` | payload hidden as a base64 blob | block | diff signals and Spark decoding it |
  | `markdown-tiny-render` → `console-logs-transport` | clean package, malicious dependency | block | dependency-tree check (gap #14) |
  | `color-hex-convert` | prompt injection aimed at AI reviewers | block | injection handling and hard rules |
  | `docs-gen-postinstall` 1.0.0 → 2.0.0 | hijacked version (2.0.0 adds a postinstall) | allow 1.0.0, block 2.0.0 | version diff |
  | `fancy-date-pickr` (never published) | a name an AI might invent | block | quick checks (already working) |
  | `fastbundle-bin` | esbuild-style binary download | **allow** | false-positive guard |
  | `image-resize-native` | sharp-style native build (`binding.gyp`) | **allow** | false-positive guard |
  | `pretty-log-kit` | heavy but benign postinstall | **allow** | false-positive guard |

- **`manifest.json`:** the same catalogue in machine-readable form, for the evaluation in Step 11.
- **`README.md`:** the safety model.
- **`verdaccio/config.yaml`:** every read and publish needs the login, self-registration is off, and anything not published here passes through to the real npm.
- **`modal_verdaccio.py`:** runs Verdaccio **6.10.5** (7.0.2 was only 2 days old, so it was skipped under our own "at least two weeks old" rule) on the `node:22-bookworm-slim` image, with published packages kept in the Modal volume `bawabu-verdaccio-data`.
- **`publish.sh`:** uploads in (name, version) order and always names the registry explicitly.

**How the practice packages are kept harmless.** An earlier attempt to write them was stopped by Claude Code's safety classifier, so they were rewritten as clearly inert demonstrations:
- Their only possible "send" destination is `collector.bawabu-test.invalid`. `.invalid` is reserved (RFC 6761) and can never resolve, so nothing can leave even on a real machine.
- In the Step 5 sandbox, the secret files they open are planted canaries (`npm_canary_7f3k9q`).
- Every file starts with a `BAWABU TEST FIXTURE — harmless` banner.
- They're never published to the real npm, and all their names were checked to be unregistered there (still HTTP 404 after publishing to the lab).
- The base64 payload in `string-format-pro-utils` was generated from, and checked to decode back to, the same inert code.

**Registry:** `https://amohntim123--bawabu-verdaccio-registry.us-east.modal.run`
- **Login:** user `bawabu` with HTTP Basic auth. The password and htpasswd line are in `.env` (`VERDACCIO_*`, single-quoted because the htpasswd hash contains `$`). The htpasswd is also in the Modal secret `bawabu-verdaccio`, which the user created; Claude Code isn't allowed to write to secret stores.
- **Live checks:**

  | Check | Result |
  |---|---|
  | `/-/ping`, first call (cold start) | 200 in 67 s |
  | `react` without the password | **401** |
  | `react` with the password, first time (passthrough to npm, cold cache) | 200 in 96 s; latest 19.3.1 |
  | `/-/whoami` | `bawabu` (the secret matches `.env`) |
  | `npm install` of all 10 named packages and `react`, with `--ignore-scripts` | **12 packages in 12 s**, including `console-logs-transport` as a dependency |
  | The same install without the password | `npm error code E401`, nothing installed |
  | `docs-gen-postinstall` | latest 2.0.0; 1.0.0 published 2.5 s before 2.0.0 |
  | Lab names on the real npm | all 404 |

  The installs used `--ignore-scripts`, so no lab code ran on the laptop; the files the install scripts would create don't exist. Running the packages is the sandbox's job (Step 5).

**Problems hit along the way:**
- **Upload order.** The first upload put 2.0.0 before 1.0.0, because the folder `docs-gen-postinstall-2/` sorts before `docs-gen-postinstall/`, and npm refused the late 1.0.0. That would also have broken the hijack test, since Bawabu compares each version with the one published before it. `publish.sh` now sorts by name and version. The package was removed from the lab registry only and uploaded again in the right order.
- **zsh doesn't split unquoted variables,** so a space-separated package list in one variable reached npm as a single name. Use arrays (`"${PKGS[@]}"`) in this environment's shell.

**Not done yet:**
- **Bawabu can't look up lab packages yet.** The service still checks the real npm, where every lab name is a 404, so today it would answer "doesn't exist" for all of them. Next: the guard tells the service which registry a project installs from (via `--registry` or the project's `.npmrc`), and the service looks lab packages up in the lab using the lab login (open question #16).
- **Every lab package is brand new by its real publish date** (published today), so the quick checks' "package is only N days old" flag fires for all of them, honest ones included. The evaluation must allow for this, or the registry's stored publish dates can be adjusted to make 1.0.0 of the hijacked package look old (open question #17).

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
| 9 | ✅ **Answered Oct 30.** Can we control reasoning on Baseten's Spark Open? | **Yes: Baseten honours `reasoning_effort`.** Same prompt: 97, 161 and 501 output tokens at minimal, low and high; low took 1.2 s vs 2.1 s by default. The screener uses `low` (9.0 s → 5.0 s on a real package) | Done |
| 10 | ✅ **Answered Oct 30.** Does Spark Open's verdict quality match Meta Spark on hard cases? | **On the hard cases we tried, yes, and it's faster.** Obfuscated payload: block in 6 s (Meta: 28 s). CI-gated: spotted the gate, re-ran with CI=true itself, block, 6/6 evidence verified, 62 s (Meta: 74 s). Legit downloader: allow in 5 s. Still to do: the full test lab and the eval (Step 11) | Done for now |
| 11 | ~~Is a large explicit `"timeout"` (for example 180 s) honoured in full, or capped?~~ | **Answered Oct 29:** honoured. A 150 s hook with `"timeout": 180` finished and blocked | See "Step 2: service skeleton" (Oct 29) |
| 12 | What is Muse's default hook timeout? | Only matters if someone's config has no `timeout`. `bawabu init` always sets one | Low priority |
| 14 | How should whole-project installs (`npm ci`, `pip install -r`) be checked? | They're the most common install an agent runs after cloning a project, and they're currently allowed unchecked | The CLI sends the direct dependencies plus lockfile entries with `hasInstallScript`. Measure how many packages that is for typical projects |
| 15 | Can Spark suggest the real package for wholly invented names (`fancy-date-pickr` → `react-datepicker`)? | Spelling-based suggestions can't guess meaning | Step 7: give the investigator the agent's task and the made-up name |
| 16 | How does Bawabu check packages from a non-npm registry (our lab, or a company's private registry)? | Today the service always asks the real npm, so lab packages look made-up | The guard reads `--registry` and the project's `.npmrc`; the service accepts only known registries (npm and the lab) and blocks unknown ones |
| 17 | Should the lab registry's stored publish dates be adjusted so the hijacked package's 1.0.0 looks long-established? | Every lab package is brand new by date, which masks the "old package, suddenly new install code" pattern | Patch Verdaccio's stored `time` on startup, or have the evaluation account for it |
| 13 | Why do some connections from this network stall for 75 s (GitHub once, Modal once)? | A stalled connection can eat most of the hook's time budget. A demo recorded during a stall would look broken | Check whether IPv6 is the cause. Consider a short connect timeout plus one retry in `bawabu check`. Record the demo on a stable network |

### Next

- **Step 1: CLI and hook.** `bawabu init` (writes the hook and `.bawabu.json`) and `bawabu check` (reads the hook payload, filters to bash, parses install commands, blocks with a message). Test open question #1 first, because the answer shapes `bawabu check`.
- ~~Run the Modal sandbox test once Modal credits arrive.~~ Done Oct 28. Step 0 is complete.
