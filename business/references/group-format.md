# Business group format (schema 1)

A **business group** lets several registry projects be assessed, modeled, planned,
launched, and tracked as **one business project**. A suite whose value is the whole
— a server plus its admin client, a CLI plus its GUI, an app plus its backend — has
one audience, one price, and one set of targets; forcing it into per-repo
`BUSINESS.md` files splits the revenue model across directories that were never
separate products.

The manifest lives in the vault beside the group's business artifacts:

```
<vault_dir>/Portfolio/business-groups/<slug>/group.md   ← the manifest
<vault_dir>/Portfolio/business-groups/<slug>/BUSINESS.md
<vault_dir>/Portfolio/business-groups/<slug>/plan.md
<vault_dir>/Portfolio/business-groups/<slug>/market-research.md
<vault_dir>/Portfolio/business-groups/<slug>/gtm-plan.md
<vault_dir>/Portfolio/business-groups/<slug>/metrics.md
```

## Why not a registry field

`~/.claude/projects-registry.yaml` is the obvious place to record membership, and it
is deliberately **not** used. Its format forbids bulk rewrites, and six independent
consumers parse it with a fixed field set (four portfolio scripts, `compass-scan.py`,
`business-scan.py`, `repo-health-scan.py`). A grouping key there couples all of them
to one plugin's feature. A vault manifest is read by exactly the two scripts that
need it and follows the existing integration-arc precedent
(`Portfolio/integrations/<arc>/` with its `spans:` list). Recorded as `DEC-002` in
this project's decisions register.

Directory nesting is also not a grouping signal: `infra/installers/{android,linux,mac,node}`
are registered as four flat projects, so nesting demonstrably does not imply one product.

## Manifest schema

```yaml
---
schema: 1
group: xray-suite            # slug; must equal the containing directory name
members:                     # >= 2, each "<area>/<name>" of an ENABLED registry entry
  - big-projects/xray-host
  - big-projects/xray-host-admin
created: 2026-07-25          # YYYY-MM-DD, set once
---
```

Below the frontmatter, free prose may explain what makes the members one product.
The scanner reads only the frontmatter.

### Field rules

| Field | Rule |
|-------|------|
| `schema` | Required int. Gated exactly like every other business artifact: missing or non-int is fatal for the group; above the supported ceiling degrades with an error rather than being misread. |
| `group` | Required slug. **Must equal the directory name** — the directory is what the resolver finds, so a mismatch would make the group addressable under two different names. |
| `members` | Required list of **≥ 2** `<area>/<name>` strings. One member is not a group; zero is malformed. Each must resolve to an enabled registry entry. |
| `created` | Required `YYYY-MM-DD`. |

### Membership rules

- **A project belongs to at most one group.** A project claimed by two manifests is an
  error reported on both groups and on the project — resolving it requires knowing
  which product the repo actually belongs to, which is a human judgment.
- **A member with its own `<home>/business/` directory is an error**, reported on the
  group entry with the member named. (It cannot also be reported on the member's own
  row, because a grouped member has no row — that is the point of grouping.) There is
  no precedence rule on purpose: silently preferring one set of artifacts would hide a
  real contradiction — someone assessed the repo standalone *and* as part of a suite,
  and those two verdicts may disagree. Resolution is to migrate the per-project
  artifacts into the group directory (and set their `project:` to the group slug) or
  drop the member.
- **An unknown or disabled member** puts the group in `couldnt_assess` with the
  offending member named. The group is never partially assessed — a revenue model
  computed over an unknown subset of a suite is worse than no answer.

## Artifact rules

Group artifacts are ordinary business artifacts with one difference: their
`project:` frontmatter field carries the **group slug** rather than a registry name
(`business-md-format.md` states the relaxed rule). Everything else — `verdict`,
`monetization`, `targets`, the `gtm-plan.md` checkbox contract, the `plan.md` and
`market-research.md` schemas — is unchanged.

### Metrics across several repos

`metrics.md` keeps its flat `<source>.<metric>` keys for **aggregate** values, summed
across members at write time, so the target-matching rule (suffix after the last `.`,
then source precedence — `metrics-format.md`) is untouched. Per-member values are
recorded as breakdown lines:

```markdown
## 2026-07-25

- github.stars: 512
- github.stars@big-projects/xray-host: 431
- github.stars@big-projects/xray-host-admin: 81
- note: xray-host-admin clones unavailable — no push access
```

A key containing `@` is **breakdown only**: it is parsed and retained for
attribution, and never considered for target matching. Without that rule two members
would both claim the `stars` suffix and one would be silently discarded.

### Ship-readiness

`launch` gates a group on the **weakest member's** `MATURITY.md`. A suite ships when
all of it ships; a polished server with an unshippable admin client is not ready.
`MATURITY.md` stays per registry project — maturity is a property of a repo, not of
a revenue model.

## Roll-up

`business-scan.py` emits one entry per group (`group: true`, plus `members`) and one
per **ungrouped** project; a grouped member never also produces its own row.
`business-rollup.py` renders the group as a single row in `global-business.md` whose
Project cell names the slug and both members:

```
| xray-suite — group: big-projects/[[xray-host]] + big-projects/[[xray-host-admin]] | monetize | paid | tracked | 0d | … |
```

`compass-scan.py` attaches the group's business state to **each member**, tagged with
`group: <slug>`, so a per-project view still answers "does this repo have a business
case" without the caller needing to know about groups.
