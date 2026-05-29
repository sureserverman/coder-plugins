# infra-build — deterministic lane

This `scripts/` directory is infra-build's **deterministic lane**, vendored from
the plugin-dev determinism kit. It encodes one rule:

> **Mechanical, decidable checks belong in scripts. Semantic judgment belongs to
> the LLM.** Scripts flag; the model decides and writes.

## Layout

```
scripts/
├── lib/findings.sh      # shared finding accumulator + JSON contract (from plugin-dev; do not fork)
├── validate.sh          # orchestrator — discovers and runs every validate-*.sh, merges, prints a verdict
└── validate-<domain>.sh # infra-build's own domain validators (you add these)
```

Run the whole lane against a project being prepped for packaging:

```bash
bash scripts/validate.sh <project-root> [--json]
```

`--json` emits the contract (consumed by this plugin's skills); without it, a human report.

## infra-build's domain validators

- `validate-deb.sh <project-root>` — the deb/ packaging tree: structure, control
  fields, maintainer-script shebang/exec bits, `systemctl --global` and
  `${SUDO_USER:-$USER}` footguns, `Architecture: all` on a compiled package.
- `validate-readiness.sh <project-root>` — source-repo signals for the
  build-for-mac (Cargo.toml, mac/Makefile targets, mac/payload) and publish-images
  (Dockerfile, dispatch wiring) pipelines.

The **cross-repo registration sync** (programs.txt / images.yml / workflow YAML in
the infra pipeline repos) stays judgment — it spans other repos and punctuation
conventions — and lives in the register skills, not here.

## The JSON contract

Every `validate-*.sh`, with `--json`, prints:

```json
{"validator","target","summary":{"errors","warnings","info"},
 "findings":[{"severity":"error|warn|info","rule","category","path","line","message"}],
 "verdict":"pass|pass-with-warnings|fail"}
```

Exit code: `1` if any error, else `0` (`2` usage, `3` jq missing).

## Adding a domain validator

Each `validate-<domain>.sh` checks one slice of infra-build's domain — only things
decidable by a rule (parse, field presence, enum, count, regex). Source the lib,
guard `jq`, call `add_finding <severity> <rule-id> <category> <path> <line> <msg>`
per check, end with `render_findings`. Anything requiring taste or rewriting is
**not** a script — it stays with infra-build's skills/agents, which run `validate.sh`
and consume its JSON instead of re-deriving the rules.

> Validating infra-build's *plugin structure* (manifest, frontmatter, layout) is
> plugin-dev's job — run plugin-dev's `validate-plugin.sh` against this repo.
> The validators here check infra-build's own domain.
