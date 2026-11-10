---
name: github-workflow-audit
description: Use when checking GitHub Actions workflows for errors, outdated actions, security issues, or improvements. Trigger on "audit my workflows", "check github actions", "are my actions secure", "update my action versions", or for a repo-wide `.github/workflows/` health check.
---

# GitHub Workflow Audit

Audit every `.github/workflows/*.yml|*.yaml` file in the repo.

## 1. Run the script

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/validate-workflows.sh" <repo-root> [--json]
```

`${CLAUDE_PLUGIN_ROOT}` is the installed `git-github/` plugin directory. The
wrapper runs `${CLAUDE_PLUGIN_ROOT}/skills/github-workflow-audit/scripts/audit-workflows.py`
and re-emits its rows on the shared finding contract (stable `gha-*` rule ids;
`--json` for structured, mergeable output). The Python can also be run directly
for its severity-sorted table; it exits 1 on any ERROR.

The script decides: YAML parse, `on:`/`runs-on:`/`uses:` structure, outdated
majors and mutable refs (`@main`), expression injection in `run:`, echoed
secrets, possible hardcoded credentials, `write-all` or missing `permissions:`,
malformed `if:`, same-step `GITHUB_ENV` reads, missing `needs:` targets,
missing `timeout-minutes`/`concurrency`, unreferenced reusable workflows. Do
not re-check these by hand.

## 2. Judge what the script cannot

Read the workflow files and check:

- **Reusable-workflow parity.** Each local `uses: ./.github/workflows/x.yml` exists; callers pass every `required: true`
  `workflow_call` input; `with:` keys match declared inputs; `secrets:` names
  match the callee's declarations.
- **Input types.** `with:` values match the declared type (string / boolean /
  number).
- **Input access.** `inputs.*` inside `workflow_call`; `inputs.*` vs
  `github.event.inputs.*` consistent within one file.
- **Artifact names** unique across jobs using `upload-artifact` /
  `download-artifact`.
- **`continue-on-error:`** used on purpose, not masking real failures.
- **Step ordering.** Steps that need files from earlier steps come after them.
- **Cross-workflow consistency.** Shared input definitions and secret
  references agree across callers; mixed runner pins (`ubuntu-latest` vs
  pinned) are INFO.
- **Expression-injection context.** User-controlled values in `with:` are WARN
  (the script covers `run:`). Default IPs in `workflow_dispatch` inputs are
  INFO, not errors. `StrictHostKeyChecking no` in CI is INFO.
- **Improvements (INFO).** Repeated step blocks worth a reusable workflow or
  composite action; jobs serialized by `needs:` that could run in parallel;
  large `run:` blocks worth moving to a script.

## 3. Report

Severity: **ERROR** (breaks the workflow), **WARN** (likely bug, security risk,
outdated), **INFO** (improvement). Merge script and judgment findings into one
table:

```
| #  | Severity | File | Line(s) | Issue |
|----|----------|------|---------|-------|
| 1  | ERROR    | reusable-deploy.yml | 68 | Expression injection: unquoted ${{ inputs.keyreplace }} in shell case statement |
```

Then list the fixes grouped by severity, ERROR first, and offer to apply them.
