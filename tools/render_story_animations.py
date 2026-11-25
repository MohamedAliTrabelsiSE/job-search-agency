"""Original dark/gold story diagrams, updated for the current workflow.

Optional artwork dependency: Pillow. Run from the repository root:
python tools/render_story_animations.py
"""
import argparse
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1080, 640
BG, PANEL, IDLE = '#0C1117', '#27384B', '#202B37'
GOLD, TEXT, MUTED = '#E8B262', '#F1EEE7', '#B8C3D0'
EDGE, PAPER, INK = '#3B4958', '#F2EEE5', '#26384E'
GREEN, RED = '#9DCCA5', '#E5A19A'


@lru_cache(maxsize=None)
def font(size, bold=False):
    candidates = [
        Path('C:/Windows/Fonts') / ('segoeuib.ttf' if bold else 'segoeui.ttf'),
        Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
        Path('/System/Library/Fonts/Supplemental') / ('Arial Bold.ttf' if bold else 'Arial.ttf'),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError('Install Segoe UI, DejaVu Sans or Arial.')


def text(d, xy, value, size=22, color=TEXT, bold=False):
    d.text(xy, value, fill=color, font=font(size, bold))


def wrap(d, xy, value, width, size=20, color=MUTED):
    x, y = xy
    line = ''
    for word in value.split():
        candidate = (line + ' ' + word).strip()
        if line and d.textlength(candidate, font=font(size)) > width:
            text(d, (x, y), line, size, color)
            y += size + 9
            line = word
        else:
            line = candidate
    text(d, (x, y), line, size, color)


def canvas(topic, title, subtitle, stage, count):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 5), fill=GOLD)
    text(d, (64, 29), topic, 18, GOLD, True)
    text(d, (64, 61), title, 36, TEXT, True)
    text(d, (64, 115), subtitle, 21, MUTED)
    text(d, (978, 29), f'{stage + 1} / {count}', 18, MUTED, True)
    for n in range(count):
        x = W / 2 + (n - (count - 1) / 2) * 18
        d.ellipse((x - 4, 612, x + 4, 620), fill=GOLD if n == stage else EDGE)
    return im, d


def box(d, rect, title, note='', active=False, color=GOLD):
    x, y, x2, y2 = rect
    d.rounded_rectangle(rect, 18, fill=PANEL if active else IDLE, outline=color if active else EDGE, width=2)
    tw = d.textlength(title, font=font(25, True))
    text(d, ((x + x2 - tw) / 2, y + 23), title, 25, TEXT if active else MUTED, True)
    wrap(d, (x + 24, y + 78), note, x2 - x - 48)


def arrow(d, start, end, active=True):
    d.line((*start, *end), fill=GOLD if active else EDGE, width=2)
    x, y = end
    direction = 1 if x >= start[0] else -1
    d.line([(x - direction * 8, y - 5), (x, y), (x - direction * 8, y + 5)], fill=GOLD if active else EDGE, width=2)


def paper(d, x, y, width=160, height=180, rows=4, title='Resume', highlight=False):
    d.rounded_rectangle((x, y, x + width, y + height), 13, fill=PAPER, outline=GOLD if highlight else '#CEC7B9', width=2)
    text(d, (x + 18, y + 18), title, 18, INK, True)
    for n in range(rows):
        yy = y + 67 + n * 22
        ww = (width - 38) * [1, .76, .91, .61][n % 4]
        d.rounded_rectangle((x + 18, yy, x + 18 + ww, yy + 7), 3, fill=GOLD if highlight and n == 0 else '#C6BFAF')


def morning(stage, t):
    titles = ['You talk to one lead', 'Three questions come first', 'The selected team starts',
              'Theo explains the fit', 'A factual check before files', 'The run stops. You decide.']
    subtitles = ['Sami is your contact throughout.', 'Review and confirm the facts before a search starts.',
                 'Only the scouts matching your preferences run.', 'Eligibility and expertise matter; overlap alone is not enough.',
                 'Maya drafts from facts. Marco checks, with one revision and recheck.', 'Nothing is emailed or automatically submitted.']
    im, d = canvas('A morning', titles[stage], subtitles[stage], stage, 6)
    if stage == 0:
        box(d, (70, 230, 470, 500), 'You', 'Your resume and the kind of job you want.', True)
        box(d, (610, 230, 1010, 500), 'Sami', 'Asks, listens, and runs the search for you.', True)
        arrow(d, (470, 365), (610, 365))
        x = 476 + 120 * t
        d.ellipse((x, 359, x + 10, 369), fill=GOLD)
    elif stage == 1:
        prompts = [('Your resume', 'Read back the facts. Keep every role and project.'),
                   ('What you want', 'Remote, relocation, or both. Which countries?'),
                   ('Your work rights', 'Current work country and sponsorship needs.')]
        for n, (title, note) in enumerate(prompts):
            y = 206 + 112 * n
            d.rounded_rectangle((120, y, 960, y + 94), 16, fill=PANEL, outline=GOLD if n <= int(t * 3) else EDGE)
            text(d, (146, y + 27), str(n + 1), 24, GOLD, True)
            text(d, (204, y + 12), title, 25, TEXT, True)
            text(d, (204, y + 51), note, 19)
    elif stage == 2:
        box(d, (60, 230, 340, 493), 'Ida', 'Reads configured mail. Never sends.', True)
        box(d, (380, 230, 720, 493), 'Selected scouts', 'Remy, Nico, Lina, Esme: the routes you selected.', True)
        paper(d, 804, 260, 190, 190, title='Job notes', highlight=True)
        arrow(d, (720, 360), (800, 360))
        text(d, (80, 536), 'Source health and coverage are reported separately from job suitability.', 21)
    elif stage == 3:
        paper(d, 90 + 130 * t, 267, 170, 180, title='Full job ad')
        arrow(d, (390, 355), (490, 355))
        box(d, (490, 223, 960, 480), 'Theo', 'Check work countries, essential expertise, required skills and experience.', True)
        text(d, (84, 530), 'Recommended / stretch → draft. Uncertain / excluded → explanation, no CV.', 21, GOLD)
    elif stage == 4:
        box(d, (60, 250, 345, 490), 'Maya', 'Only source-backed claims.', True)
        box(d, (735, 250, 1020, 490), 'Marco', 'Factual checks. Failed rechecks stay blocked.', True)
        arrow(d, (345, 365), (735, 365))
        paper(d, 360 + 190 * t, 236, 160, 180, highlight=True)
    else:
        paper(d, 150, 242, 180, 205, title='PDF', highlight=True)
        paper(d, 370, 242, 180, 205, title='DOCX')
        arrow(d, (550, 347), (650, 347))
        box(d, (650, 236, 990, 480), 'Your review', 'Inspect the files and decide whether to apply.', True)
        text(d, (150, 532), 'Passing files are prepared. No application is submitted by this pipeline.', 21, GOLD)
    return im


def cv_page(stage, t):
    subtitles = ['The approved layout starts empty.', 'Every role, project, source bullet and language stays.',
                 'Confirmed claims relevant to this job move up.', 'Long facts continue; a passing draft becomes PDF + DOCX.']
    im, d = canvas('The resume', 'Same layout. Your complete facts.', subtitles[stage], stage, 4)
    if stage == 3:
        paper(d, 415 + 25 * t, 225, 345, 310, rows=7, title='Continued')
    d.rounded_rectangle((284, 170, 704, 563), 18, fill=PAPER, outline='#CEC7B9')
    d.line((300, 174, 690, 174), fill=GOLD, width=5)
    if stage:
        text(d, (310, 193), 'Your name', 29, INK, True)
        text(d, (310, 232), 'Your confirmed headline', 17, '#6E7681')
    sections = [('OVERVIEW', 277), ('EXPERIENCE', 336), ('PROJECTS', 395), ('EDUCATION', 454), ('SKILLS + LANGUAGES', 513)]
    for n, (title, y) in enumerate(sections):
        text(d, (310, y), title, 13, INK, True)
        if stage > 0 and (stage > 1 or n <= int(t * 5)):
            fill = GOLD if stage == 2 and n < 3 else '#D3CCBE'
            d.rounded_rectangle((310, y + 24, 310 + [280, 306, 222, 250, 190][n], y + 31), 3, fill=fill)
    if stage == 2:
        box(d, (778, 310, 1018, 495), 'This job', 'Relevant claims rise. Missing skills stay gaps.', True)
    if stage == 3:
        text(d, (812, 274), 'PDF + DOCX', 25, GOLD, True)
        wrap(d, (812, 325), 'Same content. No dropped roles or projects.', 205, 20)
    return im


def review(stage, t):
    subtitles = ['Maya drafts from confirmed facts.', 'The draft goes to Marco for factual checking.',
                 'Marco checks source claims, coverage and work-right wording.',
                 'Findings return to Maya once.', 'Maya fixes once. Marco rechecks once.',
                 'Passing drafts render. Remaining failures stay blocked.']
    im, d = canvas('The resume', 'One draft. One revision. One recheck.', subtitles[stage], stage, 6)
    box(d, (64, 280, 390, 540), 'Maya · writer', 'Uses only confirmed facts.', stage in (0, 3, 4))
    box(d, (690, 280, 1016, 540), 'Marco · checker', 'Checks claims and completeness.', stage in (1, 2, 4))
    arrow(d, (390, 410), (690, 410))
    positions = [(418, 250), (430 + 90 * t, 250), (520, 250), (520 - 100 * t, 250), (420 + 100 * t, 250), (460, 230)]
    x, y = positions[stage]
    paper(d, x, y, 170, 160, rows=3, title='Findings' if stage == 3 else 'Resume', highlight=stage != 1)
    if stage in (3, 4):
        arrow(d, (690, 565), (390, 565))
        text(d, (454, 578), 'One revision loop', 18, GOLD, True)
    if stage == 5:
        d.rounded_rectangle((95, 453, 365, 510), 12, fill=IDLE, outline=GREEN, width=2)
        text(d, (122, 466), 'PASS → PDF + DOCX', 20, GREEN, True)
        d.rounded_rectangle((715, 453, 990, 510), 12, fill=IDLE, outline=RED, width=2)
        text(d, (746, 466), 'FAIL → no resume', 20, RED, True)
    return im


def decisions(stage, t):
    subtitles = ['Read the full ad, not just a remote label.', 'Shared technologies do not replace essential expertise.',
                 'Separate required, preferred and one-of requirements.', 'Explain each outcome. Only eligible supported fits get drafts.']
    im, d = canvas('Which jobs get through', 'Follow the evidence in the ad.', subtitles[stage], stage, 4)
    if stage < 3:
        paper(d, 95 + 45 * t, 252, 185, 200, title='Full job ad', highlight=True)
        arrow(d, (330, 350), (465, 350))
        title, note, outcome = [
            ('Country + work rights', 'An explicit country exclusion overrides worldwide marketing.', 'Unknown hiring country → verify first'),
            ('Essential expertise', 'Python overlap cannot replace required Linux administration.', 'No confirmed core expertise → excluded'),
            ('Requirement context', 'Go preferred is optional. Python or Go is one alternative group.', 'Substantial experience gaps → excluded'),
        ][stage]
        box(d, (465, 225, 1010, 480), title, note, True)
        text(d, (110, 536), outcome, 23, GOLD, True)
    else:
        labels = [('Recommended', 'Supported fit → draft', GREEN), ('Stretch', 'Minor gaps → draft', GOLD),
                  ('Verify first', 'Unresolved → hold', GOLD), ('Excluded', 'Mismatch → no CV', RED)]
        for n, (title, note, color) in enumerate(labels):
            x, y = 80 + (n % 2) * 480, 205 + (n // 2) * 177
            box(d, (x, y, x + 440, y + 150), title, note, True, color)
    return im


def save_story(name, draw, count, output):
    stills = [draw(stage, 1) for stage in range(count)]
    sheet = Image.new('RGB', (W, H * count))
    for n, still in enumerate(stills):
        sheet.paste(still, (0, n * H))
    palette = sheet.quantize(colors=128)
    frames, durations = [], []
    for stage in range(count):
        for tick in range(7):
            frames.append(draw(stage, tick / 6).quantize(palette=palette, dither=Image.Dither.NONE))
            durations.append(1400 if tick == 6 else 100)
    target = output / f'{name}.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True, disposal=1)
    sheet.resize((810, 480 * count), Image.Resampling.LANCZOS).save(output / f'{name}-static.png', optimize=True)
    print(f'{target.name}: {count * 2} seconds; {target.stat().st_size:,} bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, draw, count in [('how-it-works', morning, 6), ('the-page', cv_page, 4), ('ats-loop', review, 6), ('job-decisions', decisions, 4)]:
        save_story(name, draw, count, args.output)
    # Preserve the original scout selector verbatim; only extract its held scenes
    # for a static alternative. Its remote/relocate/both explanation is current.
    selector = Image.open(ROOT / 'docs/who-searches.gif')
    sheet = Image.new('RGB', (1080, 1920))
    for n, index in enumerate((0, 4, 8)):
        selector.seek(index)
        sheet.paste(selector.convert('RGB'), (0, n * 640))
    sheet.resize((810, 1440), Image.Resampling.LANCZOS).save(args.output / 'who-searches-static.png', optimize=True)


if __name__ == '__main__':
    main()
