# Safety

## What this repo does

On a fresh clone the agent asks for a general resume and whether the person wants full remote, relocation, or both, and it saves those answers only under `data/`. After that it reads public job-board APIs (Ashby, Lever, and Greenhouse), classifies the posting text, and can save a draft resume on disk. If a credential file exists it also reads the inbox. It records rejections and does not reply.

## What it does not do

- It does not submit an application. `src/send.py` has no network code and exits.
- It does not send email. `src/outbox.py` writes a file and stops.
- It has no LinkedIn client. There is no read path and no write path. A write client must not be added: LinkedIn's terms forbid automated access, and a connection request or message sent by a script is the kind of action this harness exists to keep in human hands.
- It does not ship a real CV. The committed examples are fictional. A real resume lives in `data/`, which is gitignored.

## Rate limits and terms

The board APIs used here are the public posting feeds those vendors publish for job boards. v0.1 calls them with at most 8 concurrent requests, a normal browser-like user agent that names this project, and no login.

Do not raise the concurrency to scrape faster. Do not point this at a site that is not a public posting API. Do not add a headless browser that clicks Apply. If a vendor asks you to stop, stop.

Greenhouse list responses omit descriptions. Fetch full descriptions for matching title/location/date postings. An optional `--content-cap` makes coverage partial; the default fetches all matching descriptions. All scouts share one eight-request budget.

## Human approval

Eligibility is an evidence-based reading of the ad. Unknown sponsorship stays unresolved even when relocation assistance is offered. The form may still reject a work-right answer. The agent follows `prompts/ats.md`, reports scoped checks, and stops at files. Local application-history commands record evidence; they never submit.

## Before this is public

Use it on your own search first. A repository that has not produced a single reviewed application is a weaker portfolio piece than one that has. The licence is MIT so that, when you do publish, reuse is allowed and support is not promised.
