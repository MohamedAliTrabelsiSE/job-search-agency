# README visuals

`workflow.gif` explains the current workflow in five stages: confirmed profile,
selected scouts, evidence-based assessment, drafting/checking, then user review.
It loops over 20 seconds at 1120 × 650. Text stays stationary during each stage;
only a progress packet and bar move. There are no text crossfades or flashing.

`workflow-overview.png` summarizes the same steps without animation. The README
offers it through a reduced-motion picture source and a direct static-image link.

Both assets come from `tools/render_readme_animation.py`. No real profile, job,
contact detail, or application appears in the artwork.

## Regenerate

From the repository root, with an optional artwork dependency:

```powershell
python -m pip install Pillow
python tools/render_readme_animation.py
```

Use `.venv\Scripts\python.exe` on Windows if needed. The renderer uses Segoe UI on
Windows, DejaVu Sans on Linux, or Arial on macOS. Different fonts can change text
spacing; inspect all five stages after regenerating. Edit the scene text and
graphics in the script instead of making manual changes to the generated images.
`--output PATH` renders to a separate review folder.

Open the GIF and PNG at normal README width. Check readable labels, no clipping,
correct decision gates, all frames decoding, and the complete loop. The animation
illustrates workflow stages, not independent language-model agents. The original
office and earlier explainer assets remain available in `docs/` but are not used
as the README hero.
