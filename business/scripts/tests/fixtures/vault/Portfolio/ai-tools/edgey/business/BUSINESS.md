---
schema: 1
project: edgey
verdict: monetize
audience: power users --- basically anyone who wants automation
evidence: local-only
last_reviewed: 2026-07-01
monetization:
  model: paid
  pricing: 2026-07-01
  channels: [github-releases]
targets:
  - metric: installs
    target: 100
    by: 2026-12-31
  - metric: reach
    target: .inf
    by: 2026-12-31
---

# Business case: edgey

Exercises parser hardening: an inline `---` in `audience` must not truncate the
frontmatter (fields after it must survive), and an unquoted date-shaped `pricing`
(YAML-coerced to a date) must serialize as a string instead of crashing the sweep.
