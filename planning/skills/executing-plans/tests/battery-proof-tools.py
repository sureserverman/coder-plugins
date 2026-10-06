#!/usr/bin/env python3
"""Mutation battery for the proof tools: plan-flip-audit.py and prove-claim.py,
and the opt-in commit gate: hooks/git-ref-gate.sh, hooks/proof-guard.sh and
proof-hooks-install.py.

    python3 planning/skills/executing-plans/tests/battery-proof-tools.py [-j N] [--anchors-only]

Run it at a stage gate after ANY change to one of them — never inside a task.
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

    6   a mutation was MISNAMED: a check other than the one its entry names
        killed it. The guard is pinned, but not by the check the entry says —
        the name is wrong, or the named check stopped covering it. Fix the
        name after reading which check it was. (Precedence: 1, then 5, then 6.)
        A MISNAMED trial is re-run once, alone; one its named check kills on the
        re-run is UNSTABLE — printed, with the stray failure's detail, and
        counted apart: it changes no exit code.

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

EACH MUTATION RUNS IN ITS OWN COPY of the plugin's executing-plans skill and
hooks directory (the layout the scripts find each other by), never in the
repo. The Cursor original mutated the tracked scripts in place, so it had to
run serially (121 suite runs, ~25 min) and a killed run left a weakened fraud
detector in the working tree — found there twice. A copy per mutation makes
the runs independent: they go out in parallel (-j, default every CPU) and an
interrupted battery leaves nothing behind but temporary directories.

EACH SUITE RUNS FAIL-FAST (SUITE_FAIL_FAST=1): a kill needs only the first failing
check, and that first check must be the one the entry names.

COST, measured so a change to it is visible. Before fail-fast (gate-executor-discipline
Task 4.1, 2026-10-06, 16 CPUs, -j 16): 173 mutations, every suite run to its end —
6m33s wall, 43m16s user. With fail-fast and named killers (Task 4.3, same machine, same
day): 3m58s wall, 24m17s user — 173 killed, 0 misnamed.
"""
import argparse
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]   # planning/
EP = "skills/executing-plans"
PY_S, PY_T = f"{EP}/scripts/plan-flip-audit.py", f"{EP}/tests/test-plan-flip-audit.py"
PC_S, PC_T = f"{EP}/scripts/prove-claim.py", f"{EP}/tests/test-prove-claim.py"
PI_S = f"{EP}/scripts/proof-hooks-install.py"
GR_S, GR_T = "hooks/git-ref-gate.sh", "hooks/tests/test-git-ref-gate.sh"
PG_S, PG_T = "hooks/proof-guard.sh", "hooks/tests/test-proof-guard.sh"
SUITES = [PY_T, PC_T, GR_T, PG_T]

M = [
 # (label, target, old, new, killer) — `killer` is a substring of the `  FAIL` label of the
 # check meant to kill the mutation; ` | ` separates alternatives, for a guard two checks cover
 # whose first failure varies with machine load (measured: three entries under -j 16). Seeded 2026-10-06 (Task 4.3) from each mutation's first
 # FAIL under SUITE_FAIL_FAST=1, cut before run-specific tails such as `(rc=0)`; a different
 # check killing it later is reported MISNAMED, so the name is reviewed, not silently moved.
 ('strong tier voids alone -> demoted to advisory', PY_S,
  'return m.group(0), "blocking"',
  'return m.group(0), "advisory"',
  'expected exit 1'),
 ('two-signal rule -> one signal is enough', PY_S,
  'if len({h.lower() for h in hits}) >= 2:',
  'if len({h.lower() for h in hits}) >= 1:',
  "'amended' fired from prose — the measured FP driver is back"),
 ('two-signal rule -> three signals required', PY_S,
  'if len({h.lower() for h in hits}) >= 2:',
  'if len({h.lower() for h in hits}) >= 3:',
  'the >=2 threshold is unpinned — it is masked by the parenthetical rule'),
 ('distinct-word rule -> the same word twice counts', PY_S,
  'if len({h.lower() for h in hits}) >= 2:',
  'if len(hits) >= 2:',
  'M3 SURVIVES: duplicate words counted as independent signals'),
 ('lone undisclosed amendment -> silent again (the round-2 Critical)', PY_S,
  'return hits[0] + " (undisclosed amendment)", "advisory"',
  'pass',
  "--vocab-file extension wrong: lines [5, 6] sev {5: 'blocking', 6: 'blocking'}"),
 ('DISCLOSED escape -> a was-value no longer exempts', PY_S,
  'and not DISCLOSED.search(tail.group(0))',
  'and True',
  'the amendment protocol itself fires — the measured 44% FP driver'),
 ('exit 2|78 promoted to strong -> back to weak', PY_S,
  'r"\\bexit\\s+(code\\s+)?(2|78)\\b",',
  'r"\\bZZNOMATCHZZ\\b",',
  "'amended — exit 2' should be blocking — this is the incident record's own fake"),
 ('finding 4 severity inheritance -> always advisory', PY_S,
  'sev = "blocking" if any(d.get("severity") == "blocking" for d in dirty) else "advisory"',
  'sev = "advisory"',
  'M7 SURVIVES: **Completed:** over a blocking gate line is not blocking'),
 ('finding 4 severity inheritance -> always blocking', PY_S,
  'sev = "blocking" if any(d.get("severity") == "blocking" for d in dirty) else "advisory"',
  'sev = "blocking"',
  "M8 SURVIVES: finding 4 ignores its evidence's severity"),
 ('finding 1 severity -> advisory', PY_S,
  '"finding": 1, "severity": "blocking",',
  '"finding": 1, "severity": "advisory",',
  'expected exit 1'),
 ('finding 3 severity -> advisory', PY_S,
  '"finding": 3, "severity": "blocking",',
  '"finding": 3, "severity": "advisory",',
  'M10 SURVIVES: finding 3 severity unpinned'),
 ('finding 5 severity -> advisory', PY_S,
  '"finding": 5, "severity": "blocking",',
  '"finding": 5, "severity": "advisory",',
  'M11 SURVIVES: finding 5 severity unpinned'),
 ('exit 4 for advisory-only -> collapses back into 1', PY_S,
  '        return 4',
  '        return 1',
  'advisory-only exited 1, expected 4'),
 ('blocking exit 1 -> collapses into 4', PY_S,
  '    if any(f.get("severity") == "blocking" for f in findings):\n        return 1',
  '    if False:\n        return 1',
  'expected exit 1'),
 ('NEGATED filter deleted', PY_S,
  'if NEGATED.search(pre) or NEGATED_HYPHEN.search(pre):',
  'if False:',
  'M14 SURVIVES: the NEGATED guard is unreachable from its fixture'),
 ('COUNTED filter deleted', PY_S,
  'return not COUNTED.search(pre)',
  'return True',
  'M15 SURVIVES: the COUNTED guard is unreachable from its fixture'),
 ('QUOTED_SPAN masking deleted', PY_S,
  'masked = QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), raw)',
  'masked = raw',
  'I-4 REGRESSION: 1 false positive(s) on honest prose'),
 ('--vocab-replace guard deleted', PY_S,
  'if args.vocab_replace and not args.vocab_file:',
  'if False:',
  '--vocab-replace alone exited 0, expected 2'),
 ('finding 6 severity -> advisory', PY_S,
  '"finding": 6, "severity": "blocking",',
  '"finding": 6, "severity": "advisory",',
  'unquoted owner decision must be a blocking finding 6'),
 ('finding 6 ATTESTED escape deleted (a quote no longer clears it)', PY_S,
  'if not m or ATTESTED.search(raw):',
  'if not m:',
  'a quoted owner attestation must clear finding 6'),
 ('finding 6 start-of-box anchor dropped (prose fires again)', PY_S,
  'r"^(?:\\*\\*\\(judgment\\)\\*\\*\\s*|\\(judgment\\)\\s*|the\\s+)?"',
  'r"(?:\\*\\*\\(judgment\\)\\*\\*\\s*|\\(judgment\\)\\s*|the\\s+)?"',
  'finding 6 must anchor to the start of the box'),
 ('finding 6 vocabulary widened to action verbs', PY_S,
  '|sign(?:s|ed)?[\\s-]+off|authori[sz](?:es|ed|ation))\\b",',
  '|sign(?:s|ed)?[\\s-]+off|authori[sz](?:es|ed|ation)|runs|creates)\\b",',
  'owner ACTIONS must not need a quote'),
 ('finding 6 ticked-only guard deleted', PY_S,
  '        if not ticked:\n            continue\n        # A decision phrase inside backticks',
  '        # A decision phrase inside backticks',
  'an unticked box must not be finding 6'),
 ('finding 7 severity -> blocking', PY_S,
  '"finding": 7, "severity": "advisory",',
  '"finding": 7, "severity": "blocking",',
  'finding 7 must be advisory with exit 4'),
 ('finding 7 historical/amended exemption deleted', PY_S,
  'if v in line and not STALE_EXEMPT.search(line):',
  'if v in line and "was:" not in line:',
  'a historical mention must clear finding 7'),
 ('finding 7 identifier filter deleted (words get swept)', PY_S,
  'if len(v) >= 6 and DISTINCTIVE.search(v):',
  'if len(v) >= 6:',
  'only identifier-like was-values may be swept'),
 ('baseline: second --snapshot no longer refused', PY_S,
  '    if bp.exists():',
  '    if False:',
  'second --snapshot must exit 2'),
 ('baseline: hash check deleted (edited baseline trusted)', PY_S,
  'if hashlib.sha256(text.encode()).hexdigest() != recorded:',
  'if False:',
  'tampered baseline must exit 2'),
 ('baseline: plan-identity check deleted', PY_S,
  'if doc.get("plan") != str(path.resolve()):',
  'if False:',
  'foreign baseline must exit 2'),
 ('baseline: compares the plan with itself (no flips ever)', PY_S,
  'flips = tick_delta(base["text"], text)',
  'flips = tick_delta(text, text)',
  'expected findings 1, 3, 5 and exit 1; got [8]'),
 # Re-anchored 2026-10-06 (gate-executor-discipline Task 4.1): unbacked() gained its probed
 # and cap arguments, and the rule is emitted at two sites (the plan-wide count and the
 # per-commit scan); the shared condition is the anchor, so both are mutated.
 ('baseline: bulk-flip rule deleted', PY_S,
  'if len(counted) > threshold and task_commits < threshold:',
  'if False:',
  'expected findings 1, 3, 5 and exit 1; got [3, 5, 8]'),
 ('baseline: probe rule deleted', PY_S,
  '    if not probed:',
  '    if False:',
  'finding 3 NOT flagged'),
 ('baseline: probe evidence never recognised', PY_S,
  '            probed = True',
  '            probed = False',
  'honest run must be clean'),
 ('baseline: review rule deleted', PY_S,
  '    if not reviewed:',
  '    if False:',
  'expected findings 1, 3, 5 and exit 1; got [1, 3, 8]'),
 ('baseline: not wired for a plan outside any repo', PY_S,
  'not_run = from_baseline(f"{path.parent}: {err}")',
  'not_run = skip(f"{path.parent}: {err}")',
  'no baseline must leave 1/3/5 not run, pointing at --snapshot'),
 ('finding 8 unproven claims -> advisory', PY_S,
  '            out.append({**base, "severity": "blocking",\n                        "rule": f"Task {tid}: {len(unproven)} of {n} required claim(s)',
  '            out.append({**base, "severity": "advisory",\n                        "rule": f"Task {tid}: {len(unproven)} of {n} required claim(s)',
  'a stale record must be blocking (red if the binding is not checked)'),
 ('finding 8 records ignored', PY_S,
  'unproven = [k for k in required if got.get(("claim", k), ["no record"])]',
  'unproven = list(required)',
  'valid committed records must satisfy 8 and 9 (red if records are not read)'),
 ('finding 8 legacy branch deleted (lines alone go blocking)', PY_S,
  '        elif not got and muts:',
  '        elif False:',
  'honest run must be clean'),
 ('finding 8 no-commit branch deleted', PY_S,
  '        if commits == 0 and not got:',
  '        if False:',
  'no-commit must be one advisory, from finding 8'),
 ('finding 8 claim counting collapsed to one', PY_S,
  '    claims = claim_clauses(test)\n    return [k for k, c in enumerate(claims, 1)',
  '    claims = claim_clauses(test)[:1]\n    return [k for k, c in enumerate(claims, 1)',
  'credit needs every claim (red if one record credits a task)'),
 ('finding 8 ticked-only filter dropped', PY_S,
  'return [(t["id"], t["line"], t["test"]) for t in out if t["line"]]',
  'return [(t["id"], t["line"] or 0, t["test"]) for t in out]',
  'unticked tasks must be skipped'),
 ('finding 8 runs on an implicit repo', PY_S,
  '    if args.repo:',
  '    if True:',
  'clean history produced findings'),
 ('finding 9 unmet requirements -> blocking (upstream: advisory, never blocking)', PY_S,
  '            why = "; ".join(f"requirement {k}: {p}" for k, p in open_[:4])\n            out.append({**base, "severity": "advisory",',
  '            why = "; ".join(f"requirement {k}: {p}" for k, p in open_[:4])\n            out.append({**base, "severity": "blocking",',
  "schema-2 bare req check must be advisory 'not shown met' (red if legacy has no cutoff)"),
 ('finding 9 deviations not reported', PY_S,
  '        elif devs:',
  '        elif False:',
  'a deviation must be advisory'),
 ('finding 9 legacy branch deleted', PY_S,
  '        if open_ and not got and reqs:',
  '        if False:',
  'lines alone must be legacy advisories (red if lines still count as proof)'),
 ('finding 9 clause counting collapsed to one', PY_S,
  'return len(requirement_clauses(desc))',
  'return 1',
  'honest run must be clean'),
 ('finding 9 code spans no longer masked', PY_S,
  'return QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), text)',
  'return text',
  'code spans must not be stripped as notes'),
 ('finding 9 deviation: no longer counts', PY_S,
  'REQ_LINE = re.compile(r"^\\s*(req|deviation)\\s*:\\s*\\S", re.I | re.M)',
  'REQ_LINE = re.compile(r"^\\s*(req)\\s*:\\s*\\S", re.I | re.M)',
  'deviation lines must count as legacy evidence'),
 ('finding 9 duplicates finding 8 on a task with no commit', PY_S,
  '        if n == 0 or (commits == 0 and not got):',
  '        if n == 0:',
  'no-commit must be one advisory, from finding 8'),
 ('finding 9 not wired to --repo', PY_S,
  'f9 = scan_task_requirements(path, text, Path(top8.strip())) if has_head else None',
  'f9 = []',
  'no baseline must leave 1/3/5 not run, pointing at --snapshot'),
 ('prove: green under the break is recorded', PC_S,
  '    if red_rc == 0:\n        raise Refused("the test still PASSES',
  '    if False:\n        raise Refused("the test still PASSES',
  'a green-under-break run must be refused'),
 ('prove: baseline run no longer required to pass', PC_S,
  '    if base_rc != 0:',
  '    if False:',
  'a failing baseline must be refused'),
 ('prove: a break may touch a test file', PC_S,
  '        if TEST_PATH.search(p):\n            raise Refused',
  '        if False:\n            raise Refused',
  'breaking the test must be refused'),
 ('prove: a break that stops the build is accepted', PC_S,
  '            if b_rc != 0:\n                raise Refused(f"the code does not build with',
  '            if False:\n                raise Refused(f"the code does not build with',
  'a non-building break must be refused'),
 ('prove: no build step and no reason is accepted', PC_S,
  '    if not build and not no_build:',
  '    if False:',
  'missing build step must exit 2'),
 ('prove: restore not verified', PC_S,
  '        if bad:\n            raise RestoreFailed("could not restore',
  '        if False:\n            raise RestoreFailed("could not restore',
  'journal recovery must restore and stop'),
 ('prove: restored file no newer than the broken write (stale builds)', PC_S,
  '        t = max(time.time_ns(), broke + 10**9)',
  '        t = broke',
  'the restore must leave the source newer than the broken build, exits 0/1'),
 ('prove: test runs write .pyc again', PC_S,
  'env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}',
  'env = dict(os.environ)',
  'a real proof must be recorded | test runs must not write .pyc'),
 ('prove: unstaged change outside proof/ accepted', PC_S,
  '    if diff:\n        raise Refused',
  '    if False:\n        raise Refused',
  'a dirty tree must be refused'),
 ('prove: untracked file outside proof/ accepted', PC_S,
  '    if untracked:\n        raise Refused',
  '    if False:\n        raise Refused',
  'untracked files must be refused'),
 ('prove: claim/requirement number not range-checked', PC_S,
  '    if index < 1 or index > len(items):',
  '    if False:',
  'out-of-range claim must exit 2'),
 ("prove: --test not bound to the plan's Test field", PC_S,
  '    require_planned_test(test, block["test"], task)',
  '    pass',
  'a free-form --test must be refused'),
 ('prove: a trivial --build accepted', PC_S,
  '    if build is not None and build.strip() in TRIVIAL_BUILD:',
  '    if False:',
  'a trivial build must be refused'),
 ('prove: rename / new file / mode-change breaks accepted', PC_S,
  '        if line.startswith(("rename", "copy", "create", "delete", "mode change")):',
  '        if False:',
  'a rename must be refused'),
 ('prove: patch paths read C-quoted (no -z)', PC_S,
  '"apply", "--numstat", "-z",',
  '"apply", "--numstat",',
  'a real proof must be recorded'),
 ('prove: assume-unchanged / skip-worktree accepted', PC_S,
  '    if flags:\n        raise Refused',
  '    if False:\n        raise Refused',
  'index flags must be refused'),
 ('prove: non-record files allowed under proof/', PC_S,
  '    if stray:\n        raise Refused',
  '    if False:\n        raise Refused',
  'proof/ must hold records only'),
 ('prove: no cleanliness check after the run', PC_S,
  '        require_clean(repo)\n        after = index_fingerprint(repo)',
  '        after = index_fingerprint(repo)',
  'a changed tree after the proof must exit 3'),
 ("prove: interrupted run's journal not recovered", PC_S,
  '    recover_if_needed(repo)',
  '    pass',
  'journal recovery must restore and stop'),
 ('prove: the elapsed time is not recorded', PC_S,
  '"baseline": {"exit": base[0], "tail": base[1], "elapsed_s": base[2]},',
  '"baseline": {"exit": base[0], "tail": base[1]},',
  'a record must carry elapsed_s for both runs'),
 ('prove: timeout kills only the shell', PC_S,
  '        os.killpg(p.pid, signal.SIGKILL)',
  '        p.kill()',
  'timeout must kill the process group'),
 ('req: a trivial --check accepted', PC_S,
  '        if not check or check.strip() in TRIVIAL_BUILD:',
  '        if False:',
  'a trivial check must be refused'),
 ('req: covered-by-claim not validated', PC_S,
  '        if problems:\n            raise Refused(f"claim {covered_by}',
  '        if False:\n            raise Refused(f"claim {covered_by}',
  'dangling claim reference must be refused'),
 ('deviation: no reason required', PC_S,
  '    if not why or len(why.strip()) < 10:',
  '    if False:',
  'empty deviation reason must exit 2'),
 ('replay: only re-reads the JSON', PC_S,
  '        if not problems:\n            fd, tmp = tempfile.mkstemp',
  '        if False:\n            fd, tmp = tempfile.mkstemp',
  'replay must re-run, not re-read'),
 ('validate: fingerprint not compared', PC_S,
  '    elif fingerprint and fpr != fingerprint:',
  '    elif False:',
  'fingerprint mismatch must be rejected'),
 ('validate: record path (task/index) not compared', PC_S,
  '        if rec.get("task") != etask or rec.get("index") != eindex:',
  '        if False:',
  'a record at the wrong path must be rejected'),
 ('validate: plan wording not compared', PC_S,
  '        if etext is not None and rec.get("text") != etext:',
  '        if False:',
  'reworded claim must be rejected'),
 ('validate: kind not compared to the path', PC_S,
  '        if kind != ekind:',
  '        if False:',
  'kind/path mismatch must be rejected'),
 ('validate: booleans pass as exit codes', PC_S,
  '    return type(x) is int',
  '    return isinstance(x, int)',
  'booleans must not pass as exit codes'),
 ('notes stripped without a history mark', PY_S,
  '        if HISTORY_MARK.search(m.group(0)):',
  '        if True:',
  'a history-free note must still count'),
 ('notes matched on unmasked text (code spans stripped)', PY_S,
  '    for m in ANNOTATION.finditer(masked):',
  '    for m in ANNOTATION.finditer(text):',
  'code spans must not be stripped as notes'),
 ('records: commit binding not checked', PY_S,
  'problems = pc.validate(rec, fps[sha], (kind, task, k, text), allow_legacy=True)',
  'problems = pc.validate(rec, None, (kind, task, k, text), allow_legacy=True)',
  'a stale record must be blocking (red if the binding is not checked)'),
 ('records: path and wording not checked', PY_S,
  'problems = pc.validate(rec, fps[sha], (kind, task, k, text), allow_legacy=True)',
  'problems = pc.validate(rec, fps[sha], allow_legacy=True)',
  'a reworded claim must be blocking (red if wording is not compared)'),
 ('finding 9 req records ignored', PY_S,
  '            if req == []:\n                if got.get(("legacy", k)):',
  '            if False:\n                if got.get(("legacy", k)):',
  'valid committed records must satisfy 8 and 9 (red if records are not read)'),
 ('finding 1: no task credited for its records', PY_S,
  '    return {t for t, got in recs.items() if t in blocks',
  '    return set() and {t for t, got in recs.items() if t in blocks',
  'tasks with records must each count (red if a commit counts once regardless)'),
 ('finding 1: naming tasks buys credit', PY_S,
  '    task_commits = max(task_commits, len(task_numbers(task_ids) & proven_tasks(repo, path)))\n',
  '    task_commits = max(task_commits, len(task_numbers(task_ids)))\n',
  'C4b must hold when records are partial (red if naming tasks buys credit)'),
 ('audit: legacy req checks blocking', PY_S,
  'problems = pc.validate(rec, fps[sha], (kind, task, k, text), allow_legacy=True)',
  'problems = pc.validate(rec, fps[sha], (kind, task, k, text))',
  "schema-1 bare req check (added before the cutover) must be advisory 'legacy schema-1' (red"),
 ('audit: legacy req checks not reported', PY_S,
  '        if not open_ and legacy:',
  '        if False:',
  "schema-1 bare req check (added before the cutover) must be advisory 'legacy schema-1' (red"),
 ('audit: covered-by citation not followed', PY_S,
  '            if req == [] and cites is not None and (',
  '            if False and cites is not None and (',
  'covered-by must be followed (red if the citation is not checked)'),
 ('audit: stray files under proof/ allowed', PY_S,
  '    if stray:\n        out.append(',
  '    if False:\n        out.append(',
  'stray proof/ files must be blocking (red if proof/ can carry anything)'),
 ('prove: exit 126/127 counted as red', PC_S,
  '    if red_rc in (126, 127) or red_rc < 0 or red_rc >= 128:',
  '    if red_rc < 0 or red_rc >= 128:',
  'exit 127 must not be red'),
 ('prove: killed (128+n) counted as red', PC_S,
  '    if red_rc in (126, 127) or red_rc < 0 or red_rc >= 128:',
  '    if red_rc in (126, 127) or red_rc < 0:',
  'exit 137 must not be red'),
 ('validate: red exit 0 accepted', PC_S,
  '    if not _is_int(red) or red == 0 or red in (126, 127) or red < 0 or red >= 128:',
  '    if False:',
  'red exit 0 must be rejected'),
 ('validate: a bare schema-2 req check accepted', PC_S,
  '            _check_run(rec, p, "check")\n',
  '            pass\n',
  'a bare schema-2 req check must be rejected'),
 ('validate: legacy accepted at commit', PC_S,
  '    legacy = allow_legacy and is_legacy(rec)',
  '    legacy = is_legacy(rec)',
  'legacy req checks: rejected by default, accepted only with allow_legacy'),
 ('req: --check without --break accepted', PC_S,
  '        if not brk:\n            raise Usage',
  '        if False:\n            raise Usage',
  '--check without --break must be refused'),
 ('req: the check is never run', PC_S,
  '        seen = observe(repo, brk, check, build, no_build, timeout, text)\n',
  '        seen = {"baseline": {"exit": 0, "tail": ""}, "red": {"exit": 1, "tail": ""}}\n',
  'failing req check must be refused'),
 ('prove: recovery overwrites a moved repo', PC_S,
  '    if now_head != head or now_blobs != blobs:',
  '    if False:',
  'recovery must refuse a moved repo, exits -9/3'),
 ('prove: runs not exclusive', PC_S,
  '    held = lock(repo)  # noqa: F841',
  '    held = None  # noqa: F841',
  'runs must be exclusive'),
 ('prove: unparseable break counted (no build step)', PC_S,
  '            broken = unparseable(repo, paths)\n',
  '            broken = []\n',
  'a non-parsing break must be refused'),
 ('prove: the test runner may be broken', PC_S,
  '        if os.path.normpath(p) in runs:',
  '        if False:',
  'the test runner must not be breakable'),
 ('prove: wider test trees not recognised', PC_S,
  '    r"|(^|/)[A-Za-z]*Test/"',
  '    r""',
  'TEST_PATH must cover the wider test trees'),
 ('subject_tasks: 1.10 read as 1.1', PY_S,
  '            out.add(cur.group(0))',
  '            out.add(cur.group(0)[:3])',
  'subject_tasks must read every subject form'),
 ('subject_tasks: case-sensitive again', PY_S,
  '    r"(?:tasks?\\b\\s*[:#-]?\\s*)?\\d+\\.\\d+)*)", re.I)',
  '    r"(?:tasks?\\b\\s*[:#-]?\\s*)?\\d+\\.\\d+)*)")',
  'finding 1 fired on an honest per-task history'),
 ('subject_tasks: ranges not expanded', PY_S,
  '                out.update(f"{a_major}.{n}" for n in range(a_minor + 1, b_minor))',
  '                pass',
  'subject_tasks must read every subject form'),
 ('subject_tasks: lists read as their first task', PY_S,
  '        for i, cur in enumerate(ids):',
  '        for i, cur in enumerate(ids[:1]):',
  'subject_tasks must read every subject form'),
 ('validate: a non-dict run field crashes it', PC_S,
  '    return v.get("exit") if isinstance(v, dict) else None',
  '    return v.get("exit")',
  'validate() raised AttributeError on a malformed record'),
 ('audit: legacy has no cutoff', PY_S,
  '                if added is None or added >= datetime.datetime.fromisoformat(LEGACY_CUTOFF):',
  '                if False:',
  "schema-1 bare req check (added after the cutover) must be advisory 'not shown met' (red if"),
 ('finding 1: one proven claim credits a task', PY_S,
  '            and all(got.get(("claim", k)) == [] for k in required_claims(blocks[t]["test"]))}',
  '            and any(got.get(("claim", k)) == [] for k in required_claims(blocks[t]["test"]))}',
  'credit needs every claim (red if one record credits a task)'),
 ('required claims: the first claim not required', PY_S,
  'if k == 1 or NAMED_BREAK.search(_masked(c))]',
  'if NAMED_BREAK.search(_masked(c))]',
  'honest run must be clean'),
 ('required claims: named breaks not required', PY_S,
  'if k == 1 or NAMED_BREAK.search(_masked(c))]',
  'if k == 1]',
  'credit needs every claim (red if one record credits a task)'),
 ('required claims: every claim required', PY_S,
  'if k == 1 or NAMED_BREAK.search(_masked(c))]',
  'if k == 1 or True]',
  'only the first claim and named breaks need records (red if every claim is required)'),
 ('claim deviation counted as proof', PY_S,
  '                problems = ["recorded as a claim deviation"]',
  '                problems = []',
  'a claim deviation must be advisory (red if a claim deviation counts as proof)'),
 ('claim deviation not reported', PY_S,
  '        if devs:\n',
  '        if False:\n',
  'a claim deviation must be advisory (red if a claim deviation counts as proof)'),
 ('claim deviation: reason not required (audit)', PY_S,
  'len(rec["why"].strip()) < 10:\n        p.append("a claim deviation without a reason")',
  'len(rec["why"].strip()) < 0:\n        p.append("a claim deviation without a reason")',
  'a reasonless claim deviation must be blocking (red if it is waived silently)'),
 ('claim deviation: task/index not compared', PY_S,
  '    if rec.get("task") != task or rec.get("index") != k:',
  '    if False:',
  'a claim deviation must match its path (red if task/index are not compared)'),
 ('claim deviation: wording not compared', PY_S,
  '        p.append("recorded against different wording than the plan now has")',
  '        pass',
  "a claim deviation must match the plan's wording (red if wording is not compared)"),
 ('claim deviation: fingerprint not compared', PY_S,
  '        p.append("recorded on a different tree than this one")',
  '        pass',
  'a claim deviation must be bound to its commit (red if the fingerprint is not compared)'),
 ('deviation --claim records requirement wording', PC_S,
  '        text = pick(PFA.claim_clauses(block["test"]), index, "claim")',
  '        text = pick(PFA.requirement_clauses(block["desc"]), index, "claim")',
  'a claim deviation must record'),
 ('validate(): claim deviation not delegated to the audit', PC_S,
  '    if kind == "claim-deviation" and (not expect or expect[0] == "claim"):',
  '    if False:',
  'a claim deviation must not cover a requirement'),
 ('req: covered-by accepts a claim deviation as proof', PC_S,
  '        if not problems and crec.get("kind") != "claim":',
  '        if False:',
  'a claim deviation must not cover a requirement'),
 # Re-anchored 2026-10-06 (Task 4.1): unbacked() now builds `out` before its Preflight step.
 ('finding 1: gate boxes always counted (a gate ticked with its green commit is a bulk flip)', PY_S,
  '    out = [e for e in entries if gates.get(e[2]) not in green]',
  '    out = list(entries)',
  "a stage's gate boxes are backed only by its green commit (red if gate boxes count, or coun"),
 ('finding 1: gate boxes backed without a Stage N green commit', PY_S,
  '    out = [e for e in entries if gates.get(e[2]) not in green]',
  '    out = [e for e in entries if gates.get(e[2]) is None]',
  "a stage's gate boxes are backed only by its green commit (red if gate boxes count, or coun"),
 ('finding 10: a live-check remediation with no fixture sweep goes silent', PY_S,
  '        if not hit or date < since or hit.group(1) not in stages:',
  '        if True:',
  'a live-check remediation with no sweep must be finding 10, advisory (red if it is silent)'),
 ('replay: a claim deviation counted as a failed replay', PC_S,
  '        if isinstance(rec, dict) and rec.get("kind") == "claim-deviation":',
  '        if False:',
  'replay must skip claim deviations'),
 # ---- hooks/git-ref-gate.sh: the opt-in commit gate (Task 3.1)
 ('ref gate: acts in the committed phase, where a refusal aborts nothing', GR_S,
  '[[ "${1:-}" == "prepared" ]] || exit 0',
  '[[ "${1:-}" == "committed" ]] || exit 0',
  'unproven task commit must be refused'),
 ('ref gate: the state file read naively, following symlinks (evaluator M1)', GR_S,
  'state = pcc.read_state(repo)',
  'p_ = repo / ".claude" / "plan-progress.json"; state = json.load(open(p_)) if p_.exists() else None',
  'symlinked state must not gate'),
 ('ref gate: HEAD updates ignored (a detached HEAD commit lands)', GR_S,
  'not (ref == "HEAD" or ref.startswith("refs/heads/"))',
  'not ref.startswith("refs/heads/")',
  'HEAD updates must be checked'),
 ('ref gate: commits already on a branch re-checked (old history blocks new work)', GR_S,
  'tip, "--not", "--branches", "--remotes")',
  'tip)',
  'history already on a branch must not block a proven commit'),
 ('ref gate: records read from the index, not the commit', GR_S,
  'r = git("show", f"{sha}:{rel}")',
  'r = git("show", f":{rel}")',
  'records must be read from the commit'),
 ('ref gate: the task read from the whole message, not the subject', GR_S,
  'git("log", "-1", "--format=%s", sha)',
  'git("log", "-1", "--format=%B", sha)',
  'the body must not be gated'),
 ('ref gate: stray files under proof/ allowed', GR_S,
  'if p and not pc.RECORD_PATH.match(p):',
  'if False:',
  'stray proof/ files must be refused'),
 ('ref gate: named-break claims not required (first claim only)', GR_S,
  '                if k in required:',
  '                if k == 1:',
  'a named-break claim without a record must be refused'),
 ('ref gate: every claim required (the Cursor rule, not upstream)', GR_S,
  '                if k in required:',
  '                if True:',
  'a proven task commit must land'),
 ('ref gate: a present record validated only when required', GR_S,
  '            if probs:\n                missing.append(f"{short} Task {t} claim {k}: {probs[0]}")',
  '            if probs and k in required:\n                missing.append(f"{short} Task {t} claim {k}: {probs[0]}")',
  'a present invalid record must be refused'),
 ('ref gate: a record not bound to the commit tree', GR_S,
  'problems_of(rec, fp, ("claim", t, k, c))',
  'problems_of(rec, None, ("claim", t, k, c))',
  '-a must be checked against the tree git commits'),
 ('ref gate: a record not bound to the plan wording', GR_S,
  '("claim", t, k, c))',
  '("claim", t, k, None))',
  'reworded claim must be refused'),
 ('ref gate: a claim deviation counted as proof', GR_S,
  '            elif rec.get("kind") == "claim-deviation":',
  '            elif False:',
  'a claim deviation must be allowed and named | a named-break claim without a record must be refused'),
 ('ref gate: covered-by not followed to a real proof', GR_S,
  'if probs.get("req") == [] and cites is not None and not proven.get(cites):',
  'if False:',
  'covered-by must accept only kind claim'),
 ('ref gate: deviations not named at commit time', GR_S,
  '    if deviations:\n        sys.stderr.write',
  '    if False:\n        sys.stderr.write',
  'a claim deviation must be allowed and named'),
 ('ref gate: unaccounted requirements not named (finding 9 silent)', GR_S,
  '    if advisory:',
  '    if False:',
  'an unaccounted requirement must be named, not silently passed'),
 ('ref gate: a refusal exits 0', GR_S,
  '    sys.stderr.write(text.rstrip() + "\\n")\n    sys.exit(1)',
  '    sys.stderr.write(text.rstrip() + "\\n")\n    sys.exit(0)',
  'unproven task commit must be refused'),
 # ---- proof-hooks-install.py (Task 3.1)
 ('installer: a foreign reference-transaction hook replaced', PI_S,
  '        if not shim_is_ours(hook):\n            die(',
  '        if False:\n            die(',
  'a foreign hook must not be overwritten'),
 ('installer: --remove deletes a foreign hook', PI_S,
  '    if not shim_is_ours(hook):\n        print(f"nothing to remove',
  '    if False:\n        print(f"nothing to remove',
  '--remove must remove only its own shim'),
 ('installer: a shim without its exec bit counts as installed', PI_S,
  'return os.access(hook, os.X_OK) and hook.read_text(errors="replace") == shim_text()',
  'return hook.read_text(errors="replace") == shim_text()',
  'a non-executable shim must not count as installed'),
 ('installer: an edited shim counts as installed', PI_S,
  'return os.access(hook, os.X_OK) and hook.read_text(errors="replace") == shim_text()',
  'return os.access(hook, os.X_OK)',
  'an edited shim must not count as installed'),
 ('installer: core.hooksPath ignored', PI_S,
  'hd = Path(hooks) if os.path.isabs(hooks) else r / hooks',
  'hd = r / ".git" / "hooks"',
  'a shared hooks directory must be refused'),
 ('installer: the shim is written without its exec bit', PI_S,
  'os.chmod(tmp, 0o755)',
  'os.chmod(tmp, 0o644)',
  'unproven task commit must be refused'),
 ('installer: a dangling shim fails open in silence', PI_S,
  'is missing — the commit gate is OFF;',
  'is missing;',
  'a dangling shim must fail open loudly'),
 ('installer: re-install rewrites a current shim', PI_S,
  '        if shim_is_current(hook):\n            print(f"already installed',
  '        if False:\n            print(f"already installed',
  're-install must leave the shim unchanged'),
 ('installer: a non-repo accepted', PI_S,
  '    if top.returncode != 0:\n        die(f"{r} is not a git work tree")',
  '    if False:\n        die(f"{r} is not a git work tree")',
  'a non-repo must be refused | an unproven task commit must not land by'),
 ('installer: --status reports a missing shim as installed', PI_S,
  '        print(f"not installed — no {HOOK_NAME} hook in {top}")\n    return 1',
  '        print(f"not installed — no {HOOK_NAME} hook in {top}")\n    return 0',
  '--status must report not installed after --remove'),
 # ---- hooks/proof-guard.sh: the PreToolUse guard (Task 3.2)
 ('guard: the hooksPath rule off', PG_S,
  'if re.search(r"hookspath", command, re.I):',
  'if False:',
  "must deny 'git -c core.hooksPath=/dev/null commit -m x'"),
 ('guard: hooksPath matched case-sensitively', PG_S,
  'command, re.I):',
  'command):',
  "must deny 'git -c core.hooksPath=/dev/null commit -m x'"),
 ('guard: the hook-file rule off', PG_S,
  'if re.search(rf"{HOOK_NAME}|\\.git/hooks", command):',
  'if False:',
  "must deny 'rm .git/hooks/reference-transaction'"),
 ('guard: the installer --remove rule off', PG_S,
  'if inst in command and re.search(r"--remove\\b", command):',
  'if False:',
  "must deny 'python3 "),
 ('guard: acts without opt-in', PG_S,
  'gated = [r for r in repos if opted_in(r) and in_flight(r)]',
  'gated = [r for r in repos if in_flight(r)]',
  'a repo that did not opt in must see no decision'),
 ('guard: acts with no plan in flight', PG_S,
  'gated = [r for r in repos if opted_in(r) and in_flight(r)]',
  'gated = [r for r in repos if opted_in(r)]',
  'no plan in flight must see no decision'),
 ('guard: any reference-transaction hook counts as our opt-in', PG_S,
  '        return len(lines) > 1 and lines[1].startswith(f"# {MARK} — installed by")',
  '        return True',
  "someone else's hook must not opt the repo in"),
 ('guard: the state file read naively, following symlinks (evaluator M1)', PG_S,
  '    state = pcc.read_state(repo)',
  '    p_ = repo / ".claude" / "plan-progress.json"; state = json.load(open(p_)) if p_.exists() else None',
  'symlinked state must not count'),
 ('guard: a repo reached by cd not considered', PG_S,
  're.findall(r"\\bcd\\s+(',
  're.findall(r"\\bcdXX\\s+(',
  "/repo && git -c core.hookspath=/x commit -m x' run from /"),
 ('guard: a repo reached by git -C not considered', PG_S,
  're.findall(r"\\bgit\\s+-C\\s+(',
  're.findall(r"\\bgitXX\\s+-C\\s+(',
  "/repo -c core.hooksPath=/x commit -m x' run from /tmp"),
 ('guard: the pre-filter drops hooksPath', PG_S,
  "grep -qiE 'hookspath|reference-transaction|",
  "grep -qiE 'reference-transaction|",
  "must deny 'git -c core.hooksPath=/dev/null commit -m x'"),
 ('guard: the pre-filter drops the hook file', PG_S,
  "grep -qiE 'hookspath|reference-transaction|",
  "grep -qiE 'hookspath|",
  "must deny 'cd .git && rm hooks/reference-transaction'"),
 ('guard: an unreadable payload denied (fails closed)', PG_S,
  '    none("payload is not JSON")',
  '    deny("payload is not JSON")',
  'a garbage payload must produce no decision'),
 ('guard: the decision is "ask", not "deny"', PG_S,
  '"permissionDecision": "deny"',
  '"permissionDecision": "ask"',
  "must deny 'git -c core.hooksPath=/dev/null commit -m x'"),
 # ---- Stage 3 gate remediation round 1 (review I1-I4, S1, S3)
 ('ref gate: no python3 aborts every update (review I4)', GR_S,
  'command -v python3 >/dev/null 2>&1 || {',
  'false && {',
  'a missing python3 must fail open with a note'),
 ('ref gate: an uncaught exception refuses the update (review I4)', GR_S,
  'sys.excepthook = _fail_open',
  'pass',
  'an uncaught error must fail open'),
 ('ref gate: fetched commits gated as if added here (review I3)', GR_S,
  '"--not", "--branches", "--remotes")',
  '"--not", "--branches")',
  'a fetched commit must be checkable-out'),
 ('installer: --rem abbreviates --remove past the guard (review I1)', PI_S,
  '        allow_abbrev=False,',
  '        allow_abbrev=True,',
  '--rem must not act as --remove'),
 ('installer: a shared hooks directory accepted (review I2)', PI_S,
  '    if not any(within(hd, base) for base in (top, common)):',
  '    if False:',
  'a shared hooks directory must be refused'),
 ('installer: the marker anywhere identifies our shim (review S3)', PI_S,
  '    return len(lines) > 1 and lines[1].startswith(SHIM_LINE2)',
  '    return any(SHIM_MARK in l for l in lines)',
  'the marker must identify only our shim'),
 ('guard: a shim in a shared hooks directory counts as opt-in (review I2)', PG_S,
  '        if not any(hd.resolve().is_relative_to(b.resolve()) for b in (repo, common)):',
  '        if False:',
  'a shared hooks directory must not opt a repo in'),
]


def suites_for(target):
    # The installer's suite is the git hook's: one fixture installs the shim the
    # hook runs from.
    return {PY_S: [PY_T], PC_S: [PC_T], GR_S: [GR_T], PI_S: [GR_T], PG_S: [PG_T]}[target]


SUITE_TIMEOUT = 900   # seconds; the slowest suite takes ~20 s alone


def run(root, suite):
    """(exit code, stdout) of one suite run; exit None on a timeout."""
    cmd = ["bash"] if suite.endswith(".sh") else [sys.executable]
    try:
        r = subprocess.run(cmd + [str(root / suite)], capture_output=True,
                           text=True, timeout=SUITE_TIMEOUT,
                           env=dict(os.environ, SUITE_FAIL_FAST="1"))
    except subprocess.TimeoutExpired:
        return None, ""
    return r.returncode, r.stdout


def copy_skill():
    """A private copy of the plugin's executing-plans skill and hooks directory,
    at d/planning: the suites find the scripts and hooks where the plugin has them."""
    d = Path(tempfile.mkdtemp(prefix="battery-proof-tools-"))
    ignore = shutil.ignore_patterns("__pycache__", "mod", "node_modules")
    shutil.copytree(PLUGIN / EP, d / "planning" / EP, ignore=ignore)
    shutil.copytree(PLUGIN / "hooks", d / "planning" / "hooks", ignore=ignore)
    return d


HEREDOC_PY = re.compile(r"<<'PY'\n(.*?)\nPY\n", re.S)


def unparseable(f):
    """Why the mutated file would not even run, or None. A shell hook is checked
    with `bash -n` AND its embedded Python compiled: a hook that crashes fails
    open, so its suite would go red having measured nothing about the guard."""
    if f.suffix == ".py":
        try:
            py_compile.compile(str(f), cfile=str(f.parent / ".check.pyc"), doraise=True)
        except py_compile.PyCompileError:
            return "the mutation leaves the script unparseable"
        return None
    if subprocess.run(["bash", "-n", str(f)], capture_output=True).returncode != 0:
        return "the mutation leaves the hook's shell unparseable"
    for body in HEREDOC_PY.findall(f.read_text()):
        try:
            compile(body, str(f), "exec")
        except SyntaxError:
            return "the mutation leaves the hook's Python unparseable"
    return None


def trial(entry):
    """(label, verdict) for one mutation, run in its own copy.

    killed: the suite's first failing check (`  FAIL` on stdout, every suite's
    marker; the suite runs fail-fast) is the one the entry names. MISNAMED: another
    check killed it. SURVIVED: every suite passed. ERROR: anything else — never counted
    as a kill. Exceptions are caught here, so a worker's crash cannot escape as
    Python's exit 1, which this file defines as "survived".
    """
    label, target, old, new, killer = entry
    d = None
    try:
        d = copy_skill()
        f = d / "planning" / target
        f.write_text(f.read_text().replace(old, new))
        why = unparseable(f)
        if why:
            return label, "ERROR", why
        for s in suites_for(target):
            rc, out = run(d / "planning", s)
            if rc is None:
                return label, "ERROR", f"{s} timed out after {SUITE_TIMEOUT}s"
            if rc != 0:
                fails = [ln[8:] for ln in out.splitlines() if ln.startswith("  FAIL")]
                if not fails:
                    return label, "ERROR", f"{s} exited {rc} without reporting a failing check"
                if any(k.strip() in fails[0] for k in killer.split(" | ")):
                    return label, "killed", ""
                lines = out.splitlines()
                at = next(i for i, ln in enumerate(lines) if ln.startswith("  FAIL"))
                detail = " / ".join(ln.strip() for ln in lines[at + 1: at + 4]
                                    if ln.startswith("        |"))
                return label, "MISNAMED", (f"killed by `{fails[0][:90]}`, named `{killer}`"
                                           + (f" — {detail[:300]}" if detail else ""))
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
    gone = [label for label, target, old, *_ in M if (PLUGIN / target).read_text().count(old) == 0]
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
        red = [s for s in SUITES if run(d / "planning", s)[0] != 0]
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if red:
        print(f"  ABORT — {', '.join(red)} already red")
        return 2
    print(f"  ok\n\nrunning {len(M)} mutations, {jobs} at a time")

    counts = {"killed": 0, "SURVIVED": 0, "ERROR": 0, "MISNAMED": 0, "UNSTABLE": 0}
    misnamed = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for entry, (label, verdict, why) in zip(M, pool.map(trial, M)):
            if verdict == "MISNAMED":
                misnamed.append((entry, why))
                continue
            print(f"  {verdict:<8} {label}" + (f"  ({why})" if why else ""), flush=True)
            counts[verdict] += 1
    # A MISNAMED trial is re-run once, alone, after the pool: under -j N a check that
    # also covers the guard sometimes fails first (measured 2026-10-06: an rc=128 from
    # `git commit` in test-git-ref-gate.sh, 1-2 times in ~5 full runs, never in 36
    # targeted ones). A wrong name is deterministic and stays MISNAMED; a first killer
    # that changed between runs is UNSTABLE — printed with the stray failure's detail
    # so it can be diagnosed, and never counted as a kill or a misname.
    for entry, why in misnamed:
        label, verdict, why2 = trial(entry)
        if verdict == "killed":
            verdict, why2 = "UNSTABLE", f"first run {why}; re-run alone: killed by its named check"
        print(f"  {verdict:<8} {label}" + (f"  ({why2})" if why2 else ""), flush=True)
        counts[verdict] += 1
    print(f"\nkilled {counts['killed']}  survived {counts['SURVIVED']}  "
          f"errors {counts['ERROR']}  misnamed {counts['MISNAMED']}  "
          f"unstable {counts['UNSTABLE']}  skipped 0")
    if counts["SURVIVED"]:
        return 1
    if counts["ERROR"]:
        return 5
    return 6 if counts["MISNAMED"] else 0


if __name__ == "__main__":
    sys.exit(main())
