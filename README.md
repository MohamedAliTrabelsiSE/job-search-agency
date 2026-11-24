# job-search-agency

A small agency that looks for jobs and then stops. You talk to one lead. The lead sends scouts out, keeps at most three roles, and has a writer and an ATS specialist build a resume for each one. Nothing is emailed and nothing is submitted until you say yes to a specific card.

Open this repo in Cursor, Claude, Codex, DeepSeek, or anything else that reads [`AGENTS.md`](AGENTS.md). That file is the contract. This page is the map.

![One morning: you brief the lead, five workers search together, the merger keeps three cards, the writer and the ATS specialist revise once, then the run stops](docs/how-it-works.gif)

The picture is one morning. The rest of this page is the same story in words.

## The team

You never talk to the workers. They do not talk to each other. They leave files, and the lead reads the files.

| Who | Job | Leaves behind |
| --- | --- | --- |
| **Lead** | Asks you the interview, starts the morning, shows you the folders | the decision to stop |
| **Inbox clerk** | Reads mail. Files a rejection. Drafts a reply and does not send it | `data/inbox.json`, names appended to `data/roles.json` |
| **Worldwide scout** | Full remote you can do from the country you already live in | `data/scout-worldwide.json` |
| **DACH scout** | Germany and Austria | `data/scout-dach.json` |
| **Benelux + Ireland scout** | Netherlands, Belgium, Ireland | `data/scout-benelux-ie.json` |
| **Nordics scout** | Sweden, Denmark, Finland, Norway | `data/scout-nordics.json` |
| **Merger** | Waits until the workers above have finished. One card per company. Drops duplicates, companies you already applied to, and rejections | `data/shortlist.json`, at most 3 cards |
| **Writer** | Builds that job's resume from your general one. Same facts, reordered. A gap stays a gap | `outbox/<company>-<title>/cv.json` |
| **ATS specialist** | Checks that the resume parses and matches the ad. Sends findings to the writer. One revision, one recheck, no third rewrite | `outbox/<company>-<title>/ats.json` |

The only conversation in the agency is that one pass between the ATS specialist and the writer.

A recruiter who wrote with no opening gets the general resume you already provided. A real job gets the resume in that job's folder.

## Which scouts go out

Your interest, saved at the interview, decides this. The inbox clerk is separate: it runs only if you connected mail.

| You said | Who searches |
| --- | --- |
| Full remote | Worldwide only |
| Relocate | One regional scout per place you named. Germany and Austria share a scout. So do the Netherlands, Belgium, and Ireland. So do the four Nordics |
| Both | Worldwide first, then the regional scouts. Both is a normal answer |

Places the agency knows: Germany, Austria, Netherlands, Belgium, Ireland, Sweden, Denmark, Finland, Norway.

## Two ways a job can pass

**Full remote** means any country, including the one you live in now. "Work from anywhere" passes. "Remote, Poland" does not: a country after the word remote is a country lock. A bare "Remote", with no country, still counts.

**Relocation** is for a named place, and only if you need a visa. The ad has to say it sponsors a visa or helps you relocate. "Must already have the right to work" fails. "Unable to offer visa sponsorship" fails too. The word "sponsorship" in a refusal is not an offer.

A pass is not permission to apply. It only means the text of the ad got through. US hours and contract-only roles stay visible. They are not hidden.

## First run

If `data/cv_facts.json` or `data/preferences.json` is missing, the lead stops. No scout runs. It asks, in this order:

1. **Your general resume.** A PDF, a text file, or a paste. It reads only what is written, shows you that reading, and waits for you to correct it. Then it saves `data/cv_facts.json`: contact, education, each role, the bullets you already have, languages, activities, and `never_add` (tools the resume does not claim). It does not invent a metric or a skill.
2. **Your interest.** Full remote from where you already live, relocate, or both. Relocate asks which places. More than one place is normal.
3. **Work right, in your words.** Relocation: whether you need a visa. Full remote: that you will keep working from your current country. Saved in `data/preferences.json`.

Both files are gitignored. So is your inbox, your skip list, and every resume the morning writes. [`config/cv_facts.example.json`](config/cv_facts.example.json) and [`config/preferences.example.json`](config/preferences.example.json) are a fictional person, so the shape is visible. Do not put a real resume in them.

Someone who clones this repo starts with an empty skip list. Your applications are not theirs.

## A morning

Search uses Python 3.11 and the standard library. Rendering a resume also needs `python-docx`.

```bash
pip install -r requirements.txt
python tests/test_screen.py
python tests/test_agency.py
python src/morning.py
```

On Windows, if `python` is not on PATH, use `py -3` in place of `python`.

`morning.py` refuses to start while the two profile files are missing. After you have confirmed them, it:

1. Reads the inbox, only when `~/.dsh/smtp.txt` exists (an address, then an app password) or you pass `--creds`. No credential file means the inbox is skipped and the search still runs. Mail is classified as rejection, acknowledgement, question, or other. Rejections are remembered. Nothing is sent.
2. Starts the scouts your interest turned on, together.
3. Merges them into at most three cards.
4. For each card, drafts a resume, runs the ATS check, revises once, and renders `resume.docx` and `resume.txt` when the check passes. A blocked resume is not rendered.

Then it prints `Stopped. Nothing was submitted and nothing was sent.` and waits for you.

`python src/send.py` exits on purpose. There is no SMTP client in this repository, and no LinkedIn client. Do not add one.

## Your own boards

Public Ashby, Lever, and Greenhouse boards only. Edit the lists under [`config/sources/`](config/sources/) or copy [`config/sources.example.yaml`](config/sources.example.yaml):

```bash
python src/discover.py --sources config/sources.example.yaml --rules config/rules.example.yaml
```

- `ashby`, `lever`, and `greenhouse` are lists of public board tokens.
- `location_tokens`, `title_allow`, and `seniority_block` are case-insensitive substrings.
- `cutoff_days` drops older ads. Greenhouse dates are last-updated, not first-published, so that cutoff is only as good as the board's timestamp.
- A block phrase is masked before offer phrases are searched, so a sentence that refuses a visa is not read as an offer.

To keep a company off the shortlist, create `data/roles.json` (gitignored):

```json
{ "applied": ["northwind"], "rejected": ["example-corp"] }
```

The names are board tokens, compared case-insensitively.

## Layout

```
AGENTS.md          the contract every agent runtime follows
config/            fictional profile, rules, and board tokens
prompts/           writer and ATS specialist
src/morning.py     inbox, then scouts, then merge, then resumes
src/scout.py       starts only the scouts your interest turned on
src/inbox.py       reads mail, never sends
src/merge.py       at most three cards
src/discover.py    public board APIs
src/render_cv.py   resume.docx and resume.txt
src/send.py        refuses
docs/safety.md     rate limits, terms, and why LinkedIn is absent
data/              gitignored. created on your machine
outbox/            gitignored resumes, one folder per job
```

## Terms

Public posting APIs only, at most 8 concurrent requests, no login, no Apply click. Details are in [`docs/safety.md`](docs/safety.md).

## Licence

[MIT](LICENSE).
