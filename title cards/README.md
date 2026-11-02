# Bawabu title cards

Seven finished PNGs, each **1920 × 1080**, following `docs/title-cards-plan.md`.
Import the `card-*.png` files into the video editor at their native size.

**Light mode:** `light mode/` contains a matching set of all seven cards with an
off-white background, dark ink, and deeper teal highlights, plus its own preview
and editable SVGs. The wording, dimensions, spacing, and mascot match the dark set.

| File | Placement in demo |
|---|---|
| `card-1-context.png` | 0:00–0:09 |
| `card-2a-stat.png` | About 0:17 |
| `card-2b-worm.png` | About 0:24 |
| `card-2c-agent.png` | About 0:30 |
| `card-3-title.png` | 0:37–0:41 |
| `card-4-results.png` | 2:21–2:37 |
| `card-5-end.png` | Closing segment, 2:37–2:50; hold at least 3 seconds |

`preview.png` shows all seven cards together. `source/` contains editable SVGs,
the exact text manifest, and the Pillow renderer. SVGs retain live text and embed
the mascot; Helvetica and Menlo should be installed for the closest match.
The PNGs are the final video assets and do not require fonts to be installed.

`mascot/` contains the original AI-generated image plus transparent 1024 × 1024
and 256 × 256 PNG exports. The two sized exports are also in `docs/images/` as
specified by the plan. The mascot appears only on the title and end cards.

`supporting/architecture-page-3.png` is a high-resolution render of page 3 of
`docs/Bawabu-explained.pdf` for the separate architecture cutaway. It is a portrait
source image, not one of the seven 16:9 title cards; crop or zoom to the diagram
in the editor. The overlays and captions described in the plan are editor tasks.

## Content verification

Card copy matches the plan, with line breaks adjusted for readability.
The first repository commit is dated 27 October 2026. The statement about what
existed before the event is reproduced from the supplied plan.

- Cards 2a and 2c: [Google Threat Intelligence](https://cloud.google.com/blog/topics/threat-intelligence/mitigation-guidance-for-supply-chain-compromise), including the cited OpenSSF data.
- Card 2b: [Cloud Security Alliance](https://labs.cloudsecurityalliance.org/research/csa-research-note-shai-hulud-ai-supply-chain-20260517-csa-st/), 169 npm packages plus two PyPI packages.
- Card 4: `eval/RESULTS.md`, nine attack samples in seven runs, 500/500 popular packages allowed, and 0.7-second median.

## Re-render

On macOS with Pillow installed:

```sh
python3 'title cards/source/render_cards.py'
python3 'title cards/source/render_cards.py' --theme light
```

Rendering uses 2× resolution before downsampling for clean text. The script
checks text margins, output dimensions, and mascot transparency. It also writes
the two mascot exports to `docs/images/`.

## Mascot provenance and prompt

Created with the built-in OpenAI image generation tool; no CLI image generation
or existing character reference was used. OpenAI's [Terms of Use](https://openai.com/policies/row-terms-of-use/)
assign output ownership to the user, subject to the terms and applicable law.

Final generation prompt:

> Use case: logo-brand. Create an original Bawabu friendly gatekeeper mascot, a clean flat illustration for a software security project. A small rounded watchman stands beside a simple open gate, holding a parcel and inspecting it with a magnifying glass. Kind, alert, welcoming, not a soldier. Strong iconic silhouette, solid colors, thick clean dark navy outlines, very few details, readable at 256px. Palette strictly teal #2DD4BF, dark navy #0B0F17, off-white #E6EBF5, with one small amber #FBBF24 check mark on the parcel. Transparent background, no ground/background panel, no shadows or gradients, no text, no lettering, no watermark, no existing character or brand. Square 1024 x 1024 canvas with the complete mascot centered and comfortable transparent margins. The character and gate should feel like one compact balanced emblem and look clear on a dark navy background.
