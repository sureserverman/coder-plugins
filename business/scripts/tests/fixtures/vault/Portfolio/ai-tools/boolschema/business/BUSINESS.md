---
schema: true
project: boolschema
verdict: monetize
audience: someone
evidence: local-only
last_reviewed: 2026-07-01
---

# Business case: boolschema

`schema: true` parses as a YAML boolean, and bool is an int subclass — the
scanner must reject it as a non-integer schema, not silently treat it as schema 1.
