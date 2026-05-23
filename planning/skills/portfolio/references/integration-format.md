# Integration Format: `<vault>/Portfolio/<area>/<project>/integration.md`

Each project that participates in the portfolio skill's `integrate` op MAY
carry an `integration.md` file that explicitly declares its inter-project
edges — what it depends on upstream and what it can break downstream. The
`integrate` op reads every such file across the registry, merges the edges
into a single `integration-graph.md`, and cross-checks declared symmetry.
This mirrors the Depends-on/Blocks discipline used inside a single plan, but
applied across project boundaries instead of across tasks: the goal is the
same — make every load-bearing relationship visible and navigable in both
directions, so no edge is only known to the project that happens to feel it.
The file is pure declaration; the `integrate` op never rewrites it.

## Format

Each `integration.md` begins with a YAML frontmatter block:

```yaml
---
project: <name>          # the declaring project (slug)
depends_on:              # upstreams THIS project relies on
  - target: "[[X]]"      # Obsidian wikilink to the upstream project's vault page
    why: <one line>      # what the dependency is (API, schema, shared format, deploy path)
impacts:                 # downstreams a change HERE may break
  - target: "[[Y]]"
    why: <one line>
---
```

Both `depends_on` and `impacts` are optional lists. A leaf project with no
known upstreams or downstreams may omit both entirely (or include them as
empty lists). `target` is always an Obsidian `[[wikilink]]` pointing to the
dependent project's vault page under `Portfolio/`. `why` is mandatory per
edge — a one-line summary of what the dependency is (e.g. an API contract, a
shared schema, a deploy-time path, an environment assumption).

## Symmetry rule

If project A declares `impacts: [[B]]`, then B's `integration.md` SHOULD
declare `depends_on: [[A]]` (and vice-versa). The `integrate` op
cross-checks every edge in both directions after the full rollup. Any
asymmetry — an edge declared on one side but missing on the other — is
surfaced under `## Asymmetries (review)` in `integration-graph.md` and is
NEVER auto-fixed. The user resolves the gap by editing one of the two files
and re-running `integrate`.

The rationale matches the Depends-on/Blocks discipline within a plan: if only
one side of a dependency relationship is declared, the graph is not
navigable in both directions. Someone reading B's file would have no
indication that A can break it; someone reading A's file would not know that
B is a consumer. Requiring both sides makes the full blast radius of any
change discoverable from either end of the edge, without tooling having to
infer intent.

## Body

Below the closing `---` of the frontmatter, an `integration.md` may include
free-text prose giving per-edge detail. Suggested structure:

```
## <TargetProject>

Which exact API endpoint, schema version, or file path is relied upon.
What the version constraint is, if any.
What breaks if the upstream drifts without coordinating a change here.
```

The body is for human readers and is not parsed by `integrate`. It does not
affect graph construction or symmetry checks.

## Example

A complete `integration.md` for `appimage-control`, which consumes
`multitor`'s port-allocation API and is in turn consumed by `deploy-runner`:

```markdown
---
project: appimage-control
depends_on:
  - target: "[[multitor]]"
    why: consumes multitor's port-allocation API to bind per-instance Tor SOCKS ports
impacts:
  - target: "[[deploy-runner]]"
    why: deploy-runner invokes appimage-control's install hook; signature changes break it
---

## multitor

Relies on the `GET /ports/allocate` endpoint introduced in multitor v0.4.
The response schema is `{port: int, circuit_id: str}`. If multitor removes
or renames that field, appimage-control's bind logic fails silently at
runtime (no startup-time check). Coordinate any port-API change with this
project before shipping.

## deploy-runner

deploy-runner calls `appimage-control install --hook post-deploy` with a
fixed argument set. Adding required flags or changing exit-code semantics
here will break deploy-runner's pipeline step without a corresponding update
to its invocation template.
```

With this file present, `integrate` will also expect `multitor/integration.md`
to declare `impacts: [[appimage-control]]` and
`deploy-runner/integration.md` to declare `depends_on: [[appimage-control]]`.
Missing declarations on either side are reported as asymmetries.

## Hard rules

- `integration.md` is pure declaration. The `integrate` op reads it but never
  rewrites it. User-declared edges are never mutated by tooling — not during
  rollup, not during symmetry resolution, not ever.
- A `target` wikilink that resolves to no project in the registry and no vault
  page under `Portfolio/` is flagged as `unresolved target` in
  `integration-graph.md`. This does not block the rollup; all other edges are
  still processed and the graph is still written.
- Frontmatter is parsed with Python's `yaml.safe_load`. If a file's
  frontmatter is malformed YAML — missing closing `---`, a tab where a space
  is required, a bare `@` or other unsafe type tag — that file is skipped with
  a single log line naming the file and the parse error. The rollup continues
  with all remaining files. The `integrate` op never crashes on a single bad
  file.
- `why` is required on every edge. An entry that has `target` but omits `why`
  is treated as malformed and skipped at the edge level (not the file level);
  the rest of the file's edges are still processed.
- Do not use YAML anchors or aliases in `integration.md`. `yaml.safe_load`
  will reject them and the file will be skipped.
