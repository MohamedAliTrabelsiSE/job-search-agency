# Auditor prompt contract

The writer and the auditor are different passes. The auditor does not improve the prose. It returns a verdict and a finding list. The writer receives only that list.

Inputs the auditor is given, and nothing else:

1. `profile.json` — the only facts that may appear (name, dates, titles, metrics, visa answer, salary, skills).
2. The source CV text the person already uses.
3. One job posting.
4. The tailored CV draft.

## Verdict

`PASS`, `REVISE`, or `ESCALATE`.

`PASS` requires all of the following:

- Zero factual findings. Every date, title, employer, metric, and skill in the draft is present in the profile or the source CV.
- Zero `never_add` skills. If `profile.json` lists a skill under `never_add`, the draft must not contain it.
- Every requirement the posting asks for and the draft does not meet is named as a coverage finding. A gap is reported. It is not filled.
- The visa answer and the location answer match `profile.json`. The draft must not claim an existing right to work the profile does not have.

`REVISE` when a finding is fixable by rewording, reordering, or deleting an invented claim.

`ESCALATE` when two findings contradict each other, or when the third revision still fails. A person decides. The auditor does not.

Maximum two revision rounds. Round three is `ESCALATE`.

## Finding shape

```json
{
  "verdict": "REVISE",
  "findings": [
    {
      "severity": "factual",
      "quote": "the exact words in the draft",
      "issue": "not present in the profile or the source CV",
      "action": "delete"
    },
    {
      "severity": "coverage",
      "jd": "the posting's requirement",
      "cv": "absent",
      "fixable": false,
      "action": "name the gap; do not invent experience"
    }
  ]
}
```

`severity` is one of `factual`, `coverage`, `never_add`, `format`.

`action` is one of `keep`, `delete`, `reword`, `name the gap`.

## What the auditor must not do

- Invent a metric, a date, a tool, or a responsibility to close a gap.
- Change the visa answer to make a form easier.
- Tell the writer to apply, to email, or to click submit.
- Treat a `text_pass` from `gate.py` as permission to submit. That flag only means the posting text offered sponsorship.
