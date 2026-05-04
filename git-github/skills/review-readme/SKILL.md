---
name: review-readme
description: Use when reviewing, auditing, or improving a project's README.md — also triggers on "my readme is a mess", "clean up the readme", "the readme is too long", "readme feels off", "make the readme nicer", or a user sharing a README and asking what's wrong with it
---

# Review README

Analyze and improve a project's README to be useful, brief, and visually attractive.

## Core Principle: The 30-Second Rule

A developer must understand **what this project is** and **how to start using it** within 30 seconds. Everything else is secondary. When in doubt, cut.

## Instructions

1. Read README.md and scan the project (manifests, configs, Makefile, docs/, git remote URL)
2. Run all checks below, classifying findings as **ISSUE** / **IMPROVE** / **STYLE**
3. Present findings table, ask the user which to apply, then make changes

## Structure Check

**Target: ≤6 top-level sections.** Evaluate against the essential skeleton:

| Section | Rule |
|---------|------|
| **Title + one-liner** | ≤15 words answering "What does this do?" directly under H1 |
| **Badges** | Single row: build, version, license — only if real data exists. Use shields.io with actual repo URL |
| **Quick Start** | Zero to running in **≤3 copy-pasteable steps**. Most important section |
| **Usage** | Primary use case with one code example |
| **License** | SPDX identifier or link. Bottom of file |

Optional sections — add **only** when clearly needed:

| Section | When |
|---------|------|
| Features | 3+ distinct capabilities — bullets, not paragraphs |
| Screenshot/GIF | Visual UI exists |
| Configuration | Show **minimal** example (≤15 lines), link to full reference |
| API Reference | 1-2 examples only, link to full docs |
| Contributing | Or just link to CONTRIBUTING.md |

**Anti-patterns:** ToC under 200 lines, >6 sections, separate "About"/"Introduction" when one-liner suffices, empty/boilerplate sections, backstory ("Started in 2023...").

## Content Audit

### Accuracy
- [ ] Every command is runnable (verify against actual scripts, Makefile, package.json)
- [ ] File paths, ports, URLs, container names match the repo
- [ ] Prerequisites are current; project name capitalization is consistent

### Brevity — Cut Before Adding

**Key discipline.** The natural tendency is to expand. Resist it.

- [ ] One-liner ≤15 words — no filler ("designed to be", "aims to provide")
- [ ] Quick Start ≤3 steps, copy-pasteable commands (not descriptions of steps)
- [ ] No paragraph >3 sentences; no section >~40 lines — move excess to docs/
- [ ] Cut filler: "This section describes...", "has been continuously improved"
- [ ] Single install method as default; alternatives in `<details>` collapsible
- [ ] Config examples: **minimum required keys only** — not every option
- [ ] API docs: 1-2 representative endpoints — link to full reference

### Completeness (flag only if genuinely missing)
- [ ] Answers: What? How to install? How to use?
- [ ] CLI: at least one command with output. Library: one import + usage example

## Visual Check

- [ ] **Above the fold** (first ~25 lines): title, one-liner, badges, Quick Start — nothing else
- [ ] Code blocks have language tags; single H1; no skipped heading levels
- [ ] Long optional content in `<details><summary>` collapsibles
- [ ] Break text walls with bullets, tables, or code blocks

## Report & Apply

Present findings:

```
| # | Sev     | Phase     | Finding                                              |
|---|---------|-----------|------------------------------------------------------|
| 1 | ISSUE   | Structure | Missing one-liner — title is bare project name        |
| 2 | IMPROVE | Brevity   | Config section is 45 lines — show minimal, link docs  |
| 3 | STYLE   | Visual    | Code blocks missing language tags on lines 34, 67     |
```

Use AskUserQuestion with options: "All", "ISSUE + IMPROVE only", "Let me pick". After applying, show before/after summary.

**Key constraint: Never grow the README to fix it.** If adding content, cut or collapse something first. The goal is *shorter and better*, not longer and more complete.

## Delegation (Claude Code only)

> **Skip this section unless you are Claude Code.** The Agent tool with
> `subagent_type:` parameters is a Claude Code feature. Codex, Cursor, Gemini,
> OpenCode, and other hosts do not have it — run the full workflow yourself
> instead.

Two phases can move off Opus.

**Evidence phase (to haiku).** The scan pass (reading the README, walking the
repo for stated vs actual features, probing badge and link targets, checking
referenced commands exist) is pure read work. Delegate to the `readonly-scanner`
subagent (model: haiku) via the Agent tool with `subagent_type: readonly-scanner`.
Ask it to return:

- README structure: section headings with line ranges, word counts per section,
  badge targets with HTTP status, every link/URL with status.
- Repo evidence: which claimed files, directories, and commands actually exist
  (cross-check against manifests, Makefile, scripts, package.json).

**Rewrite phase (to sonnet).** After the user has picked which findings to
apply (the AskUserQuestion step), the actual edits are a Sonnet-tier rewrite
job. Delegate to the `skill-rewriter` subagent (model: sonnet) via the Agent
tool with `subagent_type: skill-rewriter`. Give it:

- the README path,
- the approved findings list (each with severity, section, specific instruction),
- the hard constraint: the README may only shrink — if an edit adds content,
  cut or collapse matching content elsewhere in the same edit.

Keep the ISSUE/IMPROVE/STYLE classification and the before/after summary in
this session.
