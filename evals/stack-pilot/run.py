#!/usr/bin/env python3
"""run.py — run one arm of the stack-pilot comparison headless.

    run.py --arm skill|bare|rule --prompt author|audit --runs N --out DIR [--timeout S]
    run.py --probe --arm skill|bare|rule --out DIR

Arms:
  skill  rust-dev@coder-plugins enabled (the installed skill), rule file absent
  bare   rust-dev@coder-plugins disabled, rule file absent
  rule   rust-dev@coder-plugins disabled, --plugin-dir a temp copy of this
         branch's rust-dev/ without skills/, rule file present

The rule file is ${CLAUDE_CONFIG_DIR:-~/.claude}/rules/vault-stack-rust.md. The
skill and bare arms are refused while it exists and the rule arm while it does
not, before claude is ever called.

Each run copies the fixture into a scratch git folder, runs `claude -p` there
with an InstructionsLoaded hook logging into the run folder, and writes
DIR/<arm>-<prompt>-<n>/ holding tree/ (the result), transcript.jsonl,
stderr.txt, instructions.log, settings.json, diff.patch and meta.json. A run
whose folder already holds meta.json is kept, not re-run. A run that fails for
an environment reason (rate limit, network) is moved to <name>.envfail with
"environment": "failure" and run once more.

--probe makes one minimal headless call for the arm and prints a JSON object
with "skill_listed" (rust-dev:rust-coding in the session's init event); it is
merged into DIR/probe.json under the arm's name.
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PLUGIN_SRC = os.path.join(REPO, "rust-dev")
PLUGIN_ID = "rust-dev@coder-plugins"
SKILL_NAME = "rust-dev:rust-coding"
RULE_NAME = "vault-stack-rust.md"
ALLOWED_TOOLS = "Read,Write,Edit,Glob,Grep,Bash,Skill"
ARMS = ("skill", "bare", "rule")
PROMPTS = ("author", "audit")
LANE_RE = re.compile(r"(^|[^\w-])validate\.sh\b|rust-dev-validate")
ENV_RE = re.compile(
    r"rate[ _-]?limit|\b429\b|\b529\b|overloaded|API Error: 5\d\d|ECONNRESET|ECONNREFUSED|ETIMEDOUT|"
    r"ENOTFOUND|EAI_AGAIN|socket hang up|network|connection (error|refused|reset)|fetch failed|"
    r"usage limit|temporarily unavailable",
    re.IGNORECASE)

_spec = importlib.util.spec_from_file_location("stack_pilot_grade", os.path.join(HERE, "grade.py"))
grade = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grade)


class Refused(Exception):
    pass


def rule_file():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "rules", RULE_NAME)


def check_rule(arm):
    """Return whether the rule file is present, or raise Refused when the arm
    may not run in that state."""
    path = rule_file()
    present = os.path.exists(path)
    if arm in ("skill", "bare") and present:
        raise Refused(f"refusing the {arm} arm: the rule file {path} exists. The baseline arms must run "
                      f"before the rule is synced, so no baseline run can see it.")
    if arm == "rule" and not present:
        raise Refused(f"refusing the rule arm: the rule file {path} does not exist. Sync the rule first.")
    if arm == "rule" and not os.path.isfile(os.path.join(PLUGIN_SRC, "bin", "rust-dev-validate")):
        raise Refused(f"refusing the rule arm: {PLUGIN_SRC}/bin/rust-dev-validate is missing; "
                      f"the rule arm needs the plugin's bin/ commands")
    return present


def settings_for(arm, log_path):
    cmd = f"cat >> {shlex.quote(log_path)}; echo >> {shlex.quote(log_path)}"
    return {
        "enabledPlugins": {PLUGIN_ID: arm == "skill"},
        "hooks": {"InstructionsLoaded": [{"hooks": [{"type": "command", "command": cmd}]}]},
    }


def rule_plugin_copy(scratch):
    """A copy of the branch's rust-dev/ without skills/, for --plugin-dir."""
    dst = os.path.join(scratch, "plugin", "rust-dev")

    def ignore(d, names):
        drop = {"__pycache__", "target"}
        if os.path.abspath(d) == os.path.abspath(PLUGIN_SRC):
            drop.add("skills")
        return [n for n in names if n in drop]

    shutil.copytree(PLUGIN_SRC, dst, ignore=ignore)
    if not os.path.isfile(os.path.join(dst, "bin", "rust-dev-validate")):
        raise Refused(f"refusing the rule arm: {PLUGIN_SRC}/bin/rust-dev-validate is missing; "
                      f"the rule arm needs the plugin's bin/ commands")
    return dst


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=stack-pilot", "-c", "user.email=stack-pilot@localhost",
                    "-c", "commit.gpgsign=false", *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_project(scratch, fixture):
    """Copy the fixture into scratch/project and commit it, so the run's edits
    show up as a diff. An empty template dir keeps the user's git hooks out."""
    proj = os.path.join(scratch, "project")
    if fixture:
        shutil.copytree(fixture, proj, ignore=shutil.ignore_patterns("target", ".git"))
    else:
        os.makedirs(proj)
    template = os.path.join(scratch, "git-template")
    os.makedirs(template)
    git(proj, "init", "-q", f"--template={template}")
    git(proj, "add", "-A")
    git(proj, "commit", "-q", "--no-verify", "--allow-empty", "-m", "fixture")
    return proj


def read_events(path):
    events = []
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if isinstance(ev, dict):
                    events.append(ev)
    except OSError:
        pass
    return events


def init_event(events):
    for ev in events:
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            return ev
    return None


def plugin_names(init):
    out = []
    for p in (init or {}).get("plugins") or []:
        out.append(p.get("name") if isinstance(p, dict) else str(p))
    return out


def tool_uses(events):
    for ev in events:
        if ev.get("type") != "assistant":
            continue
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                yield item.get("name"), item.get("input") or {}


def summarize(events):
    skill_invoked = lane_run = False
    for name, inp in tool_uses(events):
        if name == "Skill" and str(inp.get("skill", "")).split(":")[-1] == "rust-coding":
            skill_invoked = True
        if name == "Bash" and LANE_RE.search(str(inp.get("command", ""))):
            lane_run = True
    results = [ev for ev in events if ev.get("type") == "result"]
    result = results[-1] if results else None
    init = init_event(events)
    return {
        "skill_invoked": skill_invoked,
        "lane_run": lane_run,
        "skill_listed": SKILL_NAME in ((init or {}).get("skills") or []),
        "result": result,
    }


def rule_loaded(log_path):
    """True when the hook log holds an InstructionsLoaded entry for the rule
    file with load_reason path_glob_match."""
    try:
        text = open(log_path, errors="replace").read()
    except OSError:
        return False
    dec, i = json.JSONDecoder(), 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        try:
            obj, i = dec.raw_decode(text, i)
        except ValueError:
            nl = text.find("\n", i)
            i = len(text) if nl < 0 else nl + 1
            continue
        if (isinstance(obj, dict) and str(obj.get("file_path", "")).endswith("/" + RULE_NAME)
                and obj.get("load_reason") == "path_glob_match"):
            return True
    return False


def environment_failure(exit_code, result, stderr_text):
    """The matched reason when a failed run failed for an environment reason."""
    if exit_code == 0 and result is not None and not result.get("is_error"):
        return None
    text = " ".join(str(x) for x in (
        (result or {}).get("result", ""), (result or {}).get("api_error_status", ""),
        (result or {}).get("subtype", ""), stderr_text[-4000:]))
    m = ENV_RE.search(text)
    return m.group(0) if m else None


def run_claude(cwd, args, transcript, stderr_path, timeout):
    start = time.monotonic()
    timed_out = False
    with open(transcript, "w") as out, open(stderr_path, "w") as err:
        try:
            p = subprocess.run(["claude", *args], cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                               timeout=timeout)
            code = p.returncode
        except subprocess.TimeoutExpired:
            code, timed_out = -9, True
        except FileNotFoundError:
            raise Refused("claude is not installed (not on PATH)")
    return code, round(time.monotonic() - start, 1), timed_out


def copy_result(proj, dst):
    shutil.copytree(proj, dst, ignore=shutil.ignore_patterns("target", ".git"))


def one_attempt(arm, prompt, n, folder, attempt, inputs_hash, timeout):
    rule_present = check_rule(arm)
    os.makedirs(folder)
    prompt_text = open(os.path.join(HERE, "prompts", f"{prompt}.txt")).read()
    scratch = tempfile.mkdtemp(prefix=f"stack-pilot-{arm}-{prompt}-{n}-")
    try:
        proj = make_project(scratch, os.path.join(HERE, f"fixture-{prompt}"))
        log = os.path.join(folder, "instructions.log")
        settings_path = os.path.join(folder, "settings.json")
        with open(settings_path, "w") as fh:
            json.dump(settings_for(arm, log), fh, indent=2)
        args = [ "-p", prompt_text, "--output-format", "stream-json", "--verbose",
                "--permission-mode", "acceptEdits", "--allowedTools", ALLOWED_TOOLS,
                "--settings", settings_path]
        if arm == "rule":
            args += ["--plugin-dir", rule_plugin_copy(scratch)]
        started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        transcript = os.path.join(folder, "transcript.jsonl")
        stderr_path = os.path.join(folder, "stderr.txt")
        code, seconds, timed_out = run_claude(proj, args, transcript, stderr_path, timeout)

        git(proj, "add", "-A")
        diff = subprocess.run(["git", "diff", "--cached", "HEAD"], cwd=proj, capture_output=True, text=True).stdout
        with open(os.path.join(folder, "diff.patch"), "w") as fh:
            fh.write(diff)
        copy_result(proj, os.path.join(folder, "tree"))

        s = summarize(read_events(transcript))
        result = s["result"]
        env_reason = environment_failure(code, result, open(stderr_path, errors="replace").read())
        with open(os.path.join(folder, "answer.txt"), "w") as fh:
            fh.write(str((result or {}).get("result", "")))
        meta = {
            "arm": arm, "prompt": prompt, "n": n, "attempt": attempt,
            "rule_present": rule_present, "rule_loaded": rule_loaded(log),
            "skill_invoked": s["skill_invoked"], "skill_listed": s["skill_listed"], "lane_run": s["lane_run"],
            "inputs_sha256": inputs_hash, "exit": code, "seconds": seconds, "timed_out": timed_out,
            "is_error": bool((result or {}).get("is_error")) if result else None,
            "result_subtype": (result or {}).get("subtype"),
            "environment": "failure" if env_reason else "ok", "environment_reason": env_reason,
            "rule_file": rule_file(), "started_at": started,
        }
        with open(os.path.join(folder, "meta.json"), "w") as fh:
            json.dump(meta, fh, indent=2)
            fh.write("\n")
        return meta
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def aside(folder, suffix):
    dst, k = f"{folder}.{suffix}", 2
    while os.path.exists(dst):
        dst, k = f"{folder}.{suffix}{k}", k + 1
    os.rename(folder, dst)
    return dst


def run_arm(arm, prompt, runs, out, timeout):
    check_rule(arm)
    os.makedirs(out, exist_ok=True)
    inputs_hash = grade.inputs_sha256()
    failed = []
    for n in range(1, runs + 1):
        name = f"{arm}-{prompt}-{n}"
        folder = os.path.join(out, name)
        if os.path.exists(os.path.join(folder, "meta.json")):
            print(f"{name}: kept (meta.json already there)")
            continue
        if os.path.exists(folder):
            print(f"{name}: an unfinished folder was moved to {aside(folder, 'aborted')}")
        meta = one_attempt(arm, prompt, n, folder, 1, inputs_hash, timeout)
        if meta["environment"] == "failure":
            kept = aside(folder, "envfail")
            print(f"{name}: environment failure ({meta['environment_reason']}); first attempt kept as "
                  f"{os.path.basename(kept)}, running once more")
            meta = one_attempt(arm, prompt, n, folder, 2, inputs_hash, timeout)
        status = "ok" if meta["exit"] == 0 and meta["environment"] == "ok" else "FAILED"
        print(f"{name}: {status} exit={meta['exit']} {meta['seconds']}s skill_invoked={meta['skill_invoked']} "
              f"lane_run={meta['lane_run']} rule_loaded={meta['rule_loaded']}"
              + (f" environment={meta['environment_reason']}" if meta["environment"] == "failure" else "")
              + (" (timed out)" if meta["timed_out"] else ""))
        if status != "ok":
            failed.append(name)
    if failed:
        print(f"run.py: {len(failed)} run(s) did not finish cleanly and will grade as ungradeable: "
              f"{', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


def probe(arm, out, timeout):
    check_rule(arm)
    scratch = tempfile.mkdtemp(prefix=f"stack-pilot-probe-{arm}-")
    try:
        proj = make_project(scratch, None)
        settings_path = os.path.join(scratch, "settings.json")
        with open(settings_path, "w") as fh:
            json.dump(settings_for(arm, os.path.join(scratch, "instructions.log")), fh)
        args = ["-p", "Reply OK.", "--max-turns", "1", "--output-format", "stream-json", "--verbose",
                "--settings", settings_path]
        if arm == "rule":
            args += ["--plugin-dir", rule_plugin_copy(scratch)]
        transcript = os.path.join(scratch, "probe.jsonl")
        code, seconds, timed_out = run_claude(proj, args, transcript, os.path.join(scratch, "stderr.txt"), timeout)
        init = init_event(read_events(transcript))
        if init is None:
            tail = open(os.path.join(scratch, "stderr.txt"), errors="replace").read()[-400:].strip()
            raise Refused(f"probe of the {arm} arm saw no init event (claude exit {code}"
                          f"{', timed out' if timed_out else ''}): cannot tell whether the skill is listed. "
                          f"stderr tail: {tail}")
        skills = init.get("skills") or []
        result = {
            "arm": arm,
            "skill_listed": SKILL_NAME in skills,
            "plugin_listed": "rust-dev" in plugin_names(init),
            "rust_dev_skills": sorted(s for s in skills if str(s).startswith("rust-dev:")),
            "exit": code, "seconds": seconds,
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "probe.json")
    try:
        merged = json.load(open(path))
        if not isinstance(merged, dict):
            merged = {}
    except (OSError, ValueError):
        merged = {}
    merged[arm] = result
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(merged, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
    print(json.dumps(result))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", required=True, choices=ARMS)
    ap.add_argument("--prompt", choices=PROMPTS)
    ap.add_argument("--runs", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per claude call (default 1800)")
    a = ap.parse_args(argv)
    try:
        if a.probe:
            return probe(a.arm, a.out, min(a.timeout, 300))
        if not a.prompt or not a.runs or a.runs < 1:
            ap.error("--prompt and a --runs of at least 1 are required unless --probe")
        return run_arm(a.arm, a.prompt, a.runs, a.out, a.timeout)
    except Refused as e:
        print(f"run.py: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
