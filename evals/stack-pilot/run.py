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

Isolation. Every claude call runs inside bwrap, so no arm can read a copy of the
skill's text other than the one the arm is given (the installed SKILL.md for
`skill`, the rule file for `rule`, nothing for `bare`). Without it, a bare run
asked about "the house rules" greps ~/.claude and reads the skill off disk. The
stores that change during a batch (/tmp, session transcripts, the --out folder,
the other hosts' ports, ~/dev) are hidden under an empty tmpfs. Every other file
holding one of MARKERS, found by a scan at the start of the batch, is hidden
behind /dev/null. run.py refuses to run when bwrap cannot start; it never falls
back to an unisolated run. Scratch folders live under $STACK_PILOT_SCRATCH
(default /var/tmp/stack-pilot), outside the masked /tmp.

    run.py --isolation-probe --arm skill|bare|rule --out DIR

scans for MARKERS from inside the same wrapper, beside a canary file holding a
marker. It passes only when the scan finds exactly the canary plus the arm's own
copy; the result is merged into DIR/isolation.json.
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

# Phrases only the skill's owner text carries (two gotchas and an example), so a
# hit is a copy of the skill's facts, not generic Rust documentation.
MARKERS = ("BufRead::read_line() == 0", "invisible to integration tests", "`collab` → `multi_agent`")

_spec = importlib.util.spec_from_file_location("stack_pilot_grade", os.path.join(HERE, "grade.py"))
grade = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grade)


class Refused(Exception):
    pass


def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def rule_file():
    return os.path.join(config_dir(), "rules", RULE_NAME)


def scratch_base():
    base = os.environ.get("STACK_PILOT_SCRATCH") or "/var/tmp/stack-pilot"
    os.makedirs(base, exist_ok=True)
    return os.path.realpath(base)


def installed_skill_file():
    """The SKILL.md the skill arm loads: rust-dev's installPath in installed_plugins.json."""
    path = os.path.join(config_dir(), "plugins", "installed_plugins.json")
    try:
        entries = (json.load(open(path)).get("plugins") or {}).get(PLUGIN_ID) or []
    except (OSError, ValueError, AttributeError):
        entries = []
    for e in entries:
        if isinstance(e, dict) and e.get("installPath"):
            return os.path.join(e["installPath"], "skills", "rust-coding", "SKILL.md")
    raise Refused(f"cannot find {PLUGIN_ID}'s installPath in {path}; the skill arm needs the installed plugin")


def allowed_copies(arm):
    """The copies of the skill's text the arm is given, and may read."""
    if arm == "skill":
        return [os.path.realpath(installed_skill_file())]
    if arm == "rule":
        return [os.path.realpath(rule_file())]
    return []


def dir_masks(out):
    """Stores hidden under an empty tmpfs: they change during a batch, so a scan at its start
    cannot list their files. STACK_PILOT_DIR_MASKS (colon-separated) replaces the defaults in
    the unit test; the masks used are recorded in every meta.json."""
    home = os.path.expanduser("~")
    if "STACK_PILOT_DIR_MASKS" in os.environ:
        dirs = [d for d in os.environ["STACK_PILOT_DIR_MASKS"].split(":") if d]
    else:
        dirs = ["/tmp", os.path.join(config_dir(), "projects"), os.path.join(home, "dev"),
                os.path.join(home, ".agents"), os.path.join(home, ".codex"), os.path.join(home, ".cursor"),
                os.path.join(home, ".config", "opencode"), os.path.join(home, ".config", "superpowers"),
                os.path.join(home, ".config", "Cursor")]
    dirs.append(out)
    return sorted({os.path.realpath(d) for d in dirs if os.path.isdir(d)})


def scan_roots():
    env = os.environ.get("STACK_PILOT_SCAN_ROOTS")
    roots = env.split(":") if env else [os.path.expanduser("~"), "/tmp", "/var/tmp", "/mnt/vault"]
    return [r for r in roots if r and os.path.isdir(r)]


def scan_cmd(roots):
    pats = []
    for m in MARKERS:
        pats += ["-e", m]
    if shutil.which("rg"):
        return ["rg", "-l", "-uu", "--no-messages", "-F", *pats, "--", *roots]
    return ["grep", "-rlsF", *pats, "--", *roots]


def parse_hits(stdout):
    return sorted({os.path.realpath(line) for line in stdout.splitlines() if line.strip()})


def inside(path, dirs):
    return any(path == d or path.startswith(d.rstrip("/") + "/") for d in dirs)


def isolation_plan(arm, out):
    """(dir masks, file masks): what bwrap hides for this arm's batch."""
    dirs = dir_masks(os.path.realpath(out))
    allowed = allowed_copies(arm)
    base = scratch_base()
    for p in [base, *allowed]:
        if inside(p, dirs):
            raise Refused(f"{p} lies inside a masked folder ({dirs}); the run could not see it")
    p = subprocess.run(scan_cmd(scan_roots()), capture_output=True, text=True)
    if p.returncode not in (0, 1) and not p.stdout.strip():
        raise Refused(f"the scan for the skill's text failed (exit {p.returncode}): {p.stderr.strip()[-300:]}")
    files = [h for h in parse_hits(p.stdout)
             if h not in allowed and not inside(h, dirs) and not inside(h, [base]) and os.path.isfile(h)]
    return dirs, files


def bwrap_prefix(dirs, files, cwd):
    if not shutil.which("bwrap"):
        raise Refused("bwrap is not installed; the runs must not see the skill's text on disk (OD-5)")
    args = ["bwrap", "--dev-bind", "/", "/", "--die-with-parent"]
    for d in dirs:
        args += ["--tmpfs", d]
    for f in files:
        args += ["--ro-bind", "/dev/null", f]
    return args + ["--chdir", cwd, "--"]


def check_bwrap():
    try:
        p = subprocess.run(["bwrap", "--dev-bind", "/", "/", "--", "true"], capture_output=True, text=True)
    except FileNotFoundError:
        raise Refused("bwrap is not installed; the runs must not see the skill's text on disk (OD-5)")
    if p.returncode != 0:
        raise Refused(f"bwrap cannot start here ({p.stderr.strip()[-200:]}). Run from a terminal where "
                      f"unprivileged user namespaces are allowed (OD-6); run.py never runs unisolated.")


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


def run_claude(cwd, args, transcript, stderr_path, timeout, isolation):
    if not shutil.which("claude"):
        raise Refused("claude is not installed (not on PATH)")
    prefix = bwrap_prefix(*isolation, cwd)
    start = time.monotonic()
    timed_out = False
    with open(transcript, "w") as out, open(stderr_path, "w") as err:
        try:
            p = subprocess.run([*prefix, "claude", *args], cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                               timeout=timeout)
            code = p.returncode
        except subprocess.TimeoutExpired:
            code, timed_out = -9, True
        except FileNotFoundError:
            raise Refused("claude is not installed (not on PATH)")
    return code, round(time.monotonic() - start, 1), timed_out


def copy_result(proj, dst):
    shutil.copytree(proj, dst, ignore=shutil.ignore_patterns("target", ".git"))


def one_attempt(arm, prompt, n, folder, attempt, inputs_hash, timeout, isolation):
    rule_present = check_rule(arm)
    os.makedirs(folder)
    prompt_text = open(os.path.join(HERE, "prompts", f"{prompt}.txt")).read()
    scratch = tempfile.mkdtemp(prefix=f"stack-pilot-{arm}-{prompt}-{n}-", dir=scratch_base())
    try:
        proj = make_project(scratch, os.path.join(HERE, f"fixture-{prompt}"))
        # The hook runs inside the wrapper, where the --out folder is masked: it logs
        # into the scratch folder and the log is copied into the run folder after.
        log = os.path.join(scratch, "instructions.log")
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
        code, seconds, timed_out = run_claude(proj, args, transcript, stderr_path, timeout, isolation)
        if os.path.exists(log):
            shutil.copyfile(log, os.path.join(folder, "instructions.log"))
        log = os.path.join(folder, "instructions.log")

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
            "isolated": True, "masked_dirs": isolation[0], "masked_files": isolation[1],
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
    check_bwrap()
    os.makedirs(out, exist_ok=True)
    isolation = isolation_plan(arm, out)
    print(f"isolation: {len(isolation[0])} folder(s) and {len(isolation[1])} file(s) hidden for the {arm} arm")
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
        meta = one_attempt(arm, prompt, n, folder, 1, inputs_hash, timeout, isolation)
        if meta["environment"] == "failure":
            kept = aside(folder, "envfail")
            print(f"{name}: environment failure ({meta['environment_reason']}); first attempt kept as "
                  f"{os.path.basename(kept)}, running once more")
            meta = one_attempt(arm, prompt, n, folder, 2, inputs_hash, timeout, isolation)
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


def merge_json(path, key, value):
    try:
        merged = json.load(open(path))
        if not isinstance(merged, dict):
            merged = {}
    except (OSError, ValueError):
        merged = {}
    merged[key] = value
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(merged, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def isolation_probe(arm, out):
    """Scan for the skill's text from inside the wrapper the arm's runs use. Pass only when the
    scan finds exactly a canary written for it plus the arm's own copy: the canary shows the scan
    reaches unmasked places, and nothing else shows every other copy is hidden."""
    check_rule(arm)
    check_bwrap()
    os.makedirs(out, exist_ok=True)
    dirs, files = isolation_plan(arm, out)
    scratch = tempfile.mkdtemp(prefix=f"stack-pilot-isolation-{arm}-", dir=scratch_base())
    try:
        canary = os.path.join(scratch, "canary.md")
        with open(canary, "w") as fh:
            fh.write(f"canary: {MARKERS[0]}\n")
        roots = sorted(set(scan_roots()) | {scratch})
        p = subprocess.run([*bwrap_prefix(dirs, files, scratch), *scan_cmd(roots)], capture_output=True, text=True)
        found = parse_hits(p.stdout)
        expected = sorted({os.path.realpath(canary), *allowed_copies(arm)})
        result = {
            "arm": arm, "pass": found == expected, "found": found, "expected": expected,
            "scan_exit": p.returncode, "scan_roots": roots, "markers": list(MARKERS),
            "masked_dirs": dirs, "masked_files": len(files),
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    merge_json(os.path.join(out, "isolation.json"), arm, result)
    print(json.dumps(result))
    return 0 if result["pass"] else 1


def probe(arm, out, timeout):
    check_rule(arm)
    check_bwrap()
    os.makedirs(out, exist_ok=True)
    isolation = isolation_plan(arm, out)
    scratch = tempfile.mkdtemp(prefix=f"stack-pilot-probe-{arm}-", dir=scratch_base())
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
        code, seconds, timed_out = run_claude(proj, args, transcript, os.path.join(scratch, "stderr.txt"), timeout,
                                              isolation)
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
            "exit": code, "seconds": seconds, "isolated": True,
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    merge_json(os.path.join(out, "probe.json"), arm, result)
    print(json.dumps(result))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", required=True, choices=ARMS)
    ap.add_argument("--prompt", choices=PROMPTS)
    ap.add_argument("--runs", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--isolation-probe", action="store_true",
                    help="scan for the skill's text from inside the arm's wrapper; exit 0 only when isolated")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per claude call (default 1800)")
    a = ap.parse_args(argv)
    try:
        if a.isolation_probe:
            return isolation_probe(a.arm, a.out)
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
