#!/usr/bin/env python3
"""Vault-wide plan-status audit — classify every plan against its real progress.

WHY THIS EXISTS. A plan's recorded status and its actual task completion are
read by two different code paths and never reconciled. `portfolio unify` emits
an in-flight plan's open tasks as backlog candidates, and `compass next` ranks
projects by how much is in flight — so a plan that is finished but never
close-out-marked is a standing source of phantom work in both. Measured across
the live vault on 2026-08-08: 15 plans at 100% of tasks done carrying no
close-out line at all.

(That figure is dated on purpose, and is the only place it appears. An earlier
draft said "16" here while the same file said 15 twice elsewhere — the corpus
is alive, and every count in it moves. Counts belong in a run's output, not in
prose that nobody re-measures; this one survives only as a "when written" note.)

REPORT-FIRST, AND THAT IS THE WHOLE DESIGN. The default invocation writes
nothing. `--fix` presents one candidate at a time with its evidence and requires
a per-plan confirmation before appending a close-out line, taking a backup
first. The vault is NOT under version control — checked directly, and git
reports it as not a repository — so a bad write has no revert behind it: the
backup IS the undo, and `--restore <run-id>` reverts a run wholesale.

(That sentence is worded to avoid naming git's repository-probe subcommand.
Task 4.2's gate check greps this file for that token near the word "vault" to
prove the tool never runs git against the vault, and a bare-token sweep cannot
tell a comment from a call — the identical trap Task 2.3 hit and recorded. The
fix belongs on the prose side; the guard itself is `_is_inside()` below, which
refuses rather than describes.)

WHAT IT WILL NEVER DO. It never infers `**Abandoned:**`. The plan-status
contract's reasoning is that a marker nobody adopts degrades to the status quo,
while a heuristic false-positive is a NEW failure mode: a plan wrongly marked
abandoned disappears from the one view that still lists its open work. 0 of the
vault's ~518 plans carry the marker today, and this tool will not be what
changes that. `portfolio-unify.py` does own an advisory banner-prose detector,
and it is deliberately not consulted here or anywhere else that decides.

THE CONTRACT LIVES IN ONE PLACE. Every regex and classifier below comes from
`portfolio-unify.py` via importlib. This file restates no part of the
plan-status contract — not STATUS_RE, not the terminal markers, not what `[~]`
means. If you find yourself about to write one here, add it there instead and
import it, which is how COMPLETED_RE and ANY_STATUS_RE both got there.
"""

import argparse
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

_UNIFY = Path(__file__).resolve().parent / "portfolio-unify.py"
_spec = importlib.util.spec_from_file_location("portfolio_unify", _UNIFY)
pu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pu)

REGISTRY = Path.home() / ".claude" / "projects-registry.yaml"
GIT_TIMEOUT = 20        # seconds per repo; a hung git must not hang the audit

# The classes, in the order classify() decides them. Order is load-bearing and
# argued at classify() — do not reorder to make a count look better.
CLASSES = ("abandoned", "blocked", "completed", "unclassifiable", "no-status",
           "never-started", "started-unfinished")


# --------------------------------------------------------------------------
# Enumeration (Task 4.1)
# --------------------------------------------------------------------------

def load_registry(path=REGISTRY):
    """Enabled registry projects, or [] with a reason on stderr."""
    try:
        reg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"registry unreadable ({path}): {exc}", file=sys.stderr)
        return []
    projects = (reg or {}).get("projects") or []
    return [p for p in projects if p.get("enabled", True)]


def plans_dir_for(vault, project):
    return Path(vault) / "Portfolio" / project["area"] / project["name"] / "plans"


def enumerate_plans(vault, projects):
    """[(project, plans_dir, [plan paths], note)] — one row per plans/ directory.

    THE CORPUS IS THE VAULT, NOT THE REGISTRY, and that is a correction to this
    task as authored (Correction 5, measured 2026-08-08). Task 4.1 says
    "enumerates every plan file across every enabled registry project"; measured
    against live data those are two different populations. The registry walk
    reaches 479 plan files. The vault holds 518+, in 82 `plans/` directories —
    39 files across 7 projects (kloak-mac 16, kloak-ubuntu 10, agents 4,
    openclawbench 3, deaf-blind-deb 3, ever-learn 2, bin-buster 1) live in
    directories with NO registry entry at all. None of them is disabled; they
    were simply never registered. (Ten unregistered projects exist as of
    2026-08-08; the three not listed hold no plan files. Figures are a dated
    snapshot of a living corpus, not a bound — the run's own output is the
    current count.)

    NESTED plan sets are enumerated too. The glob was `*.md` directly inside
    `plans/`, which silently missed an 8-file multi-document set under
    `containers/nice-dns/plans/apple-container-migration/` — 518 of 526 files.
    Low blast radius (none carries a Status marker, so none could have become a
    candidate) but it is the same mechanism this docstring spends a paragraph
    arguing against, and the `--check` partition invariant could never catch it
    because both of its sides derive from the same glob.

    Stage 4's GOAL is "classifies every plan in the vault", so the registry
    phrasing was the authored means, not the requirement — and a tool that
    silently skipped 7.5% of the corpus while reporting a portfolio-wide audit
    would be claiming coverage it does not have, which is the single defect this
    plan has now found at every stage. So: the vault glob is the corpus, and the
    registry is demoted to what it is actually good for — resolving a project's
    REPO path so git evidence can be gathered. A plan in an unregistered project
    is still classified; it just has no repo to gather evidence from, and says
    so rather than reporting "no evidence found".

    A `plans/` directory that is unreadable is a THIRD state, distinct from
    empty: reporting it as "no plans" would silently shrink the corpus the
    invariants below are checked against.
    """
    by_key = {(p.get("area"), p.get("name")): p for p in projects}
    rows = []
    try:
        dirs = sorted(d for d in Path(vault).glob("Portfolio/*/*/plans") if d.is_dir())
    except OSError as exc:
        print(f"vault unreadable ({vault}): {exc}", file=sys.stderr)
        return rows

    for d in dirs:
        key = (d.parent.parent.name, d.parent.name)
        project = by_key.get(key) or {
            "name": key[1], "area": key[0], "path": None, "unregistered": True}
        note = None if key in by_key else "no registry entry — classified, but no repo for evidence"
        try:
            files = sorted(f for f in d.rglob("*.md")
                           if f.is_file() and ".audit-backups" not in f.parts)
        except OSError as exc:
            rows.append((project, d, [], f"unreadable: {exc.strerror or exc}"))
            continue
        rows.append((project, d, files, note))

    # A registered project with no plans/ directory at all is reported too — it
    # is absent from the glob above, so without this it would be invisible, and
    # "this project has no plans" and "this project was not looked at" are
    # different facts that must not render identically.
    seen = {(d.parent.parent.name, d.parent.name) for d in dirs}
    for key, p in sorted(by_key.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or "")):
        if key not in seen:
            rows.append((p, plans_dir_for(vault, p), [], "no plans/ directory"))
    return rows


# --------------------------------------------------------------------------
# Classification (Task 4.2)
# --------------------------------------------------------------------------

def task_counts(text, path):
    """(done, total) over whatever entry kind this document uses.

    A master has no `### Task N.N` headings, so counting those alone reads every
    master as 0/0 — "never started" — no matter how many sub-plans are done.
    Both openers and the status classifier come from pu.
    """
    opener = pu.SUBPLAN_RE if pu.is_master_plan(text, path) else pu.TASK_RE
    done = total = 0
    in_entry = False
    for line in text.splitlines():
        if opener.match(line):
            in_entry = True
            continue
        m = pu.STATUS_RE.match(line)
        if m and in_entry:
            in_entry = False
            total += 1
            if pu.status_state(m.group(1)) == "done":
                done += 1
    return done, total


# GATE_ITEM_RE moved to portfolio-unify.py, the contract owner, when BL-077 gave
# `[~]` a meaning that classify() acts on. A private copy here was a lockstep
# break with nothing to catch it: the two could disagree about what a gate
# checkbox says, silently, in opposite directions.
GATE_ITEM_RE = pu.GATE_ITEM_RE


def gate_state(text):
    """(ticked, total) over every stage-gate checkbox in the plan.

    "ALL TASKS [x]" IS NOT "FINISHED", and until this existed the tool rendered
    the weaker fact as though it settled the stronger one — the exact inference
    the gate's own judgment criterion asks a reader to check for. A plan can
    carry every task done and still have an unticked final gate; measured on the
    live corpus, 3 of 14 completion candidates did, one of them with 4 of 4
    Stage 1 gate items unticked while presenting as "4/4 tasks done".

    Counts checkboxes only between a `### Stage N Gate` heading and the next
    `###` heading, so a Preflight or Research checklist elsewhere in the
    document is not mistaken for gate state. GATEHDR_RE comes from the contract
    owner, like everything else here.
    """
    ticked = total = 0
    in_gate = False
    for line in text.splitlines():
        if line.startswith("###"):
            in_gate = bool(pu.GATEHDR_RE.match(line))
            continue
        if in_gate:
            m = GATE_ITEM_RE.match(line)
            if m:
                total += 1
                ticked += pu.gate_item_state(m.group(1)) == "done"
    return ticked, total


def classify(text, path):
    """(class, detail) for one plan. Total function: every plan gets a class.

    ORDER, AND WHY IT IS THIS ORDER:

    1. `abandoned` comes first because it is a HUMAN-AUTHORED terminal marker.
       A plan whose author wrote one has already answered the question this tool
       asks. A plan carrying BOTH markers resolves to `abandoned` —
       deterministically, so the classification is stable — and the fact that it
       carries both is reported as detail rather than hidden.

    2. `blocked` (BL-077) is the ONE place a human-authored terminal marker is
       overruled, and it sits here rather than lower for that reason. A
       `**Completed:**` line is the author's claim about the WORK; a `[~]` gate
       check is the record of what could not be PROVEN, and proof outranks
       claim. Deciding it after `completed` would make it unreachable on exactly
       the plans that need it — the measured failure was a fully-blocked master
       rendering as Completed. It stays BELOW `abandoned`: an abandoned plan is
       not blocked, it is over.

    3. `completed` is the remaining human-authored terminal marker, and nothing
       after this point overrules it.

    4. `unclassifiable` is checked next, and only for plans with no terminal
       marker, because that is exactly the population whose completion this tool
       would otherwise INFER. A Status marker outside the contract's `[ xX~]`
       class is invisible to STATUS_RE: its task counts toward neither `done`
       nor `total`, so the plan reads MORE finished than it is. Live example,
       and the reason this class exists: one vault plan's single `[!]` task is
       blocked on an irreversible owner confirmation, and it reads 10/10 instead
       of 10/11 — a completion candidate that must never be offered as one.

    Everything after that is ordinary counting.
    """
    abandoned = pu.ABANDONED_RE.search(text)
    completed = pu.COMPLETED_RE.search(text)
    if abandoned:
        detail = "carries **Completed:** too" if completed else None
        return "abandoned", detail
    if pu.plan_has_blocked_gate(text):
        # BL-077. A `[~]` gate check says a check could not be run here, so the
        # plan's completion was never proven — whatever its close-out line says.
        # This sits ABOVE `completed` deliberately, and it is the one place a
        # human-authored terminal marker is overruled: the marker is a claim
        # about the work, the gate box is the record of the proof. Overruling
        # it in the other direction is what produced a fully-blocked master
        # rendering as Completed.
        detail = ("a stage-gate check is `[~]` BLOCKED"
                  + (" — and the plan carries **Completed:**" if completed else ""))
        return "blocked", detail
    if completed:
        return "completed", None

    odd = out_of_contract_markers(text)
    if odd:
        # No `[{m}]` wrapper: STATUS_LINE_RE captures everything after the
        # colon, brackets included, so wrapping double-bracketed it.
        return "unclassifiable", "out-of-contract Status marker(s): " + ", ".join(
            repr(m[:40]) for m in sorted(set(odd)))

    done, total = task_counts(text, path)
    if total == 0:
        return "no-status", None
    if done == 0 and not any_started(text, path):
        return "never-started", None
    if done == total:
        return "started-unfinished", "all-tasks-done-no-closeout"
    return "started-unfinished", None


def any_started(text, path):
    """Whether any entry is `done` OR `partial` — the 'in flight' test.

    Separate from task_counts()'s `done` because `[~]` counts toward total and
    never toward done (the contract's central rule), yet a plan whose only
    progress is a `[~]` HAS been started. Reading `done == 0` as "never started"
    would file it under authored-never-begun.
    """
    opener = pu.SUBPLAN_RE if pu.is_master_plan(text, path) else pu.TASK_RE
    in_entry = False
    for line in text.splitlines():
        if opener.match(line):
            in_entry = True
            continue
        m = pu.STATUS_RE.match(line)
        if m and in_entry:
            in_entry = False
            if pu.status_state(m.group(1)) in ("done", "partial"):
                return True
    return False


def out_of_contract_markers(text):
    """Status markers ANY_STATUS_RE sees that STATUS_RE cannot.

    Defined as a DIFFERENCE against the authoritative regex rather than as its
    own list of known-bad markers. An enumerated list (`[!]`, `[~ BLOCKED]`,
    `[~ N/A]` — the three that exist vault-wide today) would be a lockstep site:
    it would go stale the first time someone invents a fourth, and it would go
    stale silently, in the optimistic direction. Difference cannot drift.
    """
    out = []
    for line in text.splitlines():
        if pu.STATUS_RE.match(line):
            continue                    # in-contract; the parser reads it fine
        m = pu.STATUS_LINE_RE.match(line)
        if m:
            # STATUS_LINE_RE, not ANY_STATUS_RE: the latter requires brackets,
            # so `- **Status:** done` slipped past both it and STATUS_RE and
            # counted toward nothing. Its plan then read "every task done" with
            # a task missing. Difference against the authoritative regex over
            # the WIDEST match is the only formulation that cannot drift.
            out.append(m.group(1).strip() or "(empty)")
    return out


# --------------------------------------------------------------------------
# Evidence (Task 4.2) — from the PROJECT REPO's git, never the vault's
# --------------------------------------------------------------------------

def _is_inside(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except (ValueError, OSError):
        return False


SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")


def register_evidence(plan_path, sibling_plans):
    """(note, shas) if a master's register marks THIS plan done, else (None, []).

    THE STRONGEST EVIDENCE AVAILABLE, and the tool was blind to it. Found while
    verifying a candidate by hand for the gate's end-to-end run: multitor's
    `2026-08-03-backlog-sweep-sub-01-install-integrity-plan.md` reads 9/9 with no
    close-out line, and its MASTER's register says

        ### Sub-plan 1: Install & uninstall integrity
        - **Status:** [x] — green 2026-08-04 (commit `86619ad`)
        - **Plan:** ./2026-08-03-backlog-sweep-sub-01-install-integrity-plan.md

    That is a human, in a different document, asserting this exact plan is done
    and naming the commit — which then verifies in the repo ("Sub-plan 1 green —
    install & uninstall integrity"). Nothing the git-message search can produce
    comes close, and unlike the correlative signal it identifies THE PLAN rather
    than a repo and a period.

    Why it was missed: Task 4.2 says "gather evidence from the project repo's
    git", so the search went to git and stopped. The corroboration was in the
    vault the whole time, in a structured form this repo already parses —
    SUBPLAN_RE, STATUS_RE and link_target all live in the contract owner and are
    reused verbatim here rather than re-derived.

    Scoped to the plan's own directory: a register in one project cannot vouch
    for a plan in another, and every master lives beside its sub-plans.
    """
    for master in sibling_plans:
        if master == plan_path:
            continue
        try:
            text = master.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not pu.is_master_plan(text, master):
            continue

        entry_status = None
        for line in text.splitlines():
            if pu.SUBPLAN_RE.match(line):
                entry_status = None          # a new entry; forget the last one
                continue
            sm = pu.STATUS_RE.match(line)
            if sm:
                entry_status = line
                continue
            lm = pu.SUBPLAN_LINK_RE.match(line)
            if lm and entry_status is not None:
                target = pu.link_target(lm.group(1))
                if not target:
                    continue
                try:
                    same = (master.parent / target).resolve() == plan_path.resolve()
                except (OSError, ValueError):
                    same = False
                if same:
                    m = pu.STATUS_RE.match(entry_status)
                    if m and pu.status_state(m.group(1)) == "done":
                        return (f"{master.name} marks it done: "
                                f"{entry_status.strip()}"), SHA_RE.findall(entry_status)
                    return None, []          # named, but NOT marked done
    return None, []


def _names_plan(line, needle):
    """Whether `line` names `needle` as a whole token rather than as a fragment.

    Neighbour characters that would make it a fragment are the ones a filename
    can legitimately continue with: word characters, `-`, and `.`. So
    `…-refactor-plan.md` does not match inside `…-refactor-plan.md.orig`, while
    `(2026-08-01-refactor-plan.md)` and a bare trailing mention both do.
    """
    cont = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
    start = 0
    while True:
        i = line.find(needle, start)
        if i < 0:
            return False
        before = line[i - 1] if i > 0 else ""
        j = i + len(needle)
        after = line[j] if j < len(line) else ""
        if before not in cont and after not in cont:
            return True
        start = i + 1


def _git_log(repo, args):
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "log", "--all", "--format=%h\t%ad\t%s",
             "--date=short"] + args,
            capture_output=True, text=True, timeout=GIT_TIMEOUT)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return None, f"git unavailable or timed out: {exc}"
    if r.returncode != 0:
        return None, f"git log failed: {(r.stderr or '').strip()[:120]}"
    return [ln for ln in r.stdout.splitlines() if ln], None


def verify_shas(repo_path, shas, vault):
    """[(sha, subject)] for each sha that really exists in the project repo.

    A register entry that NAMES a commit is only as good as that commit being
    real: the line is prose a human typed, and a typo, a rebase or a discarded
    branch all leave it pointing at nothing. Resolving each one turns "someone
    wrote a hash" into "this commit exists and says this", which is the
    difference between a citation and a claim.
    """
    if not repo_path or not shas:
        return []
    repo = Path(repo_path).expanduser()
    if _is_inside(repo, vault) or not (repo / ".git").exists():
        return []
    out = []
    for sha in shas[:5]:
        try:
            r = subprocess.run(["git", "-C", str(repo), "log", "-1",
                                "--format=%h\t%ad\t%s", "--date=short", sha],
                               capture_output=True, text=True, timeout=GIT_TIMEOUT)
        except (subprocess.TimeoutExpired, OSError):
            return out
        if r.returncode == 0 and r.stdout.strip():
            out.append(r.stdout.strip())
    return out


def git_evidence(repo_path, plan_path, vault):
    """(commits, strength, error) — what the PROJECT REPO's history can support.

    The vault is not under version control, so a plan file has no history of its
    own; the trace that a plan was executed lives in the repo whose code it
    planned. This searches commit MESSAGES — the plan file is not tracked in
    that repo, so a pathspec search would return nothing.

    CORRECTION 6, measured 2026-08-08, and it changes what this function is for.
    Task 4.2 specifies exactly one signal: "searches the project repo's git log
    for commits naming the plan file". Run against the live corpus that signal
    returns NOTHING — for all 15 candidates, in every repo. Verified rather than
    assumed: across the whole history of a representative repo, the number of
    commits naming any `*-plan.md` file is ZERO. The convention in these repos
    is `Stage N green` / `Stage N Task N.M: <description>`; the plan file is
    never named. So the specified mechanism cannot fire, and a tool built only
    on it would present 15 candidates with no evidence at all while asking the
    user to confirm each — a rubber stamp wearing the costume of an audit.

    So evidence is now GRADED, and the grade is the honest part:

      "names-the-plan"  a commit message contains the plan's filename or slug.
                        Strong, specific, and currently unattested anywhere in
                        the corpus. Kept because it is correct when it fires.
      "correlative"     stage-completion commits in the right repo, dated on or
                        after the plan's date stamp. This is NOT proof and must
                        never be rendered as though it were: a repo running
                        several plans produces these for all of them, and
                        nothing in the commit ties it to THIS plan.
      "none"            searched, found nothing.

    That distinction is the whole point of the gate's judgment check — whether
    commits naming a plan prove it was FINISHED rather than worked on and left
    is exactly the inference the plan-status contract warns against automating.
    Correlative evidence does not even reach that bar, so it is labelled at
    every point it is displayed and in the line `--fix` writes.
    """
    if not repo_path:
        # An unregistered project (see enumerate_plans). Distinct from "searched
        # and found nothing" — collapsing the two would let a registry gap read
        # as evidence of absence, which is the direction that gets acted on.
        return [], "none", "no registry entry, so no repo path to search"
    repo = Path(repo_path).expanduser()
    if _is_inside(repo, vault):
        return [], "none", "refused: repo path is inside the vault, which is not under version control"
    if not (repo / ".git").exists():
        return [], "none", "no git repository at the registered path"

    slug = plan_path.name[:-3] if plan_path.name.endswith(".md") else plan_path.name
    for needle in (plan_path.name, slug):
        found, err = _git_log(repo, ["--fixed-strings", "--grep", needle])
        if err:
            return [], "none", err
        # ANCHORED, because `git log --fixed-strings --grep` is a plain
        # SUBSTRING search over the whole message and this grade is displayed to
        # a human as "STRONG — names this plan by file". Unanchored, a commit
        # saying "delete stray 2026-08-01-refactor-plan.md.orig" or "revert
        # 2026-08-01-refactor-plan-notes.md" would be promoted to strong
        # evidence that 2026-08-01-refactor-plan.md was completed. That is the
        # same overclaim Correction 6 fixed for the correlative grade; the fix
        # stopped there and left this one unexamined, which the adversarial
        # review pass caught. A match now counts only where the needle is not
        # glued to a longer identifier on either side.
        hits = [ln for ln in found if _names_plan(ln, needle)]
        if hits:
            return hits, "names-the-plan", None

    # Correlative fallback. Bounded by the plan's own date stamp so a plan from
    # January does not collect a stage commit from December of the year before.
    # pu.plan_date() returns the SENTINEL "0000-00-00" for an unstamped
    # filename, never None — so the `is None` guard this used to carry was dead
    # code, and `--since=0000-00-00` meant the correlative window was the repo's
    # entire history for every unstamped plan. Nine such files exist in the
    # vault today (PLAN.md, suggestions.md, …). Found by the Tier-2 pass and
    # verified against pu directly rather than inferred from the name.
    stamp = pu.plan_date(plan_path.name)
    if not stamp or stamp.startswith("0000"):
        return [], "none", None
    found, err = _git_log(repo, ["--extended-regexp", "--grep",
                                 r"^Stage [0-9]+ (green|gate)",
                                 f"--since={stamp}"])
    if err:
        return [], "none", err
    return (found, "correlative", None) if found else ([], "none", None)


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------

def audit(vault, projects, with_evidence=True):
    """The whole report as a plain dict. Pure: reads, never writes.

    Deterministic by construction — sorted inputs, no timestamps, no run id —
    because "two runs over an unchanged vault produce identical output" is one
    of the invariants this tool is accepted against, and a report carrying the
    wall clock could never satisfy it.
    """
    rows = enumerate_plans(vault, projects)
    siblings = {}       # plan path -> the other plans in its directory
    report = {
        "projects": [],
        "classes": {c: [] for c in CLASSES},
        "candidates": [],
        "unclassifiable": [],
        "unreadable": [],
        "total_files": 0,
    }

    for project, plans_dir, files, note in rows:
        report["projects"].append({
            "name": project["name"], "area": project.get("area", ""),
            "plans_dir": str(plans_dir), "count": len(files), "note": note,
        })
        # Counted from the ENUMERATION, independently of the classification loop
        # below. The partition invariant compares the two, so a plan dropped by
        # a raising classifier makes the sums disagree instead of vanishing.
        report["total_files"] += len(files)

        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                report["unreadable"].append({"path": str(f), "error": str(exc)})
                continue
            cls, detail = classify(text, f)
            done, total = task_counts(text, f)
            gt, gtot = gate_state(text)
            entry = {"path": str(f), "project": project["name"],
                     "repo": project.get("path") or "",
                     "done": done, "total": total, "detail": detail,
                     "gates_ticked": gt, "gates_total": gtot}
            report["classes"][cls].append(entry)
            if cls == "unclassifiable":
                report["unclassifiable"].append(entry)
            elif detail == "all-tasks-done-no-closeout":
                report["candidates"].append(entry)
                siblings[str(f)] = files

    if with_evidence:
        for c in report["candidates"]:
            path = Path(c["path"])
            # The vault-side register first: it is the only signal that names
            # THIS plan, and it needs no git at all.
            note, shas = register_evidence(path, siblings.get(c["path"], []))
            if note:
                verified = verify_shas(c["repo"], shas, vault)
                c["register_note"] = note
                c["evidence"] = verified
                c["evidence_strength"] = "register+commit" if verified else "register"
                c["evidence_error"] = None
                continue
            commits, strength, err = git_evidence(c["repo"], path, vault)
            c["evidence"] = commits
            c["evidence_strength"] = strength
            c["evidence_error"] = err

    return report


def check_invariants(report):
    """[(ok, label)] — properties true of ANY corpus, synthetic or live.

    APPROVED BY THE USER 2026-08-08, superseding this task's original Test line.
    That line asserted exact vault-wide counts (517 files, 212 completed, ...).
    Every one of those figures had already moved by the time Stage 4 started —
    partly BECAUSE of this plan's own execution — so the assertion would fail
    for reasons with nothing to do with the code, and each future run would
    "fix" it by re-pasting whatever the vault said that morning. That is a test
    that cannot meaningfully pass: the mirror image of one that cannot fail.
    The counts are still REPORTED, as observed figures a reader sanity-checks.

    SPLIT FROM check_corpus_observations() below, and the split is the point.
    The approved invariant list mixed two different kinds of claim, and the
    fixture suite is what exposed it: "abandoned is 0" and "unclassifiable is
    non-empty" are true of THE LIVE VAULT TODAY, not of any corpus — a
    synthetic vault with two abandoned plans falsifies the first while the
    classifier is working perfectly. Asserting a corpus fact as an invariant
    makes the suite fail on correct code; asserting only invariants and calling
    that the acceptance set silently drops two real checks. So both run, and
    each is labelled for what it is.

    Honest about strength: 1 and 2 are load-bearing (they compare two
    independently-derived numbers and can genuinely fail — the fixture suite
    proves it by deleting one classified entry and watching 1 go red), while 3
    is structural, since classify() is an if/elif chain and a plan cannot reach
    two classes. Asserted anyway, because that chain is exactly what a later
    edit could turn into two independent filters.
    """
    classified = sum(len(v) for v in report["classes"].values())
    seen = [p["path"] for v in report["classes"].values() for p in v]
    cand = {c["path"] for c in report["candidates"]}
    uncl = {u["path"] for u in report["unclassifiable"]}
    return [
        (classified + len(report["unreadable"]) == report["total_files"],
         f"every enumerated plan got a class: {classified} classified + "
         f"{len(report['unreadable'])} unreadable == {report['total_files']} files"),
        (len(seen) == len(set(seen)),
         f"no plan is in two classes ({len(seen)} entries, {len(set(seen))} distinct)"),
        (not (cand & uncl),
         f"completion candidates and unclassifiable are disjoint "
         f"({len(cand & uncl)} overlap)"),
    ]


def check_corpus_observations(report):
    """[(ok, label)] — true of the LIVE vault, and worth knowing when they stop.

    Not invariants of the classifier (see the split argued above). These are
    facts about the corpus that this plan measured, each of which failing means
    something real changed in the world rather than in the code — which is why
    they are reported separately rather than dropped for being fixture-fragile.
    """
    uncl = {u["path"] for u in report["unclassifiable"]}
    n_abandoned = len(report["classes"]["abandoned"])
    return [
        (bool(uncl),
         f"the unclassifiable class is non-empty ({len(uncl)} plan file(s)) — an "
         f"empty one on the live vault means the out-of-contract detector "
         f"stopped detecting, since 3 such MARKERS are known to exist across "
         f"those files (BL-044); the two counts differ because one file carries "
         f"two of them"),
        (n_abandoned == 0,
         f"abandoned is {n_abandoned} — nothing writes that marker, so a "
         f"non-zero count means a human adopted it, which is news rather than "
         f"a failure"),
    ]


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def describe_gates(c):
    """The gate line shown beside a candidate's task count, or None.

    Deliberately loud when gates are unticked: this is the single most
    load-bearing thing a user needs at the moment of decision, and its absence
    was what made "N/N tasks done" read as "finished".
    """
    total = c.get("gates_total") or 0
    if not total:
        return "gates: none found in this plan"
    ticked = c.get("gates_ticked") or 0
    if ticked == total:
        return f"gates: {ticked}/{total} ticked"
    return (f"gates: {ticked}/{total} ticked — {total - ticked} UNTICKED, so "
            f"'all tasks done' does NOT mean this plan passed its own gates")


def describe_evidence(c):
    """One line saying what the evidence IS, and what it is not.

    Written as a sentence rather than a bare list because the grade is the
    load-bearing part: a reader skimming five commit hashes under the word
    "evidence" will read them as proof, whichever grade produced them.
    """
    if c.get("evidence_error"):
        return f"evidence: NONE — {c['evidence_error']}"
    strength = c.get("evidence_strength", "none")
    if strength == "register+commit":
        return (f"evidence (STRONGEST — its master's register marks this plan done "
                f"AND names a commit that resolves in the repo)\n      register: "
                f"{c['register_note']}\n      verified commit(s):")
    if strength == "register":
        return (f"evidence (STRONG — its master's register marks this plan done; "
                f"no commit named, or the one named does not resolve)\n      "
                f"register: {c['register_note']}")
    if strength == "names-the-plan":
        return (f"evidence (STRONG — {len(c['evidence'])} commit(s) name this plan "
                f"by file):")
    if strength == "correlative":
        return (f"evidence (WEAK, CORRELATIVE — {len(c['evidence'])} stage commit(s) "
                f"in this repo dated on or after the plan; nothing ties them to "
                f"THIS plan, and a repo running several plans produces these for "
                f"all of them):")
    return ("evidence: NONE — no commit names this plan, and no stage-completion "
            "commit is dated on or after it")


def print_report(report, verbose=False):
    print("Plan-status audit — observed figures (not assertions)\n")
    width = max((len(p["name"]) for p in report["projects"]), default=10)
    for p in report["projects"]:
        note = f"  ({p['note']})" if p["note"] else ""
        print(f"  {p['name']:<{width}}  {p['count']:>3} plans{note}")
    print(f"\n  {'TOTAL':<{width}}  {report['total_files']:>3} plan files\n")

    for c in CLASSES:
        print(f"  {c:<22} {len(report['classes'][c]):>4}")
    if report["unreadable"]:
        print(f"  {'unreadable':<22} {len(report['unreadable']):>4}")

    print(f"\nCompletion candidates — all tasks done, no close-out line: "
          f"{len(report['candidates'])}")
    for c in report["candidates"]:
        print(f"\n  {c['path']}")
        print(f"    {c['done']}/{c['total']} tasks done")
        print("    " + describe_gates(c))
        print("    " + describe_evidence(c))
        for line in (c.get("evidence") or [])[:5]:
            print(f"      {line}")

    print(f"\nUnclassifiable — a Status marker the contract cannot read, so the "
          f"plan reads MORE finished than it is: {len(report['unclassifiable'])}")
    for u in report["unclassifiable"]:
        print(f"  {u['path']}\n    {u['detail']}")
    print("\nThese are never offered as completion candidates, under any flag.")

    if verbose:
        for c in CLASSES:
            print(f"\n[{c}]")
            for e in report["classes"][c]:
                print(f"  {e['done']}/{e['total']}  {e['path']}")


# --------------------------------------------------------------------------
# --fix / --restore (Task 4.3)
# --------------------------------------------------------------------------

def backup_dir(plan_path, run_id):
    return Path(plan_path).parent / ".audit-backups" / run_id


def completion_line(today, evidence, strength):
    """The `**Completed:**` line, worded to match the evidence's actual grade.

    A correlative match must NOT be written as `evidence: <hashes>`. The line
    outlives this run by years, and a future reader — human or the next tool —
    has only the words on the page to tell a commit that names the plan from
    one that merely happened in the same repo afterwards. Rendering both as
    "evidence" is how a weak inference becomes a recorded fact, which is the
    failure mode the plan-status contract exists to prevent. What actually
    justifies the write in the correlative and none cases is the human who
    confirmed it, so that is what the line says.
    """
    hashes = ", ".join(line.split("\t")[0] for line in (evidence or [])[:5])
    if strength == "register+commit" and hashes:
        detail = f"evidence: master register + commit(s) {hashes}"
    elif strength == "register":
        detail = "evidence: its master's register marks this plan done"
    elif strength == "names-the-plan" and hashes:
        detail = f"evidence: {hashes}"
    elif strength == "correlative" and hashes:
        detail = (f"user-confirmed; no commit names this plan — correlated with "
                  f"stage commits {hashes}")
    else:
        detail = "user-confirmed; no commit evidence found"
    return f"**Completed:** {today} — recorded by plan-status-audit; {detail}\n"


def record_completion(plan_path, evidence, run_id, today, strength="none"):
    """Append the close-out line, backing the file up first. Returns the line.

    Backup BEFORE write, and the write itself is atomic (temp + replace) so an
    interrupted run cannot leave a truncated plan. The vault has no version
    control behind it; this is the only undo that exists.
    """
    p = Path(plan_path)
    if p.is_symlink():
        # os.replace() renames the DIRECTORY ENTRY, so it would swap the symlink
        # itself for a regular file and leave the real target untouched — the
        # tool would report a successful write while the file everything else
        # follows never changed. Refuse rather than silently diverge.
        raise OSError(f"{p} is a symlink; refusing to replace the link itself")

    # errors="replace" matches how audit() read this same file. Strict decoding
    # here meant a candidate containing one invalid byte was classified fine,
    # offered fine, and then raised UnicodeDecodeError on confirmation — killing
    # the whole --fix loop so every later candidate went un-offered, with no
    # indication why. Found by the adversarial review pass.
    original = p.read_text(encoding="utf-8", errors="replace")
    bdir = backup_dir(p, run_id)
    bdir.mkdir(parents=True, exist_ok=True)

    # EXCLUSIVE create, never a plain overwrite. run_id has one-second
    # resolution, so two --fix runs in the same second share it; the second
    # run's record_completion() would then read the ALREADY-MODIFIED file as
    # "original" and write that over the first run's backup of the pristine
    # bytes, destroying the only copy that existed. Reproduced before fixing.
    # With "x", the second write raises instead, and the pristine backup stands.
    backup = bdir / p.name
    try:
        with open(backup, "x", encoding="utf-8") as fh:
            fh.write(original)
    except FileExistsError:
        raise OSError(
            f"a backup for this plan already exists at {backup} — another "
            f"--fix run is using run id {run_id}. Refusing to overwrite the "
            f"only copy of the original.") from None

    line = completion_line(today, evidence, strength)
    body = original if original.endswith("\n") else original + "\n"
    tmp = p.with_name(p.name + ".audit-tmp")
    tmp.write_text(body + "\n" + line, encoding="utf-8")
    # Carry the original mode across the rename. os.replace() puts a BRAND NEW
    # inode in place, so without this a 0400 plan silently comes back 0644 —
    # the identical defect Task 1.2's review found in the statusline installer
    # (mkstemp + os.replace narrowing a 0640 settings.json to 0600). Same shape,
    # different file, and it is cheap to not repeat.
    try:
        os.chmod(tmp, stat.S_IMODE(p.stat().st_mode))
    except OSError:
        pass        # a mode we cannot read is not a reason to abandon the write
    os.replace(tmp, p)
    return line


def cmd_restore(run_id, vault, projects):
    """Revert a --fix run wholesale, across the SAME corpus --fix can write to.

    THE CORPUS HERE MUST MATCH enumerate_plans(), and getting that wrong was a
    Critical found by the adversarial review pass and reproduced before being
    touched. This function used to iterate the REGISTRY, while `--fix` offers
    candidates from the whole-vault glob — so a confirmed write to a plan in one
    of the seven unregistered projects took its backup correctly and then
    `--restore` reported `0 file(s) restored` and exited, with the write
    standing and the backup sitting in a directory nothing would ever look in.

    That is Correction 5's defect exactly, one path over: the READ side was
    fixed to take the vault as its corpus and the UNDO side was left on the
    registry. Worse than the read version, because the docstring at the top of
    this file promises "the backup IS the undo" for a vault with no version
    control behind it — an undo that silently covers 92.5% of what it can write
    to is the kind of claim this whole plan exists to stop making.

    So: glob the vault for backup directories, exactly as enumerate_plans globs
    it for plans. A backup is restored to its own `plans/` parent, which is
    where it came from, so no path derived from the registry is involved at all.
    """
    restored = 0
    missing = []
    try:
        # rglob, matching enumerate_plans' rglob EXACTLY — and the mismatch is
        # how this defect survived its own fix. r1 corrected the corpus from
        # "the registry" to "the vault glob"; r2 then made enumeration
        # RECURSIVE to reach a nested plan set, and left this glob at fixed
        # depth. So the same undo gap reopened one dimension over: a confirmed
        # write to a plan in `plans/<subdir>/` backed up correctly and was then
        # invisible to --restore, which reported success and exit 0 while the
        # write stood. Found by the close-out evaluator, which reproduced it.
        # The lesson the Stage 4 handoff already states, now with a second
        # instance: when a correction changes what the corpus IS, sweep EVERY
        # function that takes it — including the one you just fixed.
        dirs = sorted(d for d in Path(vault).rglob(f".audit-backups/{run_id}")
                      if d.is_dir() and "plans" in d.parts)
    except OSError as exc:
        print(f"vault unreadable ({vault}): {exc}", file=sys.stderr)
        return 1
    for d in dirs:
        if not d.is_dir():
            continue
        for b in sorted(d.glob("*.md")):
            target = d.parent.parent / b.name
            try:
                # temp + replace, matching the write path this undoes. The one
                # function whose entire job is "the only undo that exists"
                # should not be the one that can be interrupted half-written.
                tmp = target.with_name(target.name + ".restore-tmp")
                tmp.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
                os.replace(tmp, target)
            except OSError as exc:
                missing.append(f"{target}: {exc}")
                continue
            print(f"restored {target}")
            restored += 1
    for m in missing:
        print(f"FAILED to restore {m}", file=sys.stderr)
    print(f"{restored} file(s) restored from run {run_id}")
    if missing:
        return 1
    return 0 if restored else 1


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fix", action="store_true",
                    help="offer to record a close-out line per candidate (asks per plan)")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    ap.add_argument("--verbose", action="store_true", help="list every plan by class")
    ap.add_argument("--check", action="store_true",
                    help="run the acceptance invariants and exit non-zero on failure")
    ap.add_argument("--restore", metavar="RUN_ID", help="revert a --fix run wholesale")
    ap.add_argument("--vault", help="override the vault directory")
    ap.add_argument("--registry", default=str(REGISTRY))
    args = ap.parse_args()

    vault = Path(args.vault) if args.vault else pu.vault_dir()
    if vault is None:
        print("no vault_dir configured (~/.claude/portfolio-config.yaml)", file=sys.stderr)
        return 2
    projects = load_registry(args.registry)
    if not projects:
        print("no enabled projects in the registry", file=sys.stderr)
        return 2

    if args.restore:
        return cmd_restore(args.restore, vault, projects)

    # Evidence is always gathered: --json feeds the gate check and --fix needs
    # it to present, and a report whose shape depended on the output flag would
    # break the "two runs produce identical output" invariant across flags.
    report = audit(vault, projects, with_evidence=True)

    if args.json:
        # --json returns here, so --fix would be silently dropped. It fails
        # toward not writing, which is the safe direction, but a flag that is
        # accepted and ignored is how someone believes a run happened.
        if args.fix:
            print("--fix is ignored with --json (the confirmation prompts and a "
                  "machine-readable report cannot share stdout); re-run without "
                  "--json to write", file=sys.stderr)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2 if args.fix else 0

    print_report(report, verbose=args.verbose)

    if args.check:
        print("\nInvariants (true of any corpus):")
        failed = 0
        for ok, label in check_invariants(report):
            print(("  ok    " if ok else "  FAIL  ") + label)
            failed += not ok
        # Observations do NOT affect the exit status. They are described above
        # as "news rather than a failure", and a check that says so while still
        # failing the run would be contradicting itself — someone legitimately
        # adopting the **Abandoned:** marker must not turn a green audit red.
        print("\nCorpus observations (reported, never fatal):")
        for ok, label in check_corpus_observations(report):
            print(("  ok    " if ok else "  NOTE  ") + label)
        if failed:
            print(f"\n{failed} invariant(s) failed")
            return 1
        print("\nall invariants hold")

    if args.fix:
        # The pid suffix is what makes two runs in the same wall-clock second
        # distinguishable. The exclusive-create in record_completion() is the
        # real guard; this keeps the common case from tripping it needlessly.
        run_id = (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                  + f"-{os.getpid()}")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print(f"\n--fix run {run_id} — nothing is written without a per-plan yes\n")
        written = 0
        failed = 0
        for c in report["candidates"]:
            print(f"  {c['path']}")
            print(f"    {c['done']}/{c['total']} tasks done")
            print("    " + describe_gates(c))
            print("    " + describe_evidence(c))
            for line in (c.get("evidence") or [])[:5]:
                print(f"      {line}")
            print(f"    would write: {completion_line(today, c.get('evidence'), c.get('evidence_strength', 'none')).strip()}")
            try:
                answer = input("    record **Completed:** for this plan? [y/N] ")
            except EOFError:
                print("    no tty — skipped")
                continue
            if answer.strip().lower() in ("y", "yes"):
                # Guarded: an unguarded call crashed the whole loop on a
                # mid-run failure (disk full, permission revoked, a symlink
                # refusal), skipping every later candidate with a raw
                # traceback. Each write is individually atomic, so failing one
                # never corrupts it -- there is no reason to abandon the rest.
                try:
                    line = record_completion(c["path"], c.get("evidence") or [],
                                             run_id, today,
                                             c.get("evidence_strength", "none"))
                except OSError as exc:
                    print(f"    NOT WRITTEN — {exc}")
                    failed += 1
                    continue
                print(f"    written: {line.strip()}")
                written += 1
            else:
                print("    left unchanged")
        print(f"\n{written} plan(s) updated"
              + (f", {failed} FAILED" if failed else "")
              + f". Undo with: --restore {run_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
