---
name: decisions
description: Use to record, read, or promote architectural decisions and the reasons behind them — per-project and per-architecture-domain. Triggers on "record this decision", "why did we choose X", "log this sec-audit recommendation", "promote this to the android decisions", "what binds all Rust projects".
---

# Decisions

The decisions register answers *why the architecture is the way it is* — long
after the plan that decided it has been archived and the person who decided it
has forgotten. It has two halves:

- **Per-project** — `<portfolio_home>/decisions.md`, `DEC-NNN` entries binding
  this project.
- **Per-domain** — `<vault_dir>/Portfolio/decisions/<domain>.md`,
  `GDEC-<DOM>-NNN` entries binding every project on a platform or stack
  (`android`, `ios`, `rust`, `ubuntu`, `macos`, `tor`, …).

The two are linked in both directions and the linkage is symmetry-checked. The
full format — block grammar, field semantics, symmetry rule, parser rules — is
`../portfolio/references/decisions-format.md`. **Read it before writing any
entry**; this file covers the operations, not the format.

## Where the files live (resolver)

Neither register lives in the repo.

```
<portfolio_home>/decisions.md              where portfolio_home = <vault_dir>/Portfolio/<area>/<name>/
<vault_dir>/Portfolio/decisions/<domain>.md
```

Resolve `portfolio_home` per `../portfolio/references/registry-format.md`: read
`vault_dir` from `~/.claude/portfolio-config.yaml`, combine with the project's
`area`/`name` from `~/.claude/projects-registry.yaml`. **If `vault_dir` is unset,
refuse and fail loudly — never fall back to a path inside the repo.** That
fallback is what the vault-canonical storage law exists to prevent.

**Announce at start:** "Using the decisions skill — <add|list|read|relevant|promote|supersede> on <path>."

---

## Operations

### `add` — record a new decision

Inputs: title, reason, domains, source; optional `--global <GDEC-ID>` to link an
existing domain entry at creation time.

1. Read `<portfolio_home>/decisions.md`. If absent, create it with the header
   block from the format reference (no entries yet).
2. Compute the next ID: scan for `DEC-\d{3}`, take max, add 1. **Never reuse an
   ID**, including one whose entry is superseded.
3. Insert the new block immediately below the top `---` separator (newest first).
4. Save, and report `Recorded DEC-NNN — <title>.`

**The `Reason` field is the deliverable.** An entry whose reason restates the
decision ("chose Orbot because Orbot is the right choice") is worthless six
months later. Capture: the constraint that forced the choice, the evidence, the
alternative rejected and why, and the cost accepted. If you cannot state a cost
or a rejected alternative, question whether a decision was actually made.

**Duplicate guard.** Before writing, scan existing entries for the same `Source`
or ≥80% title token overlap. Surface the match and ask whether to supersede that
entry instead of opening a parallel one — two live entries disagreeing about the
same question is the failure mode this register exists to prevent.

### `list` — show entries

Optional filters: `domain:<slug>`, `status:accepted|superseded`,
`since:<YYYY-MM-DD>`, `--global` (list domain entries instead of project ones).

Output a compact table — `ID | Title | Domains | Decided | Status` — newest
first.

### `read` — return raw file content

For ingestion by other skills (`planning-projects` and `brainstorming` research
phases, `architecting-projects` prior-art scan). Returns the file as text; the
caller parses. With `--domain <slug>`, returns that domain register instead.

### `relevant` — digest what binds this project

The question a planner and an executor actually ask: *which recorded decisions
constrain the work in front of me?* Unlike `read`, this resolves the domain
registers for you and returns a compact digest of both halves rather than raw
files.

Inputs: optional `--domains <slug,...>`, `--project <name> --area <area>`,
`--format text|json`.

1. **Infer the domains** from the project's stack via `references/domain-slugs.md`
   — that table is paired with `dispatching-parallel-agents`'s stack-routing
   table, so the same signal that picks a subagent picks a register. When the
   stack is ambiguous, pass every plausible slug: an extra register costs one
   read, a missed one costs a violated constraint nobody catches until review.
   Run `scripts/decisions-relevant.py --list-domains` to see which registers
   exist right now.
2. **Run** `scripts/decisions-relevant.py --domains <slugs> --project <name>
   --area <area>`. It imports the same fixture-locked parser `portfolio rebuild`
   uses, so the digest can't disagree with the roll-up.
3. **Read the digest as-is.** Superseded entries come back **marked, not
   filtered** — "we believed X and stopped" is what prevents the rejected
   approach being re-proposed. Malformed blocks come back **flagged, not
   dropped**; a decision that fails to parse is precisely the one to look at.

**The three degrade states** — all normal, none an error:

| State | Meaning |
|---|---|
| `project_register: present` | Both halves returned. |
| `project_register: absent` (registered) | The project is in the registry but has recorded no decisions yet. The global half still binds it. |
| `project_register: absent` (unregistered) | A brand-new project with no portfolio home. **The global half is authoritative and sufficient** — see below. |

Never treat an absent project half as "no decisions apply". That inversion would
make a greenfield project — the one with the least local context — the one that
consults the fewest constraints.

### `promote` — lift a project decision into its domain register

Inputs: `<DEC-NNN>`, `--domain <slug>`, optional `--why "<one line>"`.

This is the operation that makes a decision *architectural* rather than local.
It writes **both** link directions in one step, which is why it exists as an
operation rather than two hand edits.

1. Read the project entry `DEC-NNN`. Abort if absent or already carrying a
   `Global:` link (report the existing link — re-promotion is a supersede, not a
   second promotion).
2. Open `<vault_dir>/Portfolio/decisions/<domain>.md`, creating it from the
   domain header template if it does not exist.
3. Compute the next `GDEC-<DOM>-NNN` for that file (`max + 1`, never reused).
   `<DOM>` is the file's established uppercase tag; for a new file, derive a
   short tag from the slug and record it in the header.
4. Append the domain block with `Decided` / `Status` / `Reason` carried from the
   project entry — **generalized**: the domain-level reason must state the
   constraint in terms that hold for every project on that platform, not just
   the originating one. If it cannot be generalized, the decision is
   project-local and should not be promoted.
5. Add the originating project to the domain entry's `Applies to:` list as
   `<area>/[[<name>]] (<why>; DEC-NNN)`, using `--why` or the project entry's
   reason condensed to one line.
6. Write `- **Global:** [[decisions/<domain>#GDEC-<DOM>-NNN]]` into the project
   entry.
7. Report both IDs and both file paths.

To attach a *further* project to an existing domain entry, run `promote` from
that project with `--global <GDEC-ID>`: steps 3–4 are skipped and only the two
link directions are written.

### `supersede` — replace a decision that no longer holds

Inputs: `<DEC-NNN>` (or `<GDEC-ID>` with `--global`), plus the fields of the
replacement entry.

1. `add` the replacement entry, which gets a fresh ID.
2. Edit the old entry's `Status:` to `superseded by DEC-NNN`.
3. **Leave the old entry in place, unedited otherwise.** Its reason is the
   record of what was believed and why — deleting it destroys exactly the
   history the register exists to hold.
4. If the superseded entry carried a `Global:` link, report it: the domain entry
   may need its own supersede, which is a separate judgment and is never done
   automatically.

---

## Recording a sec-audit recommendation

Security review is the most common producer of architectural decisions, and the
one with a hard constraint: **sec-audit and sec-review report files are
local-only and gitignored across this portfolio — they are never committed and
never copied into the vault.**

So an entry sourced from one:

- sets `Source:` to the report **filename and date only**, suffixed
  `(local-only)` — e.g. `sec-audit report sec-audit-20260720-1830.md (local-only)`;
- restates the finding's substance **in the entry's own words** under `Reason`:
  what the exposure was, what constraint it imposes, what was accepted;
- **never** pastes, quotes at length, or summarizes the report body into the
  vault, and never reproduces exploit detail.

The test is whether the entry is useful to a reader who cannot open the report.
If it is not, the `Reason` is too thin — not a reason to embed the report.

Set `Domains:` from the finding's scope, not the project's stack: a finding
about a Tor control-port assumption is `tor`, even in an Android app, so every
Tor-adjacent project inherits it on promotion.

---

## Integration

- **architecting-projects** — its approved `## Decision` section lands a `DEC`
  entry at the end of Phase 5, sourced to the architecture doc and its
  `ARCH-NN` sections. The architecture doc stays the place a decision is *made*;
  the register is where it stays findable afterwards.
- **planning-projects / brainstorming** — call `read` during research. A new plan
  that contradicts an accepted decision must either cite the supersede or be
  re-scoped; silently violating a recorded decision is the failure this closes.
- **portfolio rebuild** — reads both registers, renders
  `Portfolio/global-decisions.md`, adds the sidecar `**Decisions:**` pointer, and
  reports link asymmetries. It never writes into either register.
- **sec-audit** — its recommendations are recorded here under the sourcing rule
  above; the reports themselves stay out of git and out of the vault.
- **Ad-hoc** — invoke directly ("record this decision", "why did we pick X",
  "what binds all the Rust projects").

---

## Safety rails

- Both registers are hand-authored declaration files. Append and edit discrete
  blocks; never rewrite a file whole, and preserve unrelated entries
  byte-for-byte.
- **Never delete an entry.** Decisions are superseded, not removed — unlike
  backlog items, which are removed on implementation. The register's value is
  cumulative.
- Never auto-fix a link asymmetry the roll-up reports. Fixing it means asserting
  something about a project you have not read; the user resolves it.
- Never write a report body, credential, or exploit detail into the vault.

## Remember

- The `Reason` is the artifact; the decision is just its title.
- IDs are immutable and never reused; supersede, don't delete.
- `promote` writes both link directions — that symmetry is what makes the global
  and per-project halves one register instead of two.
