#!/usr/bin/env python3
"""Mutation battery for the proof tools: plan-flip-audit.py and prove-claim.py.

    python3 planning/skills/executing-plans/tests/battery-proof-tools.py [-j N] [--anchors-only]

Run it at a stage gate after ANY change to either tool — never inside a task.
Deliberately not named `test-*`, so `scripts/run-tests.sh` (DEC-006) does not
discover it.

EXIT CODES. A caller that branches on $? needs these to mean different things,
because the required response to each differs:

    0   every guard independently pinned — nothing survived, nothing skipped
    1   a mutation SURVIVED: that guard is not reachable from any named test
    2   the control suites were already red before mutating; nothing was run
    4   a mutation was SKIPPED because its anchor text is gone. Coverage
        silently shrank; the guard it pinned is now unpinned. Re-anchor it.
    5   a trial ERRORED: it could not run, timed out, the mutation left the
        script unparseable, or the suite went red without reporting a failing
        check. None of those is a kill — a red that measured nothing is the
        failure this battery exists to catch. Fix the entry or the environment.

--anchors-only checks the anchors (exit 0 or 4) and runs nothing — cheap enough
for CI, which runs the suites but not the battery.

WHY IT EXISTS. Both tools are fraud detectors, so their failure mode is silence
— a weakened guard changes no output anyone looks at, and the suite stays green.
In the engineering-skills Cursor port this battery is ported from
(bin/tests/mutate-stage3-audits.py at f777c04) that happened three times: a
suite passed 31/31 with a whole clause deleted; 91/91 with the severity of four
findings unpinned; and 99/101 with two guards masking each other.

Green suites were not evidence in any of those cases. This is.

Each entry weakens ONE guard. A guard is PINNED if the suite goes red; a
SURVIVOR means the suite would stay green with that protection deleted.

EACH MUTATION RUNS IN ITS OWN COPY of this skill directory, never in the
repo. The Cursor original mutated the tracked scripts in place, so it had to
run serially (121 suite runs, ~25 min) and a killed run left a weakened fraud
detector in the working tree — found there twice. A copy per mutation makes
the runs independent: they go out in parallel (-j, default every CPU) and an
interrupted battery leaves nothing behind but temporary directories.
"""
import argparse
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
PY_S, PY_T = "scripts/plan-flip-audit.py", "tests/test-plan-flip-audit.py"
PC_S, PC_T = "scripts/prove-claim.py", "tests/test-prove-claim.py"

M = [
 # (label, target, old, new)
 ('strong tier voids alone -> demoted to advisory', PY_S,
  'return m.group(0), "blocking"',
  'return m.group(0), "advisory"'),
 ('two-signal rule -> one signal is enough', PY_S,
  'if len({h.lower() for h in hits}) >= 2:',
  'if len({h.lower() for h in hits}) >= 1:'),
 ('two-signal rule -> three signals required', PY_S,
  'if len({h.lower() for h in hits}) >= 2:',
  'if len({h.lower() for h in hits}) >= 3:'),
 ('distinct-word rule -> the same word twice counts', PY_S,
  'if len({h.lower() for h in hits}) >= 2:',
  'if len(hits) >= 2:'),
 ('lone undisclosed amendment -> silent again (the round-2 Critical)', PY_S,
  'return hits[0] + " (undisclosed amendment)", "advisory"',
  'pass'),
 ('DISCLOSED escape -> a was-value no longer exempts', PY_S,
  'and not DISCLOSED.search(tail.group(0))',
  'and True'),
 ('exit 2|78 promoted to strong -> back to weak', PY_S,
  'r"\\bexit\\s+(code\\s+)?(2|78)\\b",',
  'r"\\bZZNOMATCHZZ\\b",'),
 ('finding 4 severity inheritance -> always advisory', PY_S,
  'sev = "blocking" if any(d.get("severity") == "blocking" for d in dirty) else "advisory"',
  'sev = "advisory"'),
 ('finding 4 severity inheritance -> always blocking', PY_S,
  'sev = "blocking" if any(d.get("severity") == "blocking" for d in dirty) else "advisory"',
  'sev = "blocking"'),
 ('finding 1 severity -> advisory', PY_S,
  '"finding": 1, "severity": "blocking",',
  '"finding": 1, "severity": "advisory",'),
 ('finding 3 severity -> advisory', PY_S,
  '"finding": 3, "severity": "blocking",',
  '"finding": 3, "severity": "advisory",'),
 ('finding 5 severity -> advisory', PY_S,
  '"finding": 5, "severity": "blocking",',
  '"finding": 5, "severity": "advisory",'),
 ('exit 4 for advisory-only -> collapses back into 1', PY_S,
  '        return 4',
  '        return 1'),
 ('blocking exit 1 -> collapses into 4', PY_S,
  '    if any(f.get("severity") == "blocking" for f in findings):\n        return 1',
  '    if False:\n        return 1'),
 ('NEGATED filter deleted', PY_S,
  'if NEGATED.search(pre) or NEGATED_HYPHEN.search(pre):',
  'if False:'),
 ('COUNTED filter deleted', PY_S,
  'return not COUNTED.search(pre)',
  'return True'),
 ('QUOTED_SPAN masking deleted', PY_S,
  'masked = QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), raw)',
  'masked = raw'),
 ('--vocab-replace guard deleted', PY_S,
  'if args.vocab_replace and not args.vocab_file:',
  'if False:'),
 ('finding 6 severity -> advisory', PY_S,
  '"finding": 6, "severity": "blocking",',
  '"finding": 6, "severity": "advisory",'),
 ('finding 6 ATTESTED escape deleted (a quote no longer clears it)', PY_S,
  'if not m or ATTESTED.search(raw):',
  'if not m:'),
 ('finding 6 start-of-box anchor dropped (prose fires again)', PY_S,
  'r"^(?:\\*\\*\\(judgment\\)\\*\\*\\s*|\\(judgment\\)\\s*|the\\s+)?"',
  'r"(?:\\*\\*\\(judgment\\)\\*\\*\\s*|\\(judgment\\)\\s*|the\\s+)?"'),
 ('finding 6 vocabulary widened to action verbs', PY_S,
  '|sign(?:s|ed)?[\\s-]+off|authori[sz](?:es|ed|ation))\\b",',
  '|sign(?:s|ed)?[\\s-]+off|authori[sz](?:es|ed|ation)|runs|creates)\\b",'),
 ('finding 6 ticked-only guard deleted', PY_S,
  '        if not ticked:\n            continue\n        # A decision phrase inside backticks',
  '        # A decision phrase inside backticks'),
 ('finding 7 severity -> blocking', PY_S,
  '"finding": 7, "severity": "advisory",',
  '"finding": 7, "severity": "blocking",'),
 ('finding 7 historical/amended exemption deleted', PY_S,
  'if v in line and not STALE_EXEMPT.search(line):',
  'if v in line and "was:" not in line:'),
 ('finding 7 identifier filter deleted (words get swept)', PY_S,
  'if len(v) >= 6 and DISTINCTIVE.search(v):',
  'if len(v) >= 6:'),
 ('baseline: second --snapshot no longer refused', PY_S,
  '    if bp.exists():',
  '    if False:'),
 ('baseline: hash check deleted (edited baseline trusted)', PY_S,
  'if hashlib.sha256(text.encode()).hexdigest() != recorded:',
  'if False:'),
 ('baseline: plan-identity check deleted', PY_S,
  'if doc.get("plan") != str(path.resolve()):',
  'if False:'),
 ('baseline: compares the plan with itself (no flips ever)', PY_S,
  'flips = tick_delta(base["text"], text)',
  'flips = tick_delta(text, text)'),
 ('baseline: bulk-flip rule deleted', PY_S,
  'counted = unbacked(flips, text, green_stages(subjects))\n    if len(counted) > threshold and task_commits < threshold:',
  'counted = unbacked(flips, text, green_stages(subjects))\n    if False:'),
 ('baseline: probe rule deleted', PY_S,
  '    if not probed:',
  '    if False:'),
 ('baseline: probe evidence never recognised', PY_S,
  '            probed = True',
  '            probed = False'),
 ('baseline: review rule deleted', PY_S,
  '    if not reviewed:',
  '    if False:'),
 ('baseline: not wired for a plan outside any repo', PY_S,
  'not_run = from_baseline(f"{path.parent}: {err}")',
  'not_run = skip(f"{path.parent}: {err}")'),
 ('finding 8 unproven claims -> advisory', PY_S,
  '            out.append({**base, "severity": "blocking",\n                        "rule": f"Task {tid}: {len(unproven)} of {n} required claim(s)',
  '            out.append({**base, "severity": "advisory",\n                        "rule": f"Task {tid}: {len(unproven)} of {n} required claim(s)'),
 ('finding 8 records ignored', PY_S,
  'unproven = [k for k in required if got.get(("claim", k), ["no record"])]',
  'unproven = list(required)'),
 ('finding 8 legacy branch deleted (lines alone go blocking)', PY_S,
  '        elif not got and muts:',
  '        elif False:'),
 ('finding 8 no-commit branch deleted', PY_S,
  '        if commits == 0 and not got:',
  '        if False:'),
 ('finding 8 claim counting collapsed to one', PY_S,
  '    claims = claim_clauses(test)\n    return [k for k, c in enumerate(claims, 1)',
  '    claims = claim_clauses(test)[:1]\n    return [k for k, c in enumerate(claims, 1)'),
 ('finding 8 ticked-only filter dropped', PY_S,
  'return [(t["id"], t["line"], t["test"]) for t in out if t["line"]]',
  'return [(t["id"], t["line"] or 0, t["test"]) for t in out]'),
 ('finding 8 runs on an implicit repo', PY_S,
  '    if args.repo:',
  '    if True:'),
 ('finding 9 unmet requirements -> blocking (upstream: advisory, never blocking)', PY_S,
  '            why = "; ".join(f"requirement {k}: {p}" for k, p in open_[:4])\n            out.append({**base, "severity": "advisory",',
  '            why = "; ".join(f"requirement {k}: {p}" for k, p in open_[:4])\n            out.append({**base, "severity": "blocking",'),
 ('finding 9 deviations not reported', PY_S,
  '        elif devs:',
  '        elif False:'),
 ('finding 9 legacy branch deleted', PY_S,
  '        if open_ and not got and reqs:',
  '        if False:'),
 ('finding 9 clause counting collapsed to one', PY_S,
  'return len(requirement_clauses(desc))',
  'return 1'),
 ('finding 9 code spans no longer masked', PY_S,
  'return QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), text)',
  'return text'),
 ('finding 9 deviation: no longer counts', PY_S,
  'REQ_LINE = re.compile(r"^\\s*(req|deviation)\\s*:\\s*\\S", re.I | re.M)',
  'REQ_LINE = re.compile(r"^\\s*(req)\\s*:\\s*\\S", re.I | re.M)'),
 ('finding 9 duplicates finding 8 on a task with no commit', PY_S,
  '        if n == 0 or (commits == 0 and not got):',
  '        if n == 0:'),
 ('finding 9 not wired to --repo', PY_S,
  'f9 = scan_task_requirements(path, text, Path(top8.strip())) if has_head else None',
  'f9 = []'),
 ('prove: green under the break is recorded', PC_S,
  '    if red_rc == 0:\n        raise Refused("the test still PASSES',
  '    if False:\n        raise Refused("the test still PASSES'),
 ('prove: baseline run no longer required to pass', PC_S,
  '    if base_rc != 0:',
  '    if False:'),
 ('prove: a break may touch a test file', PC_S,
  '        if TEST_PATH.search(p):\n            raise Refused',
  '        if False:\n            raise Refused'),
 ('prove: a break that stops the build is accepted', PC_S,
  '            if b_rc != 0:\n                raise Refused(f"the code does not build with',
  '            if False:\n                raise Refused(f"the code does not build with'),
 ('prove: no build step and no reason is accepted', PC_S,
  '    if not build and not no_build:',
  '    if False:'),
 ('prove: restore not verified', PC_S,
  '        if bad:\n            raise RestoreFailed("could not restore',
  '        if False:\n            raise RestoreFailed("could not restore'),
 ('prove: restored file no newer than the broken write (stale builds)', PC_S,
  '        t = max(time.time_ns(), broke + 10**9)',
  '        t = broke'),
 ('prove: test runs write .pyc again', PC_S,
  'env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}',
  'env = dict(os.environ)'),
 ('prove: unstaged change outside proof/ accepted', PC_S,
  '    if diff:\n        raise Refused',
  '    if False:\n        raise Refused'),
 ('prove: untracked file outside proof/ accepted', PC_S,
  '    if untracked:\n        raise Refused',
  '    if False:\n        raise Refused'),
 ('prove: claim/requirement number not range-checked', PC_S,
  '    if index < 1 or index > len(items):',
  '    if False:'),
 ("prove: --test not bound to the plan's Test field", PC_S,
  '    require_planned_test(test, block["test"], task)',
  '    pass'),
 ('prove: a trivial --build accepted', PC_S,
  '    if build is not None and build.strip() in TRIVIAL_BUILD:',
  '    if False:'),
 ('prove: rename / new file / mode-change breaks accepted', PC_S,
  '        if line.startswith(("rename", "copy", "create", "delete", "mode change")):',
  '        if False:'),
 ('prove: patch paths read C-quoted (no -z)', PC_S,
  '"apply", "--numstat", "-z",',
  '"apply", "--numstat",'),
 ('prove: assume-unchanged / skip-worktree accepted', PC_S,
  '    if flags:\n        raise Refused',
  '    if False:\n        raise Refused'),
 ('prove: non-record files allowed under proof/', PC_S,
  '    if stray:\n        raise Refused',
  '    if False:\n        raise Refused'),
 ('prove: no cleanliness check after the run', PC_S,
  '        require_clean(repo)\n        after = index_fingerprint(repo)',
  '        after = index_fingerprint(repo)'),
 ("prove: interrupted run's journal not recovered", PC_S,
  '    recover_if_needed(repo)',
  '    pass'),
 ('prove: timeout kills only the shell', PC_S,
  '        os.killpg(p.pid, signal.SIGKILL)',
  '        p.kill()'),
 ('req: a trivial --check accepted', PC_S,
  '        if not check or check.strip() in TRIVIAL_BUILD:',
  '        if False:'),
 ('req: covered-by-claim not validated', PC_S,
  '        if problems:\n            raise Refused(f"claim {covered_by}',
  '        if False:\n            raise Refused(f"claim {covered_by}'),
 ('deviation: no reason required', PC_S,
  '    if not why or len(why.strip()) < 10:',
  '    if False:'),
 ('replay: only re-reads the JSON', PC_S,
  '        if not problems:\n            fd, tmp = tempfile.mkstemp',
  '        if False:\n            fd, tmp = tempfile.mkstemp'),
 ('validate: fingerprint not compared', PC_S,
  '    elif fingerprint and fpr != fingerprint:',
  '    elif False:'),
 ('validate: record path (task/index) not compared', PC_S,
  '        if rec.get("task") != etask or rec.get("index") != eindex:',
  '        if False:'),
 ('validate: plan wording not compared', PC_S,
  '        if etext is not None and rec.get("text") != etext:',
  '        if False:'),
 ('validate: kind not compared to the path', PC_S,
  '        if kind != ekind:',
  '        if False:'),
 ('validate: booleans pass as exit codes', PC_S,
  '    return type(x) is int',
  '    return isinstance(x, int)'),
 ('notes stripped without a history mark', PY_S,
  '        if HISTORY_MARK.search(m.group(0)):',
  '        if True:'),
 ('notes matched on unmasked text (code spans stripped)', PY_S,
  '    for m in ANNOTATION.finditer(masked):',
  '    for m in ANNOTATION.finditer(text):'),
 ('records: commit binding not checked', PY_S,
  'problems = pc.validate(rec, fps[sha], (kind, task, k, text), allow_legacy=True)',
  'problems = pc.validate(rec, None, (kind, task, k, text), allow_legacy=True)'),
 ('records: path and wording not checked', PY_S,
  'problems = pc.validate(rec, fps[sha], (kind, task, k, text), allow_legacy=True)',
  'problems = pc.validate(rec, fps[sha], allow_legacy=True)'),
 ('finding 9 req records ignored', PY_S,
  '            if req == []:\n                if got.get(("legacy", k)):',
  '            if False:\n                if got.get(("legacy", k)):'),
 ('finding 1: no task credited for its records', PY_S,
  '    return {t for t, got in recs.items() if t in blocks',
  '    return set() and {t for t, got in recs.items() if t in blocks'),
 ('finding 1: naming tasks buys credit', PY_S,
  '    task_commits = max(task_commits, len(task_numbers(task_ids) & proven_tasks(repo, path)))\n',
  '    task_commits = max(task_commits, len(task_numbers(task_ids)))\n'),
 ('audit: legacy req checks blocking', PY_S,
  'problems = pc.validate(rec, fps[sha], (kind, task, k, text), allow_legacy=True)',
  'problems = pc.validate(rec, fps[sha], (kind, task, k, text))'),
 ('audit: legacy req checks not reported', PY_S,
  '        if not open_ and legacy:',
  '        if False:'),
 ('audit: covered-by citation not followed', PY_S,
  '            if req == [] and cites is not None and (',
  '            if False and cites is not None and ('),
 ('audit: stray files under proof/ allowed', PY_S,
  '    if stray:\n        out.append(',
  '    if False:\n        out.append('),
 ('prove: exit 126/127 counted as red', PC_S,
  '    if red_rc in (126, 127) or red_rc < 0 or red_rc >= 128:',
  '    if red_rc < 0 or red_rc >= 128:'),
 ('prove: killed (128+n) counted as red', PC_S,
  '    if red_rc in (126, 127) or red_rc < 0 or red_rc >= 128:',
  '    if red_rc in (126, 127) or red_rc < 0:'),
 ('validate: red exit 0 accepted', PC_S,
  '    if not _is_int(red) or red == 0 or red in (126, 127) or red < 0 or red >= 128:',
  '    if False:'),
 ('validate: a bare schema-2 req check accepted', PC_S,
  '            _check_run(rec, p, "check")\n',
  '            pass\n'),
 ('validate: legacy accepted at commit', PC_S,
  '    legacy = allow_legacy and is_legacy(rec)',
  '    legacy = is_legacy(rec)'),
 ('req: --check without --break accepted', PC_S,
  '        if not brk:\n            raise Usage',
  '        if False:\n            raise Usage'),
 ('req: the check is never run', PC_S,
  '        seen = observe(repo, brk, check, build, no_build, timeout, text)\n',
  '        seen = {"baseline": {"exit": 0, "tail": ""}, "red": {"exit": 1, "tail": ""}}\n'),
 ('prove: recovery overwrites a moved repo', PC_S,
  '    if now_head != head or now_blobs != blobs:',
  '    if False:'),
 ('prove: runs not exclusive', PC_S,
  '    held = lock(repo)  # noqa: F841',
  '    held = None  # noqa: F841'),
 ('prove: unparseable break counted (no build step)', PC_S,
  '            broken = unparseable(repo, paths)\n',
  '            broken = []\n'),
 ('prove: the test runner may be broken', PC_S,
  '        if os.path.normpath(p) in runs:',
  '        if False:'),
 ('prove: wider test trees not recognised', PC_S,
  '    r"|(^|/)[A-Za-z]*Test/"',
  '    r""'),
 ('subject_tasks: 1.10 read as 1.1', PY_S,
  '            out.add(cur.group(0))',
  '            out.add(cur.group(0)[:3])'),
 ('subject_tasks: case-sensitive again', PY_S,
  '    r"(?:tasks?\\b\\s*[:#-]?\\s*)?\\d+\\.\\d+)*)", re.I)',
  '    r"(?:tasks?\\b\\s*[:#-]?\\s*)?\\d+\\.\\d+)*)")'),
 ('subject_tasks: ranges not expanded', PY_S,
  '                out.update(f"{a_major}.{n}" for n in range(a_minor + 1, b_minor))',
  '                pass'),
 ('subject_tasks: lists read as their first task', PY_S,
  '        for i, cur in enumerate(ids):',
  '        for i, cur in enumerate(ids[:1]):'),
 ('validate: a non-dict run field crashes it', PC_S,
  '    return v.get("exit") if isinstance(v, dict) else None',
  '    return v.get("exit")'),
 ('audit: legacy has no cutoff', PY_S,
  '                if added is None or added >= datetime.datetime.fromisoformat(LEGACY_CUTOFF):',
  '                if False:'),
 ('finding 1: one proven claim credits a task', PY_S,
  '            and all(got.get(("claim", k)) == [] for k in required_claims(blocks[t]["test"]))}',
  '            and any(got.get(("claim", k)) == [] for k in required_claims(blocks[t]["test"]))}'),
 ('required claims: the first claim not required', PY_S,
  'if k == 1 or NAMED_BREAK.search(_masked(c))]',
  'if NAMED_BREAK.search(_masked(c))]'),
 ('required claims: named breaks not required', PY_S,
  'if k == 1 or NAMED_BREAK.search(_masked(c))]',
  'if k == 1]'),
 ('required claims: every claim required', PY_S,
  'if k == 1 or NAMED_BREAK.search(_masked(c))]',
  'if k == 1 or True]'),
 ('claim deviation counted as proof', PY_S,
  '                problems = ["recorded as a claim deviation"]',
  '                problems = []'),
 ('claim deviation not reported', PY_S,
  '        if devs:\n',
  '        if False:\n'),
 ('claim deviation: reason not required (audit)', PY_S,
  'len(rec["why"].strip()) < 10:\n        p.append("a claim deviation without a reason")',
  'len(rec["why"].strip()) < 0:\n        p.append("a claim deviation without a reason")'),
 ('claim deviation: task/index not compared', PY_S,
  '    if rec.get("task") != task or rec.get("index") != k:',
  '    if False:'),
 ('claim deviation: wording not compared', PY_S,
  '        p.append("recorded against different wording than the plan now has")',
  '        pass'),
 ('claim deviation: fingerprint not compared', PY_S,
  '        p.append("recorded on a different tree than this one")',
  '        pass'),
 ('deviation --claim records requirement wording', PC_S,
  '        text = pick(PFA.claim_clauses(block["test"]), index, "claim")',
  '        text = pick(PFA.requirement_clauses(block["desc"]), index, "claim")'),
 ('validate(): claim deviation not delegated to the audit', PC_S,
  '    if kind == "claim-deviation" and (not expect or expect[0] == "claim"):',
  '    if False:'),
 ('req: covered-by accepts a claim deviation as proof', PC_S,
  '        if not problems and crec.get("kind") != "claim":',
  '        if False:'),
 ('finding 1: gate boxes always counted (a gate ticked with its green commit is a bulk flip)', PY_S,
  '    return [e for e in entries if gates.get(e[2]) not in green]',
  '    return list(entries)'),
 ('finding 1: gate boxes backed without a Stage N green commit', PY_S,
  '    return [e for e in entries if gates.get(e[2]) not in green]',
  '    return [e for e in entries if gates.get(e[2]) is None]'),
 ('replay: a claim deviation counted as a failed replay', PC_S,
  '        if isinstance(rec, dict) and rec.get("kind") == "claim-deviation":',
  '        if False:'),
]


def suites_for(target):
    return {PY_S: [PY_T], PC_S: [PC_T]}[target]


SUITE_TIMEOUT = 900   # seconds; the slowest suite takes ~20 s alone


def run(root, suite):
    """(exit code, stdout) of one suite run; exit None on a timeout."""
    try:
        r = subprocess.run([sys.executable, str(root / suite)], capture_output=True,
                           text=True, timeout=SUITE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, ""
    return r.returncode, r.stdout


def copy_skill():
    """A private copy of the skill directory; the suites find the scripts beside them."""
    d = Path(tempfile.mkdtemp(prefix="battery-proof-tools-"))
    shutil.copytree(SKILL, d / "skill", ignore=shutil.ignore_patterns("__pycache__"))
    return d


def trial(entry):
    """(label, verdict) for one mutation, run in its own copy.

    killed: a suite reported a failing check (`  FAIL` on stdout, both suites'
    marker). SURVIVED: every suite passed. ERROR: anything else — never counted
    as a kill. Exceptions are caught here, so a worker's crash cannot escape as
    Python's exit 1, which this file defines as "survived".
    """
    label, target, old, new = entry
    d = None
    try:
        d = copy_skill()
        f = d / "skill" / target
        f.write_text(f.read_text().replace(old, new))
        try:
            py_compile.compile(str(f), cfile=str(d / "check.pyc"), doraise=True)
        except py_compile.PyCompileError:
            return label, "ERROR", "the mutation leaves the script unparseable"
        for s in suites_for(target):
            rc, out = run(d / "skill", s)
            if rc is None:
                return label, "ERROR", f"{s} timed out after {SUITE_TIMEOUT}s"
            if rc != 0:
                if "  FAIL" in out:
                    return label, "killed", ""
                return label, "ERROR", f"{s} exited {rc} without reporting a failing check"
        return label, "SURVIVED", ""
    except Exception as e:  # noqa: BLE001
        return label, "ERROR", f"{e.__class__.__name__}: {e}"
    finally:
        if d is not None:
            shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--anchors-only", action="store_true",
                    help="check every anchor still matches, run nothing")
    args = ap.parse_args()
    jobs = max(1, args.jobs)

    # Every anchor is checked BEFORE anything runs. A missing one is the exit-4
    # outcome anyway; finding it first costs a second rather than a battery.
    # An anchor at several sites is mutated at ALL of them: a guard emitted in
    # two places is only pinned if BOTH are covered.
    gone = [label for label, target, old, _new in M if (SKILL / target).read_text().count(old) == 0]
    if gone:
        for label in gone:
            print(f"  SKIP     {label}  (anchor missing)")
        sys.stderr.write(f"\n{len(gone)} mutation(s) SKIPPED — anchors gone, those guards are "
                         "no longer pinned. Re-anchor them. Nothing was mutated.\n")
        return 4
    if args.anchors_only:
        print(f"anchors: all {len(M)} present")
        return 0

    print("control: suites must be green before mutating")
    d = copy_skill()
    try:
        red = [s for s in (PY_T, PC_T) if run(d / "skill", s)[0] != 0]
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if red:
        print(f"  ABORT — {', '.join(red)} already red")
        return 2
    print(f"  ok\n\nrunning {len(M)} mutations, {jobs} at a time")

    counts = {"killed": 0, "SURVIVED": 0, "ERROR": 0}
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for label, verdict, why in pool.map(trial, M):
            print(f"  {verdict:<8} {label}" + (f"  ({why})" if why else ""), flush=True)
            counts[verdict] += 1
    print(f"\nkilled {counts['killed']}  survived {counts['SURVIVED']}  "
          f"errors {counts['ERROR']}  skipped 0")
    if counts["SURVIVED"]:
        return 1
    return 5 if counts["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
