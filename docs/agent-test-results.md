# Agent verification: local review branch

Date: 2026-11-24. Branch: `codex/evidence-based-job-workflow`.
Baseline: `d870e0eead74e3d232e54caab1fa1561a1332fe2`.

## Automated checks

- 57 unittest cases passed locally on Windows with Python 3.11. The original
  baseline had 26 tests; existing behavior tests were updated where the agreed
  matching contract deliberately changed.
- Regressions cover common-word matches, aliases, missing required skills,
  unknown experience, EMEA/country/hybrid restrictions, negative sponsorship,
  relocation without visa support and existing work rights.
- Profile confirmation becomes invalid after edits. Runs ignore stale reports;
  all-source failure preserves the last successful pointer.
- Full ads and board errors are retained; malformed feeds fail visibly. A
  concurrent fake HTTP boundary verified no more than eight active requests.
- Invented metrics, arbitrary overview claims, changed contacts/dates/skills,
  dropped roles/projects/languages and multiple roles at one employer are checked.
- Job URL identity preserves Greenhouse job query IDs and removes tracking noise.
  Duplicate outcomes block that job without blocking another job at the company.
- Converter failure retains previous successful DOCX/PDF artifacts. A Windows
  long-path regression covers short atomic-write filenames.
- `compileall` and `git diff --check` passed. Private profiles, preview images,
  temporary converter files and SQLite history are ignored.
- The skill-creator validator accepted all four repo skills. Its optional YAML
  dependency was installed under ignored `tmp/`, not added to runtime requirements.

## Live source and workflow checks

- Tested 40 prospective platform/token pairs; selected 23 working, nonempty
  boards. The final configured-source recheck returned 23 healthy, 0 failed.
  This is point-in-time endpoint evidence, not comprehensive worldwide coverage.
- An isolated live search using the fictional Ada example completed: 32 raw
  candidates across selected scouts, 9 shortlisted, 2 fact-checked CV drafts,
  7 held for verification. PDF rendering was deliberately disabled for that live
  test. No real mailbox was read and no application was submitted.
- The first live attempt exposed a Windows path-length failure. Short atomic
  temporary filenames and bounded output folder names fixed it; the rerun passed.

## PDF checks

- Ran the complete offline fictional demo with LibreOffice on Windows. The
  deliberately failed fixture board correctly made the result partial.
- Generated two one-page PDFs and matching DOCX files for distinct jobs at the
  same fictional company. Uncertain relocation received no resume.
- Extracted text retained candidate identity, role, project and spoken languages.
- Verified three clickable links in each PDF (email, GitHub contact, project).
- Rendered and inspected every page: readable text, no clipping or overlap.
- Windows converter process waiting and error reporting were fixed during these
  checks. Atomic publication preserves prior successful output on conversion failure.

## Still pending / limitations

- User acceptance: follow `docs/manual-testing.md` and record results privately.
- CI is configured for Windows and Linux but was not run remotely; no push occurred.
- PDF inspection used fictional one-page documents. The existing tests exercise
  longer document structure; users should inspect their own multi-page output.
- Requirement and country extraction remain explicit heuristics, with known limits
  documented in README. Human review of the full ad remains necessary.
- Legacy company-wide exclusions are retained, not silently migrated. Existing
  real profiles require explicit confirmation under the new digest-based gate.
- No merge, publication, email, real-profile search or application submission was
  performed during implementation testing.

## Follow-up: confirmed remote sponsorship wording

Removed the blanket remote-resume `visa` keyword rejection. Five added regression
tests reproduced the pre-fix failures and passed after the change: confirmed
sponsorship statements, altered work-right rejection, a confirmed employer named
Visa, faithful revision/recheck, and the pipeline reaching the renderer. The
pipeline test uses a mocked rendering boundary and also verifies Canada-only
remote exclusion. No new live search or PDF conversion was needed for this
validation-only change. The complete local suite now passes 62 tests;
`git diff --check` passes. Submission and eligibility safeguards are unchanged.
