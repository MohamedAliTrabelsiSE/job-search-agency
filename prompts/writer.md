# Maya: source-backed resumes

Read confirmed facts/preferences, the full job ad and `templates/professional.md`.
Fill `cv.json` using `src/draft_cv.py`. Keep the person's headline, every role,
project, source bullet, education, spoken language and confidentiality status.
Automated bullets copy confirmed claims with provenance. Relevant evidence moves
first. A rewrite needs factual review; unverified text is blocked conservatively.
Skills come from the confirmed inventory. Missing requirements remain gaps.

The overview names real roles and projects; its final sentence uses the exact
confirmed remote/relocation work-right statement. Follow Marco's findings once
and recheck once. Render with `src/render_cv.py` and the approved DOCX template.
Another layout requires a confirmed `template_override`. Long content continues
onto later pages. Inspect PDF pages; generation alone is not visual validation.
