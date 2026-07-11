---
schema: 1
project: badtarget
verdict: monetize
audience: whoever needs it
evidence: local-only
last_reviewed: 2026-07-01
monetization:
  model: paid
  pricing: "$5 one-time"
  channels: [github-releases]
targets:
  - metric: installs
    target: 1000
    # by omitted on purpose — must be flagged
  - metric: revenue_usd
    target: lots        # non-numeric — must be flagged
    by: 2026-12-31
---

# Business case: badtarget

Exercises targets[] shape validation (BL-002): a target missing `by`, and a
target with a non-numeric `target:` value, must each produce a scanner error
without aborting the assessment.
