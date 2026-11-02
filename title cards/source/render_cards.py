"""Render the nine Bawabu title cards (seven plus two architecture cards). Requires Pillow; macOS Helvetica/Menlo.

Run: python3 'title cards/source/render_cards.py' [--theme light]
Text remains editable in the accompanying self-contained SVG files.
"""
from pathlib import Path
from html import escape
import base64
import json
import argparse
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--theme', choices=('dark', 'light'), default='dark')
args = parser.parse_args()
BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
OUT = BASE / 'light mode' if args.theme == 'light' else BASE
(OUT / 'source').mkdir(parents=True, exist_ok=True)
S = 2
W, H = 1920, 1080
NAVY, WHITE, GREY, TEAL = '#0B0F17', '#E6EBF5', '#8B97B0', '#2DD4BF'
LINE, SHEET = '#253142', '#17202E'
# Architecture cards: box fill, then the report page's colours for Bawabu, Spark, caution, danger and safe.
PANEL, TEAL_BG = '#121826', '#102B2A'
VIOLET, VIOLET_BG, AMBER, AMBER_BG = '#A78BFA', '#221B39', '#FBBF24', '#2A2110'
RED, RED_BG, GREEN, GREEN_BG = '#F87171', '#2A1215', '#4ADE80', '#0F2418'
if args.theme == 'light':
    NAVY, WHITE, GREY, TEAL = '#F6F7F9', '#101828', '#5E687B', '#08786C'
    LINE, SHEET = '#D9DEE7', '#E6EAF0'
    PANEL, TEAL_BG = '#FFFFFF', '#E4F7F3'
    VIOLET, VIOLET_BG, AMBER, AMBER_BG = '#6941C6', '#F0EAFC', '#B54708', '#FEF0C7'
    RED, RED_BG, GREEN, GREEN_BG = '#B42318', '#FEE4E2', '#067647', '#DCFAE6'
FONT = '/System/Library/Fonts/Helvetica.ttc'
MONO = '/System/Library/Fonts/Menlo.ttc'

original = Image.open(BASE / 'mascot/bawabu-mascot-original.png').convert('RGBA')
assert original.getchannel('A').getextrema() == (0, 255), 'Mascot must have transparency'
mascot = original.resize((1024, 1024), Image.Resampling.LANCZOS)
if args.theme == 'dark':
    mascot.save(OUT / 'mascot/bawabu-mascot.png')
    mascot.resize((256, 256), Image.Resampling.LANCZOS).save(OUT / 'mascot/bawabu-mascot-small.png')
    for name in ('bawabu-mascot.png', 'bawabu-mascot-small.png'):
        (ROOT / 'docs/images' / name).write_bytes((OUT / 'mascot' / name).read_bytes())

cards = []
manifest = []

class Card:
    def __init__(self, name):
        self.name = name
        self.im = Image.new('RGB', (W*S, H*S), NAVY)
        self.draw = ImageDraw.Draw(self.im)
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><rect width="1920" height="1080" fill="{NAVY}"/>']
        self.texts = []

    def text(self, text, y, size, color=WHITE, bold=False, x=None, mono=False, cx=None):
        font = ImageFont.truetype(MONO if mono else FONT, size*S, index=1 if bold and not mono else 0)
        # Helvetica's macOS face lacks the arrow glyph; use Menlo only for it.
        runs = []
        for i, part in enumerate(text.split('→')):
            if i:
                runs.append(('→', ImageFont.truetype(MONO, size*S)))
            runs.append((part, font))
        width = sum(self.draw.textlength(t, font=f) for t,f in runs)/S
        if cx is not None:
            x = cx - width/2
        if x is None:
            x = (W-width)/2
        box = self.draw.textbbox((x*S, y*S), text, font=font, anchor='ls')
        assert box[0] >= 96*S and box[2] <= (W-96)*S, (self.name, text, box)
        assert box[1] >= 65*S and box[3] <= (H-65)*S, (self.name, text, box)
        cursor = x*S
        for t,f in runs:
            self.draw.text((cursor, y*S), t, font=f, anchor='ls', fill=color)
            cursor += self.draw.textlength(t, font=f)
        family = 'Menlo, monospace' if mono else 'Helvetica, Arial, sans-serif'
        weight = '700' if bold else '400'
        self.parts.append(f'<text x="{x:.3f}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(text)}</text>')
        self.texts.append(text)
        return width

    def rich(self, runs, y, size):
        font = ImageFont.truetype(FONT, size*S, index=1)
        widths = [self.draw.textlength(t, font=font)/S for t,c in runs]
        x = (W-sum(widths))/2
        for (t,c), width in zip(runs, widths):
            self.text(t, y, size, c, True, x)
            x += width

    def mascot(self, y, height):
        # Trim only transparent padding for accurate visible height on each card.
        asset = mascot.crop(mascot.getchannel('A').getbbox())
        width = round(height*asset.width/asset.height)
        x = (W-width)//2
        resized = asset.resize((width*S, height*S), Image.Resampling.LANCZOS)
        self.im.paste(resized, (x*S, y*S), resized)
        import io
        buffer = io.BytesIO()
        asset.save(buffer, format='PNG')
        uri = base64.b64encode(buffer.getvalue()).decode()
        self.parts.append(f'<image x="{x}" y="{y}" width="{width}" height="{height}" href="data:image/png;base64,{uri}"/>')

    def line(self, y):
        self.draw.line((240*S,y*S,1680*S,y*S), fill=LINE, width=2)
        self.parts.append(f'<path d="M240 {y}H1680" stroke="{LINE}"/>')

    def rect(self, x0, y0, x1, y1, border, fill=None, width=3, radius=22):
        fill = fill or PANEL
        self.draw.rounded_rectangle((x0*S, y0*S, x1*S, y1*S), radius*S, fill=fill, outline=border, width=width*S)
        self.parts.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="{radius}" fill="{fill}" stroke="{border}" stroke-width="{width}"/>')

    def box(self, x0, y0, x1, y1, border, title, lines, accent=None, title_y=None, title_size=32):
        """A diagram box: bold title, grey lines, an optional coloured last line (text, colour[, mono])."""
        self.rect(x0, y0, x1, y1, border)
        cx, room = (x0+x1)/2, x1-x0-36
        y = title_y or y0+70
        assert self.text(title, y, title_size, bold=True, cx=cx) <= room, (self.name, title)
        y += 45
        for line in lines:
            assert self.text(line, y, 23, GREY, cx=cx) <= room, (self.name, line)
            y += 33
        if accent:
            text, color, *mono = accent
            assert self.text(text, y1-28, 24, color, bold=True, mono=bool(mono), cx=cx) <= room, (self.name, text)

    def arrow(self, points, color, width=4):
        """A polyline ending in an arrowhead at its last point."""
        (ax, ay), (bx, by) = points[-2], points[-1]
        length = ((bx-ax)**2 + (by-ay)**2) ** .5
        ux, uy = (bx-ax)/length, (by-ay)/length
        base = (bx-ux*18, by-uy*18)
        head = [(bx, by), (base[0]-uy*10, base[1]+ux*10), (base[0]+uy*10, base[1]-ux*10)]
        shaft = points[:-1] + [base]
        self.draw.line([(x*S, y*S) for x, y in shaft], fill=color, width=width*S, joint='curve')
        self.draw.polygon([(x*S, y*S) for x, y in head], fill=color)
        self.parts.append(f'<polyline points="{" ".join(f"{x:g},{y:g}" for x, y in shaft)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')
        self.parts.append(f'<polygon points="{" ".join(f"{x:g},{y:g}" for x, y in head)}" fill="{color}"/>')

    def pill(self, text, cy, color, tint, size=24, cx=None, x=None):
        """A rounded tinted label; returns its width."""
        font = ImageFont.truetype(FONT, size*S, index=1)
        width = self.draw.textlength(text, font=font)/S + 2*size
        x0 = x if x is not None else cx - width/2
        self.rect(x0, cy-size*.95, x0+width, cy+size*.95, color, fill=tint, width=2, radius=size)
        self.text(text, cy+size*.36, size, color, True, x=x0+size)
        return width

    def save(self):
        self.im.resize((W,H), Image.Resampling.LANCZOS).save(OUT / f'{self.name}.png', dpi=(144,144))
        (OUT / 'source' / f'{self.name}.svg').write_text('\n'.join(self.parts)+ '</svg>\n')
        cards.append(self.name)
        manifest.append({'file':f'{self.name}.png','size':[W,H],'text':self.texts})

c = Card('card-1-context')
c.text('Meta Global AI Developer Hackathon · 26 Oct – 4 Nov 2026', 180, 32, TEAL)
c.text('Bawabu was built', 450, 80, bold=True)
c.text('during this hackathon.', 548, 80, bold=True)
c.text('Before the event: no Bawabu code, repository or service', 658, 40, GREY)
c.text('(first commit: 27 October)', 713, 34, GREY)
c.text('Built on: Muse Code · Muse Spark · Muse Spark Open (Meta)', 921, 32, GREY)
c.text('Modal · Baseten · Supabase · Verdaccio · OSV.dev', 968, 32, GREY)
c.save()

c = Card('card-2a-stat')
c.text('+1,444%', 540, 208, TEAL, True)
c.text('malicious open-source packages, 2024 → 2025', 654, 56)
c.text('Source: OpenSSF, via Google Threat Intelligence', 955, 32, GREY)
c.save()

c = Card('card-2b-worm')
c.text('171 packages', 540, 172, TEAL, True)
c.text('hit by the Mini Shai-Hulud worm, May 2026', 654, 56)
c.text('Source: Cloud Security Alliance', 955, 32, GREY)
c.save()

c = Card('card-2c-agent')
c.rich([('An ',WHITE),('AI agent',TEAL),(' added',WHITE)], 430, 80)
c.text('a malicious package', 532, 80, bold=True)
c.text('to a real project.', 634, 80, bold=True)
c.text('Source: Google Threat Intelligence', 955, 32, GREY)
c.save()

c = Card('card-3-title')
c.mascot(180,300)
c.text('Bawabu', 678, 156, bold=True)
c.text('the gatekeeper between AI coding agents', 790, 48, GREY)
c.text('and the packages they install', 854, 48, GREY)
c.save()

# 3b: the funnel, for "Normal packages pass in under a second. Suspicious ones get investigated."
c = Card('card-3b-architecture')
c.text('HOW IT WORKS', 140, 28, TEAL, True)
c.text('Every install goes through the gate', 215, 60, bold=True)
BW, TOP, BOTTOM = 280, 370, 590
xs = [130, 460, 850, 1180, 1510]
centers = [x + BW/2 for x in xs]
c.rect(106, 300, 764, 620, LINE, fill=SHEET, width=2, radius=28)
c.rect(826, 300, 1814, 620, LINE, fill=SHEET, width=2, radius=28)
c.text('YOUR MACHINE', 345, 22, GREY, True, x=130)
c.text('BAWABU SERVICE · MODAL', 345, 22, GREY, True, x=850)
for x, border, title, lines, accent in [
    (xs[0], GREY, 'Muse Code', ['AI coding agent', 'starts an install'], ('npm install x', WHITE, 'mono')),
    (xs[1], TEAL, 'Bawabu hook', ['stops the install,', 'asks the service'], ('name + version', TEAL)),
    (xs[2], TEAL, 'Quick checks', ['known malware,', 'made-up names'], ('about 1 s', TEAL)),
    (xs[3], VIOLET, 'Screener', ['Muse Spark Open', '(open weights)'], ('a few seconds', VIOLET)),
    (xs[4], RED, 'Investigation', ['locked sandbox', '+ Muse Spark'], ('30–90 s', RED)),
]:
    c.box(x, TOP, x+BW, BOTTOM, border, title, lines, accent, title_y=TOP+62)
for a, b in zip(xs, xs[1:]):
    c.arrow([(a+BW, 480), (b, 480)], GREY)
# Each stage can answer; the answer goes back through the hook.
RETURN = 770
for cx, text, color, tint in [(centers[2], 'allow · block', TEAL, TEAL_BG), (centers[3], 'allow', VIOLET, VIOLET_BG),
                              (centers[4], 'allow · block · ask', RED, RED_BG)]:
    c.draw.line((cx*S, BOTTOM*S, cx*S, RETURN*S), fill=color, width=4*S)
    c.parts.append(f'<path d="M{cx:g} {BOTTOM}V{RETURN}" stroke="{color}" stroke-width="4"/>')
    c.pill(text, 680, color, tint, cx=cx)
c.arrow([(centers[4], RETURN), (centers[1], RETURN), (centers[1], BOTTOM)], TEAL)
c.text('the answer goes back to the agent, with the evidence and a report link', 822, 28, cx=(centers[1]+centers[4])/2)
c.text('Most packages are cleared by the quick checks. Only red flags go further.', 955, 30, GREY)
c.save()

# 3c: inside an investigation (optional).
c = Card('card-3c-investigation')
c.text('INSIDE AN INVESTIGATION', 140, 28, TEAL, True)
c.text('Muse Spark has to prove every claim', 215, 60, bold=True)
c.box(130, 300, 560, 470, TEAL, 'Diff engine', ['what changed since', 'the previous version'])
c.box(130, 530, 560, 700, TEAL, 'Sandbox X-ray', ['locked Modal sandbox,', 'fake secrets planted'])
c.rect(700, 300, 1220, 700, VIOLET)
c.text('Muse Spark', 378, 44, bold=True, cx=960)
c.text('Meta Model API', 422, 24, VIOLET, True, cx=960)
for i, line in enumerate(['reads the code', 'decodes what’s hidden', 'asks for a sandbox re-run', 'cites evidence for each claim']):
    c.text(line, 500 + i*50, 30, cx=960)
c.box(1360, 300, 1790, 470, AMBER, 'Evidence check', ['every claim checked against', 'what the tools saw'])
c.box(1360, 530, 1790, 700, RED, 'Hard rules', ['a stolen fake secret', 'means block, always'])
c.arrow([(560, 385), (700, 385)], GREY)
c.arrow([(560, 590), (700, 590)], GREY)
c.arrow([(700, 650), (560, 650)], AMBER)
c.text('re-run', 690, 22, AMBER, True, cx=630)
c.arrow([(1220, 385), (1360, 385)], GREY)
c.arrow([(1575, 470), (1575, 530)], GREY)
c.arrow([(1575, 700), (1575, 790)], GREY)
c.rect(130, 790, 1790, 910, LINE)
c.text('Verdict', 862, 34, bold=True, x=170)
x = 340
for text, color, tint in [('ALLOW', GREEN, GREEN_BG), ('BLOCK', RED, RED_BG), ('ASK', AMBER, AMBER_BG)]:
    x += c.pill(text, 850, color, tint, x=x) + 16
c.text('with the evidence and a report link · saved in Supabase', 862, 28, GREY, x=x+20)
c.text('Claims the tools can’t back up are thrown out.', 975, 30, GREY)
c.save()

c = Card('card-4-results')
for number, lines, baseline in [
    ('9 / 9',['attack samples caught, in every run,','with both models'],350),
    ('0 / 500',['of the most popular npm','packages blocked'],565),
    ('0.7 s',['for a normal package'],780),
]:
    c.text(number, baseline, 116, TEAL, True, x=240)
    y = baseline - 38 if len(lines)>1 else baseline-22
    for line in lines:
        c.text(line,y,48,x=800)
        y += 63
c.line(419)
c.line(634)
c.text('Full results: github.com/Amoh-Ntim/bawabu (eval/RESULTS.md)', 968, 32, GREY)
c.save()

c = Card('card-5-end')
c.mascot(138,240)
c.text('Bawabu', 529, 112, bold=True)
c.text('npm i -g bawabu', 675, 64, TEAL, mono=True)
c.text('github.com/Amoh-Ntim/bawabu', 786, 48)
c.text('Built during the Meta Global AI Developer Hackathon', 928, 32, GREY)
c.text('Muse Code · Muse Spark · Muse Spark Open', 975, 32, GREY)
c.save()

(OUT / 'source/manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n')

sheet = Image.new('RGB',(1640,20+(len(cards)+1)//2*515),SHEET)
d = ImageDraw.Draw(sheet)
font = ImageFont.truetype(FONT,24)
for i,name in enumerate(cards):
    x = 20 + (i%2)*820
    y = 20 + (i//2)*515
    thumb = Image.open(OUT/f'{name}.png').resize((800,450),Image.Resampling.LANCZOS)
    sheet.paste(thumb,(x,y))
    d.text((x+12,y+465),name,font=font,fill=WHITE)
sheet.save(OUT/'preview.png')
print(f'Rendered {len(cards)} {args.theme} cards, editable SVGs, and preview in {OUT}.')
