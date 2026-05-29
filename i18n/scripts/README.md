# i18n — deterministic lane

This `scripts/` directory is i18n's **deterministic lane**, vendored from
the plugin-dev determinism kit. It encodes one rule:

> **Mechanical, decidable checks belong in scripts. Semantic judgment belongs to
> the LLM.** Scripts flag; the model decides and writes.

## Layout

```
scripts/
├── lib/findings.sh           # shared finding accumulator + JSON contract (from plugin-dev; do not fork)
├── validate.sh               # orchestrator — discovers and runs every validate-*.sh, merges, prints a verdict
├── validate-catalog-diff.sh  # missing / stale / extra keys across locales
└── validate-placeholders.sh  # placeholder & CLDR-plural integrity of existing translations
```

## Domain validators

Each wrapper is a thin shim over i18n's existing Python (under
`skills/*/scripts/`): it runs the real Python against a target project, parses
its output, and re-emits findings on the shared contract. The Python logic is
not duplicated in bash. Both take
`<target-project-root> [--json] [--framework <name>] [--source-locale <code>]`
and auto-detect the framework(s) via `detect-framework.py` when `--framework`
is omitted. They require `python3` (exit 3 if missing, mirroring the `jq` guard).

| Wrapper | Wraps | Rule ids | Checks |
|---|---|---|---|
| `validate-catalog-diff.sh` | `i18n-audit/scripts/diff-catalogs.py` | `i18n-missing-key` (error), `i18n-stale-key` (error), `i18n-extra-key` (warn) | keys in source but absent from a target locale; keys whose placeholder set drifted from source (stale); keys in a target with no source counterpart |
| `validate-placeholders.sh` | `i18n-translate/scripts/validate-placeholders.py` (+ `diff-catalogs.collect_catalogs` to build the workpacket) | `i18n-placeholder-mismatch` (error), `i18n-missing-plural-categories` (error), `i18n-unbalanced-braces` (error), `i18n-printf-type-mismatch` (error), `i18n-html-tag-mismatch` (warn), `i18n-empty-translation` (warn) | placeholder / ICU / printf / HTML integrity and required CLDR plural categories of translations already in the catalogs |

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

Each `validate-<domain>.sh` checks one slice of i18n's domain — only things
decidable by a rule (parse, field presence, enum, count, regex). Source the lib,
guard `jq`, call `add_finding <severity> <rule-id> <category> <path> <line> <msg>`
per check, end with `render_findings`. Anything requiring taste or rewriting is
**not** a script — it stays with i18n's skills/agents, which run `validate.sh`
and consume its JSON instead of re-deriving the rules.

> Validating i18n's *plugin structure* (manifest, frontmatter, layout) is
> plugin-dev's job — run plugin-dev's `validate-plugin.sh` against this repo.
> The validators here check i18n's own domain.
