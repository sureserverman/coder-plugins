#!/usr/bin/env python3
"""portfolio-unify — implements `backlog unify --target vault` across the registry.

Reads each project's plans from <vault>/Portfolio/<area>/<name>/plans/, applies
the plan-parser rules (references/plan-parser.md), dedups against the existing
<home>/backlog.md by exact Source string, and (with --write) appends BL-NNN
entries tagged `auto-unified`. Dry-run by default.

Candidate signals (accept-all policy):
  - Status-authoritative tasks     (plans carrying `- **Status:**` fields, from
                                     planning-projects v0.5.1+: Task N.N with
                                     `Status: [ ]` -> one candidate per task
                                     (signal status-unexecuted); `[~]` -> one
                                     candidate, signal status-partial (started,
                                     unfinished); `[x]` -> done, emits nothing;
                                     stray body bullets ignored)
  - unchecked Task N.N tasks       (legacy plans without Status fields:
                                     ### Task N.N: with an unchecked `- [ ]`
                                     body bullet, or no `- [x]` in its body)
  - Deferred-section bullets       (## Deferred / ### Deferred blocks — active
                                     in BOTH modes; an explicit parking
                                     register, not a task-state heuristic)
Excluded: Preflight bullets; Stage Gate bullets (acceptance criteria that restate
a stage's definition-of-done — `### Stage N Gate` headers and `**Stage Gate:**`
bold markers — NOT deferred work); *-done.md historical summaries; stale-plan
items unless --include-stale (off by default — staleness from the filename
YYYY-MM-DD stamp, since the vault is not a git repo and mtime is rewritten by
migrations).

A `**Abandoned:** YYYY-MM-DD — reason` marker is a terminal state parsed here
(plan_terminal_state) for consumers; it suppresses a plan from compass `next`
ranking only — unify still emits its open tasks for human triage.

See backlog/SKILL.md `### unify` + references/plan-parser.md for the spec.
"""
import argparse, re, subprocess, sys, yaml, datetime
from pathlib import Path

def _home():
    """A home directory, never an exception.

    `Path.home()` raises RuntimeError when HOME is unset AND the uid has no
    /etc/passwd entry (arbitrary-uid containers), and this runs at import.

    This file is a CLI script where a loud failure would be fine — but it is
    also imported, at module scope, by plan-progress.py, the statusline
    renderer whose one hard contract is to print a bar or print nothing and
    always exit 0. An import-time raise here lands as a traceback in the user's
    status line, before the renderer's own guard exists to catch it. So the
    guard belongs on the importable module, not only on the importer.

    The sibling CLI scripts (portfolio-migrate / -rebuild / -integrate,
    security-scan) still call Path.home() directly and deliberately: nothing
    imports them into a renderer, and for a tool the user invoked by hand a
    loud failure at startup is the right behavior.
    """
    try:
        return Path.home()
    except Exception:
        import os
        return Path(os.environ.get("HOME") or "/nonexistent")


REGISTRY = _home() / ".claude" / "projects-registry.yaml"
CONFIG = _home() / ".claude" / "portfolio-config.yaml"
TODAY = datetime.date.today().isoformat()


def git_stage_evidence(repo_path):
    """Mine the repo git log for (date, stage_number) references. Used to mark a
    plan's stage as executed when a commit dated >= the plan's date references
    that stage number (best-effort attribution; commit msgs don't name the plan)."""
    repo = Path(repo_path)
    if subprocess.run(["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
                      capture_output=True, text=True).returncode != 0:
        return []
    out = subprocess.run(["git", "-C", str(repo), "log", "--format=%ad|%s", "--date=short"],
                         capture_output=True, text=True).stdout
    pairs = []
    for ln in out.splitlines():
        if "|" not in ln:
            continue
        date, msg = ln.split("|", 1)
        for m in re.finditer(r"[Ss]tage\s+(\d+)", msg):
            pairs.append((date, int(m.group(1))))
    return pairs


def plan_date(fname):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", fname)
    return m.group(1) if m else "0000-00-00"


STALE_DAYS = 90


def stale_age_days(fname, today=None):
    """Days since the plan's filename date stamp, or None when the name carries
    no usable stamp — staleness unknown, never assumed (plan-parser.md § 3).

    Deliberately NOT plan_date(): that returns "0000-00-00" for an unstamped
    name, which is the right sentinel for the git-stage comparison (every commit
    counts as later) but would read as infinitely old here and mark every legacy
    file stale — the exact opposite of the documented fallback.
    """
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", fname)
    if not m:
        return None
    try:
        d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:          # e.g. 2026-13-45 in a filename
        return None
    return ((today or datetime.date.today()) - d).days

TASK_RE = re.compile(r"^###\s+Task\s+(\d+\.\d+):\s*(.+)$")
STAGE_RE = re.compile(r"^##\s+Stage\s+\d+:")
GATE_RE = re.compile(r"^###\s+Stage\s+\d+\s+Gate")
DEFERRED_RE = re.compile(r"^###?\s+Deferred\s*$")
UNCHECKED = re.compile(r"^\s*-\s*\[ \]\s+(.+)$")
CHECKED = re.compile(r"^\s*-\s*\[x\]\s+", re.I)
H2 = re.compile(r"^##\s+")
SECTION = re.compile(r"^##+\s+")
HR = re.compile(r"^---\s*$")
BULLET = re.compile(r"^\s*-\s+(.+)$")
# Stage-gate acceptance criteria are NOT deferred work. They appear either as a
# header naming a "Gate" (### Stage N Gate, #### … Gate) or as a bold marker
# (**Stage Gate:**, **Acceptance Criteria:**) above a list of `- [ ]` checks.
GATE_WORD = re.compile(r"\bGate\b", re.I)
GATE_BOLD = re.compile(
    r"^\s*\*\*\s*(?:stage\s+)?"
    r"(?:gate|acceptance(?:\s+criteria)?|verification|exit\s+criteria|success\s+criteria)\b.*\*\*",
    re.I)


def vault_dir():
    cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    vd = cfg.get("vault_dir")
    if not vd:
        sys.exit("portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml")
    return Path(vd)


PREFLIGHT_RE = re.compile(r"^##+\s+Preflight", re.I)
# `## Decisions in force` records the architectural constraints binding a plan
# (planning-projects § Decisions scan). Its bullets are declarations, not work.
# The format mandates non-checkbox bullets, but a convention the parser does not
# enforce is one an author eventually breaks: a stray `- [ ]` there became a
# false backlog candidate on the legacy heuristic path, silently, on every plan
# that recorded a decision. Excluded here so the invariant is real.
DECISIONS_RE = re.compile(r"^##+\s+Decisions in force", re.I)
STAGEHDR_RE = re.compile(r"^##\s+Stage\s+(\d+)", re.I)
GATEHDR_RE = re.compile(r"^###\s+Stage\s+(\d+)\s+Gate", re.I)
# ---------------------------------------------------------------------------
# PLAN-STATUS CONTRACT — single definition; compass-scan.py and plan-progress.py
# import it via importlib rather than restating it. Decided 2026-07-24 for
# BL-001 (compass-scan blind spots). Rationale is recorded here, at the owner,
# because a change to this one regex silently alters done/total math in every
# consumer at once.
#
# (a) `[~]` IS a first-class parsed state — "partial / in flight".
#     Counted in TOTAL, never in DONE. A partially-done task is not done;
#     counting it done would let a plan report 100% with work outstanding,
#     while the previous behaviour (excluded from the character class, so
#     excluded from both numerator and denominator) made the task vanish from
#     progress entirely — the plan looked smaller instead of less finished.
#     portfolio-unify emits a candidate for it, with signal `status-partial`
#     distinct from `status-unexecuted`: residual work is still open work, but
#     "started and unfinished" is not the same backlog item as "never begun".
#
#     Consumers MUST classify through `status_state()` below and MUST NOT test
#     `group(1) != " "` — under the widened class that idiom silently reports a
#     partial task as DONE, which is strictly worse than the bug being fixed.
#
# (b) Abandonment is a STRUCTURED marker, not a prose heuristic:
#         **Abandoned:** YYYY-MM-DD — <reason>
#     mirroring the `**Completed:**` line plans already carry, and parsed by
#     ABANDONED_RE below. It is the only thing that suppresses a plan from
#     compass `next`.
#
#     Why not a banner heuristic over prose like "OBSOLETE — DO NOT IMPLEMENT":
#     that text is unbounded natural language, so any regex over it carries
#     both false positives (a plan *about* deprecating something; a task titled
#     "remove the OBSOLETE banner"; a Research Summary quoting one) and false
#     negatives ("superseded by", "shelved", "do not build"). A false positive
#     hides live work from `next` — the same class of failure BL-001 exists to
#     fix, merely inverted, and a silent one. A deterministic parser must not
#     take a fuzzy signal as authoritative.
#
#     The marker's cost — authors must adopt it — is bounded, and its
#     non-adoption failure mode is the STATUS QUO (the plan keeps looking
#     active), not a regression. To blunt that cost without reintroducing
#     false-positive risk, ABANDON_HINT_RE below detects banner prose and
#     consumers surface it as a NON-SUPPRESSING advisory ("looks abandoned; no
#     **Abandoned:** marker"), so the nudge is visible but never acted on.
# ---------------------------------------------------------------------------
STATUS_RE = re.compile(r"^\s*-\s*\*\*Status:\*\*\s*\[([ xX~])\]")

# Every bracketed Status marker, INCLUDING the ones the contract does not
# recognise. STATUS_RE's class is `[ xX~]`; anything else matches nothing at
# all, so its task counts toward neither `done` nor `total` and simply vanishes
# — which makes its plan read MORE FINISHED than it is. That is the optimistic
# direction, and the one that gets acted on.
#
# Three exist vault-wide today (BL-044, fully enumerated 2026-08-08): `[!]`
# once, `[~ BLOCKED]` and `[~ N/A]` once each in one file. The `[!]` one is the
# case that motivated this: its plan reads 10/10 instead of 10/11, so it
# presents as finished work while the invisible task is blocked on an
# irreversible confirmation nobody has given.
#
# Lives HERE rather than in the audit tool for the same single-owner reason
# COMPLETED_RE does: consumers ask the contract what it cannot read, instead of
# each maintaining its own list of known-bad markers that would drift apart.
# Deliberately NOT a fixed alternation of those three — a consumer takes the
# DIFFERENCE against STATUS_RE (see out_of_contract_markers in
# plan-status-audit.py), so a fourth marker nobody has invented yet is caught
# the day it appears rather than the day someone remembers to add it here.
ANY_STATUS_RE = re.compile(r"^\s*-\s*\*\*Status:\*\*\s*\[([^\]\n]*)\]")

# Terminal-state markers, both anchored at column 0 like the `**Completed:**`
# line executing-plans appends at close-out. ABANDONED_RE is authoritative;
# ABANDON_HINT_RE is advisory only (see the contract note above) and is
# deliberately NOT consulted by any suppression decision.
ABANDONED_RE = re.compile(r"^\*\*Abandoned:\*\*\s*(.+)$", re.M)
# The close-out line executing-plans appends ("**Completed:** YYYY-MM-DD —
# commits: ..."). It lived only in the comments above until consumers needed to
# ASK the question rather than describe it: plan-progress.py's eligibility
# filter and the plan-status audit both need "is this plan closed out?", and the
# contract's single-owner rule means they import it from here rather than each
# restating a regex that would then drift.
# The `## ` alternative is BL-053's heading dialect, and leaving it out was a
# measured false-positive generator rather than a theoretical gap: the two
# plans that write their close-out as `## Completed: <date> — commits: …`
# (both in appimage-control) were being offered by plan-status-audit as
# "all tasks done, NO CLOSE-OUT LINE" — inviting a user to stamp them
# 2026-08-08 over work that closed 2026-06-30, and with weaker provenance than
# the line they already carried. 2 of 14 candidates, i.e. a 14% false-positive
# rate on the tool's headline output, found by the Stage 4 gate evaluator.
#
# Measured across all 518 vault plans before widening: 215 use `**Completed:**`,
# 4 use `## Completed:`, and NOTHING else parses as a close-out marker — so the
# alternation below is the whole observed dialect, not a guess. Kept anchored
# at the line start in both forms; a `Completed:` mid-sentence is still prose.
COMPLETED_RE = re.compile(r"^(?:##\s*)?\*{0,2}Completed:\*{0,2}\s*(.+)$", re.M)

# EVERY Status line, whatever follows the colon -- including the ones with no
# bracket at all. ANY_STATUS_RE above catches a bracketed marker outside the
# contract's class; this catches the wider set, and consumers take the
# DIFFERENCE against STATUS_RE.
#
# Why both: a task written `- **Status:** done` matches neither STATUS_RE nor
# ANY_STATUS_RE, so it counts toward neither `done` nor `total` and vanishes
# entirely. A plan with one `[x]` task and one such line reads 1/1 -- "every
# task done" -- while a whole task is invisible. Reproduced, and it is the
# optimistic direction again: that plan becomes a completion candidate.
STATUS_LINE_RE = re.compile(r"^\s*-\s*\*\*Status:\*\*\s*(.*)$")
ABANDON_HINT_RE = re.compile(
    r"^[>#*_\s]{0,8}\b(OBSOLETE|SUPERSEDED|ABANDONED|DO NOT IMPLEMENT)\b", re.M)

# A master plan's sub-plan register entry. The counterpart of TASK_RE: a master
# has no `### Task N.N` headings at all, so every Status-counting consumer reads
# a master as 0/0 -- "not started" -- no matter how many of its sub-plans are
# done. That is why zero of the vault's masters have ever classified as in
# flight. Consumers that want a master's real progress count these instead, and
# they live here for the same single-owner reason COMPLETED_RE does.
#
# `### Sub-plan 2: Text import entry points` -> ("2", "Text import entry points")
#
# Authors zero-pad the number and separate with an em-dash as readily as they
# use a bare digit and a colon (`### Sub-plan 01 — skill-curator maintenance
# lane`), so both are matched. This is the same format-drift the close-out
# marker shows (BL-053): a register form the regex cannot see makes its master
# read 0/0, i.e. never started, which is the optimistic direction again.
#
# NOT matched, deliberately: the bare-ordinal form `### 01. Foundation and
# domain contracts` (writer-pad's android-app master). Recognising it needs the
# match scoped to the `## Sub-plans` section, because `### 01.` is too generic
# to claim anywhere in a document — a Research Summary heading would qualify.
# Left as a known false negative rather than a guessed-at true positive.
SUBPLAN_RE = re.compile(r"^###\s+Sub-plan\s+0*(\d+)\s*[:—–-]\s*(.+)$")
# Both recognised master forms, per planning-projects/references/master-plan-format.md:
# the filename suffix and the first heading. Either alone is sufficient -- a
# master saved under a different filename is still a master.
MASTER_HEADING_RE = re.compile(r"^#\s+Master Plan:", re.M)

# The two links that associate a master with its sub-plans -- one per direction.
# Same format contract SUBPLAN_RE reads, so they live here for the same
# single-owner reason, and consumers need BOTH: either side goes missing in real
# files, and a sub-plan authored without its backlink is still a sub-plan when
# the master's register names it.
#
#   Master: ./2026-08-06-topic-master-plan.md            (sub-plan, below Date:)
#   - **Plan:** ./2026-08-06-topic-sub-01-x-plan.md      (master register entry)
#
# Both capture to end-of-line rather than one \S+ token, because the vault
# carries a second written form on BOTH sides -- `[name.md](./name.md)`, used by
# two of writer-pad's masters and their sub-plans. A token-shaped capture
# swallows the whole `[...](...)` string, resolves to nothing, and silently
# reads those masters as childless. Same format-drift as the close-out marker
# (BL-053) and the register heading above: the dialect the regex cannot see
# always fails in the direction that looks tidier.
#
# NOT scoped to a section, deliberately and with the same caveat SUBPLAN_RE
# carries: `Master:` is matched anywhere in the document rather than only on the
# line below `Date:`, and `- **Plan:**` anywhere rather than only inside a
# register entry. Consistent with STATUS_RE and SUBPLAN_RE, which are unscoped
# too, so this is the file's existing posture and not a new one -- but it means
# a stray `Master:`-prefixed line in a Research Summary would group a plan under
# the wrong master. Recorded here so whoever debugs a spurious grouping finds
# the reason rather than rediscovering it.
MASTER_BACKLINK_RE = re.compile(r"^Master:\s*(.+?)\s*$", re.M)
SUBPLAN_LINK_RE = re.compile(r"^\s*-\s*\*\*Plan:\*\*\s*(.+?)\s*$", re.M)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def link_target(raw):
    """The path a `Master:` / `- **Plan:**` line points at, or None.

    Normalises the two written forms to one relative path. Returns None rather
    than a guess for anything else -- an unresolvable link should leave a
    sub-plan ungrouped, never grouped under the wrong master.
    """
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    m = MD_LINK_RE.search(raw)
    if m:
        raw = m.group(1).strip()
    else:
        parts = raw.split()
        raw = parts[0] if parts else ""
    return raw.strip("`<>'\" ") or None


def is_master_plan(text, path=None):
    """Whether this document is a master plan (register of sub-plans)."""
    if path is not None and str(path).endswith("-master-plan.md"):
        return True
    return bool(MASTER_HEADING_RE.search(text))


def status_state(ch):
    """Classify a STATUS_RE capture into the contract's three states.

    The ONLY sanctioned way to read a Status character. Consumers must not test
    the captured char themselves — `!= " "` silently reads `[~]` as done.
    """
    if ch == "~":
        return "partial"
    if ch in ("x", "X"):
        return "done"
    return "open"


# --- GATE-CHECKBOX CONTRACT (BL-077) ---------------------------------------
# A gate check is a different marker from a task `Status:` and needs its own
# state set, but it belongs HERE for exactly the reason STATUS_RE does: one
# definition, so a change cannot alter what "the gate passed" means in one
# consumer and not another. It was NOT here — plan-status-audit.py carried its
# own copy of this regex, which is a lockstep break with nothing to catch it.
#
# `[~]` means BLOCKED: the check could not be run in this environment. It is
# NOT "partially done" and NOT a softer `[x]`. honest-gates makes the three-way
# split load-bearing — GREEN (ran, passed), RED (ran, failed), BLOCKED (could
# not run) — and only BLOCKED needs a marker, because a RED gate is not written
# down as passed, it is repaired.
#
# The measured cost of not having it: a register `[x]` standing against a `[~]`
# gate took a ten-tool-call manual audit to disprove.
#
# SCOPE, stated because an earlier version of this comment overclaimed: this
# predicate reads ONE plan's own gate blocks. A master plan carries no
# `### Stage N Gate` section — 0 of 38 in the live vault do; a master's gate
# boxes live in its sub-plan files — so a master whose sub-plan is blocked
# still classifies on its own text. The master half of BL-077 is NOT closed by
# this, and propagation is a separate capability.
GATE_ITEM_RE = re.compile(r"^\s*-\s*\[([ xX~])\]")


def gate_item_state(ch):
    """Classify a GATE_ITEM_RE capture. The ONLY sanctioned way to read one.

    Deliberately different words from status_state(): a task is `partial`
    because work is under way, a gate check is `blocked` because a command
    could not run. Sharing the vocabulary would invite sharing the treatment,
    and a blocked gate is not a gate in progress.
    """
    if ch == "~":
        return "blocked"
    if ch in ("x", "X"):
        return "done"
    return "open"


def plan_has_blocked_gate(text):
    """True when any stage-gate checkbox in the plan is `[~]`.

    Scoped between a `### Stage N Gate` heading and the next `###`, so a
    Preflight or Research checklist elsewhere in the document is never mistaken
    for gate state — the same scoping plan-status-audit's gate_state() uses,
    now sharing one implementation with it rather than two copies of the idea.
    """
    in_gate = False
    for line in text.splitlines():
        if line.startswith("###"):
            in_gate = bool(GATEHDR_RE.match(line))
            continue
        if in_gate:
            m = GATE_ITEM_RE.match(line)
            if m and gate_item_state(m.group(1)) == "blocked":
                return True
    return False


def plan_terminal_state(text):
    """(abandoned, advisory, reason) for one plan's full text.

    `abandoned` is True only on the structured marker, and `reason` carries the
    marker's own text (None when not abandoned) — compass lists a suppressed
    plan WITH its reason, so discarding the captured group would leave the
    judgment layer unable to follow its own instruction. `advisory` is a short
    note when banner prose is present WITHOUT the marker — surfaced to the
    operator, never acted on, so a false-positive banner match can never hide
    live work.

    DELIBERATELY NOT CALLED by parse_plan/unify_project in this module — it is
    contract API for consumers, like STATUS_RE itself. Abandonment suppresses a
    plan from compass `next` (a *ranking* decision) and nothing else; unify
    keeps emitting an abandoned plan's open tasks as backlog candidates on
    purpose. Those candidates are proposed for human acceptance, never
    auto-written, so surfacing them costs a triage decision while suppressing
    them would silently delete work from the only view that still lists it —
    turning an author's one-line marker into a destructive action with a far
    wider blast radius than the ranking change it was introduced for.
    """
    am = ABANDONED_RE.search(text)
    if am:
        return True, None, am.group(1).strip()
    m = ABANDON_HINT_RE.search(text)
    if m:
        return False, (f"looks abandoned ({m.group(1).lower()} banner) but "
                       f"carries no **Abandoned:** marker — not suppressed"), None
    return False, None, None


def parse_plan_status(text, plan_rel):
    """Authoritative path (plan-parser.md § Authoritative signal) for plans that
    carry per-task `- **Status:**` fields: Task N.N with `Status: [ ]` emits ONE
    candidate (signal `status-unexecuted`, title = the task description); `[~]`
    likewise emits one but with signal `status-partial` (started, unfinished —
    still open work, distinguishable from never-begun); `[x]` means done and
    emits nothing. Raw unchecked bullets are ignored entirely — Status is the
    only task-state source, and git stage evidence is not consulted. Deferred
    blocks still surface (explicit parking register, independent of task
    state). Master-plan registers use
    `### Sub-plan N:` headers, so their Status fields have no Task context and
    emit nothing."""
    out = []
    cur_stage = None
    cur_task = None
    in_deferred = False
    defer_n = 0
    for line in text.splitlines():
        if SECTION.match(line):
            in_deferred = bool(DEFERRED_RE.match(line))
            cur_task = None
        sh = STAGEHDR_RE.match(line)
        if sh:
            cur_stage = int(sh.group(1))
        tm = TASK_RE.match(line)
        if tm:
            cur_task = (tm.group(1), tm.group(2).strip())
        if in_deferred:
            bm = BULLET.match(line)
            if bm:
                defer_n += 1
                title = re.sub(r"^\[[ x]\]\s*", "", bm.group(1).strip())
                out.append({"source": f"{plan_rel} — Deferred / bullet {defer_n}",
                            "title": title, "signal": "deferred-section"})
            continue
        sm = STATUS_RE.match(line)
        if sm and cur_task:
            st = status_state(sm.group(1))
            if st != "done":
                num, desc = cur_task
                loc = f"Stage {cur_stage} / Task {num}" if cur_stage else f"Task {num}"
                out.append({"source": f"{plan_rel} — {loc}",
                            "title": desc,
                            "signal": ("status-unexecuted" if st == "open"
                                       else "status-partial")})
            cur_task = None       # one Status field per task; consume it
    return out


def parse_plan(text, plan_rel, done_stages):
    """Return candidates from one plan. Plans carrying any `- **Status:**` field
    take the authoritative path (parse_plan_status); legacy plans fall back to
    the heuristic below: every unchecked `- [ ]` (excluding the Preflight and
    `Decisions in force` sections) whose enclosing Stage is NOT git-confirmed-done, plus all
    `## Deferred` bullets. `done_stages` is the set of stage numbers a commit
    (dated >= the plan's date) referenced as executed."""
    # Detection requires the checkbox, matching STATUS_RE: a checkbox-less
    # `- **Status:** Draft` line must NOT capture the file for the
    # authoritative path (which would silently drop its legacy candidates).
    # The class must stay in lockstep with STATUS_RE's — when `[~]` was absent
    # here, a plan whose tasks were ALL partial matched nothing, fell through
    # to the legacy heuristic, and emitted its raw `- [ ]` gate bullets as
    # candidates instead of its tasks.
    if re.search(r"(?m)^\s*-\s*\*\*Status:\*\*\s*\[[ xX~]\]", text):
        return parse_plan_status(text, plan_rel)
    out = []
    lines = text.splitlines()
    cur_stage = None
    in_preflight = False
    in_decisions = False
    in_deferred = False
    in_gate = False
    defer_n = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if SECTION.match(line):
            in_preflight = bool(PREFLIGHT_RE.match(line))
            in_decisions = bool(DECISIONS_RE.match(line))
            in_deferred = bool(DEFERRED_RE.match(line))
            # A header naming a "Gate" opens an acceptance-criteria block; any
            # other header (a Task, a new Stage, Deferred, …) closes it.
            in_gate = bool(GATE_WORD.search(line))
        elif GATE_BOLD.match(line):
            in_gate = True            # bold marker form, e.g. **Stage Gate:**
        elif HR.match(line):
            in_gate = False
        sh = STAGEHDR_RE.match(line) or GATEHDR_RE.match(line)
        if sh:
            cur_stage = int(sh.group(1))
        if in_deferred:
            bm = BULLET.match(line)
            if bm:
                defer_n += 1
                title = re.sub(r"^\[[ x]\]\s*", "", bm.group(1).strip())
                out.append({"source": f"{plan_rel} — Deferred / bullet {defer_n}",
                            "title": title, "signal": "deferred-section"})
            i += 1
            continue
        um = UNCHECKED.match(line)
        if um and not in_preflight and not in_decisions and not in_gate:
            # exclude if this stage was git-confirmed executed
            if cur_stage is None or cur_stage not in done_stages:
                loc = f"Stage {cur_stage}" if cur_stage else "checklist"
                # rstrip the 50-char slice so the Source has no trailing space;
                # existing_sources strips on read, so both sides must be stripped
                # for the dedup to match (idempotency).
                snippet = um.group(1).strip()[:50].rstrip()
                out.append({"source": f"{plan_rel} — {loc} / unchecked: {snippet}",
                            "title": um.group(1).strip(),
                            "signal": "unchecked-open"})
        i += 1
    return out


def existing_sources(backlog_text):
    return set(re.findall(r"^\s*-\s*\*\*Source:\*\*\s*(.+?)\s*$", backlog_text, re.M))


def max_bl(backlog_text):
    ids = [int(m) for m in re.findall(r"^##\s+BL-(\d+)\b", backlog_text, re.M)]
    return max(ids) if ids else 0


def render_entry(bid, c):
    # The originating plan's filename stamp rides along as a tag, so a unified
    # entry stays greppable back to the plan that produced it. The "0000-00-00"
    # sentinel (unstamped filename) is deliberately NOT emitted — a fake date in
    # a tag is worse than no tag.
    stamp = c.get("plan_date")
    tags = "auto-unified" + (f", {stamp}" if stamp and stamp != "0000-00-00" else "")
    return (f"## BL-{bid:03d} — {c['title'][:80]}\n\n"
            f"- **Opened:** {TODAY}\n"
            f"- **Source:** {c['source']}\n"
            f"- **Reason:** Auto-unified from plan ({c['signal']}).\n"
            f"- **Next step:** TBD — opened by unify on {TODAY}; review and refine.\n"
            f"- **Tags:** {tags}\n\n---\n")


HEADER = ("# Backlog\n\nDeferred items from plan execution, code review, or ad-hoc "
          "capture. Entries are removed when implemented; git history is the audit trail.\n\n---\n")


def unify_project(home, write, repo_path, include_stale=False):
    plans_dir = home / "plans"
    if not plans_dir.is_dir():
        return (0, 0, 0)
    gpairs = git_stage_evidence(repo_path)
    cands = []
    for pf in sorted(plans_dir.rglob("*.md")):
        if pf.name.endswith("-done.md") or pf.name == "backlog.md":
            continue
        rel = "plans/" + pf.relative_to(plans_dir).as_posix()
        pdate = plan_date(pf.name)
        done_stages = {sn for (cdate, sn) in gpairs if cdate >= pdate}
        text = pf.read_text(errors="ignore")
        normal = parse_plan(text, rel, done_stages)
        for c in normal:
            c["plan_date"] = pdate
        cands.extend(normal)
        if not include_stale:
            continue
        age = stale_age_days(pf.name)
        if age is None or age <= STALE_DAYS:
            continue
        # Signal 3 lowers the bar for an old plan: re-parse with the git-stage
        # suppression lifted, and keep only what signals 1-2 did NOT already
        # emit. It adds items from plans the normal heuristics skip; it never
        # relabels ones they found (plan-parser.md § 3).
        # Keyed on (source, title), not source alone: the legacy `unchecked-open`
        # locator encodes the Stage but not the Task N.N, so two tasks in one
        # stage whose bullets share a 50-char prefix produce the same source.
        # Deduping on that key would silently DROP a real stale candidate, and a
        # false negative is the worse failure for a register meant to surface
        # forgotten work.
        seen = {(c["source"], c["title"]) for c in normal}
        for c in parse_plan(text, rel, set()):
            if (c["source"], c["title"]) not in seen:
                cands.append(dict(c, signal="stale-plan-unchecked", plan_date=pdate))
    backlog = home / "backlog.md"
    btext = backlog.read_text() if backlog.exists() else HEADER
    have = existing_sources(btext)
    new = [c for c in cands if c["source"] not in have]
    dups = len(cands) - len(new)
    if write and new:
        nid = max_bl(btext)
        # ensure file ends clean
        if not btext.endswith("\n"):
            btext += "\n"
        add = ""
        for c in new:
            nid += 1
            add += render_entry(nid, c)
        backlog.write_text(btext + add)
    return (len(new), dups, len(cands))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--project")
    ap.add_argument("--include-stale", action="store_true",
                    help="also surface unresolved items in plans older than "
                         f"{STALE_DAYS} days by filename stamp (off by default)")
    args = ap.parse_args()
    vd = vault_dir()
    reg = yaml.safe_load(REGISTRY.read_text())
    projects = [p for p in reg["projects"] if p.get("enabled", True)]
    if args.project:
        projects = [p for p in projects if p["path"] == str(Path(args.project))]
    tot_new = tot_dup = tot_cand = 0
    for proj in projects:
        home = vd / "Portfolio" / proj["area"] / proj["name"]
        n, d, c = unify_project(home, args.write, proj["path"], args.include_stale)
        tot_new += n; tot_dup += d; tot_cand += c
        if c:
            print(f"  {proj['area']}/{proj['name']}: {n} new, {d} dup, {c} candidates")
    print(f"\n{'WRITE' if args.write else 'DRY-RUN'}: {tot_new} new entries, "
          f"{tot_dup} duplicates skipped, {tot_cand} candidates across "
          f"{len(projects)} projects")


if __name__ == "__main__":
    main()
