# job-search-agency

A small agency that looks for jobs, then stops and waits for you. You talk to one lead. The lead asks three questions, sends the team out, and comes back with every role that overlaps your resume, best match first. Each of those roles gets its own resume. Nothing is emailed and nothing is submitted until you say yes to a specific one.

Open this repo in Cursor, Claude, Codex, DeepSeek, or anything else that reads [`AGENTS.md`](AGENTS.md). That file is the contract. This page is the picture.

## Start here

You need Python 3.11.

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py"
```

Then open this folder in your agent and wait. It asks three questions before it searches. On Windows, if `python` is not on PATH, use `py -3`.

Feedback goes in a [discussion](https://github.com/MohamedAliTrabelsiSE/job-search-agency/discussions) or an [issue](https://github.com/MohamedAliTrabelsiSE/job-search-agency/issues). Do not paste a real resume, a phone number, or a mail password. See [CONTRIBUTING.md](CONTRIBUTING.md).

## A morning

![Six steps: you talk to the lead, answer three questions, the inbox and scouts start together, matching jobs come back, each gets a resume, then everything stops](docs/how-it-works.gif)

1. You talk only to the lead.
2. The lead asks for your resume, whether you want remote work or relocation or both, and whether you can legally work that way. It reads the resume back and waits.
3. The inbox and the scouts start together. They hand back notes. They do not talk to each other.
4. Repeats, companies you already applied to, and rejections drop out. Every remaining ad that shares words with your resume is kept, best first. An ad with no shared words is listed and not drafted.
5. Each kept job gets a resume made from the same facts. The page is one column: your headline, then experience, projects, education, skills, and languages.
6. The run stops. You decide.

## Who goes looking

![Remote sends a worldwide scout, relocate sends one scout per region, both sends both](docs/who-searches.gif)

Germany and Austria share a scout. So do the Netherlands, Belgium, and Ireland. So do Sweden, Denmark, Finland, and Norway. The inbox runs only when you have connected mail. Without that, the search still runs.

## How a resume is checked

![The writer drafts from your real experience, the ATS specialist checks it, findings go back once, the writer fixes once, then the resume passes or is blocked](docs/ats-loop.gif)

The writer fills the resume fields and does not design a second page. `src/render_cv.py` is the only layout. It may reorder and reword bullets. It may not add a skill, a metric, or a job that was not in your general resume. A gap stays a gap. The visa line appears only on a relocation resume. The specialist sends findings once, the writer fixes once, and there is no third draft. A blocked resume is not saved. A recruiter who wrote with no specific opening gets the general resume you already gave.

## Which ads get through

![Full remote passes work-from-anywhere and a bare remote, and fails a country lock. Relocation passes visa help and fails an existing right-to-work requirement](docs/what-passes.png)

A pass only means the text of the ad got through. It is not permission to apply. Jobs with US hours, or contract-only jobs, stay visible.

## What each one writes

You never talk to the workers. The only reply inside the agency is the one list of findings from the ATS specialist to the writer.

| Who | Writes |
| --- | --- |
| Inbox | `data/inbox.json`, and rejected companies in `data/roles.json` |
| Scouts | `data/scout-worldwide.json`, `data/scout-dach.json`, `data/scout-benelux-ie.json`, `data/scout-nordics.json` |
| Merger | `data/pool.json`, every text-pass card |
| Ranker | `data/shortlist.json`, every resume match, best first |
| Writer | `outbox/<company>-<title>/cv.json` |
| ATS specialist | `outbox/<company>-<title>/ats.json` |

## First run

If `data/cv_facts.json` or `data/preferences.json` is missing, the lead stops. No scout runs. It asks, in this order:

1. **Your general resume.** A PDF, a text file, or a paste. It reads only what is written, shows you that reading, and waits for you to correct it. Then it saves `data/cv_facts.json`: contact, education, each role, the bullets you already have, languages, activities, and `never_add` (tools the resume does not claim).
2. **Your interest.** Full remote from where you already live, relocate, or both. Relocate asks which places. More than one place is normal.
3. **Work right, in your words.** Relocation: whether you need a visa. Full remote: that you will keep working from your current country. Saved in `data/preferences.json`.

Both files are gitignored. So is your inbox, your skip list, and every resume the morning writes. [`config/cv_facts.example.json`](config/cv_facts.example.json) and [`config/preferences.example.json`](config/preferences.example.json) are a fictional person, so the shape is visible. Do not put a real resume in them.

Someone who clones this repo starts with an empty skip list. Your applications are not theirs.

## Run a morning

Search uses Python 3.11 and the standard library. Rendering a resume also needs `python-docx`.

```bash
pip install -r requirements.txt
python tests/test_screen.py
python tests/test_agency.py
python src/morning.py
```

On Windows, if `python` is not on PATH, use `py -3` in place of `python`.

`morning.py` refuses to start while the two profile files are missing. After you have confirmed them, it reads the inbox when `~/.dsh/smtp.txt` exists (an address, then an app password), runs the scouts your answer turned on, merges them, ranks every ad that shares words with your resume, and renders `resume.docx` and `resume.txt` for each of those. Then it prints `Stopped. Nothing was submitted and nothing was sent.`

`python src/send.py` exits on purpose. There is no mail sender in this repository, and no LinkedIn client. Do not add one.

## Your own boards

Public Ashby, Lever, and Greenhouse boards only. Edit the lists under [`config/sources/`](config/sources/) or copy [`config/sources.example.yaml`](config/sources.example.yaml):

```bash
python src/discover.py --sources config/sources.example.yaml --rules config/rules.example.yaml
```

- `ashby`, `lever`, and `greenhouse` are lists of public board tokens.
- `location_tokens`, `title_allow`, and `seniority_block` are case-insensitive substrings.
- `cutoff_days` drops older ads. Greenhouse dates are last-updated, not first-published.
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
prompts/           ranker, writer, and ATS specialist
src/morning.py     inbox, scouts, merge, rank, then resumes
src/send.py        refuses
docs/              the diagrams on this page, and safety.md
data/              gitignored. created on your machine
outbox/            gitignored resumes, one folder per job
```

## Known limits

Some board names in `config/sources/` return nothing. The resume is a `.docx` plus `resume.txt`, not a PDF. `src/send.py` exits on purpose: this repo cannot email anyone and cannot click Apply.

## Terms

Public posting APIs only, at most 8 concurrent requests, no login, no Apply click. Details are in [`docs/safety.md`](docs/safety.md).

## Licence

[MIT](LICENSE).
