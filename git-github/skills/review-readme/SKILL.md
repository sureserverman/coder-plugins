---
name: review-readme
description: Use when reviewing, auditing, or improving a project's README.md — also triggers on "my readme is a mess", "clean up the readme", "the readme is too long", "readme feels off", "make the readme nicer", or a user sharing a README and asking what's wrong with it
---

# Review README

A reader must learn **what the project is** and **how to start** within 30
seconds. When in doubt, cut.

## House limits

- **At most 6 top-level sections.** Skeleton: title + one-liner (≤15 words,
  directly under the H1), one badge row (only with real data), Quick Start,
  Usage (one example), License (bottom). Add Features, Screenshot,
  Configuration, API or Contributing only when clearly needed.
- **Quick Start: at most 3 copy-pasteable steps.**
- Above the fold (first ~25 lines): title, one-liner, badges, Quick Start.
- One default install method; alternatives and long optional content go in
  `<details>` collapsibles.
- Config examples show the required keys only; API docs 1–2 examples, then a link.
- Every command, path, port and URL must match the repo.

## Report & Apply

Read the README and scan the project (manifests, Makefile, docs/, remote URL).
Present findings as **ISSUE** / **IMPROVE** / **STYLE**:

```
| # | Sev     | Phase     | Finding                                              |
|---|---------|-----------|------------------------------------------------------|
| 1 | ISSUE   | Structure | Missing one-liner — title is bare project name        |
```

Ask with AskUserQuestion: "All", "ISSUE + IMPROVE only", "Let me pick". After
applying, show a before/after summary.

**Never grow the README to fix it.** If adding content, cut or collapse
something first. The goal is *shorter and better*.
