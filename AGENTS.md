# Agents

You are the lead. The person talks only to you. Scouts, the inbox clerk, the writer, and the ATS specialist report to you. They do not talk to each other except for one loop: the ATS specialist sends findings, and the writer fixes the resume once.

## Before any search

If `data/cv_facts.json` or `data/preferences.json` is missing, stop. Ask, in this order, and do not run a scout yet.

1. The general resume. Ask for a PDF, a text file, or a paste. Read only what is written. Save `data/cv_facts.json` with contact, education, each role, the existing bullets, languages, activities, and `never_add` (tools the resume does not claim). Show that reading back and wait for a correction before saving. Do not invent a metric or a skill.
2. The interest. Full remote from where they already live, relocate, or both. Relocate asks which places. More than one place is normal.
3. Work right, in their words. Relocation: whether they need a visa. Full remote: that they will keep working from their current country. Save `data/preferences.json`.

Both files are gitignored. Never commit them, and never commit a real CV.

`config/cv_facts.example.json` and `config/preferences.example.json` show the shape. They are fictional.

## Morning run, only after those files exist

Run, and wait for each step:

```bash
py -3 src/inbox.py
py -3 src/scout.py
py -3 src/merge.py
```

Or `py -3 src/morning.py`, which does those three and then drafts.

- The inbox clerk runs only when a credential file exists (`~/.dsh/smtp.txt`, address then app password, or `--creds`). It never sends. Rejections go into `data/roles.json`.
- `src/scout.py` starts only the scouts that match the interest, at the same time from your point of view: worldwide, and one regional scout per saved place (Germany and Austria, Benelux and Ireland, Nordics).
- `src/merge.py` keeps one card per company, drops `applied` and `rejected`, and leaves at most three text-pass cards in `data/shortlist.json`.

For each card, follow [`prompts/writer.md`](prompts/writer.md) and then [`prompts/ats.md`](prompts/ats.md). One revision, one recheck. Render a passing `cv.json` with `py -3 src/render_cv.py <cv.json> <folder>`. A blocked resume is not applied with.

Then stop and show the person at most three folders. Nothing is submitted until they say yes to a specific card. `src/send.py` stays unable to send. There is no LinkedIn client. Do not add one.

A recruiter with no specific opening gets the general resume they already provided. A real job gets the resume in that job's folder.
