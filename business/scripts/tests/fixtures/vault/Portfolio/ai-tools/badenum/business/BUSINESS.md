---
schema: 1
project: wrongname
verdict: someday
audience: someone
evidence: maybe-later
monetization:
  model: paid
  channels: not-a-list
---

# Business case: badenum

Syntactically valid YAML, but: verdict and evidence are outside their enums,
`last_reviewed` is missing, `project` doesn't match the registry name, and
channels is a scalar instead of a list. The scanner must record one error per
violation and null the invalid enum fields — never silently accept them.
