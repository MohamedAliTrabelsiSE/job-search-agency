"""Render the three focused README guides (optional dependency: Pillow)."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw
from render_readme_animation import (
    ROOT, W, H, BG, PANEL, INNER, LINE, TEXT, MUTED, TEAL, AMBER,
    CORAL, BLUE, base, box, label, wrapped,
)

GUIDES = {
    'cv-generation': {
        'title': 'A tailored CV. Facts stay intact.',
        'subtitle': 'Confirmed facts → Maya drafts → Marco checks → application files',
        'tabs': ['Confirmed source', 'Tailored draft', 'Factual check', 'Passing output'],
        'captions': [
            'Review your facts first. Keep every role, project, bullet and spoken language.',
            'Maya reorders confirmed claims for the job. Missing skills never become your skills.',
            'Marco checks claims and work rights. One revision + one recheck; failures stay blocked.',
            'A passing draft uses the approved layout. PDF and DOCX keep the same content.',
        ],
    },
    'job-decisions': {
        'title': 'A shared skill is only the beginning.',
        'subtitle': 'Theo checks eligibility and essential expertise before recommending a job.',
        'tabs': ['Location + rights', 'Core expertise', 'Required vs optional', 'Explain the outcome'],
        'captions': [
            'Remote does not mean worldwide. Explicit hiring restrictions override broad labels.',
            'A Python overlap cannot replace required Linux, networking or cloud expertise.',
            'Preferred skills are optional. One-of alternatives are assessed as alternatives.',
            'Recommended or stretch can get a CV. Verification holds and exclusions do not.',
        ],
    },
    'search-routing': {
        'title': 'Your preferences choose the scouts.',
        'subtitle': 'Remote, relocation, or both. Search scope stays visible.',
        'tabs': ['Remote', 'Relocation', 'Both', 'Coverage report'],
        'captions': [
            'Remote work starts from your confirmed current country. Remy searches public boards.',
            'Relocation uses your selected countries. Only matching regional scouts run.',
            'Both combines the relevant routes. Ida reads mail only when configured; she never sends.',
            'Verified discoveries can expand the seeds. Healthy boards do not prove market coverage.',
        ],
    },
}


def card(d, rect, title, note, color=TEAL, active=True, tag=None):
    x, y, x2, y2 = rect
    box(d, rect, PANEL if active else INNER, color if active else LINE)
    if tag:
        label(d, (x + 18, y + 16), tag, 16, color if active else MUTED, True)
    wrapped(d, (x + 18, y + 50), title, x2 - x - 36, 25, TEXT if active else MUTED)
    wrapped(d, (x + 18, y + 119), note, x2 - x - 36, 19, MUTED)


def frame(key, stage, progress=0.5):
    info = GUIDES[key]
    im = base()
    d = ImageDraw.Draw(im)
    d.rectangle((40, 90, 1080, 580), fill=BG)
    label(d, (44, 104), info['title'], 39, TEXT, True)
    label(d, (46, 163), info['subtitle'], 22, MUTED)
    for n, tab in enumerate(info['tabs']):
        x = 44 + n * 264
        box(d, (x, 225, x + 240, 267), '#203E43' if n == stage else INNER, TEAL if n == stage else None, 12)
        label(d, (x + 14, 233), tab, 18, TEAL if n == stage else MUTED, n == stage)
    if key == 'cv-generation':
        items = [
            ('Confirmed facts', 'Roles, projects, skills, languages', 'YOUR SOURCE'),
            ('Maya drafts', 'Only source-backed claims', 'FOR THIS JOB'),
            ('Marco checks', 'Claims + coverage', 'FACTUAL REVIEW'),
            ('PDF + DOCX', 'Same content, approved layout', 'YOUR JOB FOLDER'),
        ]
        for n, (title, note, tag) in enumerate(items):
            x = 44 + n * 264
            card(d, (x, 297, x + 240, 493), title, note, active=n == stage, tag=tag)
            if n < 3:
                label(d, (x + 245, 376), '›', 28, TEAL)
        if stage == 2:
            label(d, (602, 464), 'Revise once ↔ recheck', 16, AMBER, True)
    elif key == 'job-decisions':
        if stage == 0:
            card(d, (44, 297, 548, 493), 'Worldwide, except your country', 'Explicit country exclusion → excluded', CORAL, tag='EXAMPLE: COUNTRY RESTRICTION')
            card(d, (572, 297, 1076, 493), 'Remote, hiring country unclear', 'Unresolved location → verify first', AMBER, tag='EXAMPLE: MISSING EVIDENCE')
        elif stage == 1:
            card(d, (44, 297, 548, 493), 'Shared technology: Python', 'Overlap is evidence, not the whole assessment.', BLUE, tag='WHAT MATCHES')
            card(d, (572, 297, 1076, 493), 'Required: Linux administration', 'No confirmed core expertise → excluded', CORAL, tag='WHAT IS STILL MISSING')
        elif stage == 2:
            for n, (title, note, color, tag) in enumerate([
                ('Python required', 'A mandatory skill stays mandatory.', TEAL, 'REQUIRED'),
                ('Go preferred', 'A preference is not a required gap.', BLUE, 'OPTIONAL'),
                ('Python or Go', 'One confirmed option satisfies this group.', AMBER, 'ONE OF'),
            ]):
                x = 44 + n * 352
                card(d, (x, 297, x + 328, 493), title, note, color, tag=tag)
        else:
            for n, (title, note, color) in enumerate([
                ('Recommended', 'Supported fit → draft', TEAL), ('Stretch', 'Minor gaps → draft', BLUE),
                ('Verify first', 'Unknowns → hold', AMBER), ('Excluded', 'Mismatch → no CV', CORAL),
            ]):
                x = 44 + n * 264
                card(d, (x, 297, x + 240, 493), title, note, color, tag='DECISION')
    else:
        scouts = [
            ('Remy', 'Worldwide remote', 'CURRENT COUNTRY'),
            ('Nico', 'Germany / Austria', 'SELECTED COUNTRIES'),
            ('Lina', 'Benelux / Ireland', 'SELECTED COUNTRIES'),
            ('Esme', 'Nordics', 'SELECTED COUNTRIES'),
        ]
        if stage < 3:
            for n, (name, region, tag) in enumerate(scouts):
                x = 44 + n * 264
                active = stage == 2 or (stage == 0 and n == 0) or (stage == 1 and n > 0)
                card(d, (x, 297, x + 240, 493), name, region, active=active, tag=tag)
        else:
            for n, (title, note, color, tag) in enumerate([
                ('Source health', 'Healthy, failed and incomplete feeds.', TEAL, 'WHAT RESPONDED'),
                ('Search scope', 'Seed-only or expanded discovery.', BLUE, 'WHERE WE LOOKED'),
                ('Open questions', 'Unknown eligibility stays visible.', AMBER, 'WHAT NEEDS REVIEW'),
            ]):
                x = 44 + n * 352
                card(d, (x, 297, x + 328, 493), title, note, color, tag=tag)
    box(d, (44, 516, 1076, 575), INNER, radius=12)
    wrapped(d, (60, 530), info['captions'][stage], 1000, 20, TEXT)
    d.rectangle((44, 634, 1076, 642), fill=BG)
    d.rounded_rectangle((44, 636, 1076, 640), 2, fill=LINE)
    d.rounded_rectangle((44, 636, 44 + 1032 * (stage + progress) / 4, 640), 2, fill=TEAL)
    return im


def render(key, output):
    stills = [frame(key, stage) for stage in range(4)]
    sheet = Image.new('RGB', (W, H * 4))
    for stage, still in enumerate(stills):
        sheet.paste(still, (0, stage * H))
    palette = sheet.quantize(colors=128)
    frames = [frame(key, stage, tick / 15).quantize(palette=palette, dither=Image.Dither.NONE)
              for stage in range(4) for tick in range(16)]
    target = output / f'{key}.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=250,
                   loop=0, optimize=True, disposal=1)
    # One static sheet includes every scene, not just the opening frame.
    sheet.resize((840, 1950), Image.Resampling.LANCZOS).save(output / f'{key}-static.png', optimize=True)
    print(f'{target.name}: 64 frames, 16 seconds, {target.stat().st_size:,} bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for key in GUIDES:
        render(key, args.output)


if __name__ == '__main__':
    main()
