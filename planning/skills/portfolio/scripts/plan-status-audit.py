#!/usr/bin/env python3
"""Vault-wide plan-status audit — classify every plan against its real progress.

WHY THIS EXISTS. A plan's recorded status and its actual task completion are
read by two different code paths and never reconciled. `portfolio unify` emits
an in-flight plan's open tasks as backlog candidates, and `compass next` ranks
projects by how much is in flight — so a plan that is finished but never
close-out-marked is a standing source of phantom work in both. Measured across
the live vault when this was written: 16 plans at 100% of tasks done carrying no
`**Completed:**` line at all.

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
CLASSES = ("abandoned", "completed", "unclassifiable", "no-status",
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
    reaches 479 plan files. The vault holds 518, in 82 `plans/` directories —
    39 files across 7 projects (kloak-mac 16, kloak-ubuntu 10, agents 4,
    openclawbench 3, deaf-blind-deb 3, ever-learn 2, bin-buster 1) live in
    directories with NO registry entry at all. None of them is disabled; they
    were simply never registered.

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
            files = sorted(f for f in d.glob("*.md") if f.is_file())
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


def classify(text, path):
    """(class, detail) for one plan. Total function: every plan gets a class.

    ORDER, AND WHY IT IS THIS ORDER:

    1. `abandoned` and 2. `completed` come first because they are HUMAN-AUTHORED
       terminal markers. A plan whose author wrote a close-out line has already
       answered the question this tool asks, and nothing below should overrule
       it. A plan carrying BOTH resolves to `abandoned` — deterministically, so
       the classification is stable — and the fact that it carries both is
       reported as detail rather than hidden.

    3. `unclassifiable` is checked next, and only for plans with no terminal
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
    if completed:
        return "completed", None

    odd = out_of_contract_markers(text)
    if odd:
        return "unclassifiable", "out-of-contract Status marker(s): " + ", ".join(
            f"[{m}]" for m in sorted(set(odd)))

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
    return [m.group(1) for line in text.splitlines()
            if (m := pu.ANY_STATUS_RE.match(line)) and not pu.STATUS_RE.match(line)]


# --------------------------------------------------------------------------
# Evidence (Task 4.2) — from the PROJECT REPO's git, never the vault's
# --------------------------------------------------------------------------

def _is_inside(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except (ValueError, OSError):
        return False


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
        if found:
            return found, "names-the-plan", None

    # Correlative fallback. Bounded by the plan's own date stamp so a plan from
    # January does not collect a stage commit from December of the year before.
    stamp = pu.plan_date(plan_path.name)
    if stamp is None:
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
            entry = {"path": str(f), "project": project["name"],
                     "repo": project.get("path") or "",
                     "done": done, "total": total, "detail": detail}
            report["classes"][cls].append(entry)
            if cls == "unclassifiable":
                report["unclassifiable"].append(entry)
            elif detail == "all-tasks-done-no-closeout":
                report["candidates"].append(entry)

    if with_evidence:
        for c in report["candidates"]:
            commits, strength, err = git_evidence(c["repo"], Path(c["path"]), vault)
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
         f"the unclassifiable class is non-empty ({len(uncl)}) — an empty one on "
         f"the live vault means the out-of-contract detector stopped detecting, "
         f"since 3 such markers are known to exist (BL-044)"),
        (n_abandoned == 0,
         f"abandoned is {n_abandoned} — nothing writes that marker, so a "
         f"non-zero count means a human adopted it, which is news rather than "
         f"a failure"),
    ]


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def describe_evidence(c):
    """One line saying what the evidence IS, and what it is not.

    Written as a sentence rather than a bare list because the grade is the
    load-bearing part: a reader skimming five commit hashes under the word
    "evidence" will read them as proof, whichever grade produced them.
    """
    if c.get("evidence_error"):
        return f"evidence: NONE — {c['evidence_error']}"
    strength = c.get("evidence_strength", "none")
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
    if strength == "names-the-plan" and hashes:
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
    original = p.read_text(encoding="utf-8")
    bdir = backup_dir(p, run_id)
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / p.name).write_text(original, encoding="utf-8")

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
    restored = 0
    for project in projects:
        d = plans_dir_for(vault, project) / ".audit-backups" / run_id
        if not d.is_dir():
            continue
        for b in sorted(d.glob("*.md")):
            target = d.parent.parent / b.name
            target.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"restored {target}")
            restored += 1
    print(f"{restored} file(s) restored from run {run_id}")
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
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

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
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print(f"\n--fix run {run_id} — nothing is written without a per-plan yes\n")
        written = 0
        for c in report["candidates"]:
            print(f"  {c['path']}")
            print(f"    {c['done']}/{c['total']} tasks done")
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
                line = record_completion(c["path"], c.get("evidence") or [],
                                         run_id, today,
                                         c.get("evidence_strength", "none"))
                print(f"    written: {line.strip()}")
                written += 1
            else:
                print("    left unchanged")
        print(f"\n{written} plan(s) updated. Undo with: "
              f"--restore {run_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
