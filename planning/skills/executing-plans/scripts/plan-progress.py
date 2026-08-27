#!/usr/bin/env python3
"""plan-progress — statusline progress bar for executing-plans.

Reads the Claude Code statusline JSON on stdin, walks up from cwd to find
.claude/plan-progress.json (maintained by the executing-plans skill at each
execution transition), parses the referenced plan file with the authoritative
plan-parser regexes from portfolio-unify.py (one contract, one
implementation), and prints a filled progress bar over the plan's Status
fields plus the current stage / task / phase.

Since Stage 3 it prints SEVERAL lines, not one, and the state file is no
longer the only source. How many: up to MAX_BARS (3) non-master plans, PLUS
every in-flight master plan for the project — masters are exempt from the cap
(BL-056), so the line count has no fixed ceiling and "three" has been wrong
since that shipped. The GROUP containing the plan a session is executing
leads -- which is that plan itself, unless it is a sub-plan, in which case its
master prints above it and the phase indicator sits on the indented child.
Below come other in-flight plans for the same project, discovered from the
portfolio vault. A consequence worth stating plainly,
because it changes the old contract: a project with in-flight plans renders
bars even when NO execution is running there and no state file exists at all.
What it prints is "this project has unfinished plans", not only "this session
is executing one".

Prints NOTHING when there is nothing to say — no state file AND no discoverable
in-flight plan. Degradation is GRANULAR rather than all-or-nothing: one
unreadable plan costs its own line and leaves its siblings standing, and a
vault that has gone away costs the discovered bars but not the pinned one.
Safe to chain after any existing statusline command; a broken environment costs
lines, never noise.
"""
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

# Reuse the authoritative plan-parser pieces from the portfolio skill (stable
# sibling layout inside the planning plugin). Hyphenated filename → importlib.
# The plan-status contract (what `[ ]` / `[x]` / `[~]` mean) is defined and
# argued once, at portfolio-unify.py's STATUS_RE — read it there before
# changing anything here. This module classifies via pu.status_state() and
# never tests the captured character directly: a partial task counts toward
# the bar's denominator but never fills it.
_UNIFY = Path(__file__).resolve().parents[2] / "portfolio" / "scripts" / "portfolio-unify.py"
_spec = importlib.util.spec_from_file_location("portfolio_unify", _UNIFY)
pu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pu)

BAR_WIDTH = 20
STALE_AFTER_H = 12  # a state file this old is probably a crashed session

GREEN = "\033[38;2;0;160;0m"
RED = "\033[38;2;255;85;85m"
YELLOW = "\033[38;2;230;200;0m"
CYAN = "\033[38;2;46;149;153m"
PURPLE = "\033[38;2;167;139;250m"
DIM = "\033[2m"
RESET = "\033[0m"


# pathlib raises ValueError -- NOT OSError -- for a path containing a NUL byte
# ("embedded null byte"). Every guard in this file that means "this path is
# unusable, degrade" therefore has to name both, and a bare `except OSError` is
# a hole wherever the path came from text rather than from a directory listing.
# Three sources feed such paths: the `cwd` in the statusline's stdin JSON, the
# `plan` field of the state file, and -- since Task 3.2 -- the `Master:` /
# `- **Plan:**` links read out of plan PROSE. Found by Tier-1 review and
# reproduced: one NUL in a sub-plan's backlink blanked the whole status line,
# pinned bar included, on every redraw.
#
# WHICH calls raise is not uniform, and guessing it wrong is how the hole got
# there. Measured on CPython 3.12: `stat()`, `resolve()` and `read_text()`
# RAISE, while `is_file()`, `is_dir()` and `exists()` SWALLOW it internally
# (pathlib classes a NUL path as non-encodable and returns False). The guards
# below therefore load-bear on the first group and are belt-and-braces on the
# second; test-plan-progress.py pins both halves, so a future pathlib that
# changes either one fails loudly rather than silently reopening this.
BAD_PATH = (OSError, ValueError)


def find_state(start):
    try:
        d = Path(start).resolve()
    except BAD_PATH:
        return None
    for p in [d, *d.parents]:
        try:
            f = p / ".claude" / "plan-progress.json"
            if f.is_file():
                return f
        except BAD_PATH:
            continue
    return None


# --- portfolio discovery ---------------------------------------------------
# Everything below returns None rather than raising or printing. The portfolio
# scripts under ../../portfolio/scripts/ sys.exit() with a message when the
# config is missing, which is right for a CLI a user invoked on purpose and
# wrong here: this code runs on EVERY statusline redraw, in every project, on
# machines this repo does not control, where the only acceptable failure is a
# missing bar. `yaml` in particular is a third-party import that a user's
# python3 may simply not have.

def _home():
    """A home directory, never an exception.

    `Path.home()` raises RuntimeError when HOME is unset AND the uid has no
    /etc/passwd entry — the arbitrary-uid container case (OpenShift restricted
    SCC, distroless images). posixpath.expanduser swallows the KeyError and
    returns "~" unchanged, and pathlib then raises on that leading tilde.

    That matters far more than the odds suggest, because these paths are
    computed at MODULE SCOPE: the raise happens at import, before
    `if __name__ == "__main__"` installs the try/except below, so the guard
    that makes this file safe never runs. The statusline prints a traceback and
    exits 1 — the single outcome this script exists to never produce.
    """
    try:
        return Path.home()
    except Exception:
        return Path(os.environ.get("HOME") or "/nonexistent")


CONFIG_PATH = _home() / ".claude" / "portfolio-config.yaml"
REGISTRY_PATH = _home() / ".claude" / "projects-registry.yaml"


def _load_yaml(path):
    """A mapping from a YAML file, or None on ANY failure."""
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        # OSError, yaml.YAMLError, UnicodeDecodeError — all the same answer.
        return None
    return data if isinstance(data, dict) else None


def repo_root_of(state_file):
    """The repo root implied by a state file at <root>/.claude/plan-progress.json."""
    return state_file.parent.parent


def portfolio_plans_dir(repo_root):
    """The vault `plans/` directory for this repo, or None.

    Falls back to `<repo>/docs/plans` when the portfolio is not configured at
    all, so a project that keeps plans in-tree still gets discovery. Returns
    None — never a guess — when the project is not registered: showing bars
    from some OTHER project's plans would be worse than showing none.
    """
    # `repo_root` reaches here from the statusline's stdin `cwd` when no state
    # file exists, so it is untrusted text like everything else in BAD_PATH's
    # note. Guarded at the top rather than left to render()'s outer try, because
    # the corpus sweep calls this function RAW on purpose — a surface that only
    # degrades when someone else catches for it is not a surface that degrades.
    try:
        repo_root = Path(repo_root).resolve()
    except BAD_PATH:
        return None

    # "Could not load the config" and "config loaded but names no vault" are
    # DIFFERENT answers, and collapsing them is a real defect: a machine with
    # no portfolio config, an unreadable one, a malformed one, or no `yaml`
    # module would otherwise all silently fall through to <repo>/docs/plans and
    # render bars from whatever happened to be there. Only an intact config
    # that simply omits vault_dir means "this project keeps plans in-tree".
    cfg = _load_yaml(CONFIG_PATH)
    if cfg is None:
        return None
    vault = cfg.get("vault_dir")
    if vault is None:
        try:
            local = repo_root / "docs" / "plans"
            return local if local.is_dir() else None
        except BAD_PATH:
            return None
    if not isinstance(vault, str) or not vault:
        return None

    reg = _load_yaml(REGISTRY_PATH)
    if not reg:
        return None
    projects = reg.get("projects")
    if not isinstance(projects, list):
        return None

    entry = None
    for proj in projects:
        if not isinstance(proj, dict):
            continue
        raw = proj.get("path")
        if not isinstance(raw, str):
            continue
        try:
            if Path(raw).expanduser().resolve() == repo_root:
                entry = proj
                break
        except BAD_PATH:
            continue
    if entry is None or entry.get("enabled") is False:
        return None

    area, name = entry.get("area"), entry.get("name")
    if not isinstance(area, str) or not isinstance(name, str):
        return None
    plans = Path(vault).expanduser() / "Portfolio" / area / name / "plans"
    try:
        return plans if plans.is_dir() else None
    except BAD_PATH:
        # an unreadable or unmounted vault path raises rather than returning False
        return None


def parse_plan(text, path=None):
    """(done, total, stage_count) via the portfolio-unify Status contract.

    A `[~]` partial task counts toward `total` but never toward `done`, so the
    bar shows the plan as less finished rather than shorter — classification
    goes through pu.status_state(), never `!= " "` (which would fill the bar
    for an in-flight task).
    """
    if pu.is_master_plan(text, path):
        return parse_master(text)
    stages = set()
    done = total = 0
    in_task = False
    for line in text.splitlines():
        sh = pu.STAGEHDR_RE.match(line)
        if sh:
            stages.add(int(sh.group(1)))
        if pu.TASK_RE.match(line):
            in_task = True
        sm = pu.STATUS_RE.match(line)
        if sm and in_task:
            total += 1
            done += pu.status_state(sm.group(1)) == "done"
            in_task = False
    return done, total, len(stages)


def parse_master(text):
    """(done, total, stage_count) for a MASTER plan, from its sub-plan register.

    A master has no `### Task N.N` headings, so the ordinary counter reads every
    master as 0/0 — indistinguishable from a plan nobody has started. That is
    why zero of the vault's 517 plans that are masters had ever classified as in
    flight: not a decision, an artifact of two regexes not matching.

    Its progress is its register: one `### Sub-plan N:` entry per sub-plan, each
    with a `- **Status:**` the master's own close-out flips. stage_count is 0 —
    a master has sub-plans, not stages, so `S2/4` would be a category error.
    Sub-plan registers also carry `**Gate:**` blocks of `- [ ]` checkboxes;
    those are not Status lines and STATUS_RE does not match them.
    """
    done = total = 0
    in_entry = False
    for line in text.splitlines():
        if pu.SUBPLAN_RE.match(line):
            in_entry = True
            continue
        sm = pu.STATUS_RE.match(line)
        if sm and in_entry:
            total += 1
            done += pu.status_state(sm.group(1)) == "done"
            in_entry = False        # one Status per entry; consume it
    return done, total, 0


def plan_is_eligible(text, path=None):
    """Whether a plan counts as 'in flight' and so earns a bar.

    Eligible = STARTED but not CLOSED OUT:
      started    -> at least one Status classified `done` or `partial`
      closed out -> a **Completed:** or **Abandoned:** line

    A MASTER plan is exempt from the `started` half (BL-056, decided by the user
    2026-08-08): it is visible whenever it is not closed out. A master with no
    sub-plan yet begun is still work the project has committed to, and its bar
    reads 0/N rather than being invisible. "Not closed out" means NEITHER
    **Completed:** NOR **Abandoned:** -- abandonment is the other terminal
    marker, and suppressing on it is the plan-status contract's existing rule,
    so the exemption widens what counts as started and nothing else.

    Classification goes through pu.status_state(), never a test on the captured
    character: `!= " "` reads `[~]` as done, which is the exact defect BL-001
    exists to prevent. Both terminal markers come from pu as well, so this file
    restates no part of the plan-status contract.

    Deliberately NOT eligible: an all-`[ ]` non-master plan (authored, never
    started -- a bar reading 0/13 is noise), a plan with no Status fields at all
    (the checkbox-era legacy and *-design.md documents), and anything closed out.
    """
    started = False
    in_entry = False
    # A master's progress lives in its `### Sub-plan N:` register, not in Task
    # headings it does not have. Counting only TASK_RE is why no master had ever
    # been eligible -- every one read as "authored, never started".
    is_master = pu.is_master_plan(text, path)
    opener = pu.SUBPLAN_RE if is_master else pu.TASK_RE
    for line in text.splitlines():
        if opener.match(line):
            in_entry = True
            continue
        sm = pu.STATUS_RE.match(line)
        if sm and in_entry:
            in_entry = False
            if pu.status_state(sm.group(1)) in ("done", "partial"):
                started = True
    if not started and not is_master:
        return False
    return not (pu.COMPLETED_RE.search(text) or pu.ABANDONED_RE.search(text))


MAX_BARS = 3

# The date stamp a plan filename opens with (2026-08-06-<slug>-plan.md).
# Recency comes from THIS, never from the file's modification time:
# references/plan-parser.md records that the five oldest coder-plugins plans
# all share a 2026-05-23 timestamp, the date the vault was migrated, so that
# timestamp measures a copy operation rather than when the work happened.
# (The Stage 2 gate proves this two ways: test_ordering_ignores_mtime reads the
# source of date_stamp/_rank and asserts neither names a stat field, and the
# ordering test utimes the oldest plan to 2038 and asserts the order does not
# move. An earlier draft of that gate grepped the whole file for the field
# name, which would have banned mtime for cache invalidation too — a different
# and necessary use — and matched explanatory comments like this one.)
DATE_STAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def date_stamp(path):
    """The filename's leading date stamp, or "" when it has none.

    "" sorts last under reverse=True, so an unstamped plan ranks below every
    stamped one instead of crashing the sort or jumping to the front.
    """
    m = DATE_STAMP_RE.match(path.name)
    return m.group(1) if m else ""


def _same_file(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except BAD_PATH:
        return False


def _rank(path):
    # name as tiebreaker so same-day plans have a stable, reproducible order
    return (date_stamp(path), path.name)


CACHE_NAME = "plan-progress-cache.json"
CACHE_VERSION = 3   # v2 -> v3: the cache gained a `masters` list (BL-056)


def rule_signature():
    """A fingerprint of the CODE that produced a cache's verdicts, or None.

    scan_signature() below fingerprints the plans DIRECTORY, so the cache
    correctly rebuilds whenever a plan file changes. Nothing fingerprinted the
    ELIGIBILITY RULE, and that is an independent axis: when `plan_is_eligible`
    itself changes, every cache on disk keeps serving verdicts computed by the
    OLD rule against a directory whose signature is still perfectly valid — and
    keeps doing so forever, because nothing in the key can ever notice. Only an
    unrelated edit to some plan file breaks the spell.

    Not hypothetical, and not caught by any test. Making masters countable
    (BL-054, `4d45fbf`) changed the rule; measured immediately afterwards, 3 of
    the 4 caches on this machine went on hiding every master bar. The feature
    had shipped and could not fire — twice over, since the tree glyphs that
    render those masters have nothing to render without them.

    Deliberately a digest of the two whole source files rather than of the
    rule's individual functions and regexes. Eligibility depends on
    plan_is_eligible, TASK_RE, SUBPLAN_RE, STATUS_RE, COMPLETED_RE,
    ABANDONED_RE, status_state and is_master_plan; enumerating those here would
    create exactly the lockstep site that drifts, which is the bug class this
    key exists to close. Over-invalidating on a comment edit costs one ~12 ms
    rescan, once.

    CONTENT, not (mtime, size), which is what this first shipped as. Review
    caught the gap: a deployment that preserves timestamps across a real edit —
    `rsync -a`, some Docker COPY layers, a same-second checkout — leaves
    (mtime, size) identical while the rule underneath has changed, which is
    precisely the silent-stale failure this function exists to prevent, sneaking
    back in through the key itself. Measured: 0.048 ms against a 33 ms redraw.
    """
    out = []
    for f in (Path(__file__), _UNIFY):
        try:
            out.append(hashlib.sha256(Path(f).read_bytes()).hexdigest())
        except BAD_PATH:
            return None     # rule unknown -> decline the cache, never trust a stale one
    return out

# Instrumentation for the cache test. Counting actual plan-file READS is the
# only honest way to assert "the cache was used": a timing assertion passes on
# a fast machine whether or not the cache works, which is the test-that-cannot-
# fail shape this plan keeps producing.
PLAN_READS = 0


def _read_plan(path):
    global PLAN_READS
    PLAN_READS += 1
    return path.read_text(errors="ignore")


def scan_signature(plans_dir):
    """A fingerprint of the plans directory, or None if it cannot be read.

    Per-file (name, modification time, size) — NOT the directory's own
    timestamp, which the task originally specified. Verified on this platform:
    a directory's timestamp moves when an entry is added, removed or renamed,
    and does NOT move when a file's CONTENT changes. A cache keyed on it would
    therefore go stale on exactly the edit that matters most here — a Status
    flip during execution — so the bar would show yesterday's eligibility for
    the entire run the bar exists to narrate.

    Size alone does not rescue it either: `- **Status:** [ ]` and
    `- **Status:** [x]` are the same number of bytes.

    Cheap by design: a stat per file, no reads. The reads are what this caches.

    ACCEPTED RESIDUAL RISK, named because rule_signature() below rejects the
    identical shortcut and silence here would read as oversight. (name, mtime,
    size) misses a content change that preserves the timestamp -- `rsync -a`, a
    restored backup, some Docker COPY layers -- exactly as it does for the rule.
    Reproduced by review: flip `[ ]` to `[x]` (same byte length), restore the
    mtime, and the cache serves the stale verdict forever with zero reads.
    Not fixed the same way, deliberately: rule_signature hashes TWO files, while
    this covers every plan in the directory (~50), and hashing them means
    READING them all -- which is the precise cost this cache exists to avoid.
    Content-addressing here would leave the cache saving only the parse, turning
    a 4x saving into nearly none. The trade is a real edit going unseen only
    when a tool deliberately preserves timestamps; ordinary edits, including the
    Status flips this bar narrates, always move mtime.
    """
    try:
        out = []
        for f in sorted(Path(plans_dir).glob("*.md")):
            st = f.stat()
            out.append([f.name, st.st_mtime_ns, st.st_size])
        return out
    except BAD_PATH:
        return None


def _safe_cache_name(name):
    """Whether a filename read back from the cache may be joined to plans_dir.

    The cache is trusted to skip the reads, so nothing downstream re-validates
    what it names. `Path(plans_dir) / "/etc/passwd"` DISCARDS plans_dir and
    yields /etc/passwd, and "../../x" is preserved literally — so a planted
    cache entry becomes an arbitrary file read whose name is then displayed in
    the user's terminal chrome. Bare filenames only (CWE-22).
    """
    return (isinstance(name, str)
            and name not in ("", ".", "..")
            and not os.path.isabs(name)
            and os.sep not in name
            and (os.altsep is None or os.altsep not in name))


def _is_file(path):
    """`path.is_file()` that cannot raise.

    pathlib swallows only ENOENT / ENOTDIR / EBADF / ELOOP; **EACCES is not in
    that set**, so `is_file()` on a path inside an unreadable directory raises
    PermissionError. Same platform detail as portfolio_plans_dir's `is_dir()`
    guard above — it was handled there and missed here, and the pinned plan is
    the common case, so this raised on every redraw whose vault directory had
    become unreadable.
    """
    try:
        return path.is_file()
    except BAD_PATH:
        return False


def _read_cache(cache_file):
    if cache_file is None:
        return None
    try:
        data = json.loads(Path(cache_file).read_text(encoding="utf-8"))
    except Exception:
        # Missing, truncated, corrupt, not JSON, wrong encoding — every one of
        # them means "rebuild", never "raise". A cache that can break the
        # statusline is worse than no cache.
        return None
    return data if isinstance(data, dict) else None


def _write_cache(cache_file, plans_dir, signature, names, rule, masters=()):
    if cache_file is None or rule is None:
        return              # an unkeyed cache is worse than none — see rule_signature()
    try:
        p = Path(cache_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps({
            "version": CACHE_VERSION,
            "rule": rule,
            "plans_dir": str(plans_dir),
            "signature": signature,
            "eligible": names,
            # Masterhood is cached beside eligibility because the cap now needs
            # it (BL-056) and only the FILENAME half of it can be recovered from
            # a name: `# Master Plan:` in the first heading is equally valid, so
            # recomputing on a cache hit would mean reading every plan file --
            # the exact cost this cache exists to avoid.
            "masters": list(masters),
        }), encoding="utf-8")
        os.replace(tmp, p)
    except BAD_PATH:
        pass  # an unwritable cache is a missed optimisation, not a failure


def discover_plans(plans_dir, pinned=None, cache_file=None):
    """The plans to render, newest first by filename date stamp.

    `pinned` is the plan the state file names. It is included UNCONDITIONALLY
    when it exists — not merely bumped up the ranking — because it is the plan
    actually being executed, and the pre-existing single-plan behavior must not
    regress. A plan can legitimately be mid-execution and ineligible: one at
    0/13 has been started by a human but carries no `[x]` yet, and the bar has
    always shown it. Eligibility governs which OTHER plans earn a bar, not
    whether the executing one does.

    MAX_BARS bounds NON-MASTER plans only; eligible masters are added on top of
    that budget rather than competing for its slots (BL-056, decided by the user
    2026-08-08). The cap selects by date stamp and knows nothing of the
    master->sub-plan association that group_plans() then renders, so while they
    shared one budget a 4th eligible plan newer than a master evicted the
    MASTER — and, because `-master-plan.md` sorts below `-sub-NN-` within a
    shared date stamp, the parent was dropped FIRST, leaving its children flat
    and glyphless: a tree with no root. Exempting masters dissolves the question
    "which plan gets dropped to make room for a master?" rather than answering
    it, which is what made it a user's call and not an executor's.

    THE NUMBER OF MASTERS IS UNBOUNDED BY THIS CODE, and that is a deliberate
    consequence of the decision rather than an oversight. A project renders
    `3 + (its open masters)` bars. The figures below are an OBSERVED MAXIMUM on
    one vault at one moment — not a bound anything enforces, and not a number a
    future maintainer may rely on. Stated this way because the first draft of
    this docstring called 5 the "worst case", which reads as a guarantee the
    code does not make.

    Observed on the live vault when this shipped: 21 -> 25 bars total, with only
    multitor (3 -> 5), writer-pad (3 -> 4) and health-alert (0 -> 1) changing at
    all — so 5 was the most any single project rendered that day. If the count
    ever does read as too many, the lever is a SEPARATE cap on masters, never
    reinstating the shared one — the point of the decision is that a master must
    not lose its slot to its own children.
    """
    pinned_r = None
    if pinned is not None:
        try:
            pinned_r = Path(pinned).resolve()
        except BAD_PATH:
            pinned_r = None

    eligible = []       # eligible non-masters — these compete for MAX_BARS
    masters = []        # eligible masters — exempt from the cap (BL-056)
    pinned_is_master = False
    if plans_dir is not None:
        plans_dir = Path(plans_dir)
        sig = scan_signature(plans_dir)
        rule = rule_signature()
        cached = _read_cache(cache_file) if (sig is not None and rule is not None) else None
        if (cached is not None
                # `version` was written from the start and never once read — a
                # key field that existed and did nothing. Checked now, so a
                # future format change invalidates rather than misreads.
                and cached.get("version") == CACHE_VERSION
                and cached.get("rule") == rule
                and cached.get("plans_dir") == str(plans_dir)
                and cached.get("signature") == sig
                and isinstance(cached.get("eligible"), list)
                and isinstance(cached.get("masters"), list)):
            cached_masters = {n for n in cached["masters"] if _safe_cache_name(n)}
            # dict.fromkeys, not the raw list: _write_cache builds its names
            # from a directory glob and so can never emit a duplicate, but a
            # TAMPERED cache can — and that is the threat model _safe_cache_name
            # already exists for. A repeated name would otherwise spend two of
            # the three non-master slots on one plan and make group_plans()
            # render the same master's group twice. Not a traversal; a way to
            # spend the bar budget on nothing.
            for name in dict.fromkeys(cached["eligible"]):
                if _safe_cache_name(name):
                    (masters if name in cached_masters else eligible).append(
                        plans_dir / name)
        elif sig is not None:
            for f in sorted(plans_dir.glob("*.md")):
                try:
                    text = _read_plan(f)
                    if plan_is_eligible(text, f):
                        (masters if pu.is_master_plan(text, f) else eligible).append(f)
                except BAD_PATH:
                    continue  # deleted or unreadable mid-scan — never raise
            _write_cache(cache_file, plans_dir, sig,
                         [f.name for f in eligible + masters], rule,
                         [f.name for f in masters])

        # The pinned plan is added below on its own terms, so it must not also
        # arrive through either list.
        if pinned_r is not None:
            eligible = [f for f in eligible if not _same_file(f, pinned_r)]
            before = len(masters)
            masters = [f for f in masters if not _same_file(f, pinned_r)]
            pinned_is_master = len(masters) < before

    eligible.sort(key=_rank, reverse=True)
    masters.sort(key=_rank, reverse=True)

    chosen = []
    capped = 0          # how many of the MAX_BARS non-master slots are taken
    if pinned_r is not None and _is_file(pinned_r):
        chosen.append(pinned_r)
        # A pinned MASTER does not spend a capped slot, for the same reason no
        # other master does. When the pinned plan is a master that is itself
        # closed out it is absent from `masters` and so counted here — which is
        # the conservative direction: it costs one non-master bar, never a
        # master's slot.
        if not pinned_is_master:
            capped += 1
    for f in eligible:
        if capped >= MAX_BARS:
            break
        chosen.append(f)
        capped += 1
    chosen.extend(masters)
    chosen.sort(key=_rank, reverse=True)
    return chosen


# Tree glyphs for a master's sub-plans. Box-drawing rather than ASCII `|-`
# because every other glyph in this file is already non-ASCII (█ ░ ⚙ ▶ ◆ ⚑),
# so a terminal that mangles these was already mangling the bar itself.
TREE_MID = "├─ "
TREE_LAST = "└─ "


def _plan_text(path):
    """A plan's text, or "" — grouping must never cost a bar."""
    try:
        return _read_plan(path)
    except BAD_PATH:
        return ""


def master_of(text, path):
    """The path this sub-plan's `Master:` backlink names, or None."""
    m = pu.MASTER_BACKLINK_RE.search(text)
    if not m:
        return None
    target = pu.link_target(m.group(1))
    return path.parent / target if target else None


def subplans_of(text, path):
    """Every path this master's register `- **Plan:**` lines name, in order.

    Order is load-bearing: it is the register's dependency order, which is what
    a reader expects children to be listed in, and it is the only ordering that
    survives a sub-plan whose filename date stamp does not match its number.
    """
    out = []
    for m in pu.SUBPLAN_LINK_RE.finditer(text):
        target = pu.link_target(m.group(1))
        if target:
            out.append(path.parent / target)
    return out


def group_plans(paths, pinned=None):
    """[(path, prefix)] — each master immediately above its own sub-plans.

    Presentation only. This reorders and prefixes what discovery already chose;
    it never adds a plan and never drops one, so the cap and the eligibility
    filter keep meaning exactly what Stage 2 gated them to mean. A sub-plan
    whose master is not among the chosen plans therefore renders as it always
    did — top level, no glyph — which is the COMMON case, since a master earns
    its own bar on its own eligibility and often has none.

    `pinned` keeps the plan this session is executing at the top, as the old
    single-source renderer did. It is the plan's GROUP that is hoisted, not the
    plan: when the pinned plan is a sub-plan, its master has to stay above it or
    the tree glyphs point at nothing.
    """
    # Path keys throughout: discover_plans() already deduplicates by _same_file,
    # so no two entries here name one file under two spellings.
    texts = {p: _plan_text(p) for p in paths}
    masters = [p for p in paths if pu.is_master_plan(texts[p], p)]

    # Union of the two links, not either alone: the backlink is missing from
    # some sub-plans and the register entry from others, and a sub-plan is a
    # sub-plan if EITHER side says so.
    register = {m: subplans_of(texts[m], m) for m in masters}
    parent_of = {}
    for p in paths:
        if p in masters:
            continue
        back = master_of(texts[p], p)
        for m in masters:
            if ((back is not None and _same_file(back, m))
                    or any(_same_file(c, p) for c in register[m])):
                parent_of[p] = m
                break

    def child_order(master, kid):
        # Register position first; a child linked only by its backlink has none
        # and falls back to filename order. The two never compare against each
        # other, so the mixed key types below never meet.
        for i, c in enumerate(register[master]):
            if _same_file(c, kid):
                return (0, i)
        return (1, _rank(kid))

    groups = []
    for m in masters:
        kids = [p for p in paths if parent_of.get(p) == m]
        kids.sort(key=lambda k: child_order(m, k))
        groups.append([m] + kids)
    for p in paths:
        if p not in masters and p not in parent_of:
            groups.append([p])

    # A group ranks by its NEWEST member, so grouping never pushes a recent
    # sub-plan below an older unrelated plan just because its master is old.
    def group_rank(g):
        holds_pinned = pinned is not None and any(_same_file(x, pinned) for x in g)
        return (holds_pinned, max(_rank(x) for x in g))

    groups.sort(key=group_rank, reverse=True)

    # The text is handed on rather than dropped: these files were just read to
    # work out the structure, and render_*() would otherwise read them again.
    out = []
    for g in groups:
        out.append((g[0], "", plan_name(g[0]), texts[g[0]]))
        for i, kid in enumerate(g[1:]):
            glyph = TREE_LAST if i == len(g) - 2 else TREE_MID
            out.append((kid, f"{DIM}{glyph}{RESET}", relative_name(kid, g[0]), texts[kid]))
    return out


# Task 3.4 — width. Bars only read as a stack if they start at the same column,
# and plan names in the live vault run to 90 characters
# ("2026-08-04-writer-pad-external-import-audio-transcription-sub-02-text-import
# -entry-points"), which alone would push a bar off any terminal.
NAME_WIDTH = 46     # visible chars for the name column, tree prefix included
                    # Measured in CHARACTERS, which is correct for the vault's
                    # date-stamped ASCII filenames and is the assumption this
                    # column's alignment rests on -- see clip()'s note on CJK.
NOTE_WIDTH = 44     # visible chars for free-text task_desc / blocked note
ELLIPSIS = "…"

# Visible width is NOT len(): every line here carries SGR escapes, and a colour
# change is zero columns wide. Aligning on len() lines up the escape bytes
# instead of the glyphs, so a coloured line and an uncoloured one drift apart by
# exactly the length of their colour codes -- which is why the pinned bar (CYAN)
# and a discovered bar (DIM) are the pair that exposes it.
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(s):
    return len(ANSI_RE.sub("", s))


# Control characters are STRIPPED before anything is measured or cut, and ESC is
# the one that matters. Everything this renderer emits goes straight to a
# terminal, and three of its inputs are text somebody else wrote: a plan's
# FILENAME, and the state file's `task_desc` and `note`. A literal ESC in any of
# them is at best a colour nobody authorised; at worst clip() cuts through the
# middle of the CSI sequence and emits an UNTERMINATED one, which then consumes
# the bytes that follow as its own parameters -- including this file's RESET,
# leaving the user's terminal recoloured after the status line ends (CWE-150).
# Review reproduced exactly that: clip("\x1b[35mHELLO", 3) -> "\x1b[…".
#
# Stripping rather than escaping, because there is no legitimate control
# character in a plan name or a one-line task description, and a status line has
# no way to display one usefully.
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def plain(s):
    """`s` with control characters removed. Not optional — see CONTROL_RE."""
    return CONTROL_RE.sub("", s) if isinstance(s, str) else ""


def clip(s, width):
    """`s` cut to `width` VISIBLE columns, ending in … when anything was lost.

    Takes PLAIN text only — pass it through plain() first if it came from a
    filename or the state file. It counts columns with len(), so an escape
    sequence would be measured as its bytes and could be cut in half; plain()
    is what makes that unreachable rather than merely discouraged. An earlier
    version of this docstring asserted the safety instead of establishing it,
    which review correctly read as a guarantee this function does not provide.

    Width is measured in CHARACTERS, which is correct for the aligned column
    (date-stamped ASCII filenames by vault convention) and WRONG for CJK text,
    where each glyph occupies two terminal columns. The error is OVERSHOOT, not
    undershoot: review measured a 44-character CJK clip at roughly 88 columns,
    about double the intended budget -- an earlier version of this note claimed
    it would "clip a little short", which had both the direction and the
    magnitude backwards. It still never MISALIGNS anything, because notes are
    clipped and never padded against a sibling; it just overruns. Accepted for
    now: these fields are English in this vault, and the whole-line bound is
    already open as BL-057, which is where a column-aware width belongs.
    """
    if width <= 0:
        return ""
    if len(s) <= width:
        return s
    # No `if width > 1 else ELLIPSIS` branch: at width 1 this is s[:0] + ELLIPSIS,
    # which already IS ELLIPSIS. The guard was dead code — kept honest by a
    # mutation that deleted it and changed nothing, after review had to
    # hand-verify its operator precedence. One expression, no precedence question.
    return s[: width - 1] + ELLIPSIS


def plan_name(path):
    """The display name: the filename minus its plan suffix."""
    name = plain(Path(path).name)
    for suffix in ("-light-plan.md", "-plan.md", ".md"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def relative_name(child, master):
    """A sub-plan's name with the prefix it shares with its master removed.

    A tree already says who the parent is, so repeating the parent's name on
    every child spends the column on the one thing the indent has established
    and truncates away the one thing it has not.

    The Stage 3 gate evaluator found the consequence: names are clipped from the
    TAIL, but a sub-plan's distinguishing part -- `sub-NN-<slug>` -- IS the tail,
    while the shared date stamp and topic eat the column ahead of it. Measured on
    the live vault, all three of anki-kit's children render the byte-identical
    string `2026-07-16-anki-compatible-flashcard-ecosy…`. Three different plans,
    three different bars, nothing to tell them apart. The relationship read; the
    identity did not.

    Matched on whole `-`-separated TOKENS, never on raw characters, and only
    when at least four of them agree. Both halves of that rule were bought by a
    bug: a character-wise common prefix of `2026-08-01-alpha-master` and
    `2026-08-02-alpha-sub-01-foundation` is `2026-08-0`, which cut the child
    down to `02-alpha-sub-01-foundation` — a fragment of the DATE promoted to
    the front of the name, reading as a plan called "02-alpha…". Found by
    looking at the golden instead of re-pasting it.

    Four tokens means the whole date stamp (`2026`, `08`, `04`) plus at least
    one shared topic word, i.e. evidence of a genuinely shared subject rather
    than two plans that merely share a day. A child whose name diverges from its
    master's earlier than that keeps its full name: there is nothing redundant
    to remove, and the indent already says whose child it is.

    Validated across all 24 masters in the live vault.
    """
    c, p = plan_name(child), plan_name(master)
    ct, pt = c.split("-"), p.split("-")
    shared = 0
    for a, b in zip(ct, pt):
        if a != b:
            break
        shared += 1
    if shared >= 4 and len(ct) > shared:
        return "-".join(ct[shared:])
    return c


def name_column(labels, prefixes):
    """The shared visible width the name column should take.

    The widest label that fits, so a single bar is padded to its own width and
    therefore not padded at all -- which is what keeps the one-plan golden
    byte-identical while three plans align. The tree prefix counts toward the
    width, so a child's name gets less room and its bar still lands on the same
    column as its master's. Measures the LABEL that will be displayed, not the
    filename: a child shows its name relative to its master, and measuring the
    full filename here would reserve a column nothing ever fills.
    """
    widest = 0
    for label, prefix in zip(labels, prefixes):
        widest = max(widest, visible_len(prefix) + len(label))
    return min(widest, NAME_WIDTH)


def bar(done, total):
    filled = round(BAR_WIDTH * done / total) if total else 0
    return (
        f"{DIM}▐{RESET}{GREEN}{'█' * filled}{RESET}"
        f"{DIM}{'░' * (BAR_WIDTH - filled)}▌{RESET}"
    )


# The state file has TWO dialects in the wild, and the renderer only knew one.
# references/progress-state-file.md specifies `phase` as one of five keywords,
# `stage` as an integer and `task` as "N.M". Real executions also write prose
# into those same keys and put the integers in `stage_index`/`stage_total`
# beside them -- android/writer-pad's live file carries
#   "phase": "STOPPED — Stage 2 re-gate FAILED; awaiting user direction"
#   "stage_index": 2, "stage_total": 2   (and no `stage` or `task` at all)
# Neither side is simply wrong: the richer file is more useful to a human
# reading it, which is why the fix is not "make writers comply". The renderer
# reads the ints when they are there, interpolates `stage`/`task` only when they
# are the shape the schema promises, and otherwise says NOTHING -- a status line
# has one line's worth of room, so a paragraph pasted into it is worse than a
# missing field. Verified against the live file, not a fixture.
KNOWN_PHASES = ("preflight", "task", "gate", "closeout", "blocked")
TASK_ID_RE = re.compile(r"^\d+\.\d+$")


def _int(v):
    """`v` when it is a real int, else None.

    `type(v) is int`, not isinstance: bool subclasses int, so a stray
    `"stage_index": true` would otherwise render as stage 1. Same discipline
    the remediation_round field already uses below.
    """
    return v if type(v) is int else None


def _stage_int(v):
    """A POSITIVE int, else None.

    Stages are 1-indexed everywhere in the format (`## Stage 1 — …`), so 0 and
    negatives are malformed rather than edge cases, and both degrade to "no
    stage position" instead of rendering `S0/3` or `S-1/3`. Stated as its own
    predicate because the precedence below then has no falsy-but-valid value
    left to trip over: review flagged the earlier `_int(a) or _int(b)` form for
    silently letting `stage` win over an explicit `stage_index: 0`.
    """
    n = _int(v)
    return n if n is not None and n > 0 else None


def stage_position(state, stage_count):
    """(index, total) for the `S2/4` part, or None when the file does not say.

    Among VALID values, `stage_index`/`stage_total` win over `stage` — a file
    carrying both is one where `stage` holds prose. `stage_total` in turn wins
    over the count parsed from the plan: a sub-plan mid-master knows its own
    stage total, and a master's parsed count is 0 by design.
    """
    idx = _stage_int(state.get("stage_index"))
    if idx is None:
        idx = _stage_int(state.get("stage"))
    total = _stage_int(state.get("stage_total"))
    if total is None:
        total = _stage_int(stage_count)
    return (idx, total) if idx is not None and total is not None else None


def phase_part(state):
    phase = state.get("phase", "task")
    if phase not in KNOWN_PHASES:
        # A prose phase used to fall through every branch into the task case and
        # render a bare "▶ " with nothing after it -- seen live in writer-pad.
        # An unrecognised phase means the file is telling us something this bar
        # has no room for, so it says nothing at all.
        return ""
    stage = _stage_int(state.get("stage_index"))
    if stage is None:
        stage = _stage_int(state.get("stage"))
    if phase == "preflight":
        return f"{YELLOW}⚑ preflight{RESET}"
    if phase == "gate":
        # `S{stage}` only when there IS one; the old form rendered "SNone gate"
        # for a gate whose stage the file did not record.
        part = (f"{PURPLE}◆ S{stage} gate{RESET}" if stage is not None
                else f"{PURPLE}◆ gate{RESET}")
        # Only present when a gate is being re-run after a failure; a gate on its
        # first round renders exactly as it always did.
        rnd = state.get("remediation_round")
        # `type(... ) is int`, not isinstance: bool subclasses int, so a malformed
        # `"remediation_round": true` would otherwise render as round 1.
        if type(rnd) is int and rnd > 0:
            budget = state.get("remediation_budget")
            # The fallback duplicates the default stated in ../SKILL.md ("Remediation
            # budget — default 2 rounds per gate"); test-gate-remediation-contract.py
            # asserts the two stay equal, so change both or neither.
            total = budget if type(budget) is int and budget > 0 else 2
            colour = RED if rnd >= total else YELLOW
            part += f" {colour}↻{rnd}/{total}{RESET}"
        return part
    if phase == "closeout":
        return f"{GREEN}✔ close-out{RESET}"
    if phase == "blocked":
        note = state.get("note") or state.get("task_desc") or ""
        note = clip(plain(note), NOTE_WIDTH)
        return f"{RED}✘ blocked{RESET}" + (f" {DIM}{note}{RESET}" if note else "")
    task = state.get("task")
    desc = state.get("task_desc")
    desc = clip(plain(desc), NOTE_WIDTH)
    if isinstance(task, str) and TASK_ID_RE.match(task):
        label = f"T{task} "
    else:
        # Everything that is not a schema-shaped "N.M" loses only the LABEL.
        # `"task": "close-out: owed review passes dispatched over Stage 2 and
        # whole-plan diffs"` is a real value from a real run; interpolated raw it
        # puts a sentence where `T3.1` belongs and pushes every other bar off the
        # line, so it is dropped. But `task_desc` is free text BY SCHEMA and is
        # not implicated by a malformed sibling field — review caught an earlier
        # version returning "" here, which discarded a perfectly good desc and
        # contradicted the `task is None` case two lines up, where the same desc
        # was kept. One rule now: a bad `task` costs the `T…` label, nothing else.
        label = ""
    if not label and not desc:
        return ""       # nothing to say -- the bare glyph was noise, not data
    # The separator between label and desc belongs BETWEEN them, not welded to
    # the label: with no desc the old form left a trailing space inside the
    # phase part, invisible until Task 2.2 appended a marker after it and the
    # bar rendered "T1.3  ⚠". Cosmetic, pre-existing, and in a file already open.
    sep = " " if (label and desc) else ""
    return f"{GREEN}▶ {label.rstrip()}{sep}{RESET}{desc}"


def staleness(state):
    upd = state.get("updated")
    if not upd:
        return ""
    try:
        ts = datetime.datetime.fromisoformat(upd.replace("Z", "+00:00"))
    except ValueError:
        return ""
    age = datetime.datetime.now(datetime.timezone.utc) - ts
    hours = age.total_seconds() / 3600
    if hours >= STALE_AFTER_H:
        return f" {DIM}(stale {int(hours)}h){RESET}"
    return ""


LAG_TOLERANCE = 1   # tasks; one is a task in flight, two is a stall
PARALLEL_YES_RE = re.compile(r"^\s*-\s*\*\*Parallel:\*\*\s*YES\b", re.I)


def status_lag(state, text, plan_path):
    """` ⚠ status lag Nx` when the plan file trails the live run, else "".

    BL-096. `Status` flips stopped mid-plan in all three audited sessions —
    tasks kept completing and the markers stopped moving. The RULE was never
    missing (Step 3.3 rule 5 says flip it in the same change as the work); the
    SIGNAL was. Everything that could notice fired after the fact: `portfolio
    plan-status` classifies finished-but-unmarked plans on a later sweep, and a
    flip audit catches the bulk catch-up flip a stall eventually produces. Both
    report damage already in the file.

    Both artifacts are already maintained at every transition. The only new
    thing here is noticing that they disagree, and saying so while the run is
    still going.

    LAG counts the SEQUENTIAL tasks between the last marker that moved (`[x]` or
    `[~]`) and the task the state file names, plus the current one. `Parallel:
    YES` siblings are excluded: they are dispatched together and do not finish
    in document order, so an unmarked one is concurrency the plan asked for.

    NOT extended to master plans, deliberately. The state-file contract
    (`../references/progress-state-file.md`) says a master's state file always
    points at the SUB-PLAN currently executing, so a master's own register is
    never the file this function reads. An earlier version branched on
    is_master_plan() and shipped a test for a state shape the contract says
    cannot occur — green, and measuring nothing. A master register that stops
    being flipped is still undetected here; that is a real residual, recorded
    rather than papered over, and it needs a different mechanism because the
    register flip happens at a sub-plan close-out, outside any task transition. One is the ordinary case —
    the current task is legitimately not done yet — so the warning starts at
    two. Silent when the state names no task, when the task is not found in the
    plan, or when nothing is flipped yet and the run is still in the first
    couple of tasks.
    """
    cur = state.get("task")
    if not isinstance(cur, str) or not cur.strip():
        return ""
    cur = cur.strip()
    # A `task` that is not schema-shaped is phase_part()'s problem, not a lag
    # signal: it already drops the label for exactly these values. Reporting
    # them here pasted a prose `task` back into the bar — the defect two
    # existing cases were written to prevent, reintroduced from a new direction.
    if not TASK_ID_RE.match(cur):
        return ""
    order, last_marked = [], -1
    for line in text.splitlines():
        tm = pu.TASK_RE.match(line)
        if tm:
            order.append({"num": tm.group(1), "state": None, "parallel": False})
            continue
        if not order:
            continue
        sm = pu.STATUS_RE.match(line)
        if sm and order[-1]["state"] is None:
            order[-1]["state"] = pu.status_state(sm.group(1))
        elif PARALLEL_YES_RE.match(line):
            order[-1]["parallel"] = True
    # Measured from the last marker that MOVED, not the last `[x]`. BL-096 is
    # about markers that stop moving, and `[~]` is a marker that moved — warning
    # on a correctly in-flight task would be a false positive against the very
    # state the contract added to express it.
    for i, t in enumerate(order):
        if t["state"] in ("done", "partial"):
            last_marked = i
    try:
        cur_i = [t["num"] for t in order].index(cur)
    except ValueError:
        # NOT folded into the silent cases. The state naming a task the plan no
        # longer has is a WORSE divergence than an ordinary lag — the plan was
        # edited under a run whose markers had already stopped — and silence
        # made it indistinguishable from nothing to report.
        return f" {RED}⚠ T{cur} not in plan{RESET}"
    # `Parallel: YES` siblings are dispatched together and do not finish in
    # document order, so an unmarked one between the last marker and the current
    # task is the format's own first-class concurrency, not a stall. Counting it
    # made the warning fire on sanctioned behaviour — and a signal that cries
    # wolf on the thing the plan told it to expect is worse than the silence it
    # replaces, because it teaches the reader to ignore it.
    gap = [t for t in order[last_marked + 1:cur_i] if not t["parallel"]]
    lag = len(gap) + 1
    if lag <= LAG_TOLERANCE:
        return ""
    return f" {YELLOW}⚠ status lag {lag}{RESET}"


def pinned_plan_path(state, state_file):
    """The absolute path of the plan a state file names.

    A relative `plan` is anchored to the REPO ROOT (.claude's parent), never to
    the process cwd — the statusline runs from wherever the user happens to be.
    This is a shared helper rather than inline code because it had to agree in
    two places and did not: render() re-parsed `state["plan"]` itself, kept it
    relative, and then both discover_plans()'s exclusion and render()'s own
    post-filter resolved it against the OS cwd. The pinned plan therefore
    failed to match itself and was rendered twice — once with its phase part,
    once as a discovered stranger — whenever a relative `plan` pointed inside
    the discovered plans directory, which is exactly the shape of the
    `docs/plans` fallback. It also burned a MAX_BARS slot that a genuinely
    different plan should have had.
    """
    plan = Path(state["plan"])
    if not plan.is_absolute():
        plan = state_file.parent.parent / plan
    return plan


def _bar_line(name, done, total, colour, width):
    """`⚙ <name padded> <bar> <done>/<total> (<pct>%)` — the shared opening.

    Extracted because render_pinned() and render_other() carried it verbatim,
    differing only in the colour and in the tail one of them appends. Task 3.4
    had to edit the same six lines twice, once per copy — the lockstep-drift
    shape rule_signature()'s own docstring names as the class it exists to
    prevent, recreated one layer up. Two callers, one definition.

    `width > 0`, NOT `if width:` — a tree-prefixed child gets
    `width - visible_len(prefix)`, which is NEGATIVE when the caller fell back
    to width=0, and a negative width is truthy. clip() then returns "" and
    ljust() does nothing, so the line rendered a complete, correctly-numbered
    bar with an EMPTY NAME: a wrong bar rather than a missing one, which is the
    single outcome render() says it exists to avoid. Reproduced by review via
    fault injection.

    THIS guard is the load-bearing one, and the suite pins it directly (revert
    it to `if width:` and the -3/-1 cases fail). render()'s call site also
    clamps, which is redundant given this line -- verified by mutation, removing
    the clamp fails nothing -- and is kept only so the negative case is visible
    where it arises rather than only where it is absorbed.
    """
    if width > 0:
        name = clip(name, width).ljust(width)
    out = f"{colour}⚙ {name}{RESET} "
    if total:
        pct = done * 100 // total
        out += f"{bar(done, total)} {done}/{total} {DIM}({pct}%){RESET}"
    return out


def blocked_gate_marker(text):
    """` ⊘ BLOCKED` when any stage-gate check in the plan is `[~]`, else "".

    A property of the PLAN, not of the phase, so it renders whether or not this
    session is the one executing — a plan whose gate could not be run is blocked
    for whoever looks at it next, and the bar is often the only place anyone
    looks. Appended rather than woven into the counts: the task counts are about
    tasks and stay honest; BL-077's failure was a plan reading as finished
    because nothing on the line spoke for the gate.

    Reads the contract through portfolio-unify, like every other marker here.

    NAMED `GATE BLOCKED`, not `BLOCKED`, because phase_part() already renders
    `✘ blocked <note>` in the same colour on the same line for a different
    subject — an execution this session has STOPPED, versus a gate check that
    could not be proven, possibly in an earlier session. Both can appear at
    once. gate_item_state() argues for not sharing vocabulary with
    status_state()'s `partial`; the same care was owed to this file's own
    vocabulary one screen away, and a review had to supply it.
    """
    return f" {RED}⊘ GATE BLOCKED{RESET}" if pu.plan_has_blocked_gate(text) else ""


def render_pinned(state_file, state=None, width=0, label=None, text=None):
    """The one line for the plan the state file names.

    Kept as its own function, taking the state file rather than a plan path,
    because its output is pinned byte-for-byte by a golden captured from the
    pre-Task-3.1 renderer. render() below composes it with the rest.

    `text` lets the caller pass the plan's contents it has already read.
    group_plans() reads every chosen plan to work out the master/child
    structure and then threw it away, so each of the up-to-3 files was read
    TWICE per redraw — free to remove, and it closes a (tiny) window where the
    two reads could disagree about the same file.
    """
    if state is None:
        state = json.loads(state_file.read_text())
    plan = pinned_plan_path(state, state_file)
    if text is None:
        text = plan.read_text(errors="ignore")
    done, total, stage_count = parse_plan(text, plan)
    out = _bar_line(label if label is not None else plan_name(plan),
                    done, total, CYAN, width)

    # Built as a list so the ` · ` separator is emitted only when something
    # actually follows it. The old form appended it unconditionally with the bar
    # and then appended a possibly-empty phase, so a file this renderer could not
    # read left a dangling "(100%) · " — verified live in writer-pad.
    tail = []
    pos = stage_position(state, stage_count)
    if pos:
        tail.append(f"S{pos[0]}/{pos[1]}")
    part = phase_part(state)
    if part:
        tail.append(part)
    if tail:
        if total:
            out += f" {DIM}·{RESET} "
        out += " ".join(tail)
    out += blocked_gate_marker(text)
    out += status_lag(state, text, plan)
    out += staleness(state)
    return out


def render_other(plan_path, width=0, label=None, text=None):
    """A bar line for a discovered plan that is NOT the one being executed.

    No phase part and no staleness marker: those describe an execution this
    session is driving, and nothing is driving these. Task 3.3 makes that
    distinction explicit; here it falls out of not having a state to read.
    """
    if text is None:
        text = _read_plan(plan_path)
    done, total, _ = parse_plan(text, plan_path)
    return _bar_line(label if label is not None else plan_name(plan_path),
                     done, total, DIM, width) + blocked_gate_marker(text)


def render(cwd):
    """Every line the status line should carry, in order — possibly none.

    The pinned plan (the one the state file names) keeps render_pinned()'s exact
    byte-for-byte output, and its group leads. Other in-flight plans for the
    same project follow, each master immediately above its own sub-plans.
    Returning a LIST rather than a string is the whole of Task 3.1: main()
    prints each element on its own line, so a second bar costs a line rather
    than a rewrite.

    Every step degrades to "fewer lines", never to an exception — this is still
    the statusline. Note which corpus lane proves what: lane A (`python3
    plan-progress.py`) comes through main() into here and so exercises the
    guards below; lane B deliberately BYPASSES this function to call the
    discovery surface raw, precisely so those guards cannot mask a function
    that fails to degrade on its own. Reading lane B as evidence about this
    function's exception safety gets it exactly backwards.
    """
    state_file = find_state(cwd)
    state = pinned = None
    if state_file is not None:
        try:
            # ONE read, one anchoring. Re-reading to recompute `pinned` also
            # raced executing-plans' overwrite-not-patch state writes: a rewrite
            # landing between the two reads made the second one fail and
            # silently disabled dedup for that redraw.
            state = json.loads(state_file.read_text())
            pinned = pinned_plan_path(state, state_file)
        except Exception:
            state = pinned = None   # an unreadable state file pins nothing

    chosen = []
    try:
        root = repo_root_of(state_file) if state_file is not None else Path(cwd)
        plans_dir = portfolio_plans_dir(root)
        if plans_dir is not None:
            cache = root / ".claude" / CACHE_NAME
            chosen = discover_plans(plans_dir, pinned=pinned, cache_file=cache)
    except Exception:
        chosen = []                 # discovery is additive: never costs the pinned bar

    # Discovery normally returns the pinned plan itself, but it returns nothing
    # at all when the project is unregistered, the vault is unreadable, or the
    # scan raised. The plan this session is executing has to render in every one
    # of those cases -- that is the pre-Stage-2 behavior, and it is the bar that
    # matters most.
    if pinned is not None and _is_file(pinned) and not any(
            _same_file(p, pinned) for p in chosen):
        chosen.insert(0, pinned)

    # BAD_PATH above fixes the root cause; this bounds the blast radius of the
    # NEXT one. group_plans() is the only step between having the plans and
    # printing them, so anything it raises costs every bar at once — including
    # the pinned bar the whole function above works to preserve. Grouping is
    # decoration; losing it must cost the glyphs, never the lines.
    try:
        grouped = group_plans(chosen, pinned=pinned)
    except Exception:
        grouped = [(p, "", plan_name(p), None) for p in chosen]

    # ONE width for every line, computed from the paths before anything is
    # rendered -- so a child's bar lands on the same column as its master's.
    # Cheap: plan_name() reads the filename, never the file.
    try:
        width = name_column([lab for _, _, lab, _ in grouped],
                            [pre for _, pre, _, _ in grouped])
    except Exception:
        width = 0       # unaligned bars beat no bars -- see group_plans() above

    lines = []
    for path, prefix, label, text in grouped:
        # `width - visible_len(prefix)` goes NEGATIVE when the width fallback
        # above fired. _bar_line() is what actually handles that (and is what
        # the suite pins); this clamp is redundant, kept so the negative case is
        # named where it arises instead of only where it is absorbed.
        avail = max(0, width - visible_len(prefix))
        # Per line, not per block: an unreadable plan costs its own bar and
        # leaves its siblings standing.
        try:
            if state is not None and pinned is not None and _same_file(path, pinned):
                lines.append(prefix + render_pinned(
                    state_file, state, width=avail, label=label, text=text))
            else:
                lines.append(prefix + render_other(
                    path, width=avail, label=label, text=text))
        except Exception:
            continue
    return lines


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    cwd = data.get("cwd") or (data.get("workspace") or {}).get("current_dir") or "."
    for line in render(cwd):
        print(line)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # A statusline must never print a traceback — blank line beats noise.
        sys.exit(0)
