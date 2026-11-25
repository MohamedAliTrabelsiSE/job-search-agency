---
name: job-research
description: Maintain public job-board sources when searching jobs or diagnosing source coverage in this repository.
---

Before a broad live search, run `src/employers.py queries` after confirmed onboarding.
Use the available public search tool for those queries. Save query/result URLs
privately with the README input schema; use `src/employers.py import --results PATH`
to verify official ATS feeds and populate runtime employer discovery. Assign
relocation results to their regional scout and remote results to worldwide.
When no search tool is available, state that this is seed-only coverage; the CLI
does not implement or scrape an internet search engine. Imported evidence expires
after seven days. A search result proves a lead, not eligibility or suitability.

Read `config/sources/` and run `src/source_health.py` from the repo root. Review
coverage and dated errors before describing the market. A healthy feed proves
access, not relevant openings or eligibility. An empty/failed feed is not no jobs.

Use `src/morning.py` for run-isolated searches. Scouts share eight concurrent
requests and retain full ads. Report geographic gaps and failed descriptions.
Verify a public ATS platform/token pair before adding it. Use public posting APIs.
Finish with healthy/failed counts, actual coverage and unresolved sources.
