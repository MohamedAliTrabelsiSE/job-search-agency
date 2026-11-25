# Changelog

## [v0.3.0](https://github.com/MohamedAliTrabelsiSE/job-search-agency/releases/tag/v0.3.0) — 2026-11-25

### Added

- Profile confirmation tied to the exact facts and preferences, plus an archival
  fresh-start command.
- Separate run folders, source health, quoted eligibility evidence, technical
  gaps, and recommended/stretch/needs_verification/excluded decisions.
- Search-tool-assisted discovery of employers beyond the preset public boards,
  with verified feeds, expiring private caches, and explicit coverage limits.
- Local application preflight and job-level outcome history, operational skills,
  an offline fictional demo, and manual acceptance instructions.
- 105 automated regression tests and Windows/Linux CI for tests and the offline
  workflow demo.

### Changed

- Preserve full job descriptions, requirement sections, preferred skills, and
  one-of alternatives. Shared technologies alone do not establish suitability.
- Essential expertise gaps and substantial experience shortfalls exclude jobs.
  Default experience stretch is at most one year with at least two-thirds of the
  required duration; shortfalls also reduce the score.
- Keep distinct openings at the same company. Retain older and undated listed
  jobs by default, labeling freshness separately from observed availability.
- Share one eight-request budget across scouts and report partial/failed searches.
- Preserve confirmed resume claims and earlier successful artifacts if rendering
  fails. Unknown eligibility receives no application resume.

### Fixed

- Confirmed remote sponsorship statements no longer fail a blanket `visa` check.
- Explicit country/region restrictions and exceptions override worldwide labels;
  company headquarters and negated office wording are assessed in context.
- Later alternatives cannot erase earlier mandatory requirements. Mixed required
  and preferred clauses retain their individual meaning.
- Decimal experience, ranges, and wording such as “20 years in backend
  development” retain their duration. Optional experience is not a minimum.
- Negative candidate statements cannot establish skills or essential expertise.
- Relevant Web/Node.js titles survive early filtering, and “Internal Tools” is
  not mistaken for an internship.

### Upgrading from v0.2.0

1. Install dependencies with `python -m pip install -r requirements.txt`.
2. Review your private facts/preferences with `python src/profile.py show`, then
   confirm that exact revision with `python src/profile.py confirm --name "YOUR EXACT NAME"`.
   Existing files alone no longer authorize a search. Do not confirm facts you
   have not reviewed.
3. Run `python src/demo.py --root tmp/upgrade-check --no-render` for an offline
   decision check, then follow [manual testing](docs/manual-testing.md) for PDFs.

Private profiles, previous resumes, and legacy company exclusions stay local.
Submission remains disabled: this release adds no mail sender, LinkedIn client,
or automatic application submission. Eligibility and requirement extraction remain
heuristic; review the complete ad and verify uncertain conditions.

## [v0.2.0](https://github.com/MohamedAliTrabelsiSE/job-search-agency/releases/tag/v0.2.0) — 2026-11-24

- Resume-first onboarding, job discovery and ranking, and per-job resume drafts.
- Stop for the person's decision; no email sending or automatic applications.

[Compare v0.2.0…v0.3.0](https://github.com/MohamedAliTrabelsiSE/job-search-agency/compare/v0.2.0...v0.3.0)
