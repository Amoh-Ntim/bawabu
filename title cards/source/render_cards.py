"""Render the seven Bawabu title cards. Requires Pillow; macOS Helvetica/Menlo.

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
if args.theme == 'light':
    NAVY, WHITE, GREY, TEAL = '#F6F7F9', '#101828', '#5E687B', '#08786C'
    LINE, SHEET = '#D9DEE7', '#E6EAF0'
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

    def text(self, text, y, size, color=WHITE, bold=False, x=None, mono=False):
        font = ImageFont.truetype(MONO if mono else FONT, size*S, index=1 if bold and not mono else 0)
        # Helvetica's macOS face lacks the arrow glyph; use Menlo only for it.
        runs = []
        for i, part in enumerate(text.split('→')):
            if i:
                runs.append(('→', ImageFont.truetype(MONO, size*S)))
            runs.append((part, font))
        width = sum(self.draw.textlength(t, font=f) for t,f in runs)/S
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

sheet = Image.new('RGB',(1640,2080),SHEET)
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
