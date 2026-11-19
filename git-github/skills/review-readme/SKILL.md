---
name: review-readme
description: Use when reviewing, auditing, or improving a project's README.md — also triggers on "my readme is a mess", "clean up the readme", "the readme is too long", "readme feels off", "make the readme nicer", or a user sharing a README and asking what's wrong with it
---

# Review README

Review the README against the house limits in the `readme` stack page
(`~/.claude/vault-stacks/vault-stack-readme.md`). If the page is not in the
session context, read the file.

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

The goal is *shorter and better*.
