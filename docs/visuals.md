# README visuals

The original `the-office.gif` is the first item in the README. It introduces the
team visually; the workflow overview follows the project introduction.

`workflow.gif` explains the current workflow in five stages: confirmed profile,
selected scouts, evidence-based assessment, drafting/checking, then user review.
It loops over 20 seconds at 1120 × 650. Text stays stationary during each stage;
only a progress packet and bar move. There are no text crossfades or flashing.

`workflow-overview.png` summarizes the same steps without animation. The README
offers it through a reduced-motion picture source and a direct static-image link.

Both overview assets come from `tools/render_readme_animation.py`.

Three additional guides explain the important decisions in more detail:

- `cv-generation.gif`: confirmed facts, Maya's draft, Marco's factual checks and
  the passing PDF/DOCX output. Failed checks stay blocked after one revision loop.
- `job-decisions.gif`: explicit country restrictions, essential expertise,
  required/preferred/one-of skills, and the four possible outcomes.
- `search-routing.gif`: remote, relocation, both, and honest coverage reporting.

Each focused guide has four scenes over 16 seconds and a `*-static.png` companion
showing all its scenes. They come from `tools/render_detail_animations.py` and use
the same visual style as the overview. No real profile, job, contact detail, or
application appears in the generated artwork.

## Regenerate

From the repository root, with an optional artwork dependency:

```powershell
python -m pip install Pillow
python tools/render_readme_animation.py
python tools/render_detail_animations.py
```

Use `.venv\Scripts\python.exe` on Windows if needed. The renderer uses Segoe UI on
Windows, DejaVu Sans on Linux, or Arial on macOS. Different fonts can change text
spacing; inspect every scene after regenerating. Edit the scene text and
graphics in the script instead of making manual changes to the generated images.
`--output PATH` renders to a separate review folder.

Open the GIFs and PNGs at normal README width. Check readable labels, no clipping,
correct decision gates, all frames decoding, and the complete loop. The animation
illustrates workflow stages, not independent language-model agents. The original
office animation remains the README hero. Earlier explainer assets remain available
in `docs/`; the current guide animations replace them in the workflow explanation.
