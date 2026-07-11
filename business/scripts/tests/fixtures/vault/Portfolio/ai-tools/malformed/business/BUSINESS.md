---
schema: 1
project: malformed
verdict: monetize
audience: someone
monetization:
  model: paid
   pricing: "bad indent breaks the YAML block"
  channels: [f-droid
targets:
---

# Business case: malformed

The frontmatter above has broken YAML (bad indentation, unclosed list). The scanner
must record this project in `errors` with a reason and continue the sweep.
