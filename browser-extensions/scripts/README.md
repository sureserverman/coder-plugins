# browser-extensions — deterministic lane

This `scripts/` directory is browser-extensions's **deterministic lane**, vendored from
the plugin-dev determinism kit. It encodes one rule:

> **Mechanical, decidable checks belong in scripts. Semantic judgment belongs to
> the LLM.** Scripts flag; the model decides and writes.

## Layout

```
scripts/
├── lib/findings.sh      # shared finding accumulator + JSON contract (from plugin-dev; do not fork)
├── validate.sh          # orchestrator — discovers and runs every validate-*.sh, merges, prints a verdict
└── validate-amo.sh      # AMO-compliance domain validator (wraps the existing amo-check.py linter)
```

Run the whole lane:

```bash
bash scripts/validate.sh <plugin-root> [--json]
```

`--json` emits the contract (consumed by this plugin's agents/commands); without
it, a human report.

## validate-amo.sh — the AMO compliance lane

`validate-amo.sh` is a thin bash wrapper over the existing Python linter
`skills/amo-compliance-check/scripts/amo-check.py`. It does **not** reimplement
any check — it runs the Python against a target extension directory, parses its
`[FAIL]/[WARN] §N …` lines, and re-emits them on the shared JSON contract.

```bash
bash scripts/validate-amo.sh <extension-dir> [--json]
```

Note the target is a **browser-extension directory** (the one containing
`manifest.json`), not the plugin root. Severity mapping: `FAIL → error`,
`WARN → warn`, anything else → `info`. Stable kebab-case rule ids by section:

| § | Section | rule-id |
|---|---|---|
| 1 | Manifest required | `amo-manifest-field` |
| 2 | Manifest conditional | `amo-manifest-conditional` |
| 3 | Icons | `amo-icon` |
| 4 | File structure | `amo-file-structure` |
| 5 | Permissions | `amo-permission` |
| 6 | Security — remote code | `amo-remote-script` |
| 7 | Security — code quality | `amo-code-quality` |
| 8 | Data & privacy | `amo-data-privacy` |
| 9 | Content scripts | `amo-content-script` |
| 10 | MV3 specific | `amo-mv3` |

The mechanical checks (manifest parse, field presence/format, permission
whitelist, remote-script/`eval` regex) emit the contract here. The judgment calls
— is `<all_urls>` actually necessary, is this obfuscation, is the DOM injection
safe — stay in the LLM lane (`amo-compliance-check` SKILL.md).

## The JSON contract

Every `validate-*.sh`, with `--json`, prints:

```json
{"validator","target","summary":{"errors","warnings","info"},
 "findings":[{"severity":"error|warn|info","rule","category","path","line","message"}],
 "verdict":"pass|pass-with-warnings|fail"}
```

Exit code: `1` if any error, else `0` (`2` usage, `3` jq missing).

## Adding a domain validator

Each `validate-<domain>.sh` checks one slice of browser-extensions's domain — only things
decidable by a rule (parse, field presence, enum, count, regex). Source the lib,
guard `jq`, call `add_finding <severity> <rule-id> <category> <path> <line> <msg>`
per check, end with `render_findings`. Anything requiring taste or rewriting is
**not** a script — it stays with browser-extensions's skills/agents, which run `validate.sh`
and consume its JSON instead of re-deriving the rules.

> Validating browser-extensions's *plugin structure* (manifest, frontmatter, layout) is
> plugin-dev's job — run plugin-dev's `validate-plugin.sh` against this repo.
> The validators here check browser-extensions's own domain.
