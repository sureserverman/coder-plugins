# git-github — deterministic lane

This `scripts/` directory is git-github's **deterministic lane**, vendored from
the plugin-dev determinism kit. It encodes one rule:

> **Mechanical, decidable checks belong in scripts. Semantic judgment belongs to
> the LLM.** Scripts flag; the model decides and writes.

## Layout

```
scripts/
├── lib/findings.sh        # shared finding accumulator + JSON contract (from plugin-dev; do not fork)
├── validate.sh            # orchestrator — discovers and runs every validate-*.sh, merges, prints a verdict
└── validate-workflows.sh  # GitHub Actions workflow lane (wraps the github-workflow-audit Python)
```

## validate-workflows.sh — the workflow lane

```bash
bash scripts/validate-workflows.sh <repo-root> [--json]
```

A thin wrapper over `skills/github-workflow-audit/scripts/audit-workflows.py`.
It does **not** re-implement any check: it runs the existing Python against
`<repo-root>/.github/workflows`, parses its severity-sorted markdown table, and
re-emits each row as a contract finding with a stable kebab-case `rule`. The
Python stays the single source of mechanical truth. If `<repo-root>/.github/workflows`
is absent it emits one `gha-no-workflows` info finding and exits `0`.

Rule-ids (mapped from the Python's `ERROR`/`WARN`/`INFO` rows):

| rule | from |
|---|---|
| `gha-syntax` | YAML parse error, missing `on:`/`name:`/`jobs`, job without `runs-on:`/`uses:`, `uses:` without `@ref` |
| `gha-mutable-ref` | `uses:` pinned to `@main`/`@master`/`@develop`/`@HEAD` |
| `gha-action-outdated` | action major behind latest release |
| `gha-injection` | user-controlled context in `run:`/interpolated into shell |
| `gha-secret-echo` | secret echoed to log |
| `gha-hardcoded-cred` | possible hardcoded credential |
| `gha-permissions` | `permissions: write-all` / missing permissions block |
| `gha-malformed-if` | comparison outside `${{ }}` in `if:` |
| `gha-github-env-same-step` | var set via `GITHUB_ENV` and read in same step |
| `gha-needs-undefined` | `needs:` references an undefined job |
| `gha-no-timeout` | job without `timeout-minutes` |
| `gha-no-concurrency` | no top-level `concurrency:` |
| `gha-unreferenced-reusable` | reusable workflow no caller references |

Cross-workflow parity, reusable-workflow input/secret matching, and fix
authoring stay with the `github-workflow-audit` skill (the LLM lane).

Run the whole lane:

```bash
bash scripts/validate.sh <plugin-root> [--json]
```

`--json` emits the contract (consumed by this plugin's agents/commands); without
it, a human report.

## The JSON contract

Every `validate-*.sh`, with `--json`, prints:

```json
{"validator","target","summary":{"errors","warnings","info"},
 "findings":[{"severity":"error|warn|info","rule","category","path","line","message"}],
 "verdict":"pass|pass-with-warnings|fail"}
```

Exit code: `1` if any error, else `0` (`2` usage, `3` jq missing).

## Adding a domain validator

Each `validate-<domain>.sh` checks one slice of git-github's domain — only things
decidable by a rule (parse, field presence, enum, count, regex). Source the lib,
guard `jq`, call `add_finding <severity> <rule-id> <category> <path> <line> <msg>`
per check, end with `render_findings`. Anything requiring taste or rewriting is
**not** a script — it stays with git-github's skills/agents, which run `validate.sh`
and consume its JSON instead of re-deriving the rules.

> Validating git-github's *plugin structure* (manifest, frontmatter, layout) is
> plugin-dev's job — run plugin-dev's `validate-plugin.sh` against this repo.
> The validators here check git-github's own domain.
