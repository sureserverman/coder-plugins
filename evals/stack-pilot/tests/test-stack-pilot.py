#!/usr/bin/env python3
"""Hermetic tests for the stack-pilot harness (evals/stack-pilot/run.py, grade.py).

The pilot compares three arms (skill, bare, rule) and its verdict is only worth
anything if the harness really measures. So these cases pin the ways it could
pass while measuring nothing:

  - the grader counts exactly the four seeded findings in fixture-audit and zero
    in fixture-author, and does NOT grade a tree holding .unwrap() in library
    code as zero;
  - a run with no result tree is ungradeable, never "0 findings";
  - the verdict function returns no-go when any one of the four conditions
    breaks, and go only when all hold;
  - run.py refuses the skill/bare arms when the rule file exists and the rule
    arm when it does not, before it ever calls claude;
  - run.py, driven by a fake `claude` on PATH, writes the run folder, keeps an
    environment-failure first attempt, and its probe tells the arms apart.

No real claude call, no network, no writes outside a temp dir, no dependence on
~/.claude or the vault. Needs bash, jq and git (validate-safety.sh needs jq).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.dirname(HERE)
RUN_PY = os.path.join(PILOT, "run.py")
GRADE_PY = os.path.join(PILOT, "grade.py")
FIX_AUTHOR = os.path.join(PILOT, "fixture-author")
FIX_AUDIT = os.path.join(PILOT, "fixture-audit")

HOUSE_IDS = [
    "rust-unsafe-missing-safety-comment",
    "rust-sync-lock-in-async-candidate",
    "rust-unbounded-channel",
    "rust-box-dyn-error-in-pub-api",
    "rust-unwrap-outside-tests",
    "rust-serde-missing-deny-unknown",
]
SEEDED = {
    "rust-unwrap-outside-tests": 1,
    "rust-unbounded-channel": 1,
    "rust-box-dyn-error-in-pub-api": 1,
    "rust-serde-missing-deny-unknown": 1,
}

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


grade = load("stack_pilot_grade", GRADE_PY)


def copy_tree(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("target", ".git"))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def make_run(results, arm, prompt, n, tree_from=None, extra_rs=None, **meta_over):
    """A synthetic run folder as run.py writes it."""
    folder = os.path.join(results, f"{arm}-{prompt}-{n}")
    os.makedirs(folder)
    if tree_from:
        copy_tree(tree_from, os.path.join(folder, "tree"))
        if extra_rs:
            with open(os.path.join(folder, "tree", "src", "lib.rs"), "a") as fh:
                fh.write(extra_rs)
    meta = {
        "arm": arm, "prompt": prompt, "n": n,
        "rule_present": arm == "rule", "rule_loaded": arm == "rule",
        "skill_invoked": arm == "skill", "lane_run": prompt == "audit",
        "inputs_sha256": grade.inputs_sha256(), "exit": 0, "seconds": 1.0,
        "environment": "ok",
    }
    meta.update(meta_over)
    write(os.path.join(folder, "meta.json"), json.dumps(meta, indent=2))
    return folder


NEW_CODE = "\npub fn settings_port(s: &str) -> u16 {\n    s.trim().parse().unwrap_or(8080)\n}\n"


# --- grader on the fixtures --------------------------------------------------

def grader_fixture_cases():
    counts = grade.scan_tree(FIX_AUDIT)
    check(set(counts) == set(HOUSE_IDS), "scan_tree reports a count for each of the six house-rule ids")
    check(sum(counts.values()) == 4, f"fixture-audit holds exactly four house-rule findings (got {sum(counts.values())})")
    for rid, want in SEEDED.items():
        check(counts.get(rid) == want, f"fixture-audit seeds {rid} once (got {counts.get(rid)})")

    counts = grade.scan_tree(FIX_AUTHOR)
    check(sum(counts.values()) == 0, f"fixture-author holds zero house-rule findings (got {counts})")

    with tempfile.TemporaryDirectory() as tmp:
        tree = os.path.join(tmp, "tree")
        copy_tree(FIX_AUTHOR, tree)
        with open(os.path.join(tree, "src", "lib.rs"), "a") as fh:
            fh.write("\npub fn port(s: &str) -> u16 {\n    s.parse().unwrap()\n}\n")
        counts = grade.scan_tree(tree)
        check(counts.get("rust-unwrap-outside-tests", 0) >= 1,
              ".unwrap() in library code is counted as rust-unwrap-outside-tests")
        check(sum(counts.values()) > 0, "a tree holding .unwrap() in library code is NOT graded zero")


# --- gradeability -------------------------------------------------------------

def gradeability_cases():
    with tempfile.TemporaryDirectory() as res:
        no_tree = make_run(res, "skill", "author", 1)
        g = grade.grade_run(no_tree)
        check(g["status"] == "ungradeable", "a run with no result tree is ungradeable")
        check(g["total"] is None, "an ungradeable run has no finding total (None), never 0")
        check("tree" in g["reason"], f"the reason names the missing tree (got {g['reason']!r})")

        ok = make_run(res, "skill", "author", 2, tree_from=FIX_AUTHOR, extra_rs=NEW_CODE)
        g = grade.grade_run(ok)
        check(g["status"] == "gradeable" and g["total"] == 0, f"a changed clean tree grades to 0 findings (got {g})")

        same = make_run(res, "skill", "author", 3, tree_from=FIX_AUTHOR)
        g = grade.grade_run(same)
        check(g["status"] == "ungradeable", "an author run that changed no Rust source is ungradeable")

        bad_exit = make_run(res, "skill", "author", 4, tree_from=FIX_AUTHOR, extra_rs=NEW_CODE, exit=1)
        check(grade.grade_run(bad_exit)["status"] == "ungradeable", "a run whose claude exit was non-zero is ungradeable")

        envf = make_run(res, "skill", "author", 5, tree_from=FIX_AUTHOR, extra_rs=NEW_CODE, environment="failure")
        check(grade.grade_run(envf)["status"] == "ungradeable", "an environment-failure run is ungradeable")

        contaminated = make_run(res, "bare", "author", 1, tree_from=FIX_AUTHOR, extra_rs=NEW_CODE, rule_present=True)
        check(grade.grade_run(contaminated)["status"] == "ungradeable",
              "a bare run that saw the rule file is ungradeable")

        stale = make_run(res, "bare", "author", 2, tree_from=FIX_AUTHOR, extra_rs=NEW_CODE, inputs_sha256="0" * 64)
        check(grade.grade_run(stale)["status"] == "ungradeable",
              "a run made from different prompts/fixtures/grader is ungradeable")

        audit = make_run(res, "skill", "audit", 1, tree_from=FIX_AUDIT)
        g = grade.grade_run(audit)
        check(g["status"] == "gradeable" and g["total"] == 4, f"an unchanged audit tree is gradeable with 4 findings (got {g})")


def cli(args, env=None):
    p = subprocess.run([sys.executable, GRADE_PY] + args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def grade_cli_cases():
    with tempfile.TemporaryDirectory() as res:
        make_run(res, "skill", "author", 1, tree_from=FIX_AUTHOR, extra_rs=NEW_CODE)
        make_run(res, "bare", "author", 1, tree_from=FIX_AUTHOR,
                 extra_rs="\npub fn p(s: &str) -> u16 {\n    s.parse().unwrap()\n}\n")
        # a kept environment-failure first attempt is evidence, not a run
        make_run(res, "skill", "author", "1.envfail", environment="failure")
        rc, out = cli(["--results", res, "--arms", "skill,bare", "--expect-runs", "author=1"])
        check(rc == 0, f"grade.py passes when every expected run is gradeable (rc={rc}):\n{out}")
        check("skill" in out and "bare" in out, "the table names both arms")

        rc, out = cli(["--results", res, "--arms", "skill,bare", "--expect-runs", "author=2"])
        check(rc != 0 and "missing" in out.lower(), f"grade.py fails and says 'missing' when a run is absent (rc={rc})")

        shutil.rmtree(os.path.join(res, "bare-author-1", "tree"))
        rc, out = cli(["--results", res, "--arms", "skill,bare", "--expect-runs", "author=1"])
        check(rc != 0 and "UNGRADEABLE" in out, f"grade.py fails and says UNGRADEABLE for a run with no tree (rc={rc})")

    with tempfile.TemporaryDirectory() as res:
        make_run(res, "skill", "author", 1, tree_from=FIX_AUTHOR, extra_rs=NEW_CODE, rule_present=True)
        rc, out = cli(["--results", res, "--arms", "skill", "--expect-runs", "author=1"])
        check(rc != 0, "grade.py fails when a skill-arm meta.json lacks rule_present false")


# --- verdict -------------------------------------------------------------------

def good_table():
    def cell(runs, findings=0, lane=0, loaded=0, invoked=0):
        return {"expected": runs, "runs": runs, "gradeable": runs, "findings": findings,
                "lane_runs": lane, "rule_loaded": loaded, "skill_invoked": invoked}
    return {
        "skill": {"author": cell(5, findings=4, invoked=5), "audit": cell(3, findings=12, lane=3, invoked=3)},
        "bare": {"author": cell(5, findings=9), "audit": cell(3, findings=12, lane=0)},
        "rule": {"author": cell(5, findings=5, loaded=5), "audit": cell(3, findings=12, lane=2, loaded=3)},
    }


def failed_ids(v):
    return [c["id"] for c in v["conditions"] if not c["pass"]]


def verdict_cases():
    expect = {"author": 5, "audit": 3}
    v = grade.decide(good_table(), expect)
    check(v["verdict"] == "go" and failed_ids(v) == [],
          f"go when all four conditions hold (boundaries: rule=skill+1, lanes=skill-1) (got {v['verdict']}, failed {failed_ids(v)})")
    check([c["id"] for c in v["conditions"]] == [1, 2, 3, 4], "the verdict lists the four conditions in order")

    t = good_table(); t["bare"]["audit"]["gradeable"] = 2
    v = grade.decide(t, expect)
    check(v["verdict"] == "no-go" and failed_ids(v) == [1], f"no-go when one run of any arm is ungradeable (failed {failed_ids(v)})")

    t = good_table(); t["skill"]["author"]["runs"] = 4; t["skill"]["author"]["gradeable"] = 4
    v = grade.decide(t, expect)
    check(v["verdict"] == "no-go" and 1 in failed_ids(v), "no-go when an arm is missing an expected run")

    t = good_table(); t["rule"]["audit"]["rule_loaded"] = 2
    v = grade.decide(t, expect)
    check(v["verdict"] == "no-go" and failed_ids(v) == [2], f"no-go when a rule run did not log the rule as loaded (failed {failed_ids(v)})")

    t = good_table(); t["rule"]["author"]["findings"] = 6
    v = grade.decide(t, expect)
    check(v["verdict"] == "no-go" and failed_ids(v) == [3], f"no-go when rule author findings exceed skill + 1 (failed {failed_ids(v)})")

    t = good_table(); t["rule"]["audit"]["lane_runs"] = 1
    v = grade.decide(t, expect)
    check(v["verdict"] == "no-go" and failed_ids(v) == [4], f"no-go when rule lane runs fall below skill - 1 (failed {failed_ids(v)})")

    t = good_table(); del t["rule"]
    v = grade.decide(t, expect)
    check(v["verdict"] == "no-go", "no-go when the rule arm is absent from the table")


# --- run.py: refusals and a fake-claude end-to-end -----------------------------

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
state = os.environ["FAKE_CLAUDE_STATE"]
with open(os.path.join(state, "calls.log"), "a") as fh:
    fh.write(json.dumps(args) + "\n")
calls = sum(1 for _ in open(os.path.join(state, "calls.log")))
settings = json.load(open(args[args.index("--settings") + 1]))
enabled = settings.get("enabledPlugins", {}).get("rust-dev@coder-plugins", True)
def emit(o):
    print(json.dumps(o), flush=True)
emit({"type": "system", "subtype": "hook_response"})
emit({"type": "system", "subtype": "init",
      "skills": ["rust-dev:rust-coding"] if enabled else [],
      "plugins": [{"name": "rust-dev"}] if enabled else []})
if "--max-turns" in args:
    emit({"type": "result", "subtype": "success", "is_error": False, "result": "OK"})
    sys.exit(0)
if os.environ.get("FAKE_CLAUDE_MODE") == "envfail-once" and calls == 1:
    emit({"type": "result", "subtype": "success", "is_error": True,
          "result": "API Error: 429 {\"type\":\"error\",\"error\":{\"type\":\"rate_limit_error\"}}"})
    sys.exit(1)
for h in settings["hooks"]["InstructionsLoaded"][0]["hooks"]:
    ev = {"file_path": "/cfg/rules/vault-stack-rust.md", "memory_type": "User",
          "load_reason": "path_glob_match", "trigger_file_path": os.path.join(os.getcwd(), "src/lib.rs")}
    subprocess.run(h["command"], shell=True, input=json.dumps(ev), text=True)
with open("src/lib.rs", "a") as fh:
    fh.write("\npub fn port(s: &str) -> u16 {\n    s.parse().unwrap()\n}\n")
if enabled:
    emit({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "rust-dev:rust-coding"}}]}})
emit({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "bash /x/scripts/validate.sh . --json"}}]}})
emit({"type": "result", "subtype": "success", "is_error": False, "result": "Added the port parser."})
'''


def fake_env(tmp, rule_file):
    cfg = os.path.join(tmp, "cfg")
    os.makedirs(os.path.join(cfg, "rules"), exist_ok=True)
    rf = os.path.join(cfg, "rules", "vault-stack-rust.md")
    if rule_file:
        write(rf, "---\npaths: [\"**/*.rs\"]\n---\nrule\n")
    elif os.path.exists(rf):
        os.remove(rf)
    bindir = os.path.join(tmp, "bin")
    state = os.path.join(tmp, "state")
    os.makedirs(bindir, exist_ok=True)
    os.makedirs(state, exist_ok=True)
    fake = os.path.join(bindir, "claude")
    write(fake, FAKE_CLAUDE)
    os.chmod(fake, 0o755)
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = cfg
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
    env["FAKE_CLAUDE_STATE"] = state
    env["TMPDIR"] = os.path.join(tmp, "scratch")
    os.makedirs(env["TMPDIR"], exist_ok=True)
    return env, os.path.join(state, "calls.log")


def run_py(args, env):
    p = subprocess.run([sys.executable, RUN_PY] + args, capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout, p.stderr


def refusal_cases():
    with tempfile.TemporaryDirectory() as tmp:
        env, calls = fake_env(tmp, rule_file=True)
        out = os.path.join(tmp, "out")
        for arm in ("skill", "bare"):
            rc, so, se = run_py(["--arm", arm, "--prompt", "author", "--runs", "1", "--out", out], env)
            check(rc != 0 and "vault-stack-rust.md" in so + se,
                  f"run.py refuses the {arm} arm when the rule file exists, naming it (rc={rc})")
            rc, so, se = run_py(["--probe", "--arm", arm, "--out", out], env)
            check(rc != 0 and "vault-stack-rust.md" in so + se, f"run.py --probe refuses the {arm} arm too (rc={rc})")
        check(not os.path.exists(calls), "a refused arm never calls claude")
        check(not os.path.exists(out) or os.listdir(out) == [], "a refused arm writes no run folder")

        env, calls = fake_env(tmp, rule_file=False)
        rc, so, se = run_py(["--arm", "rule", "--prompt", "author", "--runs", "1", "--out", out], env)
        check(rc != 0 and "vault-stack-rust.md" in so + se,
              f"run.py refuses the rule arm when the rule file is absent, naming it (rc={rc})")
        check(not os.path.exists(calls), "the refused rule arm never calls claude")


def fake_run_cases():
    with tempfile.TemporaryDirectory() as tmp:
        env, calls = fake_env(tmp, rule_file=False)
        out = os.path.join(tmp, "out")

        rc, so, se = run_py(["--probe", "--arm", "skill", "--out", out], env)
        check(rc == 0 and '"skill_listed": true' in so, f"probe of the skill arm prints \"skill_listed\": true (rc={rc}) {so}{se}")
        rc, so, se = run_py(["--probe", "--arm", "bare", "--out", out], env)
        check(rc == 0 and '"skill_listed": false' in so, f"probe of the bare arm prints \"skill_listed\": false (rc={rc}) {so}{se}")
        probe = json.load(open(os.path.join(out, "probe.json")))
        check(probe.get("skill", {}).get("skill_listed") is True and probe.get("bare", {}).get("skill_listed") is False,
              "probe.json keeps both arms' probes")
        os.remove(calls)

        env["FAKE_CLAUDE_MODE"] = "envfail-once"
        rc, so, se = run_py(["--arm", "skill", "--prompt", "author", "--runs", "1", "--out", out], env)
        check(rc == 0, f"run.py completes a run after one environment failure (rc={rc}) {so}{se}")
        first = os.path.join(out, "skill-author-1.envfail", "meta.json")
        check(os.path.exists(first) and json.load(open(first)).get("environment") == "failure",
              "the failed first attempt is kept with environment: failure")
        mpath = os.path.join(out, "skill-author-1", "meta.json")
        meta = json.load(open(mpath)) if os.path.exists(mpath) else {}
        for key in ("arm", "prompt", "n", "rule_present", "rule_loaded", "skill_invoked", "lane_run",
                    "inputs_sha256", "exit", "seconds"):
            check(key in meta, f"meta.json carries {key}")
        check(meta.get("arm") == "skill" and meta.get("prompt") == "author" and meta.get("n") == 1, "meta names arm, prompt, n")
        check(meta.get("rule_present") is False and '"rule_present": false' in open(mpath).read(),
              "meta.json holds the literal \"rule_present\": false")
        check(meta.get("skill_invoked") is True, "a Skill tool_use naming rust-coding sets skill_invoked")
        check(meta.get("lane_run") is True, "a Bash call naming validate.sh sets lane_run")
        check(meta.get("rule_loaded") is True, "the InstructionsLoaded hook log sets rule_loaded")
        check(meta.get("exit") == 0 and meta.get("environment") == "ok", "the retried run exited 0, environment ok")
        check(meta.get("inputs_sha256") == grade.inputs_sha256(), "inputs_sha256 matches the grader's hash")
        tree = os.path.join(out, "skill-author-1", "tree")
        check(os.path.isfile(os.path.join(tree, "src", "lib.rs")) and "unwrap" in open(os.path.join(tree, "src", "lib.rs")).read(),
              "the result tree holds the edited library")
        check(not os.path.exists(os.path.join(tree, ".git")), "the result tree carries no .git")
        check(os.path.getsize(os.path.join(out, "skill-author-1", "transcript.jsonl")) > 0, "the transcript is kept")
        settings = json.load(open(os.path.join(out, "skill-author-1", "settings.json")))
        check(settings["enabledPlugins"]["rust-dev@coder-plugins"] is True, "the skill arm enables rust-dev@coder-plugins")

        env.pop("FAKE_CLAUDE_MODE")
        rc, so, se = run_py(["--arm", "bare", "--prompt", "author", "--runs", "1", "--out", out], env)
        bmeta = json.load(open(os.path.join(out, "bare-author-1", "meta.json"))) if rc == 0 else {}
        check(rc == 0 and bmeta.get("skill_invoked") is False, f"a bare run records skill_invoked false (rc={rc}) {se}")
        settings = json.load(open(os.path.join(out, "bare-author-1", "settings.json"))) if rc == 0 else {}
        check(settings.get("enabledPlugins", {}).get("rust-dev@coder-plugins") is False,
              "the bare arm disables rust-dev@coder-plugins")

        rc, gout = cli(["--results", out, "--arms", "skill,bare", "--expect-runs", "author=1"])
        check(rc == 0, f"grade.py grades the fake runs (rc={rc}):\n{gout}")
        g = grade.grade_run(os.path.join(out, "skill-author-1"))
        check(g["total"] == 1, f"the fake run's .unwrap() is counted (got {g['total']})")


def main():
    for name, fn in [("grader on fixtures", grader_fixture_cases), ("gradeability", gradeability_cases),
                     ("grade.py CLI", grade_cli_cases), ("verdict", verdict_cases),
                     ("run.py refusals", refusal_cases), ("run.py with a fake claude", fake_run_cases)]:
        print(f"== {name}")
        fn()
    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} check(s)")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nall stack-pilot checks passed")


if __name__ == "__main__":
    main()
