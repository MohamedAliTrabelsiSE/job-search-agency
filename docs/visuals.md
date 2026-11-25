# README visuals

The README uses the original dark/gold story style: documents move between
participants, the CV fills with source-backed content, and highlights direct
attention to the next step. The office animation is still the first item.

## Active assets

- `the-office.gif`: original office scene, unchanged.
- `how-it-works.gif`: six scenes following Sami, confirmed onboarding, selected
  scouts, evidence-based fit, drafting/checking, and the stop for user review.
- `who-searches.gif`: original remote/relocate/both selector, unchanged.
- `the-page.gif`: the approved CV fills, relevant claims rise, and long content
  continues onto another sheet. PDF and DOCX retain the same content.
- `ats-loop.gif`: Maya hands the draft to Marco; findings return once, Maya fixes
  once, and Marco rechecks. The filename is historical: this is a factual check,
  not an employer's ATS simulation.
- `job-decisions.gif`: an ad enters country, expertise and requirement assessment,
  then receives a supported decision or a verification hold/exclusion.

The four updated story diagrams loop over 8–12 seconds. Text stays still within
each scene while documents move; there are no text crossfades or flashing. Each
guide has a `*-static.png` companion showing every scene. The README supplies
reduced-motion sources and direct static links. No private candidate data appears.

## Regenerate

From the repository root, with an optional artwork dependency:

```powershell
python -m pip install Pillow
python tools/render_story_animations.py
```

Use `.venv\Scripts\python.exe` on Windows if needed. The renderer uses Segoe UI on
Windows, DejaVu Sans on Linux, or Arial on macOS. Font differences can affect text
spacing; inspect every scene after rendering. `--output PATH` writes a separate
review folder. The original scout GIF is read only to extract held scenes for its
static alternative; neither it nor the office GIF is regenerated.

Review the GIFs at normal README width. Check moving-document paths, readable
labels, no clipping, every frame decoding, correct decision gates and full loops.
The names are workflow stages, not independent language-model agents.

The earlier blue/teal slideshow assets and their two rendering scripts remain in
the repository as prior designs. The README no longer references them. The old
`what-passes.png` is also unused because its bare-remote eligibility explanation
does not match the current conservative checks.
