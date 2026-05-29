# plugin-dev validation & scaffolding suite

Deterministic bash tooling for the **deterministic lane** of plugin-dev. The rule
this directory encodes:

> **Mechanical, decidable checks belong in scripts. Semantic judgment belongs to
> the LLM.** Scripts flag; the model decides and writes.

## The determinism boundary

| Lane | Owner | What it covers |
|---|---|---|
| **Deterministic** | scripts here | JSON/YAML parse, required-field presence, name↔directory match, enum/whitelist checks (model, color, hook events, MCP transport), line/char caps, reference-nesting depth, `${CLAUDE_PLUGIN_ROOT}` usage, `stop_hook_active` guard, `$ARGUMENTS` quoting, hardcoded-path / plaintext-secret regex, leak-pattern **candidate** detection |
| **Semantic** | LLM (`plugin-validator`, `skill-reviewer`, skills) | leak **confirmation** + rewrite, prompt-injection risk, triggering quality, model-tier choice, tool-set minimalism, design coherence, "skill vs MCP", authoring component bodies |

Two consequences worth internalizing:

- **Regex leak detection only flags candidates.** `validate-skill.sh` can spot a
  numbered list or "first…then…" in a `description:`, but whether that is a genuine
  leak — and how to rewrite it without losing the trigger — is the model's call.
- **Scripts never edit files.** They read, decide, and report. Mutation (scaffolding)
  is a separate, explicit family of scripts (`scaffold-*.sh`).

## Layout

```
scripts/
├── lib/findings.sh          # shared accumulator + renderer + JSON contract
├── validate-plugin.sh       # orchestrator — discovers components, dispatches, merges
├── validate-manifest.sh     # .claude-plugin/plugin.json + marketplace consistency
├── validate-skill.sh        # skills/<name>/SKILL.md
├── validate-command.sh      # commands/<name>.md
├── validate-agent.sh        # agents/<name>.md
├── validate-hooks.sh        # hooks/hooks.json + bundled hook scripts
├── validate-mcp.sh          # .mcp.json
├── validate-settings.sh     # .claude/<plugin>.local.md settings files
└── scaffold-{plugin,skill,command,hook}.sh
```

## The JSON contract

Every validator, with `--json` (or `FINDINGS_JSON=1`), prints exactly:

```json
{
  "validator": "validate-skill.sh",
  "target": "skills/foo/SKILL.md",
  "summary": {"errors": 0, "warnings": 1, "info": 0},
  "findings": [
    {"severity": "warn", "rule": "skill-desc-long",
     "category": "skill", "path": "skills/foo/SKILL.md", "line": 3,
     "message": "description >800 chars; risks truncation when many skills load"}
  ],
  "verdict": "pass-with-warnings"
}
```

- `severity` ∈ `error` | `warn` | `info`.
- `verdict`: `fail` if any error, else `pass-with-warnings` if any warning, else `pass`.
- **Exit code:** `1` if any error, `0` otherwise. (`2` = usage error, `3` = `jq` missing.)
- Without `--json`, the same data renders as an emoji report for humans.

The orchestrator runs each child with `FINDINGS_JSON=1`, concatenates every `.findings`
array, and recomputes the summary/verdict over the union.

## How to add a new per-domain validator

1. Copy the skeleton of any `validate-*.sh`. Source the lib and guard `jq`:
   ```bash
   DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   . "$DIR/lib/findings.sh"
   have_jq
   ```
2. Parse `--json` → `FINDINGS_JSON=1`; first positional is the target path.
3. Run only **decidable** checks. For each, call:
   ```bash
   add_finding <severity> <rule-id> <category> <relpath> <line|0> "<message>"
   ```
   Keep `<rule-id>` stable and kebab-case — agents and tests key off it.
4. End with `render_findings "validate-foo.sh" "$target"; exit $?`.
5. If the orchestrator should auto-dispatch it, add a discovery branch in
   `validate-plugin.sh`.
6. Anything requiring taste, intent, or rewriting does **not** go here — leave it to
   `plugin-validator` / `skill-reviewer`.

## Rule-id catalogue (stable identifiers)

Rule ids are the contract between scripts and the LLM lane; the `plugin-validator`
agent reports them verbatim. Grep the validators for the authoritative list; the
common ones:

`manifest-*`, `layout-in-claude-plugin`, `skill-name-mismatch`, `skill-too-long`,
`skill-desc-long`, `skill-ref-too-deep`, `desc-first-person`, `desc-leak-candidate`,
`cmd-*`, `agent-*`, `hook-event-unknown`, `hook-stop-no-guard`, `hook-path-not-root`,
`mcp-*`, `settings-*`.
