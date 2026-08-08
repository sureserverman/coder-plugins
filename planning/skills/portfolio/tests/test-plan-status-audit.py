#!/usr/bin/env python3
"""Fixture tests for plan-status-audit.py — the vault-wide plan-status audit.

Runs against a SYNTHETIC vault built per test, never the real one, so the
assertions are about the classifier rather than about whatever the live corpus
happened to say that morning. The live corpus is checked separately by
`--check`, whose acceptance is a set of INVARIANTS rather than frozen counts
(see check_invariants() for why the counts had to go).

Covers every class plus the adversarial cases Task 4.5 names: a plan whose only
task is `[~]`, a master whose register is complete but whose sub-plan is not, a
plan already carrying both terminal markers, a read-only plan file, and a plan
that disappears between enumeration and write.

No pytest dependency — plain assertions, non-zero exit on any failure.
Run locally:  python3 planning/skills/portfolio/tests/test-plan-status-audit.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "plan-status-audit.py"

spec = importlib.util.spec_from_file_location("plan_status_audit", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILURES: list[str] = []


def check(cond, label):
    print(("  ok    " if cond else "  FAIL  ") + label)
    if not cond:
        FAILURES.append(label)


def task(n, mark, title="a task"):
    return f"### Task {n}: {title}\n- **Status:** [{mark}]\n\n"


def subplan(n, mark, title="a sub-plan"):
    return f"### Sub-plan {n}: {title}\n- **Status:** [{mark}]\n\n"


# --- fixture vault ---------------------------------------------------------

PLANS = {
    # name                     body
    "2026-01-01-done-plan.md": task("1.1", "x") + task("1.2", "x"),
    "2026-01-02-completed-plan.md": (task("1.1", "x")
                                     + "**Completed:** 2026-01-03 — commits: abc1234\n"),
    "2026-01-03-abandoned-plan.md": (task("1.1", "x")
                                     + "**Abandoned:** 2026-01-04 — overtaken\n"),
    "2026-01-04-both-markers-plan.md": (task("1.1", "x")
                                        + "**Completed:** 2026-01-05 — commits: def5678\n"
                                        + "**Abandoned:** 2026-01-06 — then dropped\n"),
    "2026-01-05-never-started-plan.md": task("1.1", " ") + task("1.2", " "),
    "2026-01-06-partway-plan.md": task("1.1", "x") + task("1.2", " "),
    "2026-01-07-no-status-plan.md": "# Plan\n\nSome prose and a - [ ] loose bullet.\n",
    "2026-01-08-design.md": "# Design\n\nNo Status fields at all.\n",
    "2026-01-09-out-of-contract-plan.md": task("1.1", "x") + task("1.2", "!"),
    "2026-01-10-annotated-marker-plan.md": task("1.1", "x") + task("1.2", "~ BLOCKED"),
    # The adversarial `[~]`-only plan: started, but `done` is 0. A classifier
    # reading `done == 0` as "never started" files this under authored-never-
    # begun, which is the optimistic direction — it is in flight.
    "2026-01-11-partial-only-plan.md": task("1.1", "~"),
    # A master whose REGISTER is complete while its sub-plan is not. The master
    # is a completion candidate on its own text; the sub-plan is not, and the
    # two must classify independently rather than one dragging the other.
    "2026-01-12-alpha-master-plan.md": ("# Master Plan: alpha\n\n## Sub-plans\n\n"
                                        + subplan(1, "x") + subplan(2, "x")),
    "2026-01-13-alpha-sub-01-plan.md": task("1.1", "x") + task("1.2", " "),
}


def build_vault(tmp, area="testarea", name="demo"):
    vault = tmp / "vault"
    plans = vault / "Portfolio" / area / name / "plans"
    plans.mkdir(parents=True)
    for fname, body in PLANS.items():
        (plans / fname).write_text(body, encoding="utf-8")
    return vault, plans


def registry_for(tmp, repo, area="testarea", name="demo"):
    reg = tmp / "registry.yaml"
    reg.write_text(
        "version: 1\nprojects:\n"
        f"  - path: {repo}\n    name: {name}\n    area: {area}\n    enabled: true\n",
        encoding="utf-8")
    return reg


def make_repo(tmp, subject):
    """A real git repo with one commit whose message names a plan file."""
    repo = tmp / "repo"
    repo.mkdir(parents=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e"}
    # `--template=` (empty) suppresses ~/.git-templates. This machine's global
    # template installs a pre-commit hook that rewrites .gitignore and ABORTS
    # the first commit, so a fixture repo created the ordinary way cannot make
    # one — the suite would fail for a reason having nothing to do with the
    # code under test, and only on machines carrying that template.
    subprocess.run(["git", "init", "-q", "--template="], cwd=repo, env=env, check=True)
    (repo / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=repo, env=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", subject], cwd=repo, env=env, check=True)
    return repo


def run_audit(vault, registry):
    projects = mod.load_registry(registry)
    return mod.audit(vault, projects), projects


# --- cases -----------------------------------------------------------------

def case_classification():
    print("classification — every class, and the adversarial ones:")
    tmp = Path(tempfile.mkdtemp(prefix="psa-cls-"))
    vault, plans = build_vault(tmp)
    repo = make_repo(tmp, "Stage 1 green (2026-01-01-done-plan.md)")
    report, _ = run_audit(vault, registry_for(tmp, repo))

    def cls_of(fname):
        for c, entries in report["classes"].items():
            for e in entries:
                if Path(e["path"]).name == fname:
                    return c
        return None

    expected = {
        "2026-01-01-done-plan.md": "started-unfinished",
        "2026-01-02-completed-plan.md": "completed",
        "2026-01-03-abandoned-plan.md": "abandoned",
        "2026-01-04-both-markers-plan.md": "abandoned",
        "2026-01-05-never-started-plan.md": "never-started",
        "2026-01-06-partway-plan.md": "started-unfinished",
        "2026-01-07-no-status-plan.md": "no-status",
        "2026-01-08-design.md": "no-status",
        "2026-01-09-out-of-contract-plan.md": "unclassifiable",
        "2026-01-10-annotated-marker-plan.md": "unclassifiable",
        "2026-01-11-partial-only-plan.md": "started-unfinished",
        "2026-01-12-alpha-master-plan.md": "started-unfinished",
        "2026-01-13-alpha-sub-01-plan.md": "started-unfinished",
    }
    for fname, want in expected.items():
        got = cls_of(fname)
        check(got == want, f"{fname} -> {want} (got {got})")

    print("  a plan carrying BOTH markers resolves deterministically:")
    both = [e for e in report["classes"]["abandoned"]
            if Path(e["path"]).name == "2026-01-04-both-markers-plan.md"]
    check(both and both[0]["detail"] == "carries **Completed:** too",
          "abandoned wins, and the other marker is REPORTED, not hidden")

    print("  the `[~]`-only plan is in flight, not 'never started':")
    partial = [e for e in report["classes"]["started-unfinished"]
               if Path(e["path"]).name == "2026-01-11-partial-only-plan.md"]
    check(bool(partial), "a plan whose only task is [~] counts as started")
    check(partial and partial[0]["done"] == 0 and partial[0]["total"] == 1,
          f"and it reads 0/1 — [~] counts toward total, never done "
          f"(got {partial[0]['done']}/{partial[0]['total']} )" if partial else "n/a")
    check(partial and partial[0]["detail"] != "all-tasks-done-no-closeout",
          "so it is NOT offered as a completion candidate")

    print("  the master and its sub-plan classify independently:")
    cands = {Path(c["path"]).name for c in report["candidates"]}
    check("2026-01-12-alpha-master-plan.md" in cands,
          f"the master's register is complete -> a candidate ({sorted(cands)})")
    check("2026-01-13-alpha-sub-01-plan.md" not in cands,
          "its unfinished sub-plan is NOT dragged in with it")

    print("  candidates carry evidence from the PROJECT REPO's git:")
    done = [c for c in report["candidates"]
            if Path(c["path"]).name == "2026-01-01-done-plan.md"]
    check(bool(done) and bool(done[0].get("evidence")),
          f"a commit naming the plan file was found ({done[0].get('evidence') if done else None})")
    check(done and "Stage 1 green" in done[0]["evidence"][0],
          "and it is the right commit")

    shutil.rmtree(tmp, ignore_errors=True)


def case_invariants_and_determinism():
    print("invariants and determinism:")
    tmp = Path(tempfile.mkdtemp(prefix="psa-inv-"))
    vault, plans = build_vault(tmp)
    repo = make_repo(tmp, "unrelated commit")
    reg = registry_for(tmp, repo)
    report, projects = run_audit(vault, reg)

    for ok, label in mod.check_invariants(report):
        check(ok, f"invariant: {label}")

    # The corpus observations are deliberately NOT asserted here. They are true
    # of the live vault, not of any corpus — this fixture vault has two
    # abandoned plans on purpose — and asserting them over synthetic data is
    # how a suite goes red on correct code. What IS asserted is that they
    # report the fixture honestly rather than silently holding.
    obs = dict((lab.split(" —")[0], ok) for ok, lab in mod.check_corpus_observations(report))
    check(not obs["abandoned is 2"],
          "the abandoned observation correctly reports 2 on a corpus that has 2")

    print("  the partition invariant can actually FAIL, not just hold:")
    # Drop one classified entry, exactly as a raising classifier would have.
    broken = json.loads(json.dumps(report))
    broken["classes"]["completed"].pop()
    results = dict((label.split(":")[0], ok) for ok, label in mod.check_invariants(broken))
    check(not results["every enumerated plan got a class"],
          "removing one classified plan makes classified != enumerated")

    print("  two runs over an unchanged vault are byte-identical:")
    a = json.dumps(mod.audit(vault, projects), sort_keys=True)
    b = json.dumps(mod.audit(vault, projects), sort_keys=True)
    check(a == b, "the report carries no timestamp, run id, or set ordering")

    shutil.rmtree(tmp, ignore_errors=True)


def case_default_run_writes_nothing():
    print("report-first — the default run writes NOTHING:")
    tmp = Path(tempfile.mkdtemp(prefix="psa-ro-"))
    vault, plans = build_vault(tmp)
    repo = make_repo(tmp, "Stage 1 green (2026-01-01-done-plan.md)")
    reg = registry_for(tmp, repo)

    before = {f.name: f.read_bytes() for f in sorted(plans.glob("*.md"))}
    r = subprocess.run([sys.executable, str(SCRIPT), "--vault", str(vault),
                        "--registry", str(reg), "--check"],
                       capture_output=True, text=True)
    after = {f.name: f.read_bytes() for f in sorted(plans.glob("*.md"))}
    check(r.returncode == 0,
          f"a default --check run exits 0 even though a corpus OBSERVATION is "
          f"false here — only invariants gate the exit status "
          f"(rc={r.returncode}, {r.stderr[:200]})")
    check("NOTE" in r.stdout and "abandoned is 2" in r.stdout,
          "and the false observation is still surfaced, not swallowed")
    check(before == after, "every plan file is byte-identical after a full default run")
    check(not (plans / ".audit-backups").exists(), "and no backup directory was created")

    print("  --json is machine-readable and carries both gate sets:")
    r2 = subprocess.run([sys.executable, str(SCRIPT), "--vault", str(vault),
                         "--registry", str(reg), "--json"],
                        capture_output=True, text=True)
    data = json.loads(r2.stdout)
    cand = {p["path"] for p in data["candidates"]}
    uncl = {p["path"] for p in data["unclassifiable"]}
    check(not (cand & uncl), "candidates and unclassifiable are disjoint")
    check(bool(uncl), "unclassifiable is non-empty")

    print("  an out-of-contract plan is never a candidate, under any flag:")
    check(not any("out-of-contract" in p for p in cand),
          "the [!] plan reads 1/1 but is withheld — it is really 1/2")

    shutil.rmtree(tmp, ignore_errors=True)


def case_fix_and_restore():
    print("--fix writes only what is confirmed, and --restore undoes it:")
    tmp = Path(tempfile.mkdtemp(prefix="psa-fix-"))
    vault, plans = build_vault(tmp)
    repo = make_repo(tmp, "Stage 1 green (2026-01-01-done-plan.md)")
    reg = registry_for(tmp, repo)
    target = plans / "2026-01-01-done-plan.md"
    original = target.read_bytes()

    print("  declining leaves the file byte-identical:")
    r = subprocess.run([sys.executable, str(SCRIPT), "--vault", str(vault),
                        "--registry", str(reg), "--fix"],
                       input="n\nn\n", capture_output=True, text=True)
    check(target.read_bytes() == original,
          "answering 'n' wrote nothing at all")

    print("  confirming appends the close-out line, with a backup taken first:")
    r = subprocess.run([sys.executable, str(SCRIPT), "--vault", str(vault),
                        "--registry", str(reg), "--fix"],
                       input="y\ny\n", capture_output=True, text=True)
    text = target.read_text()
    check("**Completed:**" in text, "the plan now carries a close-out line")
    check("recorded by plan-status-audit" in text,
          "and it says what recorded it, so a reader can tell it from a human's")
    check("evidence:" in text, "with the evidence inline")
    backups = list(plans.glob(".audit-backups/*/2026-01-01-done-plan.md"))
    check(len(backups) == 1, f"a backup was taken before the write ({backups})")
    check(backups and backups[0].read_bytes() == original,
          "and the backup is the pre-write bytes")

    print("  the newly-completed plan drops out of the candidate set:")
    report, _ = run_audit(vault, reg)
    check(target.name not in {Path(c["path"]).name for c in report["candidates"]},
          "re-running the audit no longer offers it")

    print("  --restore reverts the run wholesale:")
    run_id = backups[0].parent.name
    r = subprocess.run([sys.executable, str(SCRIPT), "--vault", str(vault),
                        "--registry", str(reg), "--restore", run_id],
                       capture_output=True, text=True)
    check(r.returncode == 0, f"restore exits 0 (rc={r.returncode})")
    check(target.read_bytes() == original,
          "the plan file is byte-identical to before the --fix run")

    shutil.rmtree(tmp, ignore_errors=True)


def case_adversarial_writes():
    print("adversarial write paths:")
    tmp = Path(tempfile.mkdtemp(prefix="psa-adv-"))
    vault, plans = build_vault(tmp)
    repo = make_repo(tmp, "Stage 1 green (2026-01-01-done-plan.md)")
    reg = registry_for(tmp, repo)

    print("  a plan that DISAPPEARS between enumeration and write:")
    report, _ = run_audit(vault, reg)
    cand = next(c for c in report["candidates"]
                if Path(c["path"]).name == "2026-01-01-done-plan.md")
    Path(cand["path"]).unlink()
    try:
        mod.record_completion(cand["path"], cand.get("evidence") or [],
                              "run-x", "2026-01-01",
                              cand.get("evidence_strength", "none"))
        check(False, "a vanished plan must not be silently recreated")
    except OSError:
        check(True, "raises rather than recreating a file the user deleted")
    check(not Path(cand["path"]).exists(), "and the file stays gone")

    print("  a READ-ONLY plan file:")
    ro = plans / "2026-01-06-partway-plan.md"
    ro.write_text(task("1.1", "x"), encoding="utf-8")   # make it a candidate
    os.chmod(ro, stat.S_IRUSR)
    try:
        report2, _ = run_audit(vault, reg)
        entry = next(c for c in report2["candidates"] if Path(c["path"]).name == ro.name)
        raised = False
        try:
            mod.record_completion(entry["path"], [], "run-y", "2026-01-01")
        except OSError:
            raised = True
        # Either outcome is acceptable; what is NOT acceptable is a silent
        # no-op reported as a successful write, so assert the file's state
        # matches whichever happened.
        if raised:
            check("**Completed:**" not in ro.read_text(),
                  "a read-only plan is left unmodified when the write raises")
        else:
            check("**Completed:**" in ro.read_text(),
                  "the write reported success and the file really changed")
    finally:
        os.chmod(ro, stat.S_IRUSR | stat.S_IWUSR)

    print("  git evidence is never gathered against the vault:")
    commits, strength, err = mod.git_evidence(str(vault / "Portfolio"),
                                              plans / "x.md", vault)
    check(commits == [] and err and "inside the vault" in err,
          f"a repo path inside the vault is REFUSED, not run ({err})")
    commits2, s2, err2 = mod.git_evidence("", plans / "x.md", vault)
    check(commits2 == [] and err2 and "no registry entry" in err2,
          "an unregistered project says so rather than 'no evidence found'")

    shutil.rmtree(tmp, ignore_errors=True)


def case_evidence_is_graded():
    """Correction 6 — evidence is graded, and a weak grade is never laundered.

    The mechanism Task 4.2 specified (commits naming the plan file) returns
    NOTHING on the live corpus — verified across a representative repo's whole
    history — because the convention is `Stage N green`, which never names a
    plan. So the correlative fallback is what a real run will almost always
    show, which makes "it is labelled honestly" the load-bearing property here,
    not a nicety.
    """
    print("evidence grading (Correction 6):")
    tmp = Path(tempfile.mkdtemp(prefix="psa-ev-"))
    vault, plans = build_vault(tmp)

    print("  a commit naming the plan file grades STRONG:")
    repo = make_repo(tmp, "Stage 1 green (2026-01-01-done-plan.md)")
    commits, strength, err = mod.git_evidence(
        str(repo), plans / "2026-01-01-done-plan.md", vault)
    check(strength == "names-the-plan" and commits,
          f"named -> strong ({strength}, {commits})")
    line = mod.completion_line("2026-02-02", commits, strength)
    check("evidence: " in line and "user-confirmed" not in line,
          f"and the written line cites the commits ({line.strip()})")

    print("  a `Stage N green` commit that names NO plan grades CORRELATIVE:")
    repo2 = make_repo(tmp / "b", "Stage 3 green")
    commits2, strength2, err2 = mod.git_evidence(
        str(repo2), plans / "2026-01-01-done-plan.md", vault)
    check(strength2 == "correlative" and commits2,
          f"unnamed stage commit -> correlative ({strength2}, {commits2})")
    line2 = mod.completion_line("2026-02-02", commits2, strength2)
    check("no commit names this plan" in line2,
          f"and the written line SAYS so ({line2.strip()})")
    check("user-confirmed" in line2,
          "attributing the write to the human, who is what actually justifies it")
    check(not line2.startswith("**Completed:** 2026-02-02 — recorded by "
                              "plan-status-audit; evidence:"),
          "a correlative match is never rendered as a bare `evidence:` list")

    print("  a stage commit dated BEFORE the plan is not correlated to it:")
    # The plan is stamped 2026-01-01; this repo's only commit predates it, so
    # nothing may be attributed to a plan that did not exist yet.
    old = make_repo(tmp / "c", "Stage 9 green")
    subprocess.run(["git", "-C", str(old), "commit", "-q", "--amend", "--no-edit",
                    "--date", "2020-01-01T00:00:00"],
                   env={**os.environ, "GIT_COMMITTER_DATE": "2020-01-01T00:00:00",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e"},
                   check=True, capture_output=True)
    c3, s3, e3 = mod.git_evidence(str(old), plans / "2026-01-01-done-plan.md", vault)
    check(s3 == "none" and not c3,
          f"a pre-dated stage commit is excluded by --since ({s3}, {c3})")

    print("  a master's register naming THIS plan is the strongest signal:")
    # The register is the only source that identifies the plan itself. Fixture
    # mirrors the live shape that prompted it (multitor's backlog-sweep master).
    reg_dir = tmp / "vault2" / "Portfolio" / "a" / "p" / "plans"
    reg_dir.mkdir(parents=True)
    sub = reg_dir / "2026-03-01-topic-sub-01-thing-plan.md"
    sub.write_text(task("1.1", "x"), encoding="utf-8")
    master = reg_dir / "2026-03-01-topic-master-plan.md"
    master.write_text(
        "# Master Plan: topic\n\n## Sub-plans\n\n"
        "### Sub-plan 1: Thing\n"
        "- **Status:** [x] — green 2026-03-02 (commit `deadbee`)\n"
        f"- **Plan:** ./{sub.name}\n\n"
        "### Sub-plan 2: Other\n"
        "- **Status:** [ ]\n"
        "- **Plan:** ./2026-03-01-topic-sub-02-other-plan.md\n", encoding="utf-8")
    other = reg_dir / "2026-03-01-topic-sub-02-other-plan.md"
    other.write_text(task("1.1", "x"), encoding="utf-8")
    sibs = sorted(reg_dir.glob("*.md"))

    note, shas = mod.register_evidence(sub, sibs)
    check(note and "marks it done" in note, f"a done register entry is found ({note})")
    check(shas == ["deadbee"], f"and the commit it names is extracted ({shas})")

    print("  but an entry that is NOT marked done vouches for nothing:")
    note2, shas2 = mod.register_evidence(other, sibs)
    check(note2 is None and shas2 == [],
          f"sub-02's entry is [ ], so the register does not vouch for it ({note2})")

    print("  a named commit that does not resolve is not counted as verified:")
    repo3 = make_repo(tmp / "d", "unrelated work")
    verified = mod.verify_shas(str(repo3), ["deadbee"], vault)
    check(verified == [], f"a bogus sha resolves to nothing ({verified})")
    real = subprocess.run(["git", "-C", str(repo3), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    verified2 = mod.verify_shas(str(repo3), [real], vault)
    check(len(verified2) == 1 and "unrelated work" in verified2[0],
          f"a real one resolves, with its subject ({verified2})")
    check(mod.completion_line("2026-03-03", verified2, "register+commit").count("master register") == 1,
          "and the written line says the register plus the commit backed it")

    print("  with no evidence at all, the line still records who decided:")
    line4 = mod.completion_line("2026-02-02", [], "none")
    check("user-confirmed; no commit evidence found" in line4,
          f"({line4.strip()})")

    shutil.rmtree(tmp, ignore_errors=True)


def case_unregistered_projects_are_covered():
    print("the corpus is the VAULT, not the registry (Correction 5):")
    tmp = Path(tempfile.mkdtemp(prefix="psa-unreg-"))
    vault, plans = build_vault(tmp)
    # A second project that exists in the vault and NOT in the registry — the
    # live shape this correction came from (7 such projects, 39 plan files).
    orphan = vault / "Portfolio" / "otherarea" / "orphan" / "plans"
    orphan.mkdir(parents=True)
    (orphan / "2026-02-01-orphan-plan.md").write_text(task("1.1", "x"), encoding="utf-8")
    repo = make_repo(tmp, "unrelated")
    reg = registry_for(tmp, repo)

    report, _ = run_audit(vault, reg)
    paths = {Path(e["path"]).name for v in report["classes"].values() for e in v}
    check("2026-02-01-orphan-plan.md" in paths,
          "a plan in an UNREGISTERED project is still classified")
    row = [p for p in report["projects"] if p["name"] == "orphan"]
    check(row and row[0]["note"] and "no registry entry" in row[0]["note"],
          f"and its project row says why it has no evidence ({row})")
    orphan_cand = [c for c in report["candidates"]
                   if Path(c["path"]).name == "2026-02-01-orphan-plan.md"]
    check(orphan_cand and orphan_cand[0]["evidence_error"],
          "its candidate carries an evidence ERROR, not an empty evidence list")

    print("  a registered project with no plans/ dir is reported, not skipped:")
    reg2 = tmp / "registry2.yaml"
    reg2.write_text("version: 1\nprojects:\n"
                    f"  - path: {repo}\n    name: demo\n    area: testarea\n    enabled: true\n"
                    f"  - path: {repo}\n    name: ghost\n    area: testarea\n    enabled: true\n",
                    encoding="utf-8")
    report2, _ = run_audit(vault, reg2)
    ghost = [p for p in report2["projects"] if p["name"] == "ghost"]
    check(ghost and ghost[0]["note"] == "no plans/ directory",
          f"'has no plans' and 'was not looked at' render differently ({ghost})")

    shutil.rmtree(tmp, ignore_errors=True)


def main():
    case_classification()
    case_invariants_and_determinism()
    case_default_run_writes_nothing()
    case_fix_and_restore()
    case_adversarial_writes()
    case_evidence_is_graded()
    case_unregistered_projects_are_covered()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
