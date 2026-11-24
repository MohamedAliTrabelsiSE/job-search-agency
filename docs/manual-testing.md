# User acceptance: test the local branch before merging

Run from the repository root in PowerShell. Use `.venv\Scripts\python.exe`
if `py -3` is unavailable. The fictional demo uses `tmp/`, reads no mail,
makes no network requests, and cannot submit an application.

## 1. Check the branch and automated tests

```powershell
git branch --show-current
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p "test_*.py"
```

Expected branch: `codex/evidence-based-job-workflow`. Tests must pass.
CI is configured for Windows and Linux; remote CI results are not implied by a
local run. Do not merge if either platform fails after you choose to push.

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

Save your results in `tmp/user-acceptance.md`: date, branch/commit, commands,
pass/fail for each section, PDF observations and any surprises. Keep real candidate
data out of issues, screenshots shared publicly, and commits.

Merge/publish only after your manual checks pass, the branch diff is reviewed,
and the published artifact contains no private data. The agent does not merge,
push, or publish as part of this task.
