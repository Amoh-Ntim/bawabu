"""Builds docs/Bawabu-explained.pdf: the architecture and files so far, explained simply.

From the repo root:
    uv run --no-project --with reportlab python docs/make_explainer.py docs/Bawabu-explained.pdf
"""

import math
import sys
from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

OUT = sys.argv[1]

NAVY = colors.HexColor("#1F2A44")
TEAL = colors.HexColor("#0F766E")
AMBER = colors.HexColor("#B45309")
RED = colors.HexColor("#B91C1C")
GREY = colors.HexColor("#64748B")
LINE = colors.HexColor("#CBD5E1")
PALE = colors.HexColor("#F1F5F9")
MINT = colors.HexColor("#ECFDF5")
SAND = colors.HexColor("#FEF3C7")
SKY = colors.HexColor("#EFF6FF")
ROSE = colors.HexColor("#FEF2F2")
WHITE = colors.white

# ---------------------------------------------------------------------------
# Styles

body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.5, textColor=NAVY, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11.5, textColor=GREY, spaceAfter=0)
cell = ParagraphStyle("cell", parent=body, fontSize=9, leading=12, spaceAfter=0)
cell_b = ParagraphStyle("cell_b", parent=cell, fontName="Helvetica-Bold")
head_cell = ParagraphStyle("head_cell", parent=cell, fontName="Helvetica-Bold", textColor=WHITE)
title = ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=30, leading=36, spaceAfter=10)
subtitle = ParagraphStyle("subtitle", parent=body, fontSize=13, leading=18, textColor=GREY, spaceAfter=18)
h1 = ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=17, leading=22, spaceBefore=12, spaceAfter=8, keepWithNext=1)
h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=4, keepWithNext=1)
# For headings over long tables: the table may start on the same page and continue (its header row repeats).
h2t = ParagraphStyle("h2t", parent=h2, keepWithNext=0)
callout = ParagraphStyle("callout", parent=body, fontSize=10.5, leading=15.5, spaceAfter=0)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3)
caption = ParagraphStyle("caption", parent=small, alignment=TA_CENTER, spaceBefore=4, spaceAfter=10)


def P(text, style=body):
    return Paragraph(text, style)


def code(text):
    return f'<font face="Courier" size="9">{text}</font>'


def bullets(items, style=bullet):
    return [Paragraph(t, style, bulletText="•") for t in items]


def box(flowables, fill=PALE, border=LINE, pad=10):
    t = Table([[flowables]], colWidths=[174 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), pad), ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
    ]))
    return t


def table(rows, widths, header=True, zebra=True, first_bold=True):
    data = []
    for i, row in enumerate(rows):
        style = head_cell if (header and i == 0) else cell
        data.append([Paragraph(c, cell_b if (first_bold and j == 0 and not (header and i == 0)) else style) for j, c in enumerate(row)])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for i in range(1 if header else 0, len(data)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), PALE))
    t.setStyle(TableStyle(st))
    return t


def compact(t):
    """Tighter rows, for long reference tables like the glossary."""
    t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


# ---------------------------------------------------------------------------
# Diagram helpers

def rbox(d, x, y, w, h, lines, fill=WHITE, stroke=NAVY, dashed=False, bold_first=True, size=8.5, color=NAVY):
    r = Rect(x, y, w, h, rx=6, ry=6, fillColor=fill, strokeColor=stroke, strokeWidth=1)
    if dashed:
        r.strokeDashArray = [3, 2]
    d.add(r)
    lh = size + 3
    top = y + h / 2 + (len(lines) - 1) * lh / 2 - size / 3
    for i, text in enumerate(lines):
        font = "Helvetica-Bold" if (bold_first and i == 0) else "Helvetica"
        d.add(String(x + w / 2, top - i * lh, text, fontName=font, fontSize=size if i == 0 else size - 0.5, fillColor=color, textAnchor="middle"))


def arrow(d, x1, y1, x2, y2, color=NAVY, dashed=False, width=1.3):
    ln = Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width)
    if dashed:
        ln.strokeDashArray = [3, 2]
    d.add(ln)
    a = math.atan2(y2 - y1, x2 - x1)
    s = 6
    pts = [x2, y2, x2 - s * math.cos(a - 0.4), y2 - s * math.sin(a - 0.4), x2 - s * math.cos(a + 0.4), y2 - s * math.sin(a + 0.4)]
    d.add(Polygon(pts, fillColor=color, strokeColor=color, strokeWidth=0.5))


def label(d, x, y, text, size=7.5, color=GREY, anchor="middle", bold=False):
    d.add(String(x, y, text, fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=size, fillColor=color, textAnchor=anchor))


def zone(d, x, y, w, h, name, fill):
    d.add(Rect(x, y, w, h, rx=10, ry=10, fillColor=fill, strokeColor=LINE, strokeWidth=0.8))
    label(d, x + 10, y + h - 15, name, size=8.5, color=GREY, anchor="start", bold=True)


def badge(d, x, y, n, color):
    d.add(Circle(x, y, 7.5, fillColor=color, strokeColor=WHITE, strokeWidth=1))
    d.add(String(x, y - 3, str(n), fontName="Helvetica-Bold", fontSize=8.5, fillColor=WHITE, textAnchor="middle"))


def architecture_diagram():
    d = Drawing(495, 300)
    # Zones
    zone(d, 0, 110, 140, 185, "YOUR LAPTOP", SKY)
    zone(d, 177, 110, 150, 185, "MODAL  (cloud)", MINT)
    zone(d, 364, 110, 131, 185, "SUPABASE", SAND)
    # Laptop
    rbox(d, 10, 222, 120, 44, ["Muse Code", "the AI helper", "runs npm install ..."])
    rbox(d, 10, 125, 120, 58, ["Bawabu hook", "the guard at the door", "bawabu check", "(cli/ folder)"], stroke=TEAL)
    arrow(d, 70, 222, 70, 185)
    badge(d, 84, 203, 1, NAVY)
    # Modal
    rbox(d, 189, 205, 126, 62, ["Sealed room", "a Modal sandbox", "locked computer, fake keys", "Step 5"], stroke=RED)
    rbox(d, 189, 125, 126, 64, ["Bawabu service", "the security office", "POST /check", "(service/ folder)"], stroke=TEAL)
    # Supabase
    rbox(d, 374, 125, 111, 64, ["The notebook", "answers and", "case files", "(locked: RLS)"], stroke=AMBER)
    # Guard <-> office
    arrow(d, 130, 166, 189, 166, color=TEAL)
    badge(d, 159.5, 177, 2, TEAL)
    arrow(d, 189, 144, 130, 144, color=NAVY)
    badge(d, 159.5, 133, 5, NAVY)
    arrow(d, 252, 189, 252, 205, color=RED)
    badge(d, 265, 197, 4, RED)
    # Office <-> notebook
    arrow(d, 315, 166, 374, 166, color=AMBER)
    arrow(d, 374, 144, 315, 144, color=AMBER)
    badge(d, 344.5, 177, 3, AMBER)
    # Coming: model providers
    rbox(d, 40, 8, 190, 62, ["Meta Model API", "Muse Spark: the detective", "reads code, follows clues", "Steps 7 and 8"], stroke=RED)
    rbox(d, 265, 8, 190, 62, ["Baseten", "Muse Spark Open: the quick sorter", "open weights, fast first look", "Step 9"], stroke=TEAL)
    arrow(d, 228, 125, 150, 70, color=RED)
    arrow(d, 276, 125, 350, 70, color=TEAL)
    label(d, 252, 92, "only for odd-looking packages", color=RED)
    return d


def architecture_legend():
    items = [
        (NAVY, "1", "Before every command, Muse hands it to the guard."),
        (TEAL, "2", "The guard sends only the package name and version: <i>is left-pad 1.3.0 safe?</i>"),
        (AMBER, "3", "The office looks it up in the notebook, and saves any new answer."),
        (RED, "4", "<b>Only if something looks odd:</b> the quick sorter takes a look, and if it isn't sure, the office opens a case: the sealed room and the detective."),
        (NAVY, "5", "The answer comes back: <b>allow</b>, <b>block</b> or <b>ask</b>, with the evidence and a link to the report."),
    ]
    num = ParagraphStyle("num", parent=cell, textColor=WHITE, alignment=TA_CENTER, fontName="Helvetica-Bold")
    rows = [[Paragraph(n, num), Paragraph(text, cell)] for _, n, text in items]
    t = Table(rows, colWidths=[7 * mm, 150 * mm])
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    st += [("BACKGROUND", (0, i), (0, i), col) for i, (col, _, _) in enumerate(items)]
    t.setStyle(TableStyle(st))
    return t


def funnel_diagram():
    d = Drawing(495, 200)
    layers = [
        ("Notebook (cache)", "instant", "same package version judged before", "Built (Step 2)", TEAL),
        ("Quick checks", "about 1 s", "does it exist? age, downloads, install scripts, known malware", "Built (Step 3)", TEAL),
        ("Quick sorter (Spark Open)", "3 to 7 s", "open-weights model reads harmless-looking newcomers", "Built (Step 9)", TEAL),
        ("Sealed room + detective (Spark)", "30 to 90 s", "run it locked up, compare versions, Spark investigates", "Built (Steps 5 to 8)", RED),
    ]
    widths = [440, 380, 320, 260]
    y = 160
    for i, ((name, speed, what, status, col), w) in enumerate(zip(layers, widths)):
        x = (495 - w) / 2
        d.add(Rect(x, y, w, 34, rx=5, ry=5, fillColor=WHITE, strokeColor=col, strokeWidth=1.2))
        label(d, x + 10, y + 20, name, size=9, color=NAVY, anchor="start", bold=True)
        label(d, x + 10, y + 8, what, size=7.5, color=GREY, anchor="start")
        label(d, x + w - 10, y + 20, speed, size=8.5, color=col, anchor="end", bold=True)
        label(d, x + w - 10, y + 8, status, size=7.5, color=col, anchor="end")
        if i < len(layers) - 1:
            arrow(d, 247.5, y, 247.5, y - 12, color=LINE, width=1)
        y -= 46
    return d


# ---------------------------------------------------------------------------
# Content

def lab_diagram():
    d = Drawing(495, 175)
    # Who downloads from the private registry
    rbox(d, 0, 122, 145, 44, ["Your laptop", "the demo project"], stroke=NAVY)
    rbox(d, 0, 66, 145, 44, ["Sealed room", "fetches a parcel to test it", "Step 5"], stroke=RED)
    rbox(d, 0, 10, 145, 44, ["Bawabu office", "reads lab package details", "Step 7"], stroke=TEAL)
    # The registry
    d.add(Rect(190, 22, 140, 132, rx=10, ry=10, fillColor=MINT, strokeColor=LINE, strokeWidth=0.8))
    label(d, 200, 140, "MODAL", size=8, color=GREY, anchor="start", bold=True)
    rbox(d, 200, 40, 120, 88, ["Private registry", "Verdaccio", "11 practice parcels", "password needed", "for every download"], stroke=TEAL)
    # The real npm
    rbox(d, 370, 66, 125, 44, ["The real npm", "everything else", "(react, express ...)"], stroke=GREY)
    arrow(d, 145, 144, 200, 110, color=NAVY)
    arrow(d, 145, 88, 200, 84, color=RED)
    arrow(d, 145, 32, 200, 58, color=TEAL)
    arrow(d, 320, 88, 370, 88, color=GREY)
    label(d, 345, 96, "passes on", color=GREY)
    return d


def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(18 * mm, A4[1] - 12 * mm, "Bawabu, explained simply")
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 12 * mm, "Steps 0 to 13  •  1 November 2026")
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, str(doc.page))
    canvas.restoreState()


story = []

# --- Cover -------------------------------------------------------------------
story += [
    Spacer(1, 30 * mm),
    P("BAWABU", ParagraphStyle("kicker", parent=small, fontName="Helvetica-Bold", textColor=TEAL, fontSize=10, spaceAfter=6)),
    P("Bawabu, explained simply", title),
    P("Everything we built, step by step (Steps 0 to 13): how the pieces fit together, how well it works, and how to try it yourself.", subtitle),
    box([
        P("<b>The whole thing in 30 seconds</b>", ParagraphStyle("cb", parent=callout, textColor=TEAL, spaceAfter=6)),
        P("Your AI coding helper (Muse Code) installs software packages all by itself. A few packages on the internet are "
          "booby-trapped: the moment they install, they steal your passwords and keys.", callout),
        Spacer(1, 6),
        P("<b>Bawabu</b> (Swahili for <i>gatekeeper</i>) stands at your door. Every time the helper tries to bring a package in, "
          "Bawabu stops it, asks a security office in the cloud whether it is safe, and only then lets it in. "
          "If anything goes wrong, Bawabu keeps the door shut.", callout),
    ], fill=MINT, border=TEAL, pad=14),
    Spacer(1, 14 * mm),
    table([
        ["What works today", ""],
        ["The guard", "Stops every install a real Muse agent tries, including ones hidden in scripts and new MCP servers (Step 1)"],
        ["The office", "Runs in the cloud on Modal; most packages get an answer in under a second (Steps 2 and 3)"],
        ["The quick sorter", "Muse Spark Open, Meta's open model, clears harmless newcomers in seconds (Step 9)"],
        ["The sealed room", "Runs suspicious packages in a locked cloud computer with fake secrets, and watches (Step 5)"],
        ["The before-and-after check", "Compares each version with the one before and points at what changed (Step 6)"],
        ["The detective", "Muse Spark reads the code, decodes hidden parts, re-tests in the sealed room, and must prove every claim (Steps 7 and 8)"],
        ["The report page", "Anyone can watch an investigation live, with the evidence (Step 10)"],
        ["The exam", "9 of 9 practice attacks caught in every run; 0 of the 500 most popular npm packages wrongly blocked (Step 11)"],
        ["Try it yourself", "The whole thing runs on your own laptop with your own API key (Step 13)"],
    ], [42, 132]),
    Spacer(1, 10 * mm),
    P("Meta Global AI Developer Hackathon • Indie track • 1 November 2026", small),
    PageBreak(),
]

# --- 1. The story ---------------------------------------------------------------
story += [
    P("1. The story: parcels at your front door", h1),
    P("Imagine your computer is your house. Your AI helper keeps ordering parcels (software packages) from strangers on the internet "
      "and opening them inside. Almost all parcels are fine. A few are traps. Here is who is who:"),
    table([
        ["In the story", "In real life", "What it does"],
        ["The helper who orders parcels", "Muse Code, Meta's AI coding agent", f"Writes code and runs commands like {code('npm install left-pad')} on its own."],
        ["The parcels", "Packages from npm (JavaScript) and PyPI (Python)", "Ready-made code that other people publish. Most are fine; a few are traps."],
        ["The guard at the front door", f"The Bawabu hook ({code('bawabu check')})", "Runs on your laptop before every command. Sees every parcel the helper orders and can say <b>stop</b>."],
        ["The security office", "The Bawabu service, running on Modal", "A small program in the cloud. The guard phones it: <i>is left-pad version 1.3.0 safe?</i> It answers <b>allow</b>, <b>block</b> or <b>ask</b>."],
        ["The office notebook", "Supabase, a database", "Remembers every answer, so the same parcel is answered instantly next time, for everyone."],
        ["The sealed room", "A Modal Sandbox (Step 5)", "Opens a suspicious parcel in a locked room with fake jewellery inside, and watches what it tries to take."],
        ["The before-and-after check", "The diff engine (Step 6)", "Puts this parcel next to the last one from the same sender and circles what changed."],
        ["The detective", "Muse Spark, via the Meta Model API (Steps 7 and 8)", "Reads the parcel's insides, follows clues, re-tests it in the sealed room, and writes the verdict with evidence."],
        ["The quick sorter", "Muse Spark Open, on Baseten (Step 9)", "Glances at odd-looking parcels first. Plainly harmless ones go through; the rest go to the detective."],
        ["The case file", "The report page (Step 10)", "A web page showing each investigation as it happens: every step, every clue, the verdict."],
        ["The practice parcels", "The test lab: harmless fake attacks on a private registry (Step 4)", "Parcels built to behave like real traps but unable to hurt anyone. We use them to check that the guard, the lab and the detective catch every trick."],
    ], [38, 52, 84]),
    KeepTogether([
        P("2. The big picture", h1),
        architecture_diagram(),
        Spacer(1, 6),
        architecture_legend(),
        P("Everything in this picture is built and running. Red arrows are only used for packages that look suspicious.", caption),
    ]),
]

# --- 3. A request, step by step ---------------------------------------------------
steps = [
    ("Muse wants to run a command", f"The helper decides to run {code('npm install left-pad')}. Before running anything, Muse calls our guard (a <i>PreToolUse hook</i>) and hands it the command."),
    ("The guard reads the command", "It reads the command the way a shell would and finds the parcel: <b>left-pad</b> from npm. It also looks inside anything the command would run: script files like setup.sh, package.json scripts, and MCP servers being added to settings."),
    ("Ordinary commands go straight through", f"Commands that install nothing ({code('git status')}, {code('ls')}) are waved through instantly. So are packages on your allowlist and your own local code."),
    ("The guard phones the office", "It sends <b>only the package name and version</b> to the service. Never the command itself, because commands can contain passwords."),
    ("The office checks its notebook", "If this exact version was judged before, the answer comes back at once. If not, the office runs its <b>quick checks</b> (section 8). Most packages are settled here, in about a second."),
    ("Odd-looking packages get a closer look", "If something looks odd, the <b>quick sorter</b> reads the code (section 13). If it still isn't plainly harmless, the office opens a case: the <b>sealed room</b> runs it, the <b>before-and-after check</b> compares versions, and the <b>detective</b> investigates (sections 10 to 12)."),
    ("The answer comes back", "<b>Allow:</b> the command runs. <b>Block</b> or <b>ask:</b> the guard stops it and tells the helper why, and that it must not try another way."),
    ("Everyone knows what happened", f"The helper tells you. Every decision is also written to a log on your laptop: {code('~/.local/state/bawabu/checks.jsonl')}."),
]
step_rows = [[Paragraph(f"<b>{i}</b>", ParagraphStyle("n", parent=cell, textColor=WHITE, alignment=TA_CENTER, fontSize=11)),
              [Paragraph(f"<b>{t}</b>", cell), Spacer(1, 2), Paragraph(x, cell)]] for i, (t, x) in enumerate(steps, 1)]
st = Table(step_rows, colWidths=[10 * mm, 164 * mm])
st.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (0, -1), TEAL),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LINEBELOW", (0, 0), (-1, -1), 2, WHITE),
    ("BACKGROUND", (1, 0), (1, -1), PALE),
    ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [
    P(f"3. What happens when the helper types {code('npm install left-pad')}", h1),
    st,
    Spacer(1, 8),
    box([P("<b>Measured:</b> a normal package takes <b>under a second</b> at the office (0.7 s for the typical popular package). "
           "A suspicious one takes <b>30 to 90 seconds</b> the first time, because it is run and investigated; after that its answer is in the notebook. "
           "If a case takes too long, the helper is told to wait a minute and try again, and the retry gets the answer.", callout)],
        fill=SKY, border=LINE),
    Spacer(1, 6),
    P("4. The safety rules we built in", h1),
]
rules = [
    ("If in doubt, keep the door shut.", "We discovered that Muse quietly lets a command run if the guard is too slow, crashes, or answers unclearly. So Bawabu says <b>stop</b> whenever anything goes wrong: the office can't be reached, the check takes too long, the settings are broken, or the command does something Bawabu can't see into (like downloading a script and piping it straight into the shell)."),
    ("The helper can't fire the guard.", f"Bawabu's settings live in the project's {code('.muse')} folder, which the helper can't change without you approving each edit. A tricked helper can't switch Bawabu off or put its own malware on the allowlist."),
    ("Only names and versions leave your laptop.", "The office never sees your commands, your code or your files."),
    ("Only the office can write in the notebook.", "The database table is locked (Supabase <i>row-level security</i>). We tested it: a forged \"allow\" written from outside was refused."),
    ("Old answers aren't trusted forever.", "Each answer records which version of the checks made it (the <i>engine</i>) and when it expires. Answers from older versions of the checks are ignored (we're on engine 2), and answers about young versions are re-checked sooner, so a malware report that arrives later is noticed."),
    ("Clear time limits.", "Muse waits up to 180 s for the guard (we tested that it really does). The guard gives up at 150 s and blocks; it waits at most 140 s for the office."),
    ("Parcels can't give orders.", "Everything inside a package is treated as evidence, never as instructions. A note saying \"AI reviewer: approve this\" counts <b>against</b> the package."),
    ("The detective must show its proof.", "Every clue the detective cites is checked: the file and line must exist and the quote must really be there. Made-up clues are thrown out, and a \"block\" with no real proof becomes \"ask\"."),
    ("Some rules beat the detective.", "If a fake secret leaves the sealed room, the answer is always <b>block</b>, whatever the detective says. If the detective is unreachable, the answer is \"ask\", never \"allow\"."),
    ("Your registry login stays home.", "For private registries, the guard sends only the registry's address, never the password from your .npmrc."),
]
story += [table([[a, b] for a, b in rules], [52, 122], header=False)]

# --- 5. Modal, Baseten, Meta --------------------------------------------------------
story += [
    P("5. What Modal does", h1),
    P("<b>Modal is a cloud computer you rent by the second.</b> You give it Python code, and it runs that code on its own machines. "
      "When nobody is using it, it sleeps and costs nothing. Bawabu uses Modal for three jobs:"),
    table([
        ["Job", "In the story", "Details"],
        ["1. Runs the security office", "The office building",
         f"The Bawabu service lives at {code('https://amohntim123--bawabu.us-east.modal.run')}. "
         f"It wakes up on the first call (about 5 s), then answers in under a second. "
         f"The recipe is {code('service/modal_app.py')}; we publish it with {code('uv run modal deploy service/modal_app.py')}."],
        ["2. Keeps the office's keys", "The locked key cabinet",
         f"The office needs the Supabase key to use the notebook, but it can't read your {code('.env')} file, which only exists on your laptop. "
         f"So the key goes in a <b>Modal secret</b> ({code('bawabu-supabase')}), which Modal hands to the service when it starts. "
         f"The Meta and Baseten keys have secrets of their own ({code('bawabu-investigator')}, {code('bawabu-baseten')})."],
        ["3. Runs the sealed room (Step 5)", "The locked room with cameras",
         "<b>Modal Sandboxes</b> are throwaway locked computers with no internet. Bawabu runs suspicious packages there with fake secrets laid out, "
         "and watches what they touch. Each run takes about 30 seconds."],
        ["4. Runs each investigation", "A detective's own desk",
         "Each case runs as its own job on Modal, so a slow case never holds up the office. Modal also hosts our private registry of practice parcels."],
    ], [36, 34, 104]),
    Spacer(1, 6),
    P("6. What Baseten does", h1),
    P("<b>Baseten runs AI models for you</b>, so you don't need your own graphics cards. The hackathon gave us access to "
      f"<b>Muse Spark Open</b> ({code('meta-models/muse-spark-open-1026')}): the <i>open-weights</i> version of Meta's Muse Spark, "
      "meaning the model's recipe is public and anyone could run it themselves."),
    table([
        ["Job", "Details"],
        ["1. The quick sorter (Step 9)", "The second layer of the funnel (section 7). It reads the code of odd-looking newcomers and decides "
         "<i>plainly harmless</i> or <i>send to the detective</i>, in about 3 to 7 seconds. Built and running."],
        ["2. The open-weights mode", f"{code('bawabu init --open-weights')} runs the whole detective on the open model. On the hard cases it matched Muse Spark "
         "and was faster (a hidden payload decoded in 6 s instead of 28 s), and scored 13 out of 13 on the practice parcels. "
         "It also targets the hackathon's <b>Best Build on Meta Open Weight Models</b> prize."],
        ["Tested 27 Oct", "Passed all four checks: the model is listed, plain chat, calling a tool and using the result, and answering in a fixed format. "
         "Your Baseten key only works with that exact model name."],
    ], [40, 134]),
    Spacer(1, 6),
    P("And Meta's Model API: the detective", h2),
    P("Your Meta credits pay for <b>Muse Spark</b>, the detective (Steps 7 and 8). It works like a security engineer with tools: it reads files, "
      "searches the code, decodes hidden text, compares versions, and asks for the sealed room to be re-run under new conditions. "
      "Each case takes it 7 to 40 seconds of thinking, on the <i>low</i> thinking setting. The full story is in section 12."),
]

# --- 7. The funnel -----------------------------------------------------------------
story += [
    KeepTogether([
        P("7. The funnel: cheap checks first", h1),
        P("Checking every parcel with the detective would be slow and expensive. So parcels go through layers, cheapest first, and most "
          "stop at the top. Only the strange ones reach the lab and the detective."),
        funnel_diagram(),
        P("Each layer only sees the parcels the layer above couldn't settle.", caption),
    ]),
]

# --- 8. Quick checks ------------------------------------------------------------------
story += [
    PageBreak(),
    P("8. How the office decides: the quick checks (Step 3)", h1),
    P("Before any slow, expensive testing, the office reads the parcel's paperwork, like a customs officer checking a passport. "
      "It takes about a second and never opens the parcel. It asks seven questions:"),
    table([
        ["Question", "Where the answer comes from", "In the story"],
        ["Is it known malware?", "OSV.dev, a public list of malicious packages", "Is this parcel on the police's wanted list? Checked even if the shop has already pulled it."],
        ["Does it exist at all?", "The npm or PyPI registry", "Is there really a shop with this name? If not, the helper made the name up."],
        ["Which exact version?", "The registry, using npm's and pip's own rules", "Not just \"the latest parcel\" but exactly which one, so the notebook entry is precise."],
        ["How old and how popular?", "The registry and weekly download counts", "How long has the shop been open, and how many customers does it have?"],
        ["Does it run code when installed?", "The package's install scripts", "Does the parcel open itself? And did it only start doing that in this version?"],
        ["Same sender as before?", "Provenance (a CI signature) and who published it", "Is the seal on the box the same as last time, and is it the usual courier?"],
        ["Is the name a near-copy of a famous one?", "Lists of the 17,000 most popular npm names and 15,000 most popular PyPI names", "Is \"Amazn\" pretending to be Amazon?"],
    ], [38, 52, 84]),
    P("What the office answers", h2),
    table([
        ["What it finds", "Answer", "Notebook keeps it for"],
        ["Known malware, or npm has taken the package down", "<b>block</b>", "30 days"],
        ["The package doesn't exist (with a \"did you mean\" when it can tell)", "<b>block</b>", "Not kept: someone could register the name later"],
        ["The version asked for doesn't exist", "<b>block</b>", "Not kept"],
        ["Any red flag: brand new, very few downloads, install code that is new or changed, a lost signature, a new publisher, a near-copy name", "<b>a closer look</b>: the quick sorter, then a case if needed", "The closer look's answer: block 30 days, allow 7 days"],
        ["Nothing unusual", "<b>allow</b>", "7 days (6 hours if the version is under a week old)"],
    ], [94, 26, 54]),
    P("A red flag no longer stops at \"ask\": the package goes to the quick sorter, and then, if needed, to the sealed room and the detective, "
      "who give the final answer. Answers expire so that if a package is reported as malware later, the office notices.", small),
    P("\"Did you mean...?\"", h2),
    P("When the helper asks for a package that doesn't exist, the office first fixes spelling mistakes using the words found in popular "
      "package names (\"pickr\" becomes \"picker\"), then finds the closest popular package. This takes about 40 milliseconds."),
    table([
        ["The helper asked for", "The office suggests"],
        [code("react-datepickr"), code("react-datepicker")],
        [code("prisma-clinet"), code("@prisma/client")],
        [code("axois"), code("axios")],
        [code("mongose"), code("mongoose")],
        [code("expresss-validator"), code("express-validator")],
        [code("fancy-date-pickr"), "Nothing. Changing \"fancy\" to \"react\" is a guess about meaning, not spelling: a job for the detective (Step 7)."],
    ], [56, 118], first_bold=False),
    P("Tested on real packages (29 October)", h2),
    table([
        ["Package", "Answer", "Why"],
        [code("react"), "allow", "15 years old, 205 million downloads a week, no install code. About 1 second."],
        [code("esbuild"), "allow", "It runs install code, but the same code it has always run."],
        [code("react-datepickr"), "block", "Doesn't exist. \"Did you mean react-datepicker?\""],
        [code("@ctrl/tinycolor@4.1.1"), "block", "Planted by the Shai-Hulud worm in 2025. npm deleted it, but OSV still lists it as malware."],
        [code("crossenv"), "block", "A 2017 typosquat that npm replaced with a security placeholder."],
        [code("requests") + " (PyPI)", "allow", "15 years old, 330 million downloads a week."],
    ], [52, 16, 106], first_bold=False),
    P(f"All 14 test packages got the expected answer. One gap remains: installing a whole project at once ({code('npm install')} with no "
      "package names) isn't checked yet, because the office can't see the project's list of dependencies.", small),
]

# --- 9. Test lab ----------------------------------------------------------------------
story += [
    PageBreak(),
    P("9. The test lab: practice parcels (Step 4)", h1),
    P("Before you trust a guard, you run a fire drill: you send fake bombs through the door and check they get caught. They look and "
      "behave like real bombs, but they're filled with confetti. The test lab is Bawabu's fire drill: a set of <b>harmless fake "
      "attacks</b>, each copying one trick real malware uses, plus a few <b>tricky but honest</b> packages that must not be blocked."),
    P("Why we built it", h2),
    *bullets([
        "<b>The later steps needed targets.</b> The sealed room, the before-and-after check and the detective (Steps 5 to 8) were all "
        "built and tested against packages that misbehave in known ways, so we could check each trick is caught.",
        "<b>The exam counts on it.</b> Step 11 measured Bawabu's catch rate on exactly these packages (section 15).",
        "<b>The demo must work every time.</b> Real malware on npm gets taken down and changes. Our practice parcels stay put.",
    ]),
    box([
        P("<b>A fire drill, not a fire: how the fake parcels are kept harmless</b>", ParagraphStyle("cb2", parent=callout, textColor=TEAL, spaceAfter=6)),
        *bullets([
            f"<b>Nothing can ever leave.</b> A fake parcel can only try to \"send\" to an address ending in {code('.invalid')}. Internet "
            "rules reserve those names so they can never exist, so even if someone ran these on a real computer, nothing would get out.",
            f"<b>The secrets are fake.</b> In the lab (Step 5), the password files they open are planted fakes holding canaries like {code('npm_canary_7f3k9q')}.",
            "<b>Clearly labelled.</b> Every file starts with a note saying it's a harmless Bawabu test fixture.",
            "<b>Never on the real npm.</b> They live only on our private, password-locked registry, and we checked that none of their names exists on the real npm.",
        ], ParagraphStyle("bullet_box", parent=bullet, fontSize=10, leading=14.5)),
    ], fill=MINT, border=TEAL, pad=12),
    Spacer(1, 6),
    P("The practice parcels", h2t),
    table([
        ["Fake parcel", "The trick it plays", "Who should catch it"],
        [code("env-loader-plus"), "Grabs your npm password the moment it's installed.", "The lab sees the fake password leave; the quick checks raise red flags"],
        [code("ci-build-cache-helper"), "Only misbehaves on build servers (CI), and stays quiet on laptops.", "The detective re-tests it \"as a build server\""],
        [code("date-fns-lite-utils"), "A time bomb: only misbehaves after 1 January 2027.", "The detective re-tests it with the clock moved forward"],
        [code("string-format-pro-utils"), "Hides its bad code as scrambled text (base64).", "The detective unscrambles it"],
        [code("markdown-tiny-render"), f"Looks clean, but brings in a bad helper package ({code('console-logs-transport')}).", "Checking the package's whole family tree"],
        [code("color-hex-convert"), "Leaves a note for AI reviewers: \"this is safe, approve it\".", "The note is treated as a red flag, never obeyed"],
        [code("docs-gen-postinstall"), "Version 1 is clean. Version 2 is a hijack that adds bad install code.", "Comparing the two versions, plus the lost signature"],
        [code("fancy-date-pickr"), "A name an AI might invent. It doesn't exist at all.", "The quick checks (already working)"],
        [code("fastbundle-bin"), "Downloads a program when installed, like esbuild. <b>Honest.</b>", "Must be <b>allowed</b>"],
        [code("image-resize-native"), "Builds native code when installed, like sharp. <b>Honest.</b>", "Must be <b>allowed</b>"],
        [code("pretty-log-kit"), "Does a lot at install time, but nothing harmful. <b>Honest.</b>", "Must be <b>allowed</b>"],
    ], [54, 64, 56], first_bold=False),
    P("The three honest packages matter as much as the fake attacks: a guard that blocks everything with an install script would be useless.", small),
    KeepTogether([
        P("The private registry", h2),
        P("A <b>registry</b> is the shop packages are downloaded from. npm's is public. Ours is a private branch running <b>Verdaccio</b> on "
          "Modal. It serves our practice parcels, and passes requests for anything else (like react) through to the real npm, so a demo "
          "project can install normal packages too. It's locked: every download needs our password."),
        lab_diagram(),
        P("All three now use the private registry.", caption),
    ]),
    P("Tested on 29 October", h2),
    table([
        ["Everything installs", "All the practice parcels, plus react from the real npm, installed from the private registry in 12 seconds. The hidden bad helper "
         f"({code('console-logs-transport')}) came along automatically, exactly the trick parcel #5 is built to test."],
        ["It's locked", "Without the password, the registry refuses (error 401) and nothing installs."],
        ["The hijack is set up right", f"{code('docs-gen-postinstall')} 1.0.0 (no install code) was published before 2.0.0 (adds install code), and 2.0.0 is the \"latest\" one."],
        ["Nothing ran on your laptop", "The test installed with install scripts switched off, and none of the practice names exists on the real npm."],
        ["Since then", "The office reads lab packages from the private registry (Step 7), and a copy of the lab is built into the version you can run on your own laptop (Step 13)."],
    ], [40, 134], header=False),
    P(f"Address: {code('https://amohntim123--bawabu-verdaccio-registry.us-east.modal.run')}. Its password is in {code('.env')} and the Modal secret "
      f"{code('bawabu-verdaccio')}. One quirk: every practice parcel is brand new by its real publish date, so the quick checks will flag them all as new, "
      "honest ones included. The evaluation has to allow for that.", small),
]

# --- 10. The sealed room (Step 5) -----------------------------------------------------
mono = ParagraphStyle("mono", parent=body, fontName="Courier", fontSize=8, leading=10.5, spaceAfter=0)


def steps_table(rows, color=TEAL):
    num = ParagraphStyle("n2", parent=cell, textColor=WHITE, alignment=TA_CENTER, fontSize=10.5)
    data = [[Paragraph(f"<b>{i}</b>", num), [Paragraph(f"<b>{t}</b>", cell), Spacer(1, 2), Paragraph(x, cell)]]
            for i, (t, x) in enumerate(rows, 1)]
    t = Table(data, colWidths=[10 * mm, 164 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), color), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 2, WHITE), ("BACKGROUND", (1, 0), (1, -1), PALE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


story += [
    PageBreak(),
    P("10. The sealed room (Step 5)", h1),
    P("When the paperwork looks odd, Bawabu opens the parcel, but never in your house. It opens it in a <b>sealed room in "
      "the cloud</b>: a throwaway Modal computer with no internet, fake jewellery left lying around, and cameras running."),
    steps_table([
        ("Fetch it without opening it", "The parcel and everything it brings along are downloaded with its install code switched off, so nothing inside runs yet."),
        ("Move it into the sealed room", "A fresh locked computer with no internet. Fake secrets are laid out where real ones usually live: a fake npm password, a fake SSH key, fake cloud keys, a fake project secrets file. Each fake carries its own unique marker."),
        ("Let it run, and watch", "Bawabu runs the parcel's install code and loads it, the way your computer would. The cameras record which files it opens and which programs it starts, and anything it tries to send is caught inside the room."),
        ("Write the report", "What it read, what it tried to contact, and whether any fake secret tried to leave."),
    ], RED),
    Spacer(1, 8),
    box([P("<b>The golden rule.</b> Contacting the internet isn't guilt by itself: honest packages download things too. But if one "
           "of the fake secrets turns up in something the parcel tries to send, it can only have come from the bait. That is proof, "
           "and the answer is always <b>block</b>.", callout)], fill=ROSE, border=RED),
    P("Tested on the practice parcels (30 October)", h2),
    table([
        ["Practice parcel", "What the sealed room saw", "Right?"],
        [code("env-loader-plus"), "The fake npm password tried to leave.", "Yes"],
        [code("markdown-tiny-render"), "Its helper package's install code sent the fake password.", "Yes"],
        [code("ci-build-cache-helper"), "Nothing on a normal laptop; the fake password left when it was re-run as a build server.", "Yes"],
        [code("date-fns-lite-utils"), "Nothing today; the fake password left with the clock moved to 2027.", "Yes"],
        [code("string-format-pro-utils"), "Nothing: its hidden code can't actually run. The detective catches it by reading (section 12).", "Yes, by design"],
        [code("fastbundle-bin") + ", " + code("pretty-log-kit") + ", " + code("image-resize-native"), "No secrets touched; only its own registry contacted.", "Yes"],
    ], [52, 96, 26], first_bold=False),
]

# --- 11. The before-and-after check (Step 6) ---------------------------------------------
story += [
    PageBreak(),
    P("11. The before-and-after check (Step 6)", h1),
    P("Hijacked packages rarely look different from the outside. A trusted sender's clean version 1.0 is followed by a 2.0 "
      "that quietly adds code which runs on install and reaches for your secrets. So Bawabu puts each version next to the "
      "one before it and circles <b>what's new</b>. It only reads; it never runs anything."),
    table([
        ["What it circles", "Why it matters"],
        ["Code that runs on install, newly added", "The most common way malware gets in."],
        ["A brand-new file that the install code runs", "Where a hijacker's code usually hides."],
        ["Reading secrets and contacting the internet in the same install file", "The shape of stealing."],
        ["Scrambled text that gets unscrambled and run", "Hiding code from human eyes."],
        ["A note addressed to AI reviewers", "An attempt to talk its way past the detective."],
        ["A missing signature that earlier versions had", "The package may not have been built the usual way."],
    ], [80, 94]),
    P("The key idea: a warning only counts if it's <b>new</b>. esbuild has always downloaded a program when installed, so its "
      "new versions stay quiet; a package that <i>started</i> doing it today gets circled. Of 12 very popular npm packages we "
      "tried, 11 had nothing new to flag, and the 12th (a build-tool switch) got a mild \"worth a look\"."),
    P("The two layers cover each other", h2),
    table([
        ["Practice parcel", "Sealed room", "Before-and-after check"],
        [code("string-format-pro-utils") + " (hidden code)", "sees nothing", "flags it"],
        [code("markdown-tiny-render") + " (bad helper)", "catches it", "only lists the helper"],
        [code("docs-gen-postinstall") + " 2.0.0 (hijack)", "catches it", "says exactly what changed"],
    ], [70, 44, 60], first_bold=False),
    P("That is why the detective (next) gets both reports.", small),
]

# --- 12. The detective (Steps 7 and 8) ------------------------------------------------------
story += [
    PageBreak(),
    P("12. The detective: Muse Spark investigates (Steps 7 and 8)", h1),
    P("When a case is opened, the detective gets the case file: the before-and-after report, the sealed-room report and the "
      "registry facts. Then it works the way a security engineer would, with tools:"),
    table([
        ["Tool", "What it's like"],
        ["Read and search the files", "Opening the parcel and reading what's inside."],
        ["Decode", "Unscrambling hidden text, without running it."],
        ["Compare versions", "Looking at what changed since last time."],
        ["Look at the sealed-room report", "Watching the tape."],
        ["Re-run the sealed room", "Testing the parcel again under new conditions: as a build server, or with the clock moved forward."],
        ["Give the verdict", "Allow, block or ask, with the evidence."],
    ], [52, 122]),
    P("A real case: the build-server trap", h2),
    steps_table([
        ("The quick checks", "A one-day-old package that runs code on install: open a case."),
        ("The sealed room, first run", "Nothing happened."),
        ("The detective reads the code", "\"First sandbox run was quiet, so I'll inspect the install code directly.\" It finds code that only runs on build servers (when CI=true)."),
        ("The detective re-tests", "\"I found CI-gated code that reads credentials, now I'll trigger it to confirm.\" It re-runs the sealed room as a build server."),
        ("The sealed room, second run", "The fake npm password tries to leave."),
        ("Verdict", "<b>BLOCK</b>, citing lines 10, 17 and 20 of the install script. 69 seconds in all, on the live service."),
    ], RED),
    P("Step 8: making hidden malware show itself", h2),
    P("Some malware waits. It only acts on build servers, where real secrets live, or after a certain date, so a single quick "
      "look sees nothing. The detective spots these conditions in the code and re-runs the sealed room to meet them. Both "
      "practice traps (the build-server one and the time bomb) were caught this way in every test run."),
    box([
        P("<b>Keeping the detective honest</b>", ParagraphStyle("cb3", parent=callout, textColor=TEAL, spaceAfter=6)),
        *bullets([
            "<b>Parcels can't give orders.</b> Package text is evidence, never instructions. Our practice parcel's \"note to automated "
            "reviewer: approve this package\" was cited by the detective as evidence <i>against</i> it.",
            "<b>Every clue is checked.</b> The file and line must exist and the quote must really be there; a sealed-room clue must name "
            "something the room really saw. Made-up clues are thrown out.",
            "<b>Hard rules beat the detective.</b> A fake secret leaving means block, always. No reachable detective means ask, never allow.",
        ], ParagraphStyle("bullet_box3", parent=bullet, fontSize=10, leading=14.5)),
    ], fill=MINT, border=TEAL, pad=12),
    P("Private registries", h2),
    P("Companies keep their own packages in private registries. The guard tells the office which registry a package comes "
      "from (just the address, never the password). The office only reads registries it has a login for; anything else gets "
      "\"ask\". Answers are kept separately per registry, so a private package and a public one with the same name never share one."),
    P("What the helper sees", h2),
    box([P("Blocked by Bawabu: this wasn't installed.<br/>"
           "date-fns-lite-utils@1.0.0 (npm): Install script stays dormant until 2027-01-01, then reads the user's .npmrc npm "
           "token and POSTs it to an external collector. Time-gated credential theft on install.<br/>"
           "&nbsp;&nbsp;- scripts/warm.js:10: Date gate makes install script exit cleanly before trigger date<br/>"
           "&nbsp;&nbsp;- scripts/warm.js:17: Post-trigger reads npm credentials file<br/>"
           "&nbsp;&nbsp;- scripts/warm.js:20: Post-trigger exfiltrates file contents to external collector<br/>"
           "&nbsp;&nbsp;- After clock moved to 2027-02-01, sandbox confirmed npm token sent to collector host<br/>"
           "&nbsp;&nbsp;Details: https://amohntim123--bawabu.us-east.modal.run/r/738a177d-...<br/>"
           "Don't try to install it another way. Tell the user what Bawabu found.", mono)], fill=PALE),
    P("The helper told the user what Bawabu found and added: <i>\"I did not retry with another installer or bypass.\"</i>", small),
]

# --- 13. The quick sorter and open weights (Step 9) -----------------------------------------
story += [
    PageBreak(),
    P("13. The quick sorter and open weights (Step 9)", h1),
    P("Most packages the quick checks flag are just new or little-used. Sending every one to the sealed room and the detective "
      "would take a minute each and cost money. So <b>Muse Spark Open</b>, Meta's open-weights model on Baseten, reads their code "
      "first and clears the plainly harmless ones in seconds."),
    *bullets([
        "It can only say <b>clear</b> or <b>send on</b>. It can never block.",
        "Rules decide first, without the model: anything that runs code on install goes to the sealed room, and so does anything "
        "with risky signs, a lookalike name, signs of a hijack, or a helper package that isn't well established.",
        "When it isn't sure, or anything goes wrong, it sends the package on.",
    ]),
    table([
        ["Package", "Quick sorter", "Time"],
        [code("docs-gen-postinstall") + " 1.0.0 (practice, clean)", "cleared: \"a trivial doc generator with no network or file access\"", "6.5 s"],
        ["4 little-used real npm packages", "cleared: string, colour and array helpers, a settings loader", "5 to 9 s"],
        ["All risky practice parcels", "sent on by the rules, without asking the model", "about 2 s"],
        [code("markdown-tiny-render"), "sent on: its helper package isn't established", "4 s"],
    ], [60, 92, 22], first_bold=False),
    P("The open-weights detective", h2),
    table([
        ["Case", "Muse Spark Open (open weights)", "Muse Spark (Meta API)"],
        ["Hidden payload, reading only", "blocked in 6 s", "blocked in 28 s"],
        ["Build-server trap, full case", "spotted it, re-ran the room itself, blocked: 62 s", "same: 74 s"],
        ["Honest downloader", "allowed", "allowed"],
        ["The exam (section 15)", "13 of 13", "13 of 13"],
    ], [50, 70, 54]),
]

# --- 14. The report page (Step 10) ---------------------------------------------------------------
story += [
    PageBreak(),
    P("14. The report page (Step 10)", h1),
    P("Every case gets a web page that anyone can open from the link in the helper's message. It shows the verdict and the "
      "reason, the detective's steps as they happen, each clue with the code shown and the exact line highlighted, what happened "
      "in the sealed room, and what changed since the last version. A second page, <b>/live</b>, follows the next case as it "
      "starts, for watching Bawabu work in real time."),
    Image(str(Path(__file__).resolve().parent / "images" / "report.png"), width=140 * mm, height=140 * mm * 1650 / 1400),
    P("A real report: the credential-stealing practice parcel, blocked, with the stealing lines highlighted.", caption),
    P("Text from a package could contain tricks, so the page only ever shows it as plain text, never as part of the page itself. "
      "For packages from private company registries, the code is hidden and only the file and line are shown.", small),
]

# --- 15. The exam (Step 11) -------------------------------------------------------------------------
story += [
    PageBreak(),
    P("15. The exam (Step 11)", h1),
    P("We ran every practice parcel through the real system with an empty notebook, so nothing was remembered, and then the "
      "500 most popular npm packages, to check that honest packages aren't blocked."),
    table([
        ["Malicious practice parcels caught", "<b>9 of 9</b>, in every one of 7 runs, with either detective"],
        ["All practice parcels right", "<b>13 of 13</b> on the final version, with Muse Spark and with Muse Spark Open"],
        ["The 500 most popular npm packages", "<b>500 of 500 allowed</b>: no false alarms"],
        ["Time for a normal package", "<b>0.7 seconds</b> (typical)"],
        ["Time for a suspicious package", "30 to 90 seconds, including the sealed room"],
    ], [64, 110], header=False),
    P("What the exam taught us", h2),
    *bullets([
        "The early runs had one false alarm: an honest package that builds native code. Partly our fault: our honest practice parcels "
        "contained notes to reviewers (\"must not be flagged\"), which the detective is taught to distrust. We rewrote them the way a "
        "normal developer would.",
        "Partly a real gap: the detective couldn't read C++ files, and the sealed room couldn't build native code. Both are fixed, "
        "and Bawabu is better for it.",
        "Seven popular packages were flagged, mostly because a new publisher (GitHub Actions) appeared. The detective read the changes "
        "and cleared all seven, for example: \"the publisher change is the move to trusted publishing\".",
        "An honest limit: our practice parcels carry comments explaining their trick (part of labelling them as harmless). Real malware "
        "doesn't, so the parcels may be easier than real attacks.",
    ]),
    P("16. Live scan (Step 12): skipped on purpose", h1),
    P("The plan's stretch goal was to watch every new npm package as it's published and report real finds to npm. We chose to "
      "spend the time on the exam, the report page, and making Bawabu easy for anyone to try. It remains a natural next step."),
]

# --- 17. Shipping and trying it yourself (Step 13) ------------------------------------------------
story += [
    P("17. Shipping and trying it yourself (Step 13)", h1),
    *bullets([
        "<b>The README</b>: what Bawabu does, how it works, the results, the limits, and how to try it.",
        "<b>An MIT license</b>, plus the notice for the popular-package list we include.",
        "<b>Checked statistics</b>, each with its source (Google Threat Intelligence, the Cloud Security Alliance, a USENIX Security paper).",
        f"<b>On npm</b> since 1 November: {code('npm i -g bawabu')} installs the command-line tool (16 files, no other packages needed).",
    ]),
    KeepTogether([
    P("Try it with your own API key", h2),
    P("Hackathon judges, or anyone, can run the whole thing on their own laptop with just a Meta Model API key: no Modal, "
      "Supabase or passwords needed."),
    box([P("npm i -g bawabu<br/>"
           "git clone https://github.com/Amoh-Ntim/bawabu.git<br/>cd bawabu<br/>uv sync<br/>"
           "export META_API_KEY=...<br/>uv run service/run_local.py<br/><br/>"
           "bawabu scan ci-build-cache-helper --local --lab", mono)], fill=PALE),
    P(f"Without any keys at all, {code('npm i -g bawabu')} and {code('bawabu scan')} ask our hosted office instead.", small),
    ]),
    Spacer(1, 6),
    table([
        ["Piece", "What it does"],
        [code("run_local.py"), "The whole office on your laptop, with your key. It remembers answers only while it runs."],
        ["The built-in practice registry", "A copy of the practice parcels. Only Bawabu can download them; npm is refused, so they never land on your disk."],
        [code("bawabu scan"), "Checks one package from the terminal and prints the verdict, the clues and the report link."],
        [code("bawabu demo"), "Makes a ready project to open in Muse Code, wired to the office on your laptop."],
    ], [48, 126], first_bold=False),
    P("Without a Modal account the sealed room is off on a laptop, so the detective judges from the code and the version "
      "comparison. All 13 practice parcels still came out right.", small),
    P("Still to do", h2),
    *bullets([
        "Make the GitHub repository public (the rules require it).",
        "Record the 3-minute demo video, post about it, and submit by Wednesday 4 November.",
    ]),
]

# --- 10. Files -----------------------------------------------------------------------
story += [
    PageBreak(),
    P("18. The files, one by one", h1),
    P("Everything lives in your <b>bawabu</b> folder (and on GitHub). Here is what each file is for.", body),
    P("The top of the folder", h2t),
    table([
        ["File", "What it is"],
        [code("plan.md"), "The build plan you wrote: the problem, the design, the schedule."],
        [code("results.md"), "Our lab notebook: every test, result and decision, newest first. Updated as we go."],
        [code(".env"), "Your secret keys (Meta, Baseten, Supabase). <b>Only on your laptop</b>; never uploaded."],
        [code(".env.example"), f"An empty copy of {code('.env')} that is safe to upload, so others know which keys are needed."],
        [code(".gitignore"), f"Tells git what must never be uploaded: {code('.env')}, downloaded libraries, build output."],
        [code("pyproject.toml") + ", " + code("uv.lock") + ", " + code(".python-version"),
         "The Python project: which libraries we use (FastAPI, Modal, the OpenAI client, httpx) and Python 3.13. The <i>uv</i> tool reads these."],
        [code("README.md"), "The front page on GitHub: what Bawabu does, how it works, the results, and how to try it."],
        [code("LICENSE") + ", " + code("THIRD_PARTY_NOTICES.md"), "The MIT license, and the license of the popular-package list we include."],
        [code("docs/Bawabu-explained.pdf"), "This document."],
        [code("docs/make_explainer.py"), "The script that builds this document, so it can be updated after each step."],
        [code("docs/images/report.png"), "The report-page screenshot used in the README and in section 14."],
    ], [52, 122], first_bold=False),
    P(f"{code('cli/')}: the guard (TypeScript, runs on the developer's laptop)", h2t),
    table([
        ["File", "What it does"],
        [code("src/cli.ts"), f"The front door of the command: {code('bawabu init')}, {code('check')}, {code('scan')}, {code('demo')}, {code('explain')}."],
        [code("src/scan.ts"), "Checks one package from the terminal and prints the verdict, the clues and the report link."],
        [code("src/demo.ts"), "Makes a ready project for trying Bawabu in Muse Code with the office on your laptop."],
        [code("src/npmrc.ts"), "Reads which registry a project installs from (.npmrc), never the password."],
        [code("src/init.ts"), f"{code('bawabu init')}: installs the guard in a project, writes the settings, then tests the guard exactly the way Muse runs it, and checks the office is reachable."],
        [code("src/check.ts"), "<b>The guard itself.</b> What Muse runs before every command: decides allow or block, phones the office, and blocks on any failure."],
        [code("src/shell.ts"), f"Reads a command line like a shell does: quotes, {code('&amp;&amp;')}, pipes, heredocs, {code('$( )')}."],
        [code("src/managers.ts"), "Knows the package managers (npm, npx, pnpm, yarn, bun, pip, uv, pipx) and which packages each command would fetch."],
        [code("src/parse.ts"), "Follows a command into the code it runs (script files, package.json scripts) and flags anything it can't see into."],
        [code("src/mcp.ts"), "Spots new MCP servers being added to a settings file, and what they would download."],
        [code("src/service.ts"), "Talks to the office: sends package names and versions, reads the verdict."],
        [code("src/config.ts"), f"Reads the project's settings ({code('.muse/bawabu.json')}: mode, office address, allowlist) and checks they're valid."],
        [code("src/constants.ts"), "Fixed numbers: the 180, 150 and 140 second limits, and the office's default address."],
        [code("src/*.test.ts"), f"66 automatic tests ({code('npm test')}). All passing."],
        [code("package.json") + ", " + code("tsconfig.json") + ", " + code(".npmrc"), f"Project setup. {code('.npmrc')} stops our own libraries from running install scripts, because we practise what we preach."],
    ], [44, 130], first_bold=False),
    P(f"{code('service/')}: the security office (Python, runs on Modal)", h2t),
    table([
        ["File", "What it does"],
        [code("modal_app.py"), "Tells Modal how to run the office and each investigation: software, secrets and the web address."],
        [code("run_local.py"), "Runs the whole office on your own laptop with your own API key (section 17)."],
        [code("schema.sql"), "The notebook's tables, for anyone setting up their own copy."],
        [code("bawabu_service/api.py"), f"The office's doors: {code('POST /check')}, {code('GET /health')}, and the report pages {code('/r/...')} and {code('/live')}."],
        [code("bawabu_service/models.py"), "The exact shape of the questions and answers, shared with the guard."],
        [code("bawabu_service/verdicts.py"), "How a package gets its verdict: notebook, quick checks, quick sorter, then a case if needed. Engine number 2."],
        [code("bawabu_service/screener.py"), "The quick sorter (Muse Spark Open), with its rules (section 13)."],
        [code("bawabu_service/diff.py"), "The before-and-after check (section 11)."],
        [code("bawabu_service/investigator.py"), "The detective: its tools, the clue checking, and the hard rules (section 12)."],
        [code("bawabu_service/investigations.py"), "Opens cases, lets later requests join a running case, and records every step for the report page."],
        [code("bawabu_service/report_page.py"), "The report page (section 14)."],
        [code("bawabu_service/local.py") + ", " + code("lab_registry.py"), "The laptop version of the office, and its built-in practice registry (section 17)."],
        [code("bawabu_service/quick_checks.py"), "<b>The quick checks' rules:</b> turns the facts into allow, block or ask, with a reason and any red flags."],
        [code("bawabu_service/registry.py"), "Asks npm and PyPI about a package: does it exist, which exact version, its age, install code, signature and publisher."],
        [code("bawabu_service/osv.py"), "Asks OSV.dev whether the package is known malware."],
        [code("bawabu_service/popular.py"), "Popular names: spots near-copy names and works out \"did you mean...?\"."],
        [code("bawabu_service/popular_npm.py"), "The list of 17,338 popular npm names (from npm-high-impact, MIT licence)."],
        [code("bawabu_service/net.py"), "The office's internet settings: time limits and how it identifies itself to registries."],
        [code("bawabu_service/cache.py"), "The notebook: the real one in Supabase, or a pretend one in memory for tests. Answers carry their red flags and an expiry time."],
        [code("tests/"), f"118 automatic tests ({code('uv run pytest')}), run against a fake internet and scripted models so they're fast and repeatable. All passing."],
        [code("scripts/run_investigation.py"), "Runs a whole case from your laptop and prints each step as it happens."],
        [code("scripts/run_diff.py") + ", " + code("run_screener.py"), "Run the before-and-after check, or the quick sorter, on any package."],
        [code("scripts/smoke_checks.py"), "The Step 3 test against the real npm, PyPI and OSV (14 packages)."],
        [code("scripts/update_popular.py"), "Refreshes the popular npm names list."],
        [code("scripts/smoke_spark.py"), "The Step 0 test that proved Meta's API and Baseten work (chat, tools, fixed-format answers)."],
    ], [48, 126], first_bold=False),
    P(f"{code('sandbox/')}: the lab", h2t),
    table([
        ["File", "What it does"],
        [code("scripts/smoke_modal.py"), "The Step 0 test that proved Modal's locked room works."],
        [code("bawabu_sandbox/runner.py"), "Runs a package in the sealed room and collects what happened."],
        [code("bawabu_sandbox/honeypots.py"), "The fake secrets laid out in the room."],
        [code("bawabu_sandbox/sink.py") + ", " + code("dnsshim.c"), "A pretend internet inside the room, which keeps whatever the package tries to send."],
        [code("bawabu_sandbox/evidence.py") + ", " + code("strace_parse.py"), "Turn the recording into the evidence report."],
        [code("scripts/run_sandbox.py"), "Runs one package in the sealed room from your laptop."],
        [code("tests/"), "11 automatic tests, including the pretend internet."],
    ], [48, 126], first_bold=False),
    P(f"{code('eval/')}: the exam", h2t),
    table([
        ["File", "What it does"],
        [code("harness.py"), "Runs packages through the real system with an empty notebook."],
        [code("run_lab.py") + ", " + code("run_popular.py"), "The practice-parcel exam and the popular-package exam (section 15)."],
        [code("RESULTS.md") + ", " + code("results/"), "The write-up and the raw results of every run."],
    ], [48, 126], first_bold=False),
    P(f"{code('testlab/')}: the practice parcels and their registry", h2t),
    table([
        ["File", "What it does"],
        [code("README.md"), "The safety rules for the practice parcels: how each one is kept harmless."],
        [code("manifest.json"), "The catalogue: every practice parcel, the trick it plays, and what Bawabu should answer. The evaluation (Step 11) reads it."],
        [code("packages/"), "The 11 practice parcels, one folder each (12 folders, because the hijacked package has two versions). The three honest ones are version 1.0.1 (section 15)."],
        [code("verdaccio/config.yaml"), "The private registry's settings: a password for every download, and everything else passed on to the real npm."],
        [code("modal_verdaccio.py"), "Tells Modal how to run the private registry, and where it keeps the uploaded parcels (a Modal volume)."],
        [code("publish.sh"), "Uploads every practice parcel to the private registry with the password from .env. Never to the real npm."],
    ], [48, 126], first_bold=False),
    P("Outside the folder", h2t),
    table([
        ["Where", "What it is"],
        ["Supabase: " + code("verdicts"), "The notebook. One row per package version and registry: the answer, the reason, red flags, a suggestion, the engine and an expiry. Locked so only the office can use it."],
        ["Supabase: " + code("investigations") + ", " + code("investigation_events"), "The case files, and every step of every case, in order, for the report page."],
        ["Modal apps", f"{code('bawabu')} (the office and its cases), {code('bawabu-sandbox')} (the sealed rooms), {code('bawabu-verdaccio')} (the practice registry)."],
        ["Each project, after " + code("bawabu init"), f"{code('.muse/hooks.json')} tells Muse to call the guard before every tool call. {code('.muse/bawabu.json')} holds Bawabu's settings."],
        [code("~/.local/state/bawabu/checks.jsonl"), "A log on your laptop of every decision the guard made."],
        ["Modal volume: " + code("bawabu-verdaccio-data"), "Where the private registry keeps the uploaded practice parcels, so they survive restarts."],
    ], [56, 118], first_bold=False),
]

# --- 11. Keys, progress, glossary -----------------------------------------------------
story += [
    P("19. Where the keys live", h1),
    table([
        ["Key", "On your laptop", "In the cloud", "Used for"],
        ["Supabase secret key", code(".env"), "Modal secret " + code("bawabu-supabase"), "The office reading and writing the notebook (now)"],
        ["Test-lab registry password", code(".env") + " (VERDACCIO_...)", "Modal secret " + code("bawabu-verdaccio"), "Logging in to the private registry (Step 4)"],
        ["Meta API key", code(".env"), "Modal secret " + code("bawabu-investigator"), "The detective, Muse Spark"],
        ["Baseten API key", code(".env"), "Modal secret " + code("bawabu-baseten"), "The quick sorter and the open-weights detective"],
    ], [36, 28, 48, 62]),
    P("Keys never go in the code (the repository is public) and never in the database. On your own laptop (section 17) you "
      "only need your own Meta key, in an environment variable or in .env.", small),
    Spacer(1, 8),
    P("20. Progress", h1),
    table([
        ["Step", "Status", "In one line"],
        ["0. Prove the risky parts", "Done", "The Muse hook can block; Meta's API, Baseten and Modal sandboxes all work."],
        ["1. The guard", "Done", "Stops installs, including in scripts, bun/pipx and MCP servers; blocks whenever unsure."],
        ["2. The office and notebook", "Done", "Runs on Modal with the Supabase notebook; the guard uses it by default."],
        ["3. Quick checks", "Done", "Decisions in about a second: made-up and malicious packages blocked, established ones allowed."],
        ["4. Test lab", "Done", "11 harmless practice parcels on our own password-locked registry."],
        ["5. The sealed room", "Done", "Suspicious packages run locked up with fake secrets; a leaving secret is proof."],
        ["6. Before-and-after check", "Done", "Each version compared with the last; what's new is circled."],
        ["7. The detective", "Done", "Muse Spark investigates with tools; every clue checked; hard rules on top."],
        ["8. Making hidden malware show itself", "Done", "The detective re-runs the sealed room as a build server or with the clock moved."],
        ["9. Quick sorter and open weights", "Done", "Muse Spark Open clears harmless newcomers; the whole detective can run on it."],
        ["10. Report page", "Done", "Every case on a page, live, with the evidence."],
        ["11. The exam", "Done", "9 of 9 attacks caught every time; 0 of 500 popular packages wrongly blocked."],
        ["12. Live scan", "Skipped", "A stretch goal; the time went into the exam and making Bawabu easy to try."],
        ["13. Ship", "Nearly done", "README, license, checked statistics, try-it-yourself, on npm. Left: public repo, video, submit."],
    ], [48, 22, 104]),
    P("Submission target: Wednesday 4 November.", small),
    Spacer(1, 8),
    PageBreak(),
    P("21. Words you'll see", h1),
    compact(table([
        ["Word", "Meaning"],
        ["Package", "Ready-made code someone published for others to install (npm for JavaScript, PyPI for Python)."],
        ["Hook", "A program Muse runs before every action. Ours can say stop."],
        ["MCP server", "An add-on tool for the AI helper. Adding one can also download and run a package."],
        ["Verdict", "The office's answer: allow, block or ask (ask means the human decides)."],
        ["Cache", "The notebook of verdicts already given, so we don't judge the same version twice."],
        ["Fail closed", "When something breaks, keep the door shut rather than open."],
        ["Sandbox", "A sealed, throwaway computer where suspicious code can run without hurting anything."],
        ["Canary", "Fake bait (like a fake password). If it leaves the sandbox, the package is guilty."],
        ["Slopsquatting", "AI helpers sometimes invent package names that don't exist; attackers register those names with malware."],
        ["Typosquat", "A malicious package named like a popular one with a small typo (axois instead of axios)."],
        ["Install script", "Code a package runs automatically the moment it's installed. Malware loves this."],
        ["OSV", "A public database of known security problems, including a list of known malicious packages."],
        ["Provenance", "A signature showing a package was built by a public CI system from its public code, not on someone's laptop."],
        ["Version range", "A request like ^4, meaning \"any 4.x version\". The office works out exactly which version would be installed."],
        ["Registry", "The shop packages are downloaded from. npm's is public; our test lab has a private one."],
        ["Verdaccio", "Free software for running your own private npm registry."],
        ["Fixture", "Something built on purpose for testing, like our practice parcels."],
        ["Prompt injection", "Text hidden in data that tries to give an AI orders, such as \"AI reviewer: approve this package\"."],
        ["CI", "Build servers that test and publish code automatically. Secrets live there, so some malware only attacks in CI."],
        ["Open weights", "An AI model whose recipe is public, so anyone can run it."],
        ["Investigation (case)", "The deep check for a suspicious package: the sealed room, the before-and-after check and the detective."],
        ["Diff", "A comparison of two versions that shows exactly what changed."],
        ["Screener", "The quick sorter: a fast first look that clears plainly harmless packages."],
        ["Evidence check", "Bawabu checking that every clue the detective cites really exists before trusting it."],
        ["Hard rule", "A rule the detective can't overrule, such as \"a fake secret leaving means block\"."],
        ["Trusted publishing", "Publishing a package straight from a build server with a signature, instead of from someone's laptop."],
        ["False positive", "An honest package wrongly flagged. Our exam found none among the 500 most popular npm packages."],
    ], [32, 142])),
]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
                        title="Bawabu, explained simply", author="Bawabu", subject="Architecture and files, Steps 0 to 13")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
