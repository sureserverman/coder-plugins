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
bold markers — NOT deferred work); *-done.md historical summaries.

A `**Abandoned:** YYYY-MM-DD — reason` marker is a terminal state parsed here
(plan_terminal_state) for consumers; it suppresses a plan from compass `next`
ranking only — unify still emits its open tasks for human triage.

See backlog/SKILL.md `### unify` + references/plan-parser.md for the spec.
"""
import argparse, re, subprocess, sys, yaml, datetime
from pathlib import Path

REGISTRY = Path.home() / ".claude" / "projects-registry.yaml"
CONFIG = Path.home() / ".claude" / "portfolio-config.yaml"
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

# Terminal-state markers, both anchored at column 0 like the `**Completed:**`
# line executing-plans appends at close-out. ABANDONED_RE is authoritative;
# ABANDON_HINT_RE is advisory only (see the contract note above) and is
# deliberately NOT consulted by any suppression decision.
ABANDONED_RE = re.compile(r"^\*\*Abandoned:\*\*\s*(.+)$", re.M)
ABANDON_HINT_RE = re.compile(
    r"^[>#*_\s]{0,8}\b(OBSOLETE|SUPERSEDED|ABANDONED|DO NOT IMPLEMENT)\b", re.M)


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
    the heuristic below: every unchecked `- [ ]` (excluding the Preflight
    section) whose enclosing Stage is NOT git-confirmed-done, plus all
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
    in_deferred = False
    in_gate = False
    defer_n = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if SECTION.match(line):
            in_preflight = bool(PREFLIGHT_RE.match(line))
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
        if um and not in_preflight and not in_gate:
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
    return (f"## BL-{bid:03d} — {c['title'][:80]}\n\n"
            f"- **Opened:** {TODAY}\n"
            f"- **Source:** {c['source']}\n"
            f"- **Reason:** Auto-unified from plan ({c['signal']}).\n"
            f"- **Next step:** TBD — opened by unify on {TODAY}; review and refine.\n"
            f"- **Tags:** auto-unified\n\n---\n")


HEADER = ("# Backlog\n\nDeferred items from plan execution, code review, or ad-hoc "
          "capture. Entries are removed when implemented; git history is the audit trail.\n\n---\n")


def unify_project(home, write, repo_path):
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
        cands.extend(parse_plan(pf.read_text(errors="ignore"), rel, done_stages))
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
    args = ap.parse_args()
    vd = vault_dir()
    reg = yaml.safe_load(REGISTRY.read_text())
    projects = [p for p in reg["projects"] if p.get("enabled", True)]
    if args.project:
        projects = [p for p in projects if p["path"] == str(Path(args.project))]
    tot_new = tot_dup = tot_cand = 0
    for proj in projects:
        home = vd / "Portfolio" / proj["area"] / proj["name"]
        n, d, c = unify_project(home, args.write, proj["path"])
        tot_new += n; tot_dup += d; tot_cand += c
        if c:
            print(f"  {proj['area']}/{proj['name']}: {n} new, {d} dup, {c} candidates")
    print(f"\n{'WRITE' if args.write else 'DRY-RUN'}: {tot_new} new entries, "
          f"{tot_dup} duplicates skipped, {tot_cand} candidates across "
          f"{len(projects)} projects")


if __name__ == "__main__":
    main()
