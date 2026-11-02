"""Builds docs/demo-video-guide.pdf from docs/demo-video-guide.md (Markdown -> styled HTML -> Chrome's print to PDF).

From the repo root (macOS, with Google Chrome installed):
    uv run --no-project --with markdown python docs/make_video_guide.py
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "demo-video-guide.md"
OUT = HERE / "demo-video-guide.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
body { font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.45;
       color: #1f2a44; }
h1 { font-size: 21pt; margin: 0 0 6pt; }
h2 { font-size: 14pt; color: #0f766e; margin: 18pt 0 6pt; padding-bottom: 3pt; border-bottom: 1px solid #cbd5e1; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; color: #1f2a44; }
h2, h3 { break-after: avoid; }
p { margin: 4pt 0; }
ul, ol { margin: 4pt 0 4pt 0; padding-left: 16pt; }
li { margin: 2pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 8pt; font-size: 8.8pt; }
th { background: #1f2a44; color: #fff; text-align: left; padding: 4pt 6pt; }
td { border-bottom: 1px solid #e2e8f0; padding: 4pt 6pt; vertical-align: top; }
tr { break-inside: avoid; }
tr:nth-child(even) td { background: #f8fafc; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.6pt; background: #f1f5f9; padding: 0 2pt; border-radius: 2pt; }
pre { background: #f1f5f9; padding: 6pt 8pt; border-radius: 4pt; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; }
/* The lines to say out loud stand out. */
blockquote { margin: 6pt 0; padding: 6pt 10pt; background: #ecfdf5; border-left: 4px solid #0f766e; font-size: 10.5pt;
             break-inside: avoid; }
blockquote p { margin: 3pt 0; }
hr { border: none; border-top: 1px solid #cbd5e1; margin: 12pt 0; }
a { color: #0f766e; text-decoration: none; word-break: break-all; }
.script-start, .appendix { break-before: page; }
"""


LIST_ITEM = re.compile(r"^\s*(?:[-*] |\d+\. )")


def loosen_lists(text: str) -> str:
    """Python-Markdown (unlike GitHub) needs a blank line before a list that follows a paragraph line."""
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        prev = out[-1] if out else ""
        if (not fenced and LIST_ITEM.match(line) and prev.strip() and not LIST_ITEM.match(prev)
                and not prev.startswith(("|", ">")) and not prev.startswith("  ")):
            out.append("")
        out.append(line)
    return "\n".join(out) + "\n"


def main() -> None:
    text = loosen_lists(SOURCE.read_text())
    html = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    # Start the script and the read-aloud appendix on fresh pages.
    html = html.replace("<h2>5. The script</h2>", '<h2 class="script-start">5. The script</h2>')
    html = html.replace("<h2>Appendix:", '<h2 class="appendix">Appendix:')
    page = f'<!doctype html><html><head><meta charset="utf-8"><title>Bawabu demo video guide</title><style>{CSS}</style></head><body>{html}</body></html>'
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "guide.html"
        source.write_text(page)
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={OUT}",
                        source.as_uri()], check=True, capture_output=True, timeout=120)
    print("wrote", OUT.relative_to(HERE.parent))


if __name__ == "__main__":
    sys.exit(main())
