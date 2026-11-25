"""Render README artwork. Optional dependency: Pillow (not needed by the app).

python -m pip install Pillow
python tools/render_readme_animation.py
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1120, 650
BG = '#0C1424'
PANEL = '#152238'
INNER = '#1C2E46'
LINE = '#31465F'
TEXT = '#F3F7FC'
MUTED = '#ACBCD0'
TEAL = '#68E0C3'
AMBER = '#F4C676'
CORAL = '#F3939B'
BLUE = '#97BBFF'
STEPS = ['Confirm', 'Search', 'Assess', 'Draft + check', 'Your decision']
SCENES = [
    ('YOUR PROFILE', 'Start with what is true.',
     'Confirm your resume facts, work country and relocation preferences before searching.'),
    ('SELECTED SCOUTS', 'Search with context.',
     'Only scouts matching your preferences run. Ida reads mail when configured. Coverage stays visible.'),
    ('THEO ASSESSES', 'Evidence before a shortlist.',
     'Check location, core expertise and experience. Uncertain jobs wait for verification.'),
    ('MAYA + MARCO', 'Your facts. A tailored resume.',
     'Maya drafts from confirmed facts. Marco checks claims, with one revision and one recheck.'),
    ('BACK TO YOU', 'Review. Then decide.',
     'Get a job folder with a PDF and matching DOCX. The pipeline stops here. You decide whether to apply.'),
]


def font(size, bold=False):
    candidates = [
        Path('C:/Windows/Fonts') / ('segoeuib.ttf' if bold else 'segoeui.ttf'),
        Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
        Path('/System/Library/Fonts/Supplemental') / ('Arial Bold.ttf' if bold else 'Arial.ttf'),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError('Install Segoe UI, DejaVu Sans or Arial to render this artwork.')


def label(d, xy, text, size=20, color=TEXT, bold=False):
    d.text(xy, text, font=font(size, bold), fill=color)


def wrapped(d, xy, text, width, size=21, color=MUTED):
    x, y = xy
    line = ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if d.textlength(trial, font=font(size)) > width and line:
            label(d, (x, y), line, size, color)
            line, y = word, y + size + 10
        else:
            line = trial
    label(d, (x, y), line, size, color)


def box(d, rect, fill=PANEL, outline=None, radius=16):
    d.rounded_rectangle(rect, radius, fill=fill, outline=outline, width=2)


def check(d, x, y, color=TEAL):
    d.line([(x, y + 6), (x + 5, y + 11), (x + 15, y)], fill=color, width=3)


def base():
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    # Restrained grid gives the workflow a shared visual home.
    for x in range(32, W, 32):
        for y in range(24, H, 32):
            d.point((x, y), fill='#23334A')
    box(d, (44, 35, 75, 66), TEAL, radius=9)
    d.line([(51, 56), (58, 45), (67, 56)], fill=BG, width=3)
    label(d, (88, 34), 'job-search-agency', 25, TEXT, True)
    box(d, (930, 35, 1076, 69), INNER, LINE, 17)
    label(d, (955, 39), 'WORKFLOW', 17, MUTED, True)
    label(d, (44, 103), 'Your next role. A clearer path.', 43, TEXT, True)
    label(d, (46, 163), 'Real openings. Evidence you can inspect. You stay in control.', 23, MUTED)
    d.line((80, 244, 1030, 244), fill=LINE, width=3)
    box(d, (44, 308, 1076, 568), PANEL, LINE, 22)
    d.line((531, 333, 531, 541), fill=LINE, width=1)
    d.ellipse((47, 603, 57, 613), fill=TEAL)
    label(d, (68, 594), 'Sami is your contact throughout.', 20, MUTED)
    label(d, (780, 594), 'No automatic submissions.', 20, TEAL, True)
    return im


def scene(index, progress=0.5):
    im = base()
    d = ImageDraw.Draw(im)
    for n, name in enumerate(STEPS):
        x = 80 + n * 237.5
        if n < index:
            d.line((x, 244, x + 237.5, 244), fill=TEAL, width=3)
        active = n == index
        d.ellipse((x - 16, 228, x + 16, 260), fill=TEAL if n <= index else INNER, outline=TEAL if active else LINE, width=2)
        if n < index:
            check(d, x - 7, 238, BG)
        else:
            text = str(n + 1)
            tw = d.textlength(text, font=font(18, True))
            label(d, (x - tw / 2, 230), text, 18, BG if active else MUTED, True)
        tw = d.textlength(name, font=font(18, active))
        label(d, (x - tw / 2, 273), name, 18, TEXT if active else MUTED, active)
    # A moving packet and timed bar supply gentle motion without text fades.
    if index < 4:
        x = 80 + index * 237.5 + 24 + progress * 189
        d.ellipse((x - 4, 240, x + 4, 248), fill=TEAL)
    tag, title, body = SCENES[index]
    label(d, (68, 336), f'0{index + 1} / {tag}', 17, TEAL, True)
    wrapped(d, (68, 377), title, 435, 29, TEXT)
    wrapped(d, (68, 457 if index == 3 else 432), body, 426, 21)
    if index == 0:
        for y, title, subtitle in [(335, 'Resume facts', 'Roles, projects, skills, languages'), (437, 'Work preferences', 'Remote country + relocation + rights')]:
            box(d, (557, y, 1050, y + 88), INNER)
            check(d, 578, y + 30)
            label(d, (609, y + 13), title, 23, TEXT, True)
            label(d, (609, y + 48), subtitle, 18, MUTED)
    elif index == 1:
        for n, (name, region) in enumerate([('Remy', 'Worldwide remote'), ('Nico', 'Germany / Austria'), ('Lina', 'Benelux / Ireland'), ('Esme', 'Nordics')]):
            x, y = 557 + (n % 2) * 252, 335 + (n // 2) * 102
            box(d, (x, y, x + 241, y + 88), INNER)
            label(d, (x + 16, y + 12), name, 23, TEXT, True)
            label(d, (x + 16, y + 48), region, 18, MUTED)
            d.ellipse((x + 213, y + 21, x + 221, y + 29), fill=TEAL)
    elif index == 2:
        for n, (name, note, color) in enumerate([
            ('Recommended', 'Supported fit', TEAL), ('Stretch', 'Minor, visible gaps', BLUE),
            ('Verify first', 'No resume yet', AMBER), ('Excluded', 'Explicit mismatch', CORAL),
        ]):
            x, y = 557 + (n % 2) * 252, 335 + (n // 2) * 102
            box(d, (x, y, x + 241, y + 88), INNER)
            d.rounded_rectangle((x + 12, y + 15, x + 16, y + 71), 2, fill=color)
            label(d, (x + 29, y + 12), name, 22, color, True)
            label(d, (x + 29, y + 49), note, 18, MUTED)
    elif index == 3:
        for x, name, duty in [(557, 'Maya', 'Draft from facts'), (821, 'Marco', 'Check the claims')]:
            box(d, (x, 350, x + 229, 463), INNER)
            label(d, (x + 20, 367), name, 27, TEXT, True)
            label(d, (x + 20, 413), duty, 19, MUTED)
        d.line((793, 405, 812, 405), fill=TEAL, width=2)
        d.line((806, 399, 812, 405, 806, 411), fill=TEAL, width=2)
        d.line((936, 475, 936, 504, 671, 504, 671, 475), fill=AMBER, width=2)
        box(d, (685, 489, 919, 522), PANEL, radius=8)
        label(d, (699, 492), 'One revision + recheck', 18, AMBER)
    else:
        for x, ext, color in [(559, 'PDF', TEAL), (723, 'DOCX', BLUE)]:
            box(d, (x, 338, x + 143, 450), INNER)
            label(d, (x + 18, 353), ext, 25, color, True)
            for width, y in [(94, 400), (71, 414), (86, 428)]:
                d.line((x + 19, y, x + 19 + width, y), fill=LINE, width=4)
        box(d, (888, 338, 1050, 450), '#203E43', TEAL)
        label(d, (912, 355), 'YOUR', 24, TEAL, True)
        label(d, (909, 390), 'REVIEW', 24, TEAL, True)
        box(d, (559, 471, 1050, 528), INNER)
        label(d, (587, 482), 'Application-ready files. Your decision.', 21, TEXT, True)
    d.rounded_rectangle((44, 636, 1076, 640), 2, fill=LINE)
    d.rounded_rectangle((44, 636, 44 + 1032 * (index + progress) / 5, 640), 2, fill=TEAL)
    return im


def overview():
    im = base()
    d = ImageDraw.Draw(im)
    # Static alternative summarizes every stage without depending on a GIF frame.
    d.rectangle((40, 220, 1080, 580), fill=BG)
    notes = [('Your facts', 'Confirm profile'), ('Selected scouts', 'Report coverage'), ('Theo assesses', 'Explain fit / holds'), ('Maya + Marco', 'Draft / check once'), ('Back to you', 'Review PDF + DOCX')]
    for n, (name, note) in enumerate(notes):
        x = 44 + n * 211
        box(d, (x, 259, x + 188, 461), PANEL, LINE)
        label(d, (x + 18, 278), f'0{n + 1}', 24, TEAL, True)
        wrapped(d, (x + 18, 329), name, 160, 23, TEXT)
        wrapped(d, (x + 18, 401), note, 160, 18, MUTED)
        if n < 4:
            label(d, (x + 193, 345), '›', 24, TEAL)
    label(d, (46, 514), 'Uncertain or excluded jobs get an explanation, not an application resume.', 24, AMBER)
    return im


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    stills = [scene(i) for i in range(5)]
    sheet = Image.new('RGB', (W, H * 5))
    for i, im in enumerate(stills):
        sheet.paste(im, (0, i * H))
    palette = sheet.quantize(colors=128)
    frames = [scene(i, tick / 15).quantize(palette=palette, dither=Image.Dither.NONE)
              for i in range(5) for tick in range(16)]
    target = args.output / 'workflow.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=250,
                   loop=0, optimize=True, disposal=1)
    overview().save(args.output / 'workflow-overview.png', optimize=True)
    print(f'{target}: {W} x {H}, {len(frames)} frames, 20 seconds, {target.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
