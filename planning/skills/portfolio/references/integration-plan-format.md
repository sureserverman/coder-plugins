# Integration Plan Format

An integration plan coordinates a change that touches multiple projects — for
example, "ship port-API v2 in multitor, then make appimage-control consume it,
then deprecate v1". It is distinct from a per-project plan because no single
project owns the full arc; and distinct from a regular `[[Plans/]]` vault page
because it is operational and multi-project, with concrete stages, dependencies,
and a live status tracker that gets updated as each stage lands.

## Directory layout

```
Portfolio/integrations/<arc-name>/
  plan.md      # the coordinated staged plan
  status.md    # which stages are green
```

`<arc-name>` is a kebab-case slug derived from the arc's theme,
e.g. `multitor-port-api-v2`.

## plan.md format

Every `plan.md` begins with YAML frontmatter followed by a staged body.

### Frontmatter

```yaml
---
arc: <arc-name>
spans:                       # the projects this arc touches
  - "[[multitor]]"
  - "[[appimage-control]]"
created: <YYYY-MM-DD>
status: active | done | abandoned
---
```

| Field | Meaning |
|---|---|
| `arc` | Matches the directory slug exactly. |
| `spans` | Wikilink list of every project the arc touches. Must contain ≥2 entries. |
| `created` | ISO date the arc was first opened. Set once; never updated. |
| `status` | Lifecycle state. Flip to `done` when all stages are green; `abandoned` if the arc is cancelled. |

### Body

The body lists stages in execution order. Each stage is attributed to one of
the spanned projects and uses the same Stage/Task/Depends-on/Blocks discipline
as planning-projects plans.

Example skeleton:

```
## Stage 1 (multitor): ship port API v2

- Task: add v2 route handler
- Task: write migration guide

## Stage 2 (appimage-control): consume v2   (depends on Stage 1)

- Task: update client to call v2 endpoint
- Task: integration smoke test

## Stage 3 (multitor): deprecate v1         (depends on Stage 2)

- Task: remove v1 handler
- Task: update changelog
```

A stage header must name its owning project in parentheses. Dependency
annotations go inline on the header line as `(depends on Stage N)`.

## status.md format

`status.md` holds a per-stage table that the user (or the `executing-plans`
skill) updates as stages land. Structure:

```markdown
# Status: <arc-name>

| Stage | Owner | State | Landed |
|---|---|---|---|
| Stage 1 | multitor | green | 2026-03-10 |
| Stage 2 | appimage-control | pending | — |
| Stage 3 | multitor | pending | — |
```

Valid states: `pending`, `in-progress`, `green`, `blocked`.

The `Landed` column records the date the stage was confirmed complete; leave
`—` until it is.

## Backlog pointer rule

When an integration plan is created, each project listed in `spans` must
receive a pointer entry in its own `backlog.md`. The entry is tagged
`integration` and carries an `Integration:` field so the project's backlog
surfaces the cross-project commitment:

```markdown
- [ ] [integration] Track arc `multitor-port-api-v2`
  Integration: plan=multitor-port-api-v2
  Ref: Portfolio/integrations/multitor-port-api-v2/plan.md
```

The portfolio `integrate` rollup links these entries when it builds the
integration graph. Do not add the pointer after stages are already complete —
add it at arc creation time.

## Relationship to integration-graph.md

The arc appears as a node in `integration-graph.md`, connecting the spanned
projects. Its edges count toward the graph's dependency and coupling metrics.
The graph entry format is:

```
multitor-port-api-v2:
  spans: [multitor, appimage-control]
  status: active
```

The portfolio `integrate` op reads `plan.md` frontmatter to build these
entries; it does not rewrite the plan body.

## Hard rules

- One arc = one directory. No nesting of integration plans inside each other.
- `spans` must list ≥2 projects. A single-project arc is just a normal project
  plan — put it in `Portfolio/<area>/<project>/plans/` instead.
- Generated or edited by hand or by the planning skills. The portfolio
  `integrate` op reads the plan for the graph but does not rewrite the plan
  body; manual edits to the body are safe.
- `arc` in the frontmatter must match the directory name exactly. Mismatches
  cause the `integrate` rollup to skip the arc with a warning.
- Do not delete a `status.md` when an arc reaches `done`. Archive the
  directory in place so the graph retains historical edge data.
