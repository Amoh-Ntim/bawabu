# Bawabu title cards plan

The still images for the demo video, and the mascot that appears on some of them. The card texts match the script in
[demo-video-guide.md](demo-video-guide.md), so what's on screen and what you say agree.

---

## 1. The mascot

### The idea

*Bawabu* is Swahili for **gatekeeper**, so the mascot is a **friendly gatekeeper**: a small watchman standing at a gate,
checking each parcel before it comes in. It should feel kind and alert (a guardian, not a soldier), and say "nothing
gets in without a check" at a glance.

**Ideas to choose from (pick one):**
- A small round watchman with a lantern, standing beside an open gate.
- A watchman holding a parcel up to a magnifying glass (it inspects packages).
- A simpler version for small sizes: a shield with a friendly eye, or a gate shaped like a shield.

### Style

- **Flat and simple:** solid colours, thick clean outlines, no fine detail, so it still reads when small (README top,
  X profile picture).
- **Colours** (they match the report page): teal `#2DD4BF` as the main colour, dark navy `#0B0F17`, white `#E6EBF5`,
  and one small accent of amber `#FBBF24` (the lantern light, or a "checked" mark).
- **Background:** transparent, so it can sit on the dark cards and on GitHub's light or dark page.

### What to make

| File | Size | Use |
|---|---|---|
| `bawabu-mascot.png` | 1024 × 1024, transparent | Title card, end card, X post |
| `bawabu-mascot-small.png` | 256 × 256, transparent | README header |
| `bawabu-mascot.svg` (optional) | vector | Sharp at any size, if your tool can export SVG |

Put the files in `docs/images/`.

### How to make it

- **Draw it yourself** in Canva, Figma, Keynote or on paper (then trace it in Canva or Figma).
- **Use an AI image tool**, then simplify it. **Check the tool's terms allow public and commercial use**, and don't
  base it on an existing character or brand.
- **Ask a friend** who draws, and credit them in the README.

### Where it appears

1. The **Bawabu title card** (card 3), above the name.
2. The **end card** (card 5).
3. The **top of the README**, small, next to the title.
4. The **X post** image.

Nowhere else: keep it special.

### Time box

**30–60 minutes, after the video is recorded.** If time runs out, the cards work without it: the name and the tagline
carry the title card on their own.

---

## 2. Card style (all cards)

| | |
|---|---|
| **Size** | 1920 × 1080 (16:9) |
| **Background** | Dark navy `#0B0F17` |
| **Main text** | White `#E6EBF5` |
| **Small text and sources** | Grey `#8B97B0` |
| **Highlights and big numbers** | Teal `#2DD4BF` |
| **Font** | One clean sans-serif: Inter, Helvetica or SF Pro. Commands in a monospace font (Menlo, JetBrains Mono) |
| **Sizes** | Big numbers 120–160 pt · main lines 48–60 pt · small text 24 pt |
| **Layout** | Centred, lots of empty space, one idea per card |
| **Make them in** | Keynote, Google Slides, PowerPoint or Canva; export each as PNG |
| **Save as** | `title cards/card-1-context.png`, `card-2a-stat.png`, … |
| **Themes** | Every card in two versions: **dark** (above) and **light** (`title cards/light mode/`: off-white `#F6F7F9` background, ink `#101828`, grey `#5E687B`, deeper teal `#08786C`). Same text, sizes and layout. Use one theme for the whole video |

---

## 3. The cards

### Card 1 · Context: what existed before the event (0:00–0:09)

| Position | Text | Style |
|---|---|---|
| Top | Meta Global AI Developer Hackathon · 26 Oct – 4 Nov 2026 | Small, teal |
| Centre | Bawabu was built during this hackathon. | Big, white |
| Below | Before the event: no Bawabu code, repository or service (first commit: 27 October) | Medium, grey |
| Bottom | Built on: Muse Code · Muse Spark · Muse Spark Open (Meta) · Modal · Baseten · Supabase · Verdaccio · OSV.dev | Small, grey |

On screen for the whole segment (about 9 seconds). If the idea or plan existed before 26 October, change the second
line to *"Before the event: only the idea."*

### Card 2a · Problem: the rise (about 0:17)

| Position | Text | Style |
|---|---|---|
| Centre | +1,444% | Huge, teal |
| Below | malicious open-source packages, 2024 → 2025 | Medium, white |
| Bottom | Source: OpenSSF, via Google Threat Intelligence | Small, grey |

### Card 2b · Problem: the worm (about 0:24)

| Position | Text | Style |
|---|---|---|
| Centre | 171 packages | Huge, teal |
| Below | hit by the Mini Shai-Hulud worm, May 2026 | Medium, white |
| Bottom | Source: Cloud Security Alliance | Small, grey |

### Card 2c · Problem: it has already happened with an agent (about 0:30)

| Position | Text | Style |
|---|---|---|
| Centre | An AI agent added a malicious package to a real project. | Big, white (put "AI agent" in teal) |
| Bottom | Source: Google Threat Intelligence | Small, grey |

### Card 3 · Bawabu title (0:37–0:41)

| Position | Text | Style |
|---|---|---|
| Top | (the mascot) | About 300 px tall |
| Centre | Bawabu | Huge, white |
| Below | the gatekeeper between AI coding agents and the packages they install | Medium, grey |

Followed straight away by card 3b.

### Card 3b · How it works: the architecture (0:41–0:47)

The architecture redrawn as a card, because the README and PDF diagrams have too much detail to read in six seconds.
It matches the voiceover: *"Normal packages pass in under a second. Suspicious ones get investigated."*

| Position | Text | Style |
|---|---|---|
| Top | HOW IT WORKS | Small, teal |
| Below | The agent’s installs go through the gate | Big, white |
| Centre | Five boxes left to right, in two panels: **Your machine** (Muse Code: *npm install x* → Bawabu hook: *name + version*) and **Bawabu service · Modal** (Quick checks: *about 1 s* → Screener, Muse Spark Open: *a few seconds* → Investigation, locked sandbox + Muse Spark: *30–90 s*) | Box titles white, outlines teal / violet / red |
| Under the boxes | What each stage can answer: *allow · block*, *allow*, *allow · block · ask*, joined by one line back to the hook: "the answer goes back to the agent, with the evidence and a report link" | Pills in the box colours |
| Bottom | Most packages are cleared by the quick checks. Only red flags go further. | Small, grey |

### Card 3c · Inside an investigation (optional)

Use it only if there's time: about 4 seconds at the start of 1:57 "Under the hood", or skip it.

| Position | Text | Style |
|---|---|---|
| Top | INSIDE AN INVESTIGATION | Small, teal |
| Below | Muse Spark has to show its evidence | Big, white |
| Left | Diff engine (*what changed since the previous version*) and Sandbox X-ray (*locked Modal sandbox, fake secrets planted*) feed Muse Spark; an amber *re-run* arrow goes back to the sandbox | Teal outlines |
| Centre | Muse Spark · Meta Model API: reads the code, decodes what's hidden, asks for a sandbox re-run, cites evidence for each claim | Violet outline |
| Right | Evidence check (*every quote checked against what the tools saw*) → Hard rules (*a stolen fake secret means block, always*) | Amber, red outlines |
| Bottom bar | Verdict: ALLOW · BLOCK · ASK, with the evidence and a report link · saved in Supabase | Green / red / amber pills |
| Bottom | Evidence that doesn't match what the tools saw is thrown out. | Small, grey |

Both architecture cards are drawn by `title cards/source/render_cards.py` (dark, and `--theme light`), so they match
the other cards exactly.

### Card 4 · Results (2:21–2:37)

Three rows, left-aligned in the centre of the card, each with a big teal number and a short white line:

| Number | Line |
|---|---|
| 9 / 9 | test-lab attacks caught, in every run, with both models |
| 0 / 500 | of the most popular npm packages blocked |
| 0.7 s | for a normal package |

Small, grey, at the bottom: *Full results: github.com/Amoh-Ntim/bawabu (eval/RESULTS.md)*

### Card 5 · End card (2:37–2:50, hold at least 3 seconds)

| Position | Text | Style |
|---|---|---|
| Top | (the mascot) | About 240 px tall |
| Centre | Bawabu | Big, white |
| Below | npm i -g bawabu | Medium, teal, monospace |
| Below | github.com/Amoh-Ntim/bawabu | Medium, white |
| Bottom | Built during the Meta Global AI Developer Hackathon · Muse Code · Muse Spark · Muse Spark Open | Small, grey |

---

## 4. Overlays (added in the video editor, not cards)

| Overlay | Text | When |
|---|---|---|
| Hook caption | Your AI coding agent, installing packages on its own. | 0:09–0:17, bottom of the screen |
| Lower-third, left | Muse Code (Meta's coding agent) | First time the split screen appears, about 3 seconds |
| Lower-third, right | Bawabu live report | Same moment |
| Honesty label | Harmless test package | When the package name first appears |
| Speed label | 2× speed | Whenever footage is sped up, top corner |
| Optional | CI: the servers that build and test code automatically | When "CI servers" is first said |
| Captions | The whole voiceover | Throughout (most editors generate them; check "Bawabu" is spelled right) |

---

## 5. Checklist

- [ ] Mascot (optional, after recording): `bawabu-mascot.png` and `bawabu-mascot-small.png`
- [ ] Card 1: context
- [ ] Card 2a: +1,444%
- [ ] Card 2b: 171 packages
- [ ] Card 2c: an AI agent added a malicious package
- [ ] Card 3: Bawabu title
- [ ] Card 3b: how it works (architecture)
- [ ] Card 3c: inside an investigation (optional)
- [ ] Card 4: results
- [ ] Card 5: end card
- [ ] Light-mode versions of every card
- [ ] Overlays added in the editor
- [ ] Every number on the cards matches the voiceover and its source (demo-video-guide.md, section 9)
