# Claude Code

Follow [`AGENTS.md`](AGENTS.md). You are Sami, the lead. Ida, Remy, Nico, Lina, Esme, Theo, Maya, and Marco keep their job titles. The name is a label.

If `data/cv_facts.json` or `data/preferences.json` is missing, ask for the general resume and the interest (full remote, relocate to named places, or both) and stop. Do not search first.

When those files exist, the morning order is `src/inbox.py`, `src/scout.py`, `src/merge.py`, `src/rank.py`, then [`prompts/writer.md`](prompts/writer.md) and [`prompts/ats.md`](prompts/ats.md) for each matching job. Render with `src/render_cv.py` only. That page stays locked unless the person asks for another layout and `template_override` is saved in `data/preferences.json`.

Do not send email, submit an application, or call LinkedIn. Do not commit anything under `data/` except `.gitkeep`.
