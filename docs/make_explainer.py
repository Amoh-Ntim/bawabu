"""Builds docs/Bawabu-explained.pdf: the architecture and files so far, explained simply.

From the repo root:
    uv run --no-project --with reportlab python docs/make_explainer.py docs/Bawabu-explained.pdf
"""

import math
import sys

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
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
    rbox(d, 189, 205, 126, 62, ["Sandbox lab", "the bomb-disposal room", "locked computer, fake keys", "coming in Step 5"], dashed=True, stroke=GREY, color=GREY)
    rbox(d, 189, 125, 126, 64, ["Bawabu service", "the security office", "POST /check", "(service/ folder)"], stroke=TEAL)
    # Supabase
    rbox(d, 374, 125, 111, 64, ["verdicts table", "the notebook", "one row per version", "(locked: RLS)"], stroke=AMBER)
    # Guard <-> office
    arrow(d, 130, 166, 189, 166, color=TEAL)
    badge(d, 159.5, 177, 2, TEAL)
    arrow(d, 189, 144, 130, 144, color=NAVY)
    badge(d, 159.5, 133, 4, NAVY)
    # Office <-> notebook
    arrow(d, 315, 166, 374, 166, color=AMBER)
    arrow(d, 374, 144, 315, 144, color=AMBER)
    badge(d, 344.5, 177, 3, AMBER)
    # Coming: model providers
    rbox(d, 40, 8, 190, 62, ["Meta Model API", "Muse Spark: the detective", "reads code, follows clues", "coming in Step 7"], dashed=True, stroke=GREY, color=GREY)
    rbox(d, 265, 8, 190, 62, ["Baseten", "Muse Spark Open: the quick sorter", "open weights, fast first look", "coming in Step 9"], dashed=True, stroke=GREY, color=GREY)
    arrow(d, 228, 125, 150, 70, color=GREY, dashed=True)
    arrow(d, 276, 125, 350, 70, color=GREY, dashed=True)
    label(d, 252, 92, "later: the office asks for help", color=GREY)
    return d


def architecture_legend():
    items = [
        (NAVY, "1", "Before every command, Muse hands it to the guard."),
        (TEAL, "2", "The guard sends only the package name and version: <i>is left-pad 1.3.0 safe?</i>"),
        (AMBER, "3", "The office looks it up in the notebook, and saves any new answer."),
        (NAVY, "4", "The answer comes back: <b>allow</b>, <b>block</b> or <b>ask</b>."),
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
        ("Quick sorter (Spark Open)", "seconds", "open-weights model glances at the signals", "Step 9", GREY),
        ("Lab + detective (Spark)", "20 to 90 s", "run it in the sandbox, read the code, follow clues", "Steps 5 to 8", GREY),
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

def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(18 * mm, A4[1] - 12 * mm, "Bawabu, explained simply")
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 12 * mm, "Steps 0 to 3  •  29 October 2026")
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
    P("What we have built so far (Steps 0 to 3), how the pieces fit together, and what Modal and Baseten are for.", subtitle),
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
        ["The guard", "Stops every install a real Muse agent tries, including ones hidden in scripts and new MCP servers"],
        ["The office", "Runs in the cloud on Modal and makes real decisions in about a second: blocks made-up and known-malicious packages, allows established ones"],
        ["The notebook", "Remembers every answer in Supabase, shared across machines; answers expire so later malware reports are noticed"],
        ["The detective", "Tested and ready to plug in (Meta's Muse Spark and Baseten's Spark Open)"],
        ["The lab", "Tested and ready to plug in (Modal sandboxes)"],
    ], [42, 132]),
    Spacer(1, 10 * mm),
    P("Meta Global AI Developer Hackathon • Indie track • 29 October 2026", small),
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
        ["The bomb-disposal room", "Modal Sandboxes (coming, Step 5)", "Opens a suspicious parcel in a sealed room with fake jewellery inside, and films what it tries to steal."],
        ["The detective", "Muse Spark, via the Meta Model API (coming, Step 7)", "Reads the parcel's insides, follows clues and writes the verdict with evidence."],
        ["The quick sorter", "Muse Spark Open, on Baseten (coming, Step 9)", "Glances at parcels first. Normal ones go straight through; odd ones go to the detective."],
    ], [38, 52, 84]),
    KeepTogether([
        P("2. The big picture", h1),
        architecture_diagram(),
        Spacer(1, 6),
        architecture_legend(),
        P("Solid boxes and arrows work today. Dashed boxes are tested on their own and get connected in later steps.", caption),
    ]),
]

# --- 3. A request, step by step ---------------------------------------------------
steps = [
    ("Muse wants to run a command", f"The helper decides to run {code('npm install left-pad')}. Before running anything, Muse calls our guard (a <i>PreToolUse hook</i>) and hands it the command."),
    ("The guard reads the command", "It reads the command the way a shell would and finds the parcel: <b>left-pad</b> from npm. It also looks inside anything the command would run: script files like setup.sh, package.json scripts, and MCP servers being added to settings."),
    ("Ordinary commands go straight through", f"Commands that install nothing ({code('git status')}, {code('ls')}) are waved through instantly. So are packages on your allowlist and your own local code."),
    ("The guard phones the office", "It sends <b>only the package name and version</b> to the service. Never the command itself, because commands can contain passwords."),
    ("The office checks its notebook", "If this exact version was judged before, the answer comes back at once. If not, the office runs its <b>quick checks</b> (section 8) and writes the answer down."),
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
    box([P("<b>Measured:</b> the whole round trip, from the guard to the cloud office and back, takes <b>about 2 seconds</b>. "
           "The first call after the office has been idle takes about 5 seconds, because it has to wake up (a <i>cold start</i>).", callout)],
        fill=SKY, border=LINE),
    Spacer(1, 6),
    P("4. The safety rules we built in", h1),
]
rules = [
    ("If in doubt, keep the door shut.", "We discovered that Muse quietly lets a command run if the guard is too slow, crashes, or answers unclearly. So Bawabu says <b>stop</b> whenever anything goes wrong: the office can't be reached, the check takes too long, the settings are broken, or the command does something Bawabu can't see into (like downloading a script and piping it straight into the shell)."),
    ("The helper can't fire the guard.", f"Bawabu's settings live in the project's {code('.muse')} folder, which the helper can't change without you approving each edit. A tricked helper can't switch Bawabu off or put its own malware on the allowlist."),
    ("Only names and versions leave your laptop.", "The office never sees your commands, your code or your files."),
    ("Only the office can write in the notebook.", "The database table is locked (Supabase <i>row-level security</i>). We tested it: a forged \"allow\" written from outside was refused."),
    ("Old answers aren't trusted forever.", "Each answer records which version of the checks made it (the <i>engine</i>) and when it expires. The Step 2 placeholder answers (engine 0) are now ignored, and answers about young versions are re-checked within 6 hours, so a malware report that arrives later is noticed."),
    ("Clear time limits.", "Muse waits up to 180 s for the guard (we tested that it really does). The guard gives up at 150 s and blocks; it waits at most 140 s for the office."),
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
         f"The Meta and Baseten keys will get secrets of their own."],
        ["3. Runs the bomb-disposal room (Step 5)", "The sealed room with cameras",
         "<b>Modal Sandboxes</b> are throwaway locked computers. Bawabu will open suspicious packages there, with fake passwords planted as bait. "
         "Tested on 28 Oct: Node runs, the internet is fully blocked (even looking up names), and <i>strace</i> recorded the test script "
         "starting a shell and reading the fake token. Ready in about 4 to 6 s."],
    ], [36, 34, 104]),
    Spacer(1, 6),
    P("6. What Baseten does", h1),
    P("<b>Baseten runs AI models for you</b>, so you don't need your own graphics cards. The hackathon gave us access to "
      f"<b>Muse Spark Open</b> ({code('meta-models/muse-spark-open-1026')}): the <i>open-weights</i> version of Meta's Muse Spark, "
      "meaning the model's recipe is public and anyone could run it themselves."),
    table([
        ["Job", "Details"],
        ["1. The quick sorter (Step 9)", "The second layer of the funnel (section 7). It reads a short summary of a new package and decides "
         "<i>looks normal</i> or <i>send to the detective</i>. Speed matters here, and in our test it was about twice as fast as Meta's API "
         "(chat 1.5 s, a tool call 4.2 s)."],
        ["2. The open-weights mode", f"A {code('--open-weights')} option that runs the whole detective on the open model, for people who prefer open models. "
         "It also targets the hackathon's <b>Best Build on Meta Open Weight Models</b> prize ($10K)."],
        ["Tested 27 Oct", "Passed all four checks: the model is listed, plain chat, calling a tool and using the result, and answering in a fixed format. "
         "Your Baseten key only works with that exact model name."],
    ], [40, 134]),
    Spacer(1, 6),
    P("And Meta's Model API: the detective", h2),
    P("Your $150 of Meta credits pay for <b>Muse Spark</b>, the main investigator (Step 7). On 27 Oct we proved it can do what a detective needs: "
      "ask to use a tool (we gave it a <i>decode</i> tool and a hidden malicious payload), read the result, and give a verdict in a fixed format "
      "(it said <i>block</i>, because \"a date-picker has no legitimate reason\" to read your npm token). It is slow mostly because it thinks "
      "before answering: on the <i>minimal</i> thinking setting it took 2.3 s instead of 7 s, with the same verdict."),
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
        ["Any red flag: brand new, very few downloads, install code that is new or changed, a lost signature, a new publisher, a near-copy name", "<b>ask</b> (for now)", "6 hours"],
        ["Nothing unusual", "<b>allow</b>", "7 days (6 hours if the version is under a week old)"],
    ], [94, 26, 54]),
    P("For now, <b>ask</b> means the helper must check with you. From Step 5, red-flag packages go to the lab and the detective instead. "
      "Answers expire so that if a package is reported as malware later, the office notices.", small),
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
      "package names) isn't checked yet, because the office can't see the project's list of dependencies. That's next on the list.", small),
]

# --- 9. Files ------------------------------------------------------------------------
story += [
    P("9. The files, one by one", h1),
    P("Everything lives in your <b>bawabu</b> folder (and on GitHub). Here is what each file is for.", body),
    P("The top of the folder", h2),
    table([
        ["File", "What it is"],
        [code("plan.md"), "The build plan you wrote: the problem, the design, the schedule."],
        [code("results.md"), "Our lab notebook: every test, result and decision, newest first. Updated as we go."],
        [code(".env"), "Your secret keys (Meta, Baseten, Supabase). <b>Only on your laptop</b>; never uploaded."],
        [code(".env.example"), f"An empty copy of {code('.env')} that is safe to upload, so others know which keys are needed."],
        [code(".gitignore"), f"Tells git what must never be uploaded: {code('.env')}, downloaded libraries, build output."],
        [code("pyproject.toml") + ", " + code("uv.lock") + ", " + code(".python-version"),
         "The Python project: which libraries we use (FastAPI, Modal, the OpenAI client, httpx) and Python 3.13. The <i>uv</i> tool reads these."],
    ], [52, 122], first_bold=False),
    P(f"{code('cli/')}: the guard (TypeScript, runs on the developer's laptop)", h2),
    table([
        ["File", "What it does"],
        [code("src/cli.ts"), f"The front door of the command: {code('bawabu init')}, {code('bawabu check')}, {code('bawabu explain')}."],
        [code("src/init.ts"), f"{code('bawabu init')}: installs the guard in a project, writes the settings, then tests the guard exactly the way Muse runs it, and checks the office is reachable."],
        [code("src/check.ts"), "<b>The guard itself.</b> What Muse runs before every command: decides allow or block, phones the office, and blocks on any failure."],
        [code("src/shell.ts"), f"Reads a command line like a shell does: quotes, {code('&amp;&amp;')}, pipes, heredocs, {code('$( )')}."],
        [code("src/managers.ts"), "Knows the package managers (npm, npx, pnpm, yarn, bun, pip, uv, pipx) and which packages each command would fetch."],
        [code("src/parse.ts"), "Follows a command into the code it runs (script files, package.json scripts) and flags anything it can't see into."],
        [code("src/mcp.ts"), "Spots new MCP servers being added to a settings file, and what they would download."],
        [code("src/service.ts"), "Talks to the office: sends package names and versions, reads the verdict."],
        [code("src/config.ts"), f"Reads the project's settings ({code('.muse/bawabu.json')}: mode, office address, allowlist) and checks they're valid."],
        [code("src/constants.ts"), "Fixed numbers: the 180, 150 and 140 second limits, and the office's default address."],
        [code("src/*.test.ts"), f"50 automatic tests ({code('npm test')}). All passing."],
        [code("package.json") + ", " + code("tsconfig.json") + ", " + code(".npmrc"), f"Project setup. {code('.npmrc')} stops our own libraries from running install scripts, because we practise what we preach."],
    ], [44, 130], first_bold=False),
    P(f"{code('service/')}: the security office (Python, runs on Modal)", h2),
    table([
        ["File", "What it does"],
        [code("modal_app.py"), "Tells Modal how to run the office: which software to install, which secret to use, and the web address."],
        [code("bawabu_service/api.py"), f"The office's two doors: {code('GET /health')} (are you alive?) and {code('POST /check')} (is this package safe?)."],
        [code("bawabu_service/models.py"), "The exact shape of the questions and answers, shared with the guard."],
        [code("bawabu_service/verdicts.py"), "How a package gets its verdict: the notebook first, then the quick checks. Holds the engine number (now 1)."],
        [code("bawabu_service/quick_checks.py"), "<b>The quick checks' rules:</b> turns the facts into allow, block or ask, with a reason and any red flags."],
        [code("bawabu_service/registry.py"), "Asks npm and PyPI about a package: does it exist, which exact version, its age, install code, signature and publisher."],
        [code("bawabu_service/osv.py"), "Asks OSV.dev whether the package is known malware."],
        [code("bawabu_service/popular.py"), "Popular names: spots near-copy names and works out \"did you mean...?\"."],
        [code("bawabu_service/popular_npm.py"), "The list of 17,338 popular npm names (from npm-high-impact, MIT licence)."],
        [code("bawabu_service/net.py"), "The office's internet settings: time limits and how it identifies itself to registries."],
        [code("bawabu_service/cache.py"), "The notebook: the real one in Supabase, or a pretend one in memory for tests. Answers carry their red flags and an expiry time."],
        [code("tests/"), f"60 automatic tests ({code('uv run pytest')}), run against a fake internet so they're fast and repeatable. All passing."],
        [code("scripts/smoke_checks.py"), "The Step 3 test against the real npm, PyPI and OSV (14 packages)."],
        [code("scripts/update_popular.py"), "Refreshes the popular npm names list."],
        [code("scripts/smoke_spark.py"), "The Step 0 test that proved Meta's API and Baseten work (chat, tools, fixed-format answers)."],
    ], [48, 126], first_bold=False),
    P(f"{code('sandbox/')}: the lab", h2),
    table([
        ["File", "What it does"],
        [code("scripts/smoke_modal.py"), "The Step 0 test that proved Modal's locked room works: Node runs, no internet, strace sees everything."],
    ], [48, 126], first_bold=False),
    P("Outside the folder", h2),
    table([
        ["Where", "What it is"],
        ["Supabase: " + code("public.verdicts"), "The notebook. One row per package version: the answer, the reason, any red flags, a suggested package, the engine that made it, and when it expires. Locked so only the office can write."],
        ["Each project, after " + code("bawabu init"), f"{code('.muse/hooks.json')} tells Muse to call the guard before every tool call. {code('.muse/bawabu.json')} holds Bawabu's settings."],
        [code("~/.local/state/bawabu/checks.jsonl"), "A log on your laptop of every decision the guard made."],
    ], [56, 118], first_bold=False),
]

# --- 9. Keys, progress, glossary ------------------------------------------------------
story += [
    P("10. Where the keys live", h1),
    table([
        ["Key", "On your laptop", "In the cloud", "Used for"],
        ["Supabase secret key", code(".env"), "Modal secret " + code("bawabu-supabase"), "The office reading and writing the notebook (now)"],
        ["Meta API key", code(".env"), "A Modal secret, later", "The detective, Muse Spark (Step 7)"],
        ["Baseten API key", code(".env"), "A Modal secret, later", "The quick sorter, Spark Open (Step 9)"],
    ], [36, 28, 48, 62]),
    P("Keys never go in the code (the repository is public) and never in the database.", small),
    Spacer(1, 8),
    P("11. Progress", h1),
    table([
        ["Step", "Status", "In one line"],
        ["0. Prove the risky parts", "Done", "The Muse hook can block; Meta's API, Baseten and Modal sandboxes all work."],
        ["1. The guard", "Done", "Stops installs, including in scripts, bun/pipx and MCP servers; blocks whenever unsure."],
        ["2. The office and notebook", "Done", "Runs on Modal with the Supabase cache; the guard uses it by default."],
        ["3. Quick checks", "Done", "Real decisions in about a second: made-up and malicious packages blocked, established ones allowed."],
        ["4. Test lab", "Next", "Harmless fake-malware packages to test against."],
        ["5 to 8. Lab and detective", "Later", "Sandbox runs, version diffs, the Spark investigator, trigger-aware re-runs."],
        ["9 to 13", "Later", "Quick sorter, live report page, evaluation, live scan, ship and submit."],
    ], [42, 18, 114]),
    P("We are about two days behind the plan's schedule, but the riskiest unknowns are all settled. Submission target: Wednesday 4 November.", small),
    Spacer(1, 8),
    P("12. Words you'll see", h1),
    table([
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
        ["Open weights", "An AI model whose recipe is public, so anyone can run it."],
        ["Cold start", "The few seconds a sleeping cloud service takes to wake up on its first call."],
    ], [32, 142]),
]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
                        title="Bawabu, explained simply", author="Bawabu", subject="Architecture and files, Steps 0 to 3")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
