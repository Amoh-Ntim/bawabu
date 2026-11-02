# Report page UI plan

A new look for the live report page (`/r/<id>` and `/live`): calm, card-based and colour-coded, with a light and a
dark theme. These are the pages judges see in the demo video and click from the README, so the verdict and the
danger level should read in two seconds.

**What changes:** only how the page looks. The sections, what they show, and how it works stay the same.

**When:** before recording the video (the demo and B-roll shots B3–B6 film this page). Time box: about 4 hours,
including tests and redeploying. If time runs short, do section 4 (colour) first: it's the part that matters most on
video.

---

## 1. The look we're going for

Two reference designs (a healthcare reports dashboard and an analytics dashboard) set the style. What we take from
them:

| In the references | On the Bawabu report page |
|---|---|
| Soft off-white page, white cards with large rounded corners and a faint shadow, no hard borders | The same cards for every section; a dark version for the dark theme |
| Each card title with a small rounded-square icon, then a grey subtitle ("Quality measures *against the national benchmark*") | "The investigation *step by step*", "Evidence *checked against what the tools saw*", "The sandbox *locked, with fake secrets planted*" |
| Tinted status pills ("Above" / "Below", "On track" / "At risk") | Verdict, static risk, signal severity, verified / unverified, stolen |
| Big-number tiles along the top (208, $18M, $3M…) with a small pill underneath | A row of tiles under the verdict: evidence verified, tool calls, sandbox runs, investigator time, confidence |
| A ring gauge with one big number (MIPS score 74 of 100) | A ring for **evidence verified** (e.g. 4 of 4), a real number from the result |
| A segmented bar with a legend and counts ("218 gaps closed": green / amber / blue) | **Signals by severity**: one bar split into high / medium / low, with the counts beside it |
| A clean table with grey column headings and coloured values (care gaps) | **Network contacts in the sandbox** as a table: method, host, path, and a pill (stolen, unknown, its own registry) |
| A tinted callout box with an icon and one key sentence (the green box at the bottom) | The verdict reason, in a callout tinted by the verdict (red, green or amber) |
| Pill-shaped tabs (Operations, Financials…) | The row of recent checks in `/live`, each with a coloured dot |
| A sun / moon switch at the top right | The light / dark theme switch in the header |

**What we don't take:** sparklines and line charts (an investigation has no history over time), avatars, a search box
or a "New" button. Everything on the page shows real data from the investigation. Nothing is made up for looks.

---

## 2. What stays the same

- **Security.** Package text (code, Spark's words, hostnames) still goes in only through `textContent`, never as HTML.
  The strict Content-Security-Policy stays: no external fonts, scripts, images or stylesheets. Icons are small inline
  SVGs written into the page; fonts are the system's own (SF Pro on a Mac, Segoe UI on Windows), which look close to
  the references.
- **Sections and order.** The verdict at the top, the timeline on the left, then evidence, sandbox, diff and hard rules
  on the right, as the README and the video guide describe.
- **Old reports keep working.** Reports already saved in Supabase (including the links in the README and the video
  guide) must look right with the new page, even without any new data fields.
- **Colour never works alone.** Every colour sits next to a word (HIGH, BLOCKED, STOLEN…), so the page still makes
  sense to someone who can't tell red from green.
- **Phones.** Cards stack into one column; the tiles wrap two per row.

---

## 3. Light and dark themes

- **Two themes, one set of colour names.** All colours become named tokens (`--bg`, `--card`, `--text`, `--danger`…).
  The dark theme redefines them.
- **Which one shows:** it follows the computer's setting (`prefers-color-scheme`). A sun / moon switch in the header
  overrides it, and the page remembers the choice in the browser (`localStorage`, wrapped in try/catch so a private
  window still works).
- **No flash.** The theme is set before the page draws, so it never blinks from light to dark.

| Token | Light | Dark |
|---|---|---|
| Page background | `#F6F7F9` | `#0B0F17` |
| Card | `#FFFFFF`, shadow `0 1px 2px rgba(16,24,40,.04), 0 8px 24px rgba(16,24,40,.06)` | `#121826`, 1px border `#1F2940`, no shadow |
| Text | `#101828` | `#E6EBF5` |
| Muted text | `#667085` | `#8B97B0` |
| Lines | `#EAECF0` | `#24304A` |
| Code block | `#F2F4F7`, hit line `#FEE4E2` | `#0A0E15`, hit line `#3A1A1D` |

**For the video:** record in one theme throughout. Light matches the references and survives video compression well.
Dark matches the terminal and the title cards. Look at both, then pick one. If light wins, the title cards can switch to
a light background too (`title-cards-plan.md`, section 2).

---

## 4. One colour scale for the whole page

Used the same way everywhere, in both themes (text colour on a tinted background, like the reference pills):

| Level | Light theme | Dark theme | Used for |
|---|---|---|---|
| **Danger** | `#B42318` on `#FEE4E2` | `#F87171` on `#2A1215` | Blocked, risk HIGH, high signals, stolen secrets, hard rules |
| **Caution** | `#B54708` on `#FEF0C7` | `#FBBF24` on `#2A2110` | Needs a human, risk MEDIUM, medium signals, secret files read, unknown network contact, sandbox re-runs, unverified |
| **Low** | `#175CD3` on `#D1E9FF` | `#60A5FA` on `#0F1D33` | Risk LOW, low signals: worth knowing, not alarming |
| **Safe** | `#067647` on `#DCFAE6` | `#4ADE80` on `#0F2418` | Allowed, risk NONE, verified evidence |
| **Bawabu** | `#0E9384` | `#2DD4BF` | Live and in progress, Bawabu's own steps. Never a verdict |
| **Spark** | `#6941C6` | `#A78BFA` | Spark's thinking, decoded payloads |

Every pair passes WCAG AA contrast (4.5:1); this gets checked in both themes.

**Note:** the static risk levels in the code are `none`, `low`, `medium` and `high`. The page shows them as NONE, LOW,
MEDIUM and HIGH.

---

## 5. The changes, most important first

### Must do: colour

1. **Static risk gets its colour.** The "static risk: high" chip in *What changed since the previous version*
   becomes a tinted pill: HIGH red, MEDIUM amber, LOW blue, NONE green. The timeline's "Static analysis: risk high" step
   gets the same pill.

2. **Each signal gets a severity dot.** In the diff card, each signal line starts with a coloured dot and a word (HIGH,
   MED, LOW), with the most serious first. "Also in the previous version" lines are dimmed, because they aren't new.
   - *Needs a small backend change:* signals reach the page as plain sentences, without their severity.
     `diff_summary()` in `service/bawabu_service/investigations.py` adds a new list `signal_items`
     (`{text, severity, new}`) and keeps `signals` as it is.
   - Old reports don't have `signal_items`, so the page falls back to the plain list without dots.

3. **The verdict as a tinted callout.** The whole verdict box is tinted in its colour, with a large symbol in a
   rounded square: ✕ blocked, ✓ allowed, ? needs a human. The pill at the top gets the same symbol.

4. **Sandbox rows coloured by what happened:**
   - **STOLEN: …** filled red pill, so it's the first thing you see
   - **read secret file: …** amber (today it has no colour)
   - **network contact** to an unknown host: amber
   - its own registry, or "no secret files read, no network contact": grey with a green ✓

5. **Fix: "unverified" shows in green.** The evidence card uses the same green style for "✓ verified" and
   "unverified". Unverified becomes amber.

### Must do: the new look

6. **Tokens and both themes** (section 3), with the sun / moon switch.

7. **Cards like the references.** Rounded corners (16 px), soft shadow in light, no hard borders, more padding
   (20–24 px). Card titles in sentence case with an icon square and a grey subtitle, instead of today's small
   uppercase labels.

8. **Stat tiles under the verdict.** Today's grey chips (confidence, investigator, tool calls, sandbox re-runs,
   investigator time) become a row of tiles: a small grey label, a big number, and a pill where it helps. The
   investigator (Muse Spark or Muse Spark Open) stays as a chip next to the verdict, because the video points at it.

### Nice to have

9. **Evidence ring.** A ring showing "4 of 4 verified", in green when every claim was verified.

10. **Signals by severity bar.** One segmented bar (red / amber / blue) with the counts beside it, at the top of the diff
    card. Needs `signal_items`, so old reports skip it.

11. **Network contacts as a table** in the sandbox card: method, host, path, pill.

12. **Confidence as a meter, not a colour.** "Confidence: high" is about how sure Spark is, not about danger, so it
    shouldn't be red or green. Three small bars (▮▮▮ high, ▮▮▯ medium, ▮▯▯ low) in the verdict's colour.

13. **Recent checks in `/live` as pills** with a coloured dot each (red blocked, green allowed, amber needs a human,
    teal still running).

14. **Polish.** More space between timeline steps; the sandbox re-run step stands out (amber, with ↻); the hard-rule
    step gets ⚠.

---

## 6. Files to change

| File | Change |
|---|---|
| `service/bawabu_service/report_page.py` | The CSS (tokens, both themes, cards, pills, tiles, ring, bar, table) and the JavaScript (theme switch, risk pill, signal dots with fallback, sandbox rows, unverified colour, tiles, ring, recent-check dots) |
| `service/bawabu_service/investigations.py` | `diff_summary()` adds `signal_items` with each signal's severity |
| `service/tests/test_report_page.py` | Tests for the new parts (below) |
| `service/tests/test_investigations.py` | `diff_summary()` includes `signal_items` with severities |

Not affected: the CLI (`bawabu scan` reads `/check`, not the report page), the npm package, the database schema (the
result is stored as JSON, so the new field needs no migration), and the evaluation.

---

## 7. Tests

- **Existing tests still pass:** strict policy and nonce, no `innerHTML`, private-registry redaction.
- **New tests:**
  - the page has a style for each risk level (`none`, `low`, `medium`, `high`), and the JavaScript maps each one
  - both themes define every colour token
  - `diff_summary()` returns `signal_items` with the right severities, and `signals` is unchanged
  - the page still contains no `innerHTML` / `insertAdjacentHTML` / `document.write`, and loads nothing from outside
- **By eye, in a browser, in both themes,** with the local service (`uv run service/run_local.py`, then
  `bawabu scan … --local --lab`):
  - a blocked report (ci-build-cache-helper), an allowed one (left-pad), a needs-a-human one
  - an **old** report from the hosted service (from the README), to check the fallbacks
  - `/live` while an investigation runs
  - the theme switch, a reload (it remembers), and a private window (it still works)
  - phone width (browser dev tools, 390 px)
  - contrast: every coloured text passes WCAG AA on its background

---

## 8. Shipping it

1. Run the tests: `uv run pytest service/tests`
2. Check it locally (section 7)
3. Redeploy the hosted service: `modal deploy service/modal_app.py`
4. Open the README's report links and `/live` on the hosted service to check them
5. Pick the theme for the video, then record

The npm package doesn't need a new version.

---

## 9. Checklist

- [x] Colour tokens, light and dark themes, sun / moon switch
- [x] Cards restyled (corners, shadow, padding, icon titles with subtitles)
- [x] Static risk pill (diff card and timeline)
- [x] `signal_items` in `diff_summary()`, and severity dots on the page with a fallback for old reports
- [x] Tinted verdict callout with ✕ ✓ ?
- [x] Stat tiles under the verdict
- [x] Sandbox rows coloured (stolen, secret read, network, fine)
- [x] "unverified" in amber
- [x] Evidence ring (nice to have)
- [x] Signals by severity bar (nice to have)
- [x] Network contacts table (nice to have)
- [x] Confidence meter (nice to have)
- [x] Recent-check pills in `/live` (nice to have)
- [x] Tests pass; checked by eye in both themes, including an old report and phone width
- [x] `modal deploy service/modal_app.py`
- [ ] Theme picked for the video
- [x] results.md updated
