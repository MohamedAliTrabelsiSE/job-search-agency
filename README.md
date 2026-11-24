# job-search-agency

A small agency that finds roles and stops before anyone is contacted. Open it in Cursor, Claude, DeepSeek, or any agent that reads [`AGENTS.md`](AGENTS.md). The first thing it does is ask you for a general resume and how you want to work.

Nothing in this repo sends an email or submits an application.

## First run

The agent stops until both files exist. It will ask you:

1. For your general resume (a file or a paste). It reads it back and waits for you to correct it, then saves `data/cv_facts.json`.
2. Whether you want full remote from where you already live, relocation, or both. Relocation asks which places. More than one place is normal.
3. Your work-right line, in your words. Relocation: whether you need a visa. Remote: that you will keep working from your current country. Saved in `data/preferences.json`.

Those files are gitignored. [`config/cv_facts.example.json`](config/cv_facts.example.json) and [`config/preferences.example.json`](config/preferences.example.json) are a fictional person, so you can see the shape. Do not put your real resume in them.

Search uses Python 3.11 and the standard library. Rendering a resume also needs `python-docx` (`pip install python-docx`).

```bash
py -3 tests/test_screen.py
py -3 tests/test_agency.py
py -3 src/morning.py
```

`morning.py` refuses to start while the two data files are missing. After you have confirmed them, it reads the inbox only if `~/.dsh/smtp.txt` exists (address, then an app password), runs the scouts that match your interest, and writes at most three job folders under `outbox/`. Each folder has that job's own resume. You decide later whether any of them is submitted.

`py -3 src/send.py` exits on purpose. There is no SMTP client in this repository.

## Your own boards and rules

Edit the example YAML, or copy it and pass the copies:

```bash
py -3 src/discover.py --sources config/sources.example.yaml --rules config/rules.example.yaml
```

- `ashby`, `lever`, and `greenhouse` are lists of public board tokens, such as `augustus`.
- `location_tokens`, `title_allow`, and `seniority_block` are case-insensitive substrings.
- `cutoff_days` drops older ads. Greenhouse dates are last-updated, not first-published, so that cutoff is only as good as the vendor's timestamp.
- A block phrase is removed before offer phrases are searched. "Unable to offer visa sponsorship" is a refusal, not an offer.

To stop the scanner proposing a company you already applied to, or one that already rejected you, create `data/roles.json` (gitignored):

```json
{ "applied": ["almedia"], "rejected": ["example-corp"] }
```

Company names here are the board tokens, compared case-insensitively.

## What an agent is allowed to do

Read [`AGENTS.md`](AGENTS.md). In short: tailor from `data/profile.json` and the source CV, pass the draft through the auditor contract, and leave the result in `outbox/`. Do not invent a skill listed in `never_add`. Do not claim a right to work the profile does not have. Do not submit, send, or message anyone on LinkedIn. There is no LinkedIn client in this repo, and one must not be added.

## Layout

```
config/          example profile, rules, and board tokens
src/discover.py  board APIs → data/candidates.json
src/gate.py      text-level pass / hold / fail
src/screen.py    phrase matching, including the "no visa" trap
src/audit.md     the CV auditor's contract
src/outbox.py    drafts a file
src/send.py      refuses
examples/        one fictional job ad
docs/safety.md   rate limits, terms, and the approval boundary
data/            gitignored runtime files
```

CV rendering and opening the real application form are not in v0.1. The form is where a "right to work" question actually rejects people, so a later `gate` that opens the form still must not click submit.

## Terms

Public posting APIs only, at most 8 concurrent requests, no login, no Apply click. Details and the reason LinkedIn is absent are in [`docs/safety.md`](docs/safety.md).

## Licence

[MIT](LICENSE).
