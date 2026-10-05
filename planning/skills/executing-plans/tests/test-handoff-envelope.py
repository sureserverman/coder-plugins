#!/usr/bin/env python3
"""Fixture suite for scripts/handoff-envelope.py — run directly (CI convention):
    python3 planning/skills/executing-plans/tests/test-handoff-envelope.py

Asserts the script's contract: `new-id` mints distinct `h-` + 20-hex ids; each
envelope carries exactly the version-1 protocol keys; `ready`/`accept`/`fail`
write nothing when REMOTE_AGENTS_SESSION_ID is unset or empty; a linked
`.claude` or `.claude/handoffs` is refused and its target untouched; `verify`
exits 3 with the right failure code for a wrong id, a right id only in an
earlier block, a wrong cwd, a wrong branch, a missing ready and an unreadable
plan, and exits 0 when the plan's last RESUME HERE block matches; the request
reader refuses an oversized or linked request.json and matches the id.

Every subprocess runs with REMOTE_AGENTS_SESSION_ID stripped unless a case sets
it, inside temp dirs and fixture git repos made with `git init`.

Stdlib only.
"""
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "handoff-envelope.py")
ENV_VAR = "REMOTE_AGENTS_SESSION_ID"
ID_RE = re.compile(r"^h-[0-9a-f]{20}$")
SID = "ra-session_01"
BASE_KEYS = {"protocol", "version", "event", "handoff_id", "managed_session_id",
             "timestamp", "plan"}

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def env_for(sid=None):
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR}
    if sid is not None:
        env[ENV_VAR] = sid
    return env


def run(args, sid=None, cwd=None):
    """Run the script; return (rc, stdout, stderr)."""
    r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True,
                       env=env_for(sid), cwd=cwd or tempfile.gettempdir())
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def git_repo(parent, name, branch):
    """A fresh repo on `branch`; returns its path."""
    d = pathlib.Path(parent) / name
    d.mkdir()
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "checkout", "-q", "-b", branch], check=True)
    return d


def tree(d):
    """Every path under d, relative, sorted (empty list when d is absent)."""
    d = pathlib.Path(d)
    if not d.exists():
        return []
    return sorted(str(p.relative_to(d)) for p in d.rglob("*"))


def block(hid, cwd, branch, date="2026-10-05"):
    lines = [f"**RESUME HERE ({date}):**"]
    if hid is not None:
        lines.append(f"handoff_id: {hid}")
    lines += ["reason: rule context: now=1 of window=2 (table) is 50.1% > 50%",
              f"plan: /some/plan.md   cwd: {cwd}   branch: {branch} (at `abc1234`)",
              "next: Task 2.1 — something",
              "`dispatch: 0 of 0`  `review: none`  `residuals: none`",
              "**Decisions in force:** DEC-001", ""]
    return "\n".join(lines)


def plan_with(path, *blocks):
    path.write_text("# A plan\n\n## Stage 1\n\nStatus: [x]\n\n" + "\n".join(blocks),
                    encoding="utf-8")
    return path


tmp = tempfile.mkdtemp(prefix="handoff-envelope-test-")
try:
    print("script exists")
    check(os.path.isfile(SCRIPT), f"{SCRIPT} exists")

    # 1. new-id
    print("new-id")
    ids = []
    for _ in range(100):
        rc, out, _err = run(["new-id", "--root", tmp])
        ids.append(out if rc == 0 else None)
    check(all(i is not None and ID_RE.match(i) for i in ids),
          f"100 new-id values all match ^h-[0-9a-f]{{20}}$ (first: {ids[0]!r})")
    check(len(set(ids)) == 100, f"100 new-id values are distinct ({len(set(ids))})")

    rc, _out, _err = run(["ready", "--root", tmp, "--handoff-id", "h-123", "--plan", "/p.md"],
                         sid=SID)
    check(rc == 2 and os.path.isfile(SCRIPT),
          f"a --handoff-id failing the pattern exits 2 ({rc})")
    check(not (pathlib.Path(tmp) / ".claude").exists(), "and writes nothing")

    # 2. exact keys per event
    print("envelope keys")
    r2 = pathlib.Path(tmp) / "keys"
    r2.mkdir()
    hid = "h-" + "a" * 20
    plan_rel = "plan.md"
    hdir = r2 / ".claude" / "handoffs"
    cases = (
        ("ready", ["--plan", plan_rel], "ready", "HANDOFF_READY", BASE_KEYS),
        ("accept", ["--plan", plan_rel], "accepted", "HANDOFF_ACCEPTED", BASE_KEYS),
        ("fail", ["--code", "cwd-mismatch", "--plan", plan_rel], "failed", "HANDOFF_FAILED",
         BASE_KEYS | {"failure_code"}),
    )
    for cmd, extra, suffix, event, keys in cases:
        rc, out, err = run([cmd, "--root", str(r2), "--handoff-id", hid, *extra], sid=SID,
                           cwd=str(r2))
        f = hdir / f"{hid}.{suffix}.json"
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        check(rc == 0 and isinstance(data, dict) and set(data) == keys,
              f"{cmd} -> {f.name} has exactly {sorted(keys)} "
              f"({rc}, {sorted(data) if isinstance(data, dict) else data}, {err})")
        if isinstance(data, dict):
            check(data.get("protocol") == "remote-agents-handoff" and data.get("version") == 1
                  and data.get("event") == event and data.get("handoff_id") == hid
                  and data.get("managed_session_id") == SID
                  and data.get("plan") == str(r2 / plan_rel)
                  and isinstance(data.get("timestamp"), str)
                  and re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|\+00:00)$",
                               data["timestamp"]),
                  f"{cmd} values: protocol/version/event/id/session/absolute plan/UTC timestamp "
                  f"({data})")
    try:
        fdata = json.loads((hdir / f"{hid}.failed.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        fdata = {}
    check(fdata.get("failure_code") == "cwd-mismatch", "fail records its failure_code")
    hid2 = "h-" + "b" * 20
    rc, _out, _err = run(["fail", "--root", str(r2), "--handoff-id", hid2, "--code", "no-ready"],
                         sid=SID)
    try:
        d2 = json.loads((hdir / f"{hid2}.failed.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d2 = None
    check(rc == 0 and isinstance(d2, dict) and set(d2) == BASE_KEYS | {"failure_code"}
          and d2.get("plan") is None,
          f"fail without --plan keeps the exact key set, plan null ({d2})")
    rc, _out, _err = run(["fail", "--root", str(r2), "--handoff-id", hid2, "--code", "bogus"],
                         sid=SID)
    check(rc == 2 and os.path.isfile(SCRIPT), f"fail --code outside the five codes exits 2 ({rc})")
    gi = hdir / ".gitignore"
    check(gi.is_file() and gi.read_text(encoding="utf-8") == "*\n",
          "the first write creates .claude/handoffs/.gitignore containing '*'")
    leftovers = [n for n in tree(hdir) if n.endswith(".tmp")]
    check(not leftovers, f"no temp files left behind ({leftovers})")

    # 3. unsupervised -> nothing written
    print("unsupervised")
    for label, sid in (("unset", None), ("empty", "")):
        r3 = pathlib.Path(tmp) / f"unsup-{label}"
        r3.mkdir()
        outs = []
        for cmd, extra in (("ready", ["--plan", "p.md"]), ("accept", ["--plan", "p.md"]),
                           ("fail", ["--code", "id-mismatch"])):
            rc, out, _err = run([cmd, "--root", str(r3), "--handoff-id", hid, *extra], sid=sid)
            outs.append((rc, out))
        check(all(o == (0, "unsupervised") for o in outs),
              f"env {label}: ready/accept/fail exit 0 printing 'unsupervised' ({outs})")
        check(tree(r3 / ".claude" / "handoffs") == [],
              f"env {label}: nothing exists under .claude/handoffs/ ({tree(r3)})")
    rc, _out, _err = run(["ready", "--root", str(pathlib.Path(tmp) / "unsup-unset"),
                          "--handoff-id", hid, "--plan", "p.md"], sid="bad/id")
    check(rc != 0 and tree(pathlib.Path(tmp) / "unsup-unset" / ".claude" / "handoffs") == [],
          f"an invalid session id writes nothing and exits non-zero ({rc})")

    # 4. linked .claude/handoffs and .claude are refused
    print("links refused")
    r4 = pathlib.Path(tmp) / "linked"
    (r4 / ".claude").mkdir(parents=True)
    target = pathlib.Path(tmp) / "link-target"
    target.mkdir()
    (r4 / ".claude" / "handoffs").symlink_to(target)
    rc, _out, _err = run(["ready", "--root", str(r4), "--handoff-id", hid, "--plan", "p.md"],
                         sid=SID)
    check(rc != 0 and tree(target) == [] and (r4 / ".claude" / "handoffs").is_symlink(),
          f"a symlinked .claude/handoffs is refused and its target untouched ({rc}, {tree(target)})")
    r4b = pathlib.Path(tmp) / "linked-claude"
    r4b.mkdir()
    target_b = pathlib.Path(tmp) / "link-target-b"
    target_b.mkdir()
    (r4b / ".claude").symlink_to(target_b)
    rc, _out, _err = run(["accept", "--root", str(r4b), "--handoff-id", hid, "--plan", "p.md"],
                         sid=SID)
    check(rc != 0 and tree(target_b) == [],
          f"a symlinked .claude is refused and its target untouched ({rc}, {tree(target_b)})")
    # A planted link at the envelope name is replaced, never written through.
    r4c = pathlib.Path(tmp) / "linked-file"
    (r4c / ".claude" / "handoffs").mkdir(parents=True)
    victim = pathlib.Path(tmp) / "victim.txt"
    victim.write_text("keep", encoding="utf-8")
    (r4c / ".claude" / "handoffs" / f"{hid}.ready.json").symlink_to(victim)
    rc, _out, _err = run(["ready", "--root", str(r4c), "--handoff-id", hid, "--plan", "p.md"],
                         sid=SID)
    check(rc == 0 and victim.read_text(encoding="utf-8") == "keep"
          and not (r4c / ".claude" / "handoffs" / f"{hid}.ready.json").is_symlink(),
          f"a link at the envelope's name is replaced; the file it named is untouched ({rc})")

    # 5 + 6. verify
    print("verify")
    plans = pathlib.Path(tmp) / "plans"
    plans.mkdir()
    repo = git_repo(tmp, "repo", "feat/handoff")
    rc_b = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"],
                          capture_output=True, text=True).stdout.strip()
    check(rc_b == "feat/handoff", f"fixture repo is on feat/handoff ({rc_b!r})")
    good = "h-" + "c" * 20
    other = "h-" + "d" * 20
    rc, _out, err = run(["ready", "--root", str(repo), "--handoff-id", good,
                         "--plan", str(plans / "good.md")], sid=SID)
    check(rc == 0, f"fixture ready written ({rc}, {err})")

    def verify(plan, hid=good, root=repo):
        return run(["verify", "--root", str(root), "--handoff-id", hid, "--plan", str(plan)])

    p_ok = plan_with(plans / "good.md", block(other, repo, "feat/handoff", "2026-10-01"),
                     block(good, repo, "feat/handoff"))
    rc, out, err = verify(p_ok)
    check(rc == 0, f"verify exits 0 when the last block matches ({rc}, {out!r}, {err!r})")
    # Template-shaped variants: list marker and backticks.
    p_ok2 = plan_with(plans / "good2.md",
                      "**RESUME HERE (2026-10-05):**\n"
                      f"- `handoff_id: {good}`\n"
                      "reason: x\n"
                      f"plan: `/p.md`   cwd: `{repo}`   branch: `feat/handoff`\n")
    rc, out, err = verify(p_ok2)
    check(rc == 0, f"verify tolerates list markers and backticks ({rc}, {out!r}, {err!r})")

    for label, plan, code in (
        ("a wrong id", plan_with(plans / "wrong-id.md", block(other, repo, "feat/handoff")),
         "id-mismatch"),
        ("the right id only in an earlier block",
         plan_with(plans / "earlier.md", block(good, repo, "feat/handoff", "2026-10-01"),
                   block(other, repo, "feat/handoff")), "id-mismatch"),
        ("no handoff_id in the last block",
         plan_with(plans / "no-id.md", block(good, repo, "feat/handoff", "2026-10-01"),
                   block(None, repo, "feat/handoff")), "id-mismatch"),
        ("a wrong cwd", plan_with(plans / "wrong-cwd.md", block(good, plans, "feat/handoff")),
         "cwd-mismatch"),
        ("a wrong branch", plan_with(plans / "wrong-branch.md", block(good, repo, "main")),
         "branch-mismatch"),
        ("an unreadable plan", plans / "absent.md", "plan-missing"),
    ):
        rc, out, err = verify(plan)
        check(rc == 3 and out == code, f"verify: {label} -> exit 3 {code} ({rc}, {out!r})")

    rc, out, _err = verify(p_ok, hid="h-" + "e" * 20)
    check(rc == 3 and out == "no-ready", f"verify: a missing ready -> exit 3 no-ready ({rc}, {out!r})")
    # A ready that is too big, or reached through a link, counts as absent.
    big = repo / ".claude" / "handoffs" / f"{good}.ready.json"
    saved = big.read_text(encoding="utf-8") if big.is_file() else "{}"
    obj = json.loads(saved)
    obj["pad"] = "x" * 5000
    big.write_text(json.dumps(obj), encoding="utf-8")
    rc, out, _err = verify(p_ok)
    check(rc == 3 and out == "no-ready", f"verify: a 5 KiB ready -> no-ready ({rc}, {out!r})")
    big.write_text(saved, encoding="utf-8")
    repo2 = git_repo(tmp, "repo2", "feat/handoff")
    (repo2 / ".claude").mkdir()
    (repo2 / ".claude" / "handoffs").symlink_to(repo / ".claude" / "handoffs")
    p_r2 = plan_with(plans / "repo2.md", block(good, repo2, "feat/handoff"))
    rc, out, _err = verify(p_r2, root=repo2)
    check(rc == 3 and out == "no-ready",
          f"verify: a ready reached through a linked handoffs dir -> no-ready ({rc}, {out!r})")
    rc, out, _err = verify(p_ok)
    check(rc == 0, f"verify is green again on the restored fixture ({rc}, {out!r})")

    # 7. request-pending
    print("request-pending")
    r7 = pathlib.Path(tmp) / "req"
    (r7 / ".claude" / "handoffs").mkdir(parents=True)
    req = r7 / ".claude" / "handoffs" / "request.json"
    good_req = {"protocol": "remote-agents-handoff", "version": 1, "managed_session_id": SID,
                "requested_at": "2026-10-05T10:00:00Z"}

    def pending(sid):
        return run(["request-pending", "--root", str(r7)], sid=sid)[0]

    check(pending(SID) == 1, "no request.json -> exit 1")
    req.write_text(json.dumps(good_req), encoding="utf-8")
    check(pending(SID) == 0, "a valid matching request.json -> exit 0")
    check(pending("someone-else") == 1, "a non-matching session id -> exit 1")
    check(pending(None) == 1, "env var unset -> exit 1")
    req.write_text(json.dumps(dict(good_req, pad="x" * 5000)), encoding="utf-8")
    check(req.stat().st_size > 4096 and pending(SID) == 1,
          f"a 5 KiB request.json is refused -> exit 1 ({req.stat().st_size} bytes)")
    req.write_text(json.dumps(dict(good_req, version=2)), encoding="utf-8")
    check(pending(SID) == 1, "an unknown version -> exit 1")
    req.write_text(json.dumps(dict(good_req, protocol="other")), encoding="utf-8")
    check(pending(SID) == 1, "an unknown protocol -> exit 1")
    req.unlink()
    elsewhere = pathlib.Path(tmp) / "req-elsewhere.json"
    elsewhere.write_text(json.dumps(good_req), encoding="utf-8")
    req.symlink_to(elsewhere)
    check(pending(SID) == 1, "a symlinked request.json -> exit 1")
    req.unlink()
    req.write_text(json.dumps(good_req), encoding="utf-8")

    spec = importlib.util.spec_from_file_location("handoff_envelope", SCRIPT)
    mod = None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001 - report any import failure as a check
        print(f"  import error: {e!r}")
    fn = getattr(mod, "request_pending", None)
    check(callable(fn), "request_pending is importable via importlib")
    if callable(fn):
        check(fn(str(r7), {ENV_VAR: SID}) is True, "request_pending(root, env) -> True on a match")
        check(fn(str(r7), {ENV_VAR: "x"}) is False, "request_pending -> False on a mismatch")
        check(fn(str(r7), {}) is False, "request_pending -> False with the env var unset")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("OK — handoff-envelope.py mints ids, writes exact protocol envelopes only when "
      "supervised, refuses links and oversized reads, and verifies the last RESUME HERE block")
