# Manual checks: verify an installation or review a change

Run from the repository root in PowerShell. Use `.venv\Scripts\python.exe`
if `py -3` is unavailable. The fictional demo uses `tmp/`, reads no mail,
makes no network requests, and cannot submit an application.

## 1. Check the branch and automated tests

```powershell
git branch --show-current
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p "test_*.py"
```

For a v0.3.0 installation, use `master` or the `v0.3.0` release tag. For a proposed
change, use the development branch under review. A tag checkout has no current
branch name. Tests must pass in either case.
CI runs on Windows and Linux; remote CI results are not implied by a local run.
Contributors must resolve failures before merging or publishing a change.

For the latest assessment fixes, run this focused check as well:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p "test_adversarial.py" -v
```

Expected: every case passes. The fictional cases verify that country exceptions
stop rendering, company headquarters do not restrict applicants, negated office
wording does not hide actual attendance requirements, independent skill clauses
keep their meaning, decimals and experience ranges retain their values, and
negative skill statements cannot establish expertise.

## 2. Exercise the complete fictional workflow

```powershell
.\.venv\Scripts\python.exe -X utf8 src/demo.py --root tmp/my-demo
```

Needs LibreOffice or Microsoft Word for PDF conversion. For decision checks
without a converter, add `--no-render`; that intentionally produces no PDF.

Open `tmp/my-demo/data/latest-run.json`, then the referenced run directory.
Check `summary.json`, `shortlist.json`, `source-health.json`, `reviews.json`,
and `thread.md`.

Expected:

- Coverage is **partial**: two healthy boards and one deliberately failed board.
- Three shortlisted jobs: recommended TypeScript, stretch Go, uncertain relocation.
- Two separate job folders at the same fictional company.
- Go is listed as a missing required skill and never appears as your skill.
- The relocation job offers assistance but has **unknown** visa sponsorship;
  no resume is generated for that job.
- Canada-only remote work is excluded for the fictional candidate in Egypt.
- Every PDF retains the fictional candidate's role, project and languages.
- `ats.json` distinguishes factual checks from PDF rendering and visual review.

Open both PDFs and DOCX files. Check readability, no clipping/overlap, correct
contacts, same content, clickable contact links, and sensible pagination. Long
resumes can continue to another page; the approved layout stays unchanged.

## 3. Verify safeguards with disposable data

In `tmp/my-demo/data/preferences.json`, change the current country. Run:

```powershell
.\.venv\Scripts\python.exe -X utf8 src/morning.py --root tmp/my-demo --fixture tests/fixtures/scout-reports.json --no-render
```

Expected: the changed profile is unconfirmed and the run stops before searching.
Use a new demo root for the next check; the demo refuses to overwrite a changed
profile. You can inspect and confirm a disposable revision using:

```powershell
.\.venv\Scripts\python.exe -X utf8 src/profile.py --root tmp/my-demo show
.\.venv\Scripts\python.exe -X utf8 src/profile.py --root tmp/my-demo confirm --name "Ada Okonkwo"
```

For an archived fresh start, use `profile.py --root tmp/my-demo fresh-start`.
Expected: profile/history are archived, never deleted, and searches stop until
new onboarding is confirmed. Existing outbox artifacts remain available.

## 4. Optional live source check

```powershell
.\.venv\Scripts\python.exe -X utf8 src/source_health.py
```

This contacts public posting APIs only. Open `data/source-health.json`.
Availability may change: failures must be explicit, never interpreted as no jobs.
The committed source snapshot is dated evidence, not a permanent guarantee.

## 5. Optional real-profile search

Review `profile.py show` privately. Confirm only after the displayed facts and
preferences are correct, using `profile.py confirm --name "YOUR EXACT NAME"`.
Existing private JSON is preserved; this is a deliberate one-time migration gate.

Run `morning.py --skip-inbox` to test live searching without reading mail. Omit
that flag only when you want Ida to read the configured mailbox. No command sends
mail or submits applications. Inspect eligibility evidence and fit gaps yourself.

Legacy `roles.json` company exclusions still apply conservatively. New application
tracking is per job. Do not erase old exclusions automatically to inflate results.

## 6. Test application preflight locally

Copy `config/application_answers.example.json` under `tmp/` and review its values.
It contains `gross_annual_salary`, `currency`,
`availability`, `education_category`, and `visa_sponsorship_required`. Use a
fictional `card.json` from the demo and the same `--root tmp/my-demo`:

```powershell
.\.venv\Scripts\python.exe -X utf8 src/applications.py --root tmp/my-demo --card "PATH/TO/card.json" prepare --answers "PATH/TO/answers.json"
.\.venv\Scripts\python.exe -X utf8 src/applications.py --root tmp/my-demo --card "PATH/TO/card.json" record --status duplicate_blocked --evidence "Fictional duplicate notice for acceptance testing"
```

Repeat `prepare`: it must report the previous duplicate and refuse readiness.
Another job at the same company must remain available. These commands only record
local state. Do not record a real submission without observed employer evidence.

## Acceptance record

### Suitability and coverage corrections

Run the focused regressions as well as the full suite:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_assessment.py
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_employers.py
```

Check these expected behaviors in your next real-profile run:

- Two years versus 2/3/5/8/20 years yields meets/stretch/excluded/excluded/excluded.
  Stretch has an experience penalty and an explanation, not the same score.
- Nice-to-have Go is preferred. Go-or-Python is one choice, not both mandatory.
  Multiple-choice lists and explicit parentheses retain other required skills.
- Essential Linux/networking/cloud gaps do not become recommendations from Python
  overlap. Unknown mandatory platforms/cardinality go to verification.
- Brazil-only, North America-only and in-person roles do not pass remote eligibility
  for Tunisia. Unsupported locations stay uncertain despite worldwide marketing.
- Web Engineer, Node.js Developer and Internal Tools reach assessment; internships
  retain their explicit seniority classification.
- Older and undated listed ads remain visible, with freshness/availability labels.
  To test strict freshness, set `freshness_mode: recent_only` in the relevant rules;
  unknown dates stay visible and known older dates are filtered. Restore `prefer`.

For expanded coverage, have the assistant execute `employers.py queries` using its
public search tool, save the README result schema privately, then import with
`employers.py import --results PATH`. Use `--root tmp/my-demo` for a fictional profile.
Inspect private `data/employer-discovery.json` and the run's `market_discovery`:
new boards must be verified, URLs deduplicated and failed/unsupported hosts shown.
Without search results, the report must say seed_only. Adding seed tokens alone
is not employer discovery. Expanded results still do not cover the entire market.

### Record your decision

Save your results in `tmp/user-acceptance.md`: date, branch/commit, commands,
pass/fail for each section, PDF observations and any surprises. Keep real candidate
data out of issues, screenshots shared publicly, and commits.

Merge/publish only after your manual checks pass, the branch diff is reviewed,
and the published artifact contains no private data. The agent does not merge,
push, or publish as part of this task.
