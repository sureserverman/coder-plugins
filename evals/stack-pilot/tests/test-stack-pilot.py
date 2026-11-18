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
        "environment": "ok", "is_error": False, "result_subtype": "success",
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

        no_result = make_run(res, "skill", "audit", 2, tree_from=FIX_AUDIT, is_error=None, result_subtype=None)
        check(grade.grade_run(no_result)["status"] == "ungradeable",
              "a run whose transcript holds no result event (is_error null) is ungradeable")
        not_success = make_run(res, "skill", "audit", 3, tree_from=FIX_AUDIT, result_subtype="error_max_turns")
        check(grade.grade_run(not_success)["status"] == "ungradeable",
              "a run whose result is not a success is ungradeable")

        hidden = make_run(res, "bare", "audit", 1)
        copy_tree(FIX_AUDIT, os.path.join(hidden, "tree", "vendor", "crate"))
        write(os.path.join(hidden, "tree", "Cargo.toml"), "[package]\nname = \"x\"\n")
        g = grade.grade_run(hidden)
        check(g["status"] == "ungradeable",
              f"a tree whose .rs files the validator skips (under vendor/) is ungradeable, never 0 (got {g})")

    with tempfile.TemporaryDirectory() as tmp:
        lane = os.path.join(tmp, "validate-safety.sh")
        write(lane, "echo one\n")
        saved = grade.LANE_INPUTS
        try:
            grade.LANE_INPUTS = (lane,)
            before = grade.inputs_sha256()
            write(lane, "echo two\n")
            check(grade.inputs_sha256() != before, "inputs_sha256 changes when the validator that counts changes")
        finally:
            grade.LANE_INPUTS = saved
        check(any(p.endswith("validate-safety.sh") for p in grade.LANE_INPUTS)
              and any(p.endswith("findings.sh") for p in grade.LANE_INPUTS),
              "the hash covers validate-safety.sh and lib/findings.sh")


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
if "command -v rust-dev-validate" in args[args.index("-p") + 1]:
    found = "/x/plugin/rust-dev/bin/rust-dev-validate" if "--plugin-dir" in args else ""
    emit({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "b1", "name": "Bash", "input": {"command": "command -v rust-dev-validate"}}]}})
    emit({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "b1", "content": found}]}})
    emit({"type": "result", "subtype": "success", "is_error": False, "result": found or "not found"})
    sys.exit(0)
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


# A stand-in for bwrap: it logs its argv and runs the command after `--` in the
# --chdir folder. It masks nothing, so an isolation probe run through it must FAIL
# whenever a copy other than the arm's own sits in a scan root.
FAKE_BWRAP = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.path.join(os.environ["FAKE_CLAUDE_STATE"], "bwrap.log"), "a") as fh:
    fh.write(json.dumps(args) + "\n")
if os.environ.get("FAKE_BWRAP_FAIL"):
    print("bwrap: No permissions to create new namespace", file=sys.stderr)
    sys.exit(1)
rest = args[args.index("--") + 1:]
opts = args[:args.index("--")]
# Enforce the one part of masking a stand-in can: an inner argument naming a path
# under a --tmpfs folder would not exist inside the real wrapper.
masked = [opts[i + 1].rstrip("/") + "/" for i, a in enumerate(opts[:-1]) if a == "--tmpfs"]
for a in rest[1:]:
    if os.path.isabs(a) and any((os.path.realpath(a) + "/").startswith(m) for m in masked):
        print(f"fake bwrap: {a} is under a masked folder, so the wrapped command cannot see it", file=sys.stderr)
        sys.exit(1)
if "--chdir" in opts:
    os.chdir(args[args.index("--chdir") + 1])
os.execvp(rest[0], rest)
'''

MARKERS = load("stack_pilot_run", RUN_PY).MARKERS

SKILL_TEXT = "# rust-coding\n2. **`BufRead::read_line() == 0` means EOF, not \"nothing yet\".**\n"


def fake_env(tmp, rule_file):
    cfg = os.path.join(tmp, "cfg")
    os.makedirs(os.path.join(cfg, "rules"), exist_ok=True)
    rf = os.path.join(cfg, "rules", "vault-stack-rust.md")
    if rule_file:
        write(rf, "---\npaths: [\"**/*.rs\"]\n---\nrule: BufRead::read_line() == 0\n")
    elif os.path.exists(rf):
        os.remove(rf)
    install = os.path.join(cfg, "plugins", "cache", "coder-plugins", "rust-dev", "0.6.0")
    write(os.path.join(install, "skills", "rust-coding", "SKILL.md"), SKILL_TEXT)
    write(os.path.join(install, "scripts", "validate-safety.sh"), "# capacity is a compile-time small constant\n")
    write(os.path.join(cfg, "plugins", "installed_plugins.json"),
          json.dumps({"plugins": {"rust-dev@coder-plugins": [{"installPath": install}]}}))
    # An older cached version whose agent restates a house rule in the owner's words but
    # carries none of the gotcha phrases (the shape of the Stage 1 review's C1), and a
    # marketplace clone whose history holds the skill.
    write(os.path.join(cfg, "plugins", "cache", "coder-plugins", "rust-dev", "0.5.2", "agents", "rust-expert.md"),
          "3. **Bound every channel.** `unbounded_channel` only when the capacity is fixed and tiny.\n")
    write(os.path.join(cfg, "plugins", "marketplaces", "coder-plugins", "rust-dev", "README.md"), "rust-dev\n")
    write(os.path.join(cfg, "plugins", "marketplaces", "coder-plugins", ".git", "HEAD"), "ref: refs/heads/main\n")
    bindir = os.path.join(tmp, "bin")
    state = os.path.join(tmp, "state")
    os.makedirs(bindir, exist_ok=True)
    os.makedirs(state, exist_ok=True)
    for name, body in (("claude", FAKE_CLAUDE), ("bwrap", FAKE_BWRAP)):
        fake = os.path.join(bindir, name)
        write(fake, body)
        os.chmod(fake, 0o755)
    env = dict(os.environ)
    env.pop("FAKE_BWRAP_FAIL", None)
    env["CLAUDE_CONFIG_DIR"] = cfg
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
    env["FAKE_CLAUDE_STATE"] = state
    env["TMPDIR"] = os.path.join(tmp, "scratch")
    env["STACK_PILOT_SCRATCH"] = os.path.join(tmp, "scratch")
    os.makedirs(os.path.join(tmp, "scan"), exist_ok=True)
    env["STACK_PILOT_SCAN_ROOTS"] = os.path.join(tmp, "scan") + ":" + cfg
    env["STACK_PILOT_DIR_MASKS"] = ""
    env["STACK_PILOT_UNIT_TEST"] = "1"
    os.makedirs(env["TMPDIR"], exist_ok=True)
    return env, os.path.join(state, "calls.log")


def bwrap_calls(env):
    path = os.path.join(env["FAKE_CLAUDE_STATE"], "bwrap.log")
    if not os.path.exists(path):
        return []
    return [json.loads(line) for line in open(path) if line.strip()]


def masked_files(argv):
    return {argv[i + 2] for i, a in enumerate(argv[:-2]) if a == "--ro-bind" and argv[i + 1] == "/dev/null"}


def masked_dirs(argv):
    return {argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--tmpfs"}


def claude_calls_under_bwrap(env):
    return [c for c in bwrap_calls(env) if "--" in c and c[c.index("--") + 1:][:1] == ["claude"]]


def isolation_cases():
    """Every claude call runs inside bwrap with every copy but the arm's own hidden;
    no bwrap means no run; the isolation probe fails while a foreign copy is readable."""
    with tempfile.TemporaryDirectory() as tmp:
        env, calls = fake_env(tmp, rule_file=False)
        out = os.path.join(tmp, "out")
        cfgp = os.path.join(tmp, "cfg", "plugins")
        install_dir = os.path.realpath(os.path.join(cfgp, "cache", "coder-plugins", "rust-dev", "0.6.0"))
        installed = os.path.join(install_dir, "skills", "rust-coding", "SKILL.md")
        old_tree = os.path.realpath(os.path.join(cfgp, "cache", "coder-plugins", "rust-dev", "0.5.2"))
        market = os.path.realpath(os.path.join(cfgp, "marketplaces", "coder-plugins", "rust-dev"))
        market_git = os.path.realpath(os.path.join(cfgp, "marketplaces", "coder-plugins", ".git"))
        leak = os.path.join(tmp, "scan", "ports", "rust-coding", "SKILL.md")
        write(leak, SKILL_TEXT)
        leak = os.path.realpath(leak)
        write(os.path.join(tmp, "scan", "generic.md"), "Rust's read_line returns 0 at end of file.\n")

        fail_env = dict(env, FAKE_BWRAP_FAIL="1")
        for args in (["--arm", "bare", "--prompt", "author", "--runs", "1"], ["--probe", "--arm", "bare"],
                     ["--isolation-probe", "--arm", "bare"]):
            rc, so, se = run_py(args + ["--out", out], fail_env)
            check(rc == 2 and "bwrap cannot start" in se and "OD-6" in se,
                  f"run.py {args[0]} refuses when bwrap cannot start, never running unisolated (rc={rc}) {se}")
        check(not os.path.exists(calls), "a refused unisolated run never calls claude")
        no_bwrap = dict(env, PATH=os.pathsep.join(p for p in env["PATH"].split(os.pathsep)
                                                  if not os.path.exists(os.path.join(p, "bwrap"))))
        shutil.copy(os.path.join(tmp, "bin", "claude"), os.path.join(tmp, "claude-only"))
        no_bwrap["PATH"] = tmp + os.pathsep + no_bwrap["PATH"]
        os.rename(os.path.join(tmp, "claude-only"), os.path.join(tmp, "claude"))
        rc, so, se = run_py(["--arm", "bare", "--prompt", "author", "--runs", "1", "--out", out], no_bwrap)
        check(rc == 2 and "bwrap is not installed" in se, f"run.py refuses when bwrap is missing (rc={rc}) {se}")

        real = {k: v for k, v in env.items() if k != "STACK_PILOT_UNIT_TEST"}
        rc, so, se = run_py(["--arm", "bare", "--prompt", "author", "--runs", "1", "--out", out], real)
        check(rc == 2 and "STACK_PILOT_SCAN_ROOTS" in se,
              f"outside the unit test the scan and mask overrides are refused (rc={rc}) {se}")
        noisy = os.path.join(tmp, "noisy")
        scan_root = os.path.realpath(os.path.join(tmp, "scan"))
        o_dead = os.path.realpath(os.path.join(tmp, "o-dead"))
        for name, err in (("dead", f"rg: {o_dead}/.mount_app: Transport endpoint is not connected (os error 107)"),
                          ("io", "rg: /mnt/disk/f: Input/output error (os error 5)"),
                          ("deadroot", f"rg: {scan_root}: Transport endpoint is not connected (os error 107)"),
                          ("deadunmasked", f"rg: {scan_root}/sub/.mount_x: Transport endpoint is not connected (os error 107)"),
                          ("goneroot", f"rg: {scan_root}: No such file or directory (os error 2)")):
            write(os.path.join(noisy, name, "rg"), f"#!/bin/sh\necho '{err}' >&2\nexit 2\n")
            os.chmod(os.path.join(noisy, name, "rg"), 0o755)
        rc, so, se = run_py(["--arm", "bare", "--prompt", "author", "--runs", "1", "--out", os.path.join(tmp, "o-dead")],
                            dict(env, PATH=os.path.join(noisy, "dead") + os.pathsep + env["PATH"]))
        check(rc == 0, f"a dead FUSE mount inside a masked folder does not stop the batch (rc={rc}) {se}")
        for name, why in (("deadroot", "a scan root that dies mid-scan"),
                          ("deadunmasked", "a dead mount the run would see unmasked once it remounts"),
                          ("goneroot", "a scan root that vanishes mid-scan")):
            rc, so, se = run_py(["--arm", "bare", "--prompt", "author", "--runs", "1",
                                 "--out", os.path.join(tmp, f"o-{name}")],
                                dict(env, PATH=os.path.join(noisy, name) + os.pathsep + env["PATH"]))
            check(rc == 2 and scan_root in se, f"{why} is refused, never counted as scanned (rc={rc}) {se}")
        rc, so, se = run_py(["--arm", "bare", "--prompt", "author", "--runs", "1", "--out", os.path.join(tmp, "o-io")],
                            dict(env, PATH=os.path.join(noisy, "io") + os.pathsep + env["PATH"]))
        check(rc == 2 and "Input/output error" in se, f"any other scanner error is refused (rc={rc}) {se}")
        gone = dict(env, STACK_PILOT_SCAN_ROOTS=env["STACK_PILOT_SCAN_ROOTS"] + ":" + os.path.join(tmp, "no-such-root"))
        rc, so, se = run_py(["--arm", "bare", "--prompt", "author", "--runs", "1", "--out", out], gone)
        check(rc == 2 and "no-such-root" in se, f"a scan root that is absent is refused, never skipped (rc={rc}) {se}")

        for arm in ("skill", "bare"):
            rc, so, se = run_py(["--arm", arm, "--prompt", "author", "--runs", "1", "--out", out], env)
            check(rc == 0, f"the {arm} arm runs under the wrapper (rc={rc}) {so}{se}")
            runs = claude_calls_under_bwrap(env)
            check(len(runs) >= 1, f"the {arm} run's claude call went through bwrap")
            argv = runs[-1] if runs else []
            check("--unshare-pid" in argv and "--proc" in argv,
                  f"the {arm} arm gets its own PID namespace and /proc, so /proc/<pid>/root shows no unmasked view")
            check(leak in masked_files(argv), f"the {arm} arm hides a foreign copy of the skill's text")
            check(os.path.realpath(out) in masked_dirs(argv), f"the {arm} arm hides the --out folder")
            check(os.path.realpath(os.path.join(tmp, "scan", "generic.md")) not in masked_files(argv),
                  f"the {arm} arm leaves a file without the markers alone")
            check({old_tree, market, market_git} <= masked_dirs(argv),
                  f"the {arm} arm hides every other rust-dev tree, the marketplace copy and its .git by path")
            if arm == "skill":
                check(install_dir not in masked_dirs(argv) and installed not in masked_files(argv),
                      "the skill arm keeps its own installed plugin, skill included")
            else:
                check(install_dir in masked_dirs(argv), "the bare arm hides the installed plugin too")
            mpath = os.path.join(out, f"{arm}-author-1", "meta.json")
            meta = json.load(open(mpath)) if os.path.exists(mpath) else {}
            check(meta.get("isolated") is True and leak in (meta.get("masked_files") or [])
                  and old_tree in (meta.get("masked_dirs") or []),
                  f"the {arm} run's meta.json records isolated true and what was hidden")
            check(meta.get("scan_roots") == env["STACK_PILOT_SCAN_ROOTS"].split(":"),
                  f"the {arm} run's meta.json records the scan roots")
            check(meta.get("lane_commands") == ["bash /x/scripts/validate.sh . --json"],
                  f"the {arm} run's meta.json records the command that counted as the lane")
            check(meta.get("rule_loaded") is True,
                  f"the hook log written inside the wrapper still reaches the {arm} run folder")

        rc, so, se = run_py(["--isolation-probe", "--arm", "skill", "--out", out], env)
        iso = json.load(open(os.path.join(out, "isolation.json"))).get("skill", {}) if rc in (0, 1) else {}
        check(rc == 1 and iso.get("pass") is False and leak in iso.get("found", []),
              f"the isolation probe fails while a foreign copy is readable, naming it (rc={rc}) {so}{se}")
        check(not any(m in so + se for m in MARKERS),
              "the isolation probe prints no marker phrase, so its own output is not a new copy")
        os.remove(leak)
        rc, so, se = run_py(["--isolation-probe", "--arm", "skill", "--out", out], env)
        iso = json.load(open(os.path.join(out, "isolation.json"))).get("skill", {}) if rc in (0, 1) else {}
        check(rc == 1 and any("0.5.2" in f for f in iso.get("found_paths", [])),
              f"the probe fails on a readable rust-dev tree by path, whatever its text (rc={rc}) {iso.get('found_paths')}")

        stale = os.path.join(env["STACK_PILOT_SCRATCH"], "old-batch.log")
        write(stale, "an old log quoting BufRead::read_line() == 0\n")
        two_roots = dict(env, STACK_PILOT_SCAN_ROOTS=env["STACK_PILOT_SCAN_ROOTS"] + ":" + env["STACK_PILOT_SCRATCH"])
        rc, so, se = run_py(["--arm", "bare", "--prompt", "audit", "--runs", "1", "--out", out], two_roots)
        runs = claude_calls_under_bwrap(env)
        check(rc == 0 and runs and os.path.realpath(stale) in masked_files(runs[-1]),
              f"a copy inside the scratch base is hidden too (rc={rc}) {se}")
        os.remove(stale)
        for d in (old_tree, market, market_git):
            shutil.rmtree(d)
        rc, so, se = run_py(["--isolation-probe", "--arm", "skill", "--out", out], env)
        iso = json.load(open(os.path.join(out, "isolation.json"))).get("skill", {}) if rc in (0, 1) else {}
        check(rc == 0 and iso.get("pass") is True and installed in iso.get("found", [])
              and any(f.endswith("canary.md") for f in iso.get("found", [])),
              f"the probe passes when only the canary and the arm's own plugin are found (rc={rc}) {so}{se}")
        rc, so, se = run_py(["--isolation-probe", "--arm", "bare", "--out", out], env)
        check(rc == 1, f"the bare probe fails while the installed plugin is readable to it (rc={rc})")
        blind = dict(env, PATH=os.path.join(tmp, "blind") + os.pathsep + env["PATH"])
        for tool in ("rg", "grep"):
            write(os.path.join(tmp, "blind", tool), "#!/bin/sh\nexit 1\n")
            os.chmod(os.path.join(tmp, "blind", tool), 0o755)
        rc, so, se = run_py(["--isolation-probe", "--arm", "skill", "--out", out], blind)
        iso = json.load(open(os.path.join(out, "isolation.json"))).get("skill", {}) if rc in (0, 1) else {}
        check(rc == 1 and iso.get("canary_found") is False,
              f"a scan that finds nothing (not even the canary) fails the probe (rc={rc}) {iso.get('canary_found')}")
        nofind = dict(env, PATH=os.path.join(tmp, "nofind") + os.pathsep + env["PATH"])
        write(os.path.join(tmp, "nofind", "find"), "#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(tmp, "nofind", "find"), 0o755)
        rc, so, se = run_py(["--isolation-probe", "--arm", "skill", "--out", out], nofind)
        iso = json.load(open(os.path.join(out, "isolation.json"))).get("skill", {}) if rc in (0, 1) else {}
        check(rc == 1 and iso.get("own_path_found") is False,
              f"a path scan that lists nothing, not even the arm's own copy, fails the probe (rc={rc})")
        empty_root = os.path.join(tmp, "empty-root")
        os.makedirs(empty_root)
        with_empty = dict(env, STACK_PILOT_SCAN_ROOTS=env["STACK_PILOT_SCAN_ROOTS"] + ":" + empty_root)
        rc, so, se = run_py(["--isolation-probe", "--arm", "skill", "--out", out], with_empty)
        iso = json.load(open(os.path.join(out, "isolation.json"))).get("skill", {}) if rc in (0, 1) else {}
        check(rc == 1 and os.path.realpath(empty_root) in (iso.get("empty_roots") or []),
              f"an unmasked scan root that lists nothing inside the wrapper fails the probe (rc={rc})")


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


def rule_probe_cases():
    """--probe --arm rule shows whether the plugin's bin/ commands are on the session's PATH."""
    with tempfile.TemporaryDirectory() as tmp:
        env, calls = fake_env(tmp, rule_file=True)
        out = os.path.join(tmp, "out")
        rc, so, se = run_py(["--probe", "--arm", "rule", "--out", out], env)
        probe = json.load(open(os.path.join(out, "probe.json"))).get("rule", {}) if rc == 0 else {}
        check(rc == 0 and probe.get("bin_on_path") is True and probe.get("skill_listed") is False,
              f"the rule probe records rust-dev-validate on PATH and no skill (rc={rc}) {so}{se}")


def session_store_cases():
    """The default masks hide every config store a live Claude session copies file content
    into during a batch: an edit made while the batch runs lands there after the scan."""
    run = load("stack_pilot_run", os.path.join(os.path.dirname(GRADE_PY), "run.py"))
    with tempfile.TemporaryDirectory() as tmp:
        cfg = os.path.join(tmp, "cfg")
        stores = ("projects", "file-history", "backups", "paste-cache")
        for d in stores:
            os.makedirs(os.path.join(cfg, d))
        saved = {k: os.environ.get(k) for k in ("CLAUDE_CONFIG_DIR", "STACK_PILOT_DIR_MASKS")}
        os.environ["CLAUDE_CONFIG_DIR"] = cfg
        os.environ.pop("STACK_PILOT_DIR_MASKS", None)
        try:
            masks = run.dir_masks("bare", os.path.join(tmp, "out"))
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        for d in stores:
            check(os.path.realpath(os.path.join(cfg, d)) in masks,
                  f"the default masks hide the config store {d}/")
        other = os.path.join(tmp, "unrelated-vault")
        os.makedirs(other)
        saved_mounts = getattr(run, "UNRELATED_MOUNTS", None)
        run.UNRELATED_MOUNTS = (other,)
        os.environ.pop("STACK_PILOT_DIR_MASKS", None)
        os.environ["CLAUDE_CONFIG_DIR"] = cfg
        try:
            masks = run.dir_masks("bare", os.path.join(tmp, "out"))
            try:
                roots, why = run.scan_roots(), ""
            except run.Refused as e:
                roots, why = [], str(e)
        finally:
            run.UNRELATED_MOUNTS = saved_mounts
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        check(saved_mounts is not None and os.path.realpath(other) in masks,
              "an unrelated mount (the second vault) is hidden from the runs whole")
        check(other not in roots and other not in why and "/mnt/vault2" not in roots,
              "the scan never reads the second vault")
        root = "/srv/notes"
        for line, want, why in (
                ("find: ‘/srv/notes’: No such file or directory", False, "find's quoted form of a vanished root"),
                ("rg: /srv/notes: Transport endpoint is not connected (os error 107)", False, "a dead root"),
                ("find: ‘/srv/notes/a/b’: Permission denied", True, "a folder no one can read"),
                ("rg: /srv/notes/gone.md: No such file or directory (os error 2)", True, "a file that vanished"),
                ("rg: /srv/notes/f: Input/output error (os error 5)", False, "an I/O error")):
            check(run.tolerated(line, [root], []) is want, f"scan error, {why}: tolerated={want}")


def reuse_scan_cases():
    """--reuse-scan: a passed isolation probe saves its scan (paths only), and the arm's listing
    probe and runs reuse it instead of scanning again; no saved scan, a failed probe, a scan from
    another arm or marker set, or an old one is refused, never a silent fresh start."""
    with tempfile.TemporaryDirectory() as tmp:
        env, calls = fake_env(tmp, rule_file=False)
        out = os.path.join(tmp, "out")
        cfgp = os.path.join(tmp, "cfg", "plugins")
        for d in (os.path.join(cfgp, "cache", "coder-plugins", "rust-dev", "0.5.2"),
                  os.path.join(cfgp, "marketplaces", "coder-plugins")):
            shutil.rmtree(d)
        counter = os.path.join(tmp, "count")
        real_rg = shutil.which("rg")
        os.makedirs(counter)
        for tool, real in (("rg", real_rg), ("grep", shutil.which("grep"))):
            if real:
                write(os.path.join(counter, tool),
                      f"#!/bin/sh\necho {tool} \"$@\" >> {os.path.join(tmp, 'scans.log')}\nexec {real} \"$@\"\n")
                os.chmod(os.path.join(counter, tool), 0o755)
        env["PATH"] = counter + os.pathsep + env["PATH"]
        root_dirs = set(env["STACK_PILOT_SCAN_ROOTS"].split(":"))
        # A full scan names a scan root as an argument; the incremental pass names only files.
        scans = lambda: sum(1 for line in open(os.path.join(tmp, "scans.log"))
                            if root_dirs & set(line.split())) \
            if os.path.exists(os.path.join(tmp, "scans.log")) else 0
        cache = os.path.join(env["STACK_PILOT_SCRATCH"], "scan-skill.json")
        leak = os.path.join(tmp, "scan", "notes", "copy.md")
        write(leak, SKILL_TEXT)

        rc, so, se = run_py(["--arm", "skill", "--prompt", "author", "--runs", "1", "--out", out, "--reuse-scan"], env)
        check(rc == 2 and "no saved scan" in se, f"--reuse-scan with no saved scan is refused (rc={rc}) {se}")

        os.remove(leak)
        rc, so, se = run_py(["--isolation-probe", "--arm", "skill", "--out", out], env)
        check(rc == 0 and os.path.exists(cache), f"a passed isolation probe saves its scan (rc={rc}) {so}{se}")
        saved = json.load(open(cache)) if os.path.exists(cache) else {}
        check(not any(m in open(cache).read() for m in MARKERS) if saved else False,
              "the saved scan holds paths only, no marker phrase")

        write(leak, SKILL_TEXT)
        upper = os.path.join(tmp, "scan", "notes", "upper.md")
        write(upper, MARKERS[3].upper() + "\n")
        before = scans()
        rc, so, se = run_py(["--arm", "skill", "--prompt", "author", "--runs", "1", "--out", out, "--reuse-scan"], env)
        check(rc == 0 and scans() == before, f"a run with --reuse-scan does not scan the roots again (rc={rc}, "
              f"scans {before}->{scans()}) {se}")
        mpath = os.path.join(out, "skill-author-1", "meta.json")
        meta = json.load(open(mpath)) if os.path.exists(mpath) else {}
        check(os.path.realpath(leak) in (meta.get("masked_files") or []),
              "a copy written after the saved scan is still found and hidden (the files changed since are checked)")
        check(os.path.realpath(upper) in (meta.get("masked_files") or []),
              "a marker phrase in another letter case is found and hidden")
        check(meta.get("scan_at") == saved.get("at") and meta.get("scan_reused") is True,
              f"the run's meta.json records the reused scan and when it ran {meta.get('scan_at')}")
        rc, so, se = run_py(["--probe", "--arm", "skill", "--out", out, "--reuse-scan"], env)
        check(rc == 0 and scans() == before, f"the listing probe with --reuse-scan does not scan again (rc={rc}) {se}")
        before = scans()
        rc, so, se = run_py(["--arm", "skill", "--prompt", "audit", "--runs", "1", "--out", out], env)
        check(rc == 0 and scans() > before, f"without --reuse-scan a run still scans (rc={rc})")
        os.remove(leak)

        os.remove(upper)
        rc, so, se = run_py(["--arm", "skill", "--prompt", "author", "--runs", "1",
                             "--out", os.path.join(tmp, "other-out"), "--reuse-scan"], env)
        check(rc == 2 and "saved scan" in se and "mask" in se,
              f"a saved scan filtered against other masks (another --out) is refused (rc={rc}) {se}")
        rc, so, se = run_py(["--arm", "bare", "--prompt", "author", "--runs", "1", "--out", out, "--reuse-scan"], env)
        check(rc == 2 and "no saved scan" in se, f"another arm's saved scan is not reused (rc={rc}) {se}")
        for field, value, why in (("markers_sha256", "0" * 64, "a scan for another marker set"),
                                  ("at", "2000-01-01T00:00:00+00:00", "a scan older than the limit"),
                                  ("roots", ["/elsewhere"], "a scan of other roots")):
            write(cache, json.dumps(dict(saved, **{field: value})))
            rc, so, se = run_py(["--arm", "skill", "--prompt", "author", "--runs", "2", "--out", out,
                                 "--reuse-scan"], env)
            check(rc == 2 and "saved scan" in se and "usage:" not in se, f"{why} is refused (rc={rc}) {se}")
        write(cache, json.dumps(saved))
        write(leak, SKILL_TEXT)
        rc, so, se = run_py(["--isolation-probe", "--arm", "skill", "--out", out], env)
        check(rc == 1 and not os.path.exists(cache),
              f"a failed probe deletes the scan an earlier probe saved (rc={rc})")
        rc, so, se = run_py(["--arm", "skill", "--prompt", "author", "--runs", "2", "--out", out, "--reuse-scan"], env)
        check(rc == 2 and "no saved scan" in se, f"so --reuse-scan after a failed probe is refused (rc={rc}) {se}")


def main():
    for name, fn in [("grader on fixtures", grader_fixture_cases), ("gradeability", gradeability_cases),
                     ("grade.py CLI", grade_cli_cases), ("verdict", verdict_cases),
                     ("run.py refusals", refusal_cases), ("run.py with a fake claude", fake_run_cases),
                     ("run.py isolation", isolation_cases), ("run.py rule probe", rule_probe_cases),
                     ("run.py session stores", session_store_cases),
                     ("run.py --reuse-scan", reuse_scan_cases)]:
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
