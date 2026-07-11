---
schema: 2
project: newschema
verdict: monetize
audience: future users of a schema this plugin version doesn't understand yet
evidence: local-only
last_reviewed: 2026-07-01
---

# Business case: newschema

Valid YAML, but `schema: 2` is newer than this plugin understands. The scanner must
emit an explicit "newer schema — upgrade the business plugin" error, never silently
misparse it as schema 1.
