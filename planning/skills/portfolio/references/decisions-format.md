# Decisions Format: per-project `decisions.md` + per-domain `Portfolio/decisions/<domain>.md`

The portfolio records **why the architecture is the way it is** in two linked
registers:

- **Per-project:** `<vault>/Portfolio/<area>/<project>/decisions.md` — decisions
  that bind *this* project.
- **Per-domain:** `<vault>/Portfolio/decisions/<domain>.md` — decisions that bind
  every project built on a given architecture or platform (`android`, `ios`,
  `rust`, `ubuntu`, `macos`, `tor`, …).

The two are cross-linked in both directions, so a decision is reachable from the
project that feels it *and* from the domain that governs it. This mirrors the
Depends-on/Blocks discipline used inside a plan and the symmetry rule used by
`integration.md` (`integration-format.md`): a relationship declared on only one
side is not navigable, so both sides declare it and the tooling reports — never
silently repairs — any gap.

Both files are pure declaration. `portfolio rebuild` reads them and renders
`Portfolio/global-decisions.md`; it never rewrites either register. The
`decisions` skill is the authoring surface.

## Why a register and not just the architecture doc

An architecture doc (`plans/YYYY-MM-DD-<topic>-architecture.md`) is ADR-style but
**event-shaped**: it captures one architecture exercise, keyed `ARCH-NN`, and is
never revisited once its plan is executed. Decisions accrete *between* those
events — a security review lands a constraint, a platform deprecation forces a
library swap, a packaging limit rules out an approach. Those have no home in a
dated plan file, and no way to be seen across projects that share a platform.
The register is that home; the architecture doc remains the place where a
decision is first *made*, and cites into the register when it is.

## Per-project format

`decisions.md` is a flat list of `## DEC-NNN` blocks, newest first, under a short
preamble. IDs are zero-padded 3-digit, monotonic per project, and
**never reused** — the same discipline as `BL-NNN` in the backlog register; the
next ID is `max + 1` even when earlier entries have been superseded.

A register may instead key its entries `DEC-<TAG>-NNN`, where `<TAG>` is a
2–4 letter uppercase project tag (`DEC-MT-003` for multitor). Both forms
parse; a register picks one and holds to it. The tag buys nothing inside the
file — it exists because these IDs are cited from plans, backlogs and
architecture docs elsewhere in the vault, where a bare `DEC-003` does not say
whose decision it is. Untagged remains the default for a new register: the
tag is only worth its cost once a project's decisions are routinely cited
from outside the project.

```markdown
# Decisions

Architectural decisions binding this project, newest first. Each entry records
what was decided and why. Superseded entries stay — the history is the point.

---

## DEC-007 — Per-app Tor circuits via Orbot, not iptables owner-match

- **Decided:** 2026-07-20
- **Status:** accepted
- **Domains:** android, tor
- **Source:** sec-audit report `sec-audit-20260720-1830.md` (local-only)
- **Reason:** Owner-match rules need root and break under GrapheneOS's per-app
  network policy, which reassigns UIDs on profile switch. Orbot's per-app mode
  gets circuit isolation from the VPN service with no root and survives profile
  changes. Cost: Orbot becomes a hard runtime dependency.
- **Global:** [[decisions/android#GDEC-AND-003]]
```

### Field semantics

| Field | Required | Meaning |
|-------|----------|---------|
| `Decided` | yes | `YYYY-MM-DD`, the date the decision was taken (not the date it was written down). |
| `Status` | yes | `accepted`, or `superseded by DEC-NNN`. A superseded entry is never deleted or renumbered. |
| `Domains` | yes | Comma-separated domain slugs this decision touches. Drives the domain roll-up. Use `none` for a decision genuinely specific to this project. |
| `Source` | yes | What produced the decision — a plan file, an architecture doc plus its `ARCH-NN`, a code review, a sec-audit report, or `direct` when taken in conversation. |
| `Reason` | yes | **The point of the register.** The constraint, the evidence, the trade-off accepted, and what was rejected. A `Reason` that only restates the decision is a defect. |
| `Global` | no | Wikilink to the domain entry this rolls up into, `[[decisions/<domain>#GDEC-<DOM>-NNN]]`. Present when the decision has been promoted. `none` (optionally with a trailing reason) is also allowed, to say explicitly that the decision is project-local and promotion was considered — it parses as no link. |

### Recording a sec-audit recommendation

sec-audit and sec-review report files are **local-only and never committed**
(they are gitignored across this portfolio). A decision that comes from one
therefore:

- cites the report **by filename and date only**, suffixed `(local-only)`;
- restates the finding's substance **in the entry's own words** under `Reason`;
- **never** embeds, quotes at length, or copies the report body into the vault.

The register must stay useful to a reader who cannot open the report — that is
what `Reason` is for — without becoming a second copy of it.

## Projects with no per-project register

The two halves are independently resolvable, and that asymmetry is load-bearing.
`decisions.md` needs a `portfolio_home`, which needs a registry entry;
`Portfolio/decisions/<domain>.md` is keyed by **domain**, so it resolves from
`vault_dir` alone.

A project therefore has a well-defined answer at every stage of its life:

| Project state | Per-project half | Per-domain half |
|---|---|---|
| Unregistered (brand new) | absent — no `portfolio_home` | **fully readable and binding** |
| Registered, no decisions yet | absent — no `decisions.md` | fully readable and binding |
| Registered with decisions | readable | readable |

**An absent per-project half is never "no decisions apply."** It means this
project has recorded none of its own; whatever its domains bind, still binds. A
consumer that skips the scan because `portfolio_home` didn't resolve inverts the
register's purpose — the newest codebase, the one still cheap to change,
consults the fewest accumulated constraints.

Registration happens on the normal path (`../../planning-projects/SKILL.md`,
Output location step 3, appends the registry entry when it writes a project's
first plan), so this
state resolves itself without a separate step and **without any new registry
field** — see DEC-002 on why `projects-registry.yaml`'s field set is not a cheap
extension point.

## Per-domain format

`Portfolio/decisions/<domain>.md` holds `## GDEC-<DOM>-NNN` blocks, where `<DOM>`
is a short uppercase tag for the domain (`AND` for android, `RS` for rust, `UBU`
for ubuntu, `IOS`, `MAC`, `TOR`, …). Numbering is monotonic per domain file.
Domain files are created on demand; the slug list is open.

```markdown
# Android decisions

Cross-project decisions binding every Android project in the portfolio.

---

## GDEC-AND-003 — Circuit isolation comes from Orbot per-app mode

- **Decided:** 2026-07-20
- **Status:** accepted
- **Reason:** Owner-match iptables rules need root and break under GrapheneOS
  UID reassignment. Orbot's per-app VPN mode is the only rootless mechanism that
  survives profile switches. Accepted cost: a hard Orbot dependency.
- **Applies to:**
  - android/[[multitor-android]] (ships the isolation path; DEC-007)
  - android/[[nice-dns-android]] (resolver must bind inside the same tunnel; DEC-004)
```

`Applies to` entries are **area-qualified wikilinks** (`<area>/[[<name>]]`), the
same cell form the global roll-ups use, each with a mandatory parenthetical
giving the per-project why and the project-side `DEC-NNN` it pairs with. A
`why` is required per edge for the same reason `integration.md` requires one:
a bare link says a relationship exists but not what it costs the reader to
ignore it.

## Symmetry rule

If a project entry declares `Global: [[decisions/<domain>#GDEC-<DOM>-NNN]]`, that
domain entry MUST list the project under `Applies to`, and vice versa.

`portfolio rebuild` cross-checks every link in both directions after reading all
registers. Any one-sided link is reported under `## Asymmetries (review)` in
`global-decisions.md` and is **NEVER auto-fixed** — the user resolves it by
editing one of the two files and re-running. A `Global:` or `Applies to:` link
whose target does not resolve to an existing entry is reported under
`## Unresolved targets`.

This is deliberate. Auto-fixing would let the tool invent an `Applies to` edge —
and therefore a claim about a project it has not read — from one side's
assertion alone.

## Roll-up

`portfolio rebuild` renders `<vault>/Portfolio/global-decisions.md`:

- `## By domain` — one section per domain file, listing its GDEC entries with
  status and the projects each applies to.
- `## By project` — a table of per-project decision counts (total / accepted /
  superseded), each project as an area-qualified wikilink. A project with any
  malformed entry carries a ⚠️ beside its count.
- `## Malformed entries (review)` — every flagged entry named by project, ID (or
  raw heading), and defect: malformed heading, missing field, duplicate field.
  It exists because "something is wrong with one of twelve decisions" is not an
  actionable flag.
- `## Asymmetries (review)` — one-sided links, both directions.
- `## Unresolved targets` — links pointing at entries that do not exist,
  including a GDEC id defined in two domain files (an ambiguous target).

Rendering goes through `write_if_changed()`, so a rebuild with no upstream
change is a no-op — the same idempotency guarantee the other globals carry.

## Sidecar

When a project has a `decisions.md`, `portfolio rebuild` adds one pointer line
to its repo's `PORTFOLIO-STATUS` block (`sidecar-format.md`):

```
- **Decisions:** see [decisions.md](<home>/decisions.md)
```

Pointer-only, like every other line in that block: no counts are embedded,
because a repo-committed sidecar lags the vault and an inlined count goes stale
the moment a decision lands.

## Parser rules

The deterministic reader in `portfolio-rebuild.py` follows these, and
`tests/test-portfolio-decisions.py` locks them:

1. **Block boundaries are found with a generic `^## ` match**, and the ID shape
   is validated *afterwards*. Boundaries are deliberately NOT detected with the
   strict ID regex: a heading that misses the em-dash (a plain hyphen is the
   common slip) would then start no block at all, and its body would either be
   dropped outright — if it were the first heading — or silently swallowed into
   the previous block's last field. Either way a binding decision disappears,
   which is the one outcome this register exists to prevent.
2. A heading that fails `^DEC-(?:[A-Z]{2,4}-)?\d+ — ` (project) or
   `^GDEC-[A-Z]+-\d+ — ` (domain) yields a **flagged entry** carrying the raw heading, not a skipped
   one. It is listed by project and verbatim under `## Malformed entries
   (review)` in the roll-up. The heading must be repaired before the entry's
   other fields mean anything, so such an entry is excluded from counts, from
   domain grouping, and from `last_decided`; if it also carries a `Global:`
   link, that link is reported as unresolvable rather than followed.
3. Fields are `- **Name:** value` lines; a field may wrap onto continuation
   lines, which are joined with a single space. A horizontal rule (`---`,
   `***`, `___`) never joins into a field value.
4. A field repeated inside one block keeps the last value and is **flagged** as
   a duplicate — the register's job is catching exactly this kind of
   hand-editing slip, so it must not pass silently.
5. A block missing a required field is **reported, not dropped** — it appears in
   the roll-up flagged, so a malformed entry is visible rather than silently
   invisible. Same degrade-never-drop contract the compass collectors use.
6. A file that is unreadable or has no recognizable blocks contributes zero
   entries and one error line; it never aborts the rebuild.
7. `Domains` values are lowercased and whitespace-stripped before grouping;
   `none` expands to no domains and is not a malformation.
8. IDs are matched as `DEC-(?:[A-Z]{2,4}-)?\d+` / `GDEC-[A-Z]+-\d+`.
   Zero-padding to three digits is the authoring convention (above), not a
   parser requirement — a `DEC-7` parses, it is simply not how entries
   should be written. The project tag is likewise optional
   (see § Per-project format): both `DEC-003` and `DEC-MT-003` parse, and a
   register uses one form or the other throughout, never both.
9. **An ID claimed by two blocks in the same file is reported** — every
   reference to it is ambiguous, and nothing here can know which block the
   author meant. Both blocks are still parsed and listed; the duplicate is
   flagged, not dropped. (The cross-*file* GDEC case is caught separately by the
   symmetry check.)
10. **An `Applies to` wikilink with no `<area>/` prefix is reported** under
    `## Unresolved targets`. A bare `[[name]]` matches neither direction of the
    symmetry check, so without this it would simply not exist as an edge —
    invisible rather than wrong.
11. **A `Global:` link's domain segment is checked against the register that
    actually owns the GDEC id.** Resolving on the id alone would report a link
    pointing at a file that does not contain the entry as correct.
12. A `## `-prefixed line inside a field's continuation (e.g. a Reason quoting a
    heading) is read as a block boundary — that is inherent to rule 1. It
    degrades **visibly**: the quoted line becomes a flagged malformed-heading
    entry and the following decision parses intact, so the truncation is
    reported rather than silent. Avoid `## ` at the start of a continuation
    line; indent it or use inline code.
