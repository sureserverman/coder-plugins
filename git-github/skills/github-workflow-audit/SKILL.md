---
name: github-workflow-audit
description: Use when checking GitHub Actions workflows for errors, outdated actions, security issues, or improvements. Trigger on "audit my workflows", "check github actions", "are my actions secure", "my release workflow is broken", "update my action versions", or when the user wants a health check across the repo's `.github/workflows/` directory.
---

# GitHub Workflow Audit

Systematic review of all GitHub Actions workflow files in a repository for errors, outdated actions, security issues, and improvement opportunities.

## Instructions

When invoked, audit all workflows in the repository.

**Preferred — run the bundled script first:**

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/github-workflow-audit/scripts/audit-workflows.py" [repo-root]
```

`${CLAUDE_PLUGIN_ROOT}` resolves to the installed `git-github/` plugin
directory. If `repo-root` is omitted the script audits the current working
directory.

It covers: YAML parse via `yaml.safe_load`, required `on:`/`runs-on:`/`uses:` structure, action-version currency via GitHub `releases/latest` redirect-scrape (flags outdated major versions and mutable branch refs like `@main`), expression-injection detection for `github.event.*`/`inputs.*`/`github.head_ref` in `run:` blocks, secret-echo patterns, possible hardcoded credentials, `permissions: write-all` and missing permissions blocks, malformed `if:` comparisons, same-step `GITHUB_ENV` reads, missing `needs:` targets, missing `timeout-minutes`/`concurrency`, and unreferenced reusable workflows. Findings are printed as a severity-sorted table. Exit 1 if any ERROR was found.

**After the script, still read the sections below** — they remain the source of truth for what's checked and cover the pieces that need human judgment: section 1 (reusable-workflow input/secret parity between callers and callees), section 4 (artifact-name uniqueness across jobs, `continue-on-error` intent, input type correctness), section 5 (cross-workflow consistency beyond what parsing can verify), and section 6 (parallelization opportunities, run-block extraction). Use the numbered sections as both the script's spec and your manual-pass checklist. Offer to fix all issues at the end.

<details>
<summary>Manual pass (fallback — only if the script isn't available)</summary>

Find all `.github/workflows/*.yml` and `.github/workflows/*.yaml` files in the repository using the Glob tool. Read every workflow file. Then run every check section below in order.

For each finding, report severity: **ERROR** (will break the workflow), **WARN** (likely bug, security risk, or outdated), or **INFO** (improvement suggestion). At the end, provide a summary table and offer to fix all issues.

</details>

## 1. YAML Syntax & Structure

Read each workflow file and check:

- [ ] Valid YAML — run `python3 -c "import yaml; yaml.safe_load(open('<file>'))"` or `yq '.' <file>` via Bash tool to verify parse
- [ ] Every workflow has a `name:` field
- [ ] Every workflow has an `on:` trigger defined
- [ ] Every job has a `runs-on:` field (unless it uses `uses:` for reusable workflows)
- [ ] Step `uses:` values follow the format `owner/repo@ref` or `./.github/workflows/file.yml`
- [ ] Reusable workflows referenced via `uses: ./.github/workflows/*.yml` actually exist — cross-check against discovered workflow files
- [ ] `workflow_call` inputs declared in reusable workflows match what callers pass via `with:`
- [ ] `secrets:` declared in reusable workflows match what callers pass via `secrets:`
- [ ] No YAML anchors/aliases used incorrectly

## 2. Action Version Check

For every `uses:` reference that pins to a version tag (e.g. `actions/checkout@v4`):

1. Extract the owner, repo, and current ref
2. For GitHub-hosted actions, fetch the latest release:
   ```bash
   curl -sI -o /dev/null -w "%{url_effective}" -L "https://github.com/<owner>/<repo>/releases/latest"
   ```
3. Compare the pinned major version against the latest major version
4. Report **WARN** for outdated major versions (e.g. `@v3` when `@v4` is available)
5. Report **INFO** for outdated minor/patch versions within the same major (e.g. `@v4.1.0` when `@v4.2.0` exists) — only if pinned to a full semver, not just a major tag

Note: Pinning to a major version tag like `@v4` is standard practice and is considered current as long as the major version is latest.

## 3. Security Review

Check for common security anti-patterns:

- [ ] **Expression injection** — `${{ github.event.inputs.* }}`, `${{ github.event.pull_request.title }}`, or other user-controlled context values used directly in `run:` blocks without quoting. These allow arbitrary command injection. Flag as **ERROR** if the value is interpolated into a shell command. Flag as **WARN** if used in a `with:` parameter (less dangerous but still risky with untrusted PRs)
- [ ] **Overly broad permissions** — `permissions: write-all` or no permissions block at all (defaults to broad). Suggest least-privilege `permissions:` block
- [ ] **Secrets in logs** — secrets echoed or used in ways that could leak to logs (e.g. `echo ${{ secrets.KEY }}`)
- [ ] **Mutable action references** — `uses:` pinned to a branch like `@main` or `@master` instead of a tag or SHA. Report **WARN** — these can change without notice
- [ ] **StrictHostKeyChecking no** — SSH steps that disable host key verification. Report **INFO** for CI contexts (common but worth noting)
- [ ] **Hardcoded credentials** — API keys, tokens, passwords, or IP addresses hardcoded in workflow files instead of using secrets. Note: default input values for manual `workflow_dispatch` triggers (like default server IPs) are **INFO** level, not errors

## 4. Logic & Correctness

- [ ] `if:` conditions use correct syntax — e.g. `${{ inputs.foo == 'bar' }}` not `${{ inputs.foo }} == 'bar'`
- [ ] `env:` variables set via `>> $GITHUB_ENV` use correct syntax and are available in subsequent steps (not same step)
- [ ] Artifact names are unique across jobs when using `upload-artifact` / `download-artifact`
- [ ] `needs:` dependencies between jobs form a valid DAG (no cycles, referenced jobs exist)
- [ ] `continue-on-error:` is used intentionally and not masking real failures
- [ ] Steps that depend on files from previous steps have proper ordering
- [ ] Inputs accessed via `${{ inputs.* }}` vs `${{ github.event.inputs.* }}` — within `workflow_call` use `inputs.*`; within `workflow_dispatch` both work but should be consistent within the same file
- [ ] Reusable workflow `with:` values match expected types (string, boolean, number) — e.g. passing a boolean to a string input or vice versa

## 5. Cross-Workflow Consistency

When multiple workflows exist:

- [ ] Caller workflows pass all `required: true` inputs to reusable workflows
- [ ] Secret names used in callers match declarations in the reusable workflow
- [ ] Shared patterns (input definitions, secret references) are consistent across caller workflows
- [ ] No orphaned workflows — reusable workflows are actually referenced by at least one caller
- [ ] Runner versions are consistent (`ubuntu-latest` vs pinned versions) — report **INFO** if mixed

## 6. Improvement Suggestions

Look for opportunities to improve workflows:

- [ ] Repeated step blocks across workflows that could be extracted into a reusable workflow or composite action
- [ ] Missing `timeout-minutes:` on jobs (default is 360 minutes / 6 hours — usually too long)
- [ ] Missing `concurrency:` group to prevent duplicate runs
- [ ] Jobs that could run in parallel but are serialized with `needs:`
- [ ] Large `run:` blocks that could be extracted into scripts for easier testing and maintenance

## Summary Format

After all checks, output:

```
| #  | Severity | File | Line(s) | Issue |
|----|----------|------|---------|-------|
| 1  | ERROR    | reusable-deploy.yml | 68 | Expression injection: unquoted ${{ inputs.keyreplace }} in shell case statement |
| 2  | WARN     | deploy.yml | 45 | actions/checkout@v3 is outdated (latest: v4) |
| 3  | INFO     | reusable-deploy.yml | 41 | Missing timeout-minutes on deploy job |
| ...| ...      | ...  | ...     | ... |
```

Then list **actionable fixes** grouped by severity (ERROR first), and offer to apply all fixes.

## Delegation (Claude Code only)

> **Skip this section unless you are Claude Code.** The Agent tool with
> `subagent_type:` parameters is a Claude Code feature. Codex, Cursor, Gemini,
> OpenCode, and other hosts do not have it — run the full workflow yourself
> instead.

The workflow/action enumeration, YAML parse, action-version redirect-scrapes,
and `actionlint` pass are read-only bulk work. If you are on Opus, delegate
them to the `readonly-scanner` subagent (model: haiku) via the Agent tool with
`subagent_type: readonly-scanner`. Ask it to return:

- Every `.github/workflows/*.yml` parsed, with `on`, `jobs.*.runs-on`,
  `permissions`, and `timeout-minutes` per job.
- Every `uses:` reference with its pinned ref and whether it's a SHA, a tag,
  or a floating branch — plus the latest release for the owner/repo.
- `actionlint` raw output if the binary is on PATH.

Keep the severity assignment (sections 3 security and 4 correctness), the
cross-workflow consistency check (section 5), and any fix offering in this
session.
