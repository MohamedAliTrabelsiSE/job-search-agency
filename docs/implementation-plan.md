# Evidence-based job workflow

Branch: `codex/evidence-based-job-workflow`. Local review only: no merge, push,
publication, application submission or email is part of this implementation.

## Acceptance plan

1. Profile and runs: validate confirmed facts/preferences, bind confirmation to
   their digest, isolate every run, preserve previous outputs on failure. Test
   missing, malformed, changed and unconfirmed profiles and stale scout reports.
2. Sources: record per-board health and complete descriptions, report incomplete
   coverage, retry transient failures and share one eight-request budget across
   scouts. Verify adapter behavior with fixtures; check public endpoints separately.
3. Eligibility: separate sponsorship, relocation help and permitted countries;
   retain evidence and unknown/conflicting states. Verify EMEA, country locks,
   relocation without sponsorship and preferences outside a scout's region.
4. Matching: score normalized technical requirements, report gaps and decisions,
   retain all distinct jobs, and group only for display. Verify useful TypeScript
   matches beat common words and missing required Go produces a stretch result.
5. Resumes: retain approved layout, all roles/projects/languages, record claim
   provenance and block unsupported claims/metrics. Preserve successful outputs
   when rendering fails. Verify a fictional PDF by text extraction and page images.
6. Applications: local preflight and job-level history, approved/submitted/duplicate
   states with evidence. No automatic submission. Verify duplicate handling without
   suppressing different openings at the same company.
7. Documentation and handoff: update agent contracts, add operational runbooks,
   executable fictional demo and manual acceptance checklist. Report actual checks
   and remaining uncertainty before the user tests the branch.

## Test boundaries

Use public behavior of profile confirmation, eligibility assessment, ranking,
fact checking, application history and CLI orchestration. Inject fixture data at
the network boundary. Use a failing regression followed by its implementation for
each behavior; no real inbox or candidate data in fixtures. Run existing tests too.

## Delivery gates

- Automated regressions and isolated CLI demo pass.
- Windows PDF render and page inspection pass; CI covers Windows and Linux logic.
- Live source health reports successful and failed boards honestly.
- `git diff --check` passes and generated/private files remain ignored.
- User follows `docs/manual-testing.md`, records results locally, and decides
  whether to merge. A green suite alone is not permission to publish.

## Scope and limitations

Keep a local Python CLI, JSON artifacts and SQLite operational history; no hosted
service or dashboard. Deterministic matching is explainable, not a semantic model.
Country and requirement extraction is conservative and exposes uncertainty.
Source availability is time-dependent; source count is never worldwide coverage.
