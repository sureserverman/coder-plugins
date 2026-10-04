#!/usr/bin/env bash
# git-ref-gate.sh — git `reference-transaction` hook: a task commit needs proof records.
#
# OPT-IN. Nothing runs this by default. A project opts in with
# `python3 <planning>/skills/executing-plans/scripts/proof-hooks-install.py --install --repo R`,
# which writes a shim into R's git hooks directory that execs this file; a repo
# without the shim never runs it. (A plugin's hooks.json reaches every user who
# enables the plugin, so this gate is deliberately NOT a plugin hook.)
#
# WHY A REF HOOK. Ported from the engineering-skills Cursor port (f777c04), where
# two earlier gates checked the wrong thing: one read the index before the shell
# command ran (`git commit -a` slipped past), one parsed shell commands and a
# quoted `;` before `--no-verify` beat it. Git runs `reference-transaction`
# whenever a ref moves, and a non-zero exit in the `prepared` phase aborts the
# update. Measured on git 2.43: it refuses `commit --no-verify`, `commit -n
# --amend`, `commit-tree` + `update-ref`, `merge --no-verify`, cherry-pick and a
# detached HEAD; only a `core.hooksPath` override bypasses it, and that is what
# the PreToolUse guard (proof-guard.sh) denies while a plan is in flight. So this
# hook parses no commands: it reads the finished COMMIT.
#
# WHAT IT DOES. In the `prepared` phase, for each commit that an update of HEAD or
# refs/heads/* adds (reachable from the new tip and from no local branch or
# remote-tracking ref yet — a teammate's fetched commit is history to read, not
# work being committed here), when the commit's SUBJECT names a task of the plan
# in flight (.claude/plan-progress.json,
# read with plan-continue.sh's hardening), it reads that commit's own proof records
# and validates each against that commit's tree fingerprint, the record's path and
# the plan's current wording. The claims a task must prove are upstream's claim
# set — its FIRST claim and every claim that names its break "(red if …)"
# (plan-flip-audit's required_claims), so the hook and the audit agree. A record
# that is present is validated whether or not it is required. A claim deviation is
# a valid record, named on stderr — never proof: a requirement "covered by" it is
# refused. A requirement with no record is advisory (finding 9 carries no
# mandate): named on stderr, never refused. A file under proof/ that is not a
# record is refused.
#
# WHAT IT DOES NOT GATE. A commit whose subject names no task of the plan ("wip")
# is not a task commit and is not checked; nor is a commit already reachable from
# a remote-tracking ref, so one written there by hand (`update-ref refs/remotes/…`)
# is exempt. The gate holds an agent to the plan's own commit convention; it is a
# rail, not a sandbox.
#
# IT FAILS OPEN on its own errors (no python3, no plan, unreadable state, git or
# import failures, any uncaught exception) and says why on stderr. A record it cannot read is a problem with the
# record, not an error of the hook: it refuses. There is deliberately NO
# environment escape — the committing command's environment is the agent's.
# Rebasing or cherry-picking a task commit onto a new tree is refused until it is
# re-proven: its records were bound to the old tree.
set -uo pipefail
[[ "${1:-}" == "prepared" ]] || exit 0
command -v python3 >/dev/null 2>&1 || {
    echo "commit gate: python3 not found — not checked; allowing" >&2; exit 0; }
HOOK_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" 2>/dev/null && pwd)"
UPDATES="$(cat)"
COMMIT_GATE_SCRIPTS="${HOOK_DIR:-}/../skills/executing-plans/scripts" \
COMMIT_GATE_UPDATES="$UPDATES" python3 - <<'PY'
import importlib.util, json, os, stat, subprocess, sys
from pathlib import Path

ZERO = "0" * 40


def allow(note=None):
    if note:
        sys.stderr.write(f"commit gate: {note}\n")
    sys.exit(0)


def _fail_open(kind, exc, _tb):
    # An uncaught exception would exit 1, which git reads as a refusal.
    sys.stderr.write(f"commit gate: internal error ({kind.__name__}: {exc}); allowing\n")
    sys.stderr.flush()
    os._exit(0)


sys.excepthook = _fail_open


def refuse(text):
    sys.stderr.write(text.rstrip() + "\n")
    sys.exit(1)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, errors="replace",
                          timeout=20)


try:
    top = git("rev-parse", "--show-toplevel")
except Exception as e:
    allow(f"cannot run git ({e}); allowing")
if top.returncode != 0:
    allow()  # a bare repo, or not a work tree: no plan can be in flight here
repo = Path(top.stdout.strip())

# ---- the plan in flight (same hardening as plan-continue.sh's read_state)
state_path = repo / ".claude" / "plan-progress.json"
try:
    fd = os.open(state_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
except OSError:
    allow()  # no plan in flight: not ours to gate
try:
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_size > 256 * 1024:
        allow("plan-progress.json is not a regular file we own; allowing")
    with os.fdopen(fd, "r", errors="replace") as fh:
        fd = None
        state = json.load(fh)
except Exception:
    allow("plan-progress.json unreadable; allowing")
finally:
    if fd is not None:
        os.close(fd)
plan = state.get("plan") if isinstance(state, dict) else None
if not isinstance(plan, str) or not plan:
    allow("no plan named in plan-progress.json")
plan_path = Path(plan) if os.path.isabs(plan) else repo / plan
if not plan_path.is_file():
    allow(f"plan {plan_path} not found")

# ---- the commits this transaction adds to a branch or HEAD
tips = set()
for line in os.environ.get("COMMIT_GATE_UPDATES", "").splitlines():
    parts = line.split()
    if len(parts) != 3:
        continue
    _old, new, ref = parts
    if new == ZERO or not (ref == "HEAD" or ref.startswith("refs/heads/")):
        continue
    if git("cat-file", "-t", new).stdout.strip() == "commit":
        tips.add(new)
if not tips:
    allow()
added = []
for tip in sorted(tips):
    r = git("rev-list", "--max-count=200", tip, "--not", "--branches", "--remotes")
    if len(r.stdout.split()) >= 200:
        sys.stderr.write("commit gate: over 200 commits added; only the newest 200 checked\n")
    for sha in r.stdout.split():
        if sha not in added:
            added.append(sha)
if not added:
    allow()

# ---- the tools
scripts = Path(os.environ.get("COMMIT_GATE_SCRIPTS", ""))
try:
    spec = importlib.util.spec_from_file_location("prove_claim", scripts / "prove-claim.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    pfa = pc.PFA
    blocks = {b["id"]: b for b in pfa.task_blocks(plan_path.read_text(errors="replace"))}
except Exception as e:
    allow(f"cannot load prove-claim.py or read the plan ({e}); allowing")
stem = plan_path.stem


def record(sha, rel):
    """A record from the commit's own tree: None when absent, a dict — or the
    value it holds, which validate() then rejects — when present."""
    r = git("show", f"{sha}:{rel}")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"_unreadable": "not JSON"}


def problems_of(rec, fp, expect):
    try:
        return pc.validate(rec, fp, expect)
    except Exception as e:  # noqa: BLE001 — a record that crashes the validator is not valid
        return [f"malformed record ({e.__class__.__name__})"]


def why_of(rec):
    return str(rec.get("why", "") if isinstance(rec, dict) else "")[:200]


missing, deviations, advisory = [], [], []
for sha in added:
    subject = git("log", "-1", "--format=%s", sha).stdout.strip()
    tasks = sorted(t for t in pfa.subject_tasks(subject) if t in blocks)
    if not tasks:
        continue
    short = sha[:10]
    try:
        fp = pc.commit_fingerprint(repo, sha)
    except Exception as e:
        allow(f"cannot fingerprint {short} ({e}); allowing")
    # proof/ is outside every fingerprint: anything but a record there rides along unbound.
    ls = git("ls-tree", "-r", "-z", "--name-only", sha, "--", pc.PROOF_DIR).stdout
    for p in ls.split("\0"):
        if p and not pc.RECORD_PATH.match(p):
            missing.append(f"{short}: {p}: not a proof record — proof/ may hold records only")
    for t in tasks:
        b = blocks[t]
        required = set(pfa.required_claims(b["test"]))
        proven = {}  # claim k -> True only for a valid kind "claim" record
        for k, c in enumerate(pfa.claim_clauses(b["test"]), 1):
            rec = record(sha, f"{pc.PROOF_DIR}/{stem}/{t}/claim-{k}.json")
            if rec is None:
                if k in required:
                    missing.append(f"{short} Task {t} claim {k}: no record")
                continue
            probs = problems_of(rec, fp, ("claim", t, k, c))
            if probs:
                missing.append(f"{short} Task {t} claim {k}: {probs[0]}")
            elif rec.get("kind") == "claim-deviation":
                deviations.append(f"Task {t} claim {k}: {why_of(rec)}")
            else:
                proven[k] = True
        for k, c in enumerate(pfa.requirement_clauses(b["desc"]), 1):
            recs = {kind: record(sha, f"{pc.PROOF_DIR}/{stem}/{t}/{kind}-{k}.json")
                    for kind in ("req", "deviation")}
            probs = {kind: problems_of(r, fp, (kind, t, k, c))
                     for kind, r in recs.items() if r is not None}
            req_rec = recs.get("req")
            cites = req_rec.get("covered_by_claim") if isinstance(req_rec, dict) else None
            if probs.get("req") == [] and cites is not None and not proven.get(cites):
                # A req "covered by claim J" is only as good as claim J's PROOF; a
                # claim deviation discloses, it proves nothing (Stage 1 review I1).
                probs["req"] = [f"cites claim {cites}, which is missing or not a valid proof"]
            if not probs:
                advisory.append(f"Task {t} requirement {k}: no req or deviation record")
            elif probs.get("req") == []:
                continue
            elif probs.get("deviation") == []:
                deviations.append(f"Task {t} requirement {k}: {why_of(recs['deviation'])}")
            else:
                missing.append(f"{short} Task {t} requirement {k}: {next(iter(probs.values()))[0]}")

if not missing:
    if deviations:
        sys.stderr.write("commit gate: recorded as deviations — name each in the gate "
                         "report:\n" + "".join(f"  - {d}\n" for d in deviations))
    if advisory:
        sys.stderr.write("commit gate: advisory — requirements with no record (finding 9, "
                         "not blocking):\n" + "".join(f"  - {a}\n" for a in advisory))
    allow()

shown = "\n".join(f"  - {m}" for m in missing[:20])
more = f"\n  (+{len(missing) - 20} more)" if len(missing) > 20 else ""
refuse(
    f"commit gate: refused — {len(missing)} proof record(s) missing or stale in the commit(s) "
    f"being added:\n{shown}{more}\n\n"
    "A task must prove its first claim and every claim that names its break (red if …). "
    "Stage the change, run prove-claim.py claim for each (a claim no repo patch can break: "
    "prove-claim.py deviation --claim K --why …), `git add proof/`, then commit again. A "
    "record proven before the last code change is stale: re-prove after staging the final "
    "code. A task commit rebased or cherry-picked onto another tree needs re-proving too."
)
PY
