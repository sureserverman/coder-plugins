#!/usr/bin/env python3
"""Classify a plan's stage-gate checks, and fail on instance-shaped ones.

Why this exists: a gate check asserting a property of a *set* — "no file still
claims X", "every example sets Y" — must be written as the command that sweeps
the set. An instance-shaped check names one member, so it CANNOT fail on the
siblings that make the defect class; they survive the gate and each one costs
another remediation round. In the run that motivated this script, one defect
class was discovered across four separate gate rounds for exactly that reason.

Every legitimate check has one of three shapes:

    EXECUTABLE  a command that sweeps the set it is claiming over
    JUDGMENT    marked `(judgment)`, because a reader genuinely must verify it
    SCOPED      marked `(scoped)`, because one artifact really is the whole set — a
                backlog ID unique within one register, a single generated manifest.
                The author asserts it in the check so a reviewer can disagree; syntax
                cannot tell this from the harmful narrow form, and widening it anyway
                produces a check that cannot pass at all rather than a stricter one.

Two failure shapes:

    INSTANCE-SHAPED  names one concrete artifact with no sweep and no marker.
                     Includes a command scoped to a single literal path — being
                     a shell command is not the point, scope is.
    PROSE            neither executable nor marked, and names no artifact. Weaker
                     signal (reported, not failed): often a legacy judgment check
                     written before the marker existed.

Exit 0 when no INSTANCE-SHAPED check is found, 1 otherwise, 2 on bad usage.
Always prints a per-class count and the total examined: an empty sweep must not
read as a pass (honest-gates).

Known limits, stated rather than implied (honest-gates). CALIBRATION is asserted by
tests/test-validate-gate-checks.py group 9 against the frozen corpus in
tests/fixtures/gate-check-corpus/, so the pin runs wherever the suite runs, CI included.
Every figure below is measured over that corpus and is therefore reproducible from the
repo alone — except where a bullet says otherwise, which is the one thing worth reading
carefully here:

  - Calibrated against 48 gate checks in 3 real plans: 21 EXECUTABLE,
    7 JUDGMENT, 3 INSTANCE-SHAPED, 17 PROSE. The corpus is frozen in the repo at
    tests/fixtures/gate-check-corpus/ (see its PROVENANCE.md) and these figures are pinned
    to it by tests/test-validate-gate-checks.py group 9, so they move only when someone
    deliberately edits that directory. Those 3 INSTANCE-SHAPED are legacy non-compliance,
    which is why `executing-plans` treats this as advisory on existing plans and mandatory
    only for newly authored ones.
  - A check carrying BOTH a narrow command and explicitly plural language ("`grep -c x
    one.md` = 1 and no stray refs remain") classifies EXECUTABLE. That branch carries 3
    corpus checks ("command plus set-quantified claim"), so it is deliberate — but it IS
    a way for a narrow command to pass, and a human reviewer is the only backstop.
  - PROSE is reported, never failed. 7 corpus checks are set-quantified claims that
    simply aren't executable yet; failing them would retro-fail every pre-rule plan.
  - Classification is syntactic. It cannot know that a directory argument happens to
    hold one file, nor read a script to see what it really asserts.
  - NOT MEASURED OVER THE FROZEN CORPUS — this one bullet is a MANUAL read (no script,
    so nothing re-runs it) of the 23 INSTANCE-SHAPED checks found across 12 of the 44
    plans in the vault corpus at /mnt/vault/Portfolio/ai-tools/coder-plugins/plans/,
    kept because the qualitative point survives the corpus change and nothing in the
    repo reproduces it. Roughly a quarter were set-valued claims narrowed to one member
    (the harmful form); about a third were live/manual judgment checks predating the
    `(judgment)` marker, wanting the marker rather than a sweep; the rest were
    single-file facts where one file really is the whole set. All are non-compliant with
    the rule as written, but the class name oversells how many are dangerous. Treat the
    proportions as an unpinned observation, not a figure you can re-derive from here.
  - A nested `- [ ]` sub-item under a gate bullet counts as its own top-level check.
    No real plan does this today; a sub-checklist would be double-counted.
  - An extension-less path (`plugins/foo`) is read as a directory, because syntax cannot
    distinguish it from an extension-less file. A check inspecting one such file reads
    EXECUTABLE.
  - `INLINE_SCRIPT`'s quote matching is not escape-aware, so an interpreter payload
    containing an escaped copy of its own delimiter truncates early.
  - The `Scope:`-advisory (`unswept_scopes`) is REPORTED, never failed, and only for
    stages that declare the field — so a plan predating it classifies identically. It
    accepts either sanctioned shape (a sweep or a `(judgment)` marker) as covering the
    declared set; it cannot tell whether the sweep actually covers the set the `Scope:`
    names, only that the stage has one.

Usage:
    validate-gate-checks.py <plan.md> [<plan.md> ...]
    validate-gate-checks.py --quiet <plan.md>     # counts + failures only
"""
import argparse
import pathlib
import re
import sys

# INVOKERS run a program whose scope is genuinely opaque: `pytest tests/one_test.py`
# may assert over a thousand files, so second-guessing it is not this script's job.
INVOKERS = (
    "python3", "python", "bash", "sh ", "pytest", "make ", "npm ", "cargo ",
    "podman", "docker", "gradlew", "node ",
)
# INSPECTORS read exactly the paths they are given, so their scope IS the check's
# scope. `git`, `sed`, `jq`, `awk`, `cat`, `head`, `tail`, `adb` and `curl` belong here,
# not above: `git grep -q x -- one.md` and `sed -n 1,5p one.md` inspect one file, and
# treating them as opaque runners let them launder the exact shape SKILL.md calls
# "ALSO BAD".
INSPECTORS = (
    "grep", "rg ", "ls ", "find ", "diff ", "git ", "sed ", "jq ",
    "cat ", "head ", "tail ", "adb ", "curl", "wc ",
)
# `for` and `awk` are ordinary English substrings ("wait for confirmation",
# "awkward phrasing"), so they only count as commands at the start of the span.
LEADING_ONLY = re.compile(r"^\s*(for|awk|while|if|test)\b")
RUNNERS = INVOKERS + INSPECTORS

# An inline-script flag turns an invoker into an inspector wearing its coat:
# `bash -c "grep -q x one.md"` is perfectly readable off the command line, so its
# scope must be judged from the payload rather than waved through.
#
# The interpreter must be named: `-c` is also grep's --count flag, and matching it
# bare made `grep -c 'x' a.md b.md c.md` recurse into 'x' and stop being a sweep.
INLINE_SCRIPT = re.compile(
    r"\b(?:bash|sh|zsh|python3?|perl|ruby|node)\s+(?:-\w+\s+)*-c\s+(['\"])(.*?)\1", re.S)
SHELL_OPS = ("&&", "||", " | ", "$(", ">/dev/null", "; ")

# Language that shows the claim is quantified over a set rather than one artifact.
# "no" must be a quantifier over a noun ("no file", "no plugin") — NOT the negation
# in "no longer" / "no more", which is how the canonical BAD example ("the README no
# longer claims X") slipped through as PROSE and passed a gate it should have failed.
SET_WORDS = re.compile(
    r"\bno (?!longer\b|more\b)\w"
    r"|\b(none|every|all|each|any|zero|both|neither|across|everywhere)\b"
    r"|\bper-\w", re.I)

# A concrete artifact: a path or filename carrying a known extension, or a path
# ending in a directory separator. Deliberately narrow, and it must NOT match a bare
# slash in prose — measured when the corpus stood at 357 checks (it is 374 now; master-plan
# `**Gate:**` recognition later surfaced 17 more), "pass/fail", "4/4",
# "skill/agent" and "scan/rollup" were the entire false-positive population when the
# slash alone was enough.
EXT = r"(?:md|py|sh|ya?ml|json|toml|kts?|gradle|txt|mjs|js|ts)"
ARTIFACT = re.compile(rf"[\w.\-]+(?:/[\w.\-]+)*\.{EXT}\b|[\w.\-]+/(?=\s|$|`)")

# "the README", "the manifest" — a definite article plus a file-ish noun is an
# artifact reference even without an extension.
DEFINITE_ARTIFACT = re.compile(
    r"\bthe (README|manifest|changelog|compose file|plugin\.json|marketplace entry|"
    r"SKILL\.md|workflow|index)\b", re.I)

# The heading must START with an optional "Stage N" and then "Gate", matching the
# documented contract. A looser `\bGate\b` anywhere also matched task headings such as
# "### Task 1.1: Gate `podman compose build` on image presence", which would vacuum
# unrelated task checklist items in as gate checks.
GATE_HEADING = re.compile(r"^#{2,4}\s+(?:Stage\s+\d+\s+)?Gates?\b[^\n]*$", re.M)
# Master plans carry their cross-plan checks under a `**Gate:**` bold marker rather than a
# heading — a deliberate second form, documented in master-plan-format.md, because a master
# is parser-safe by construction. Recognising only the heading made every master plan's
# gate checks structurally invisible (0 extracted from a fixture holding 3 real ones).
GATE_MARKER = re.compile(r"^\s*\*\*Gates?:?\*\*\s*$", re.M)
ANY_GATE_START = re.compile(
    r"^(?:#{2,4}\s+(?:Stage\s+\d+\s+)?Gates?\b[^\n]*|\s*\*\*Gates?:?\*\*\s*)$", re.M)
BULLET = re.compile(r"^(\s*)- \[[ xX]\] (.*)$")
NEXT_HEADING = re.compile(r"^#{2,4} ", re.M)


def backticked(text):
    return re.findall(r"`([^`]+)`", text)


SCRIPT_ONLY = re.compile(r"^[\w./\-]+\.(?:py|sh)$")


def is_command(span):
    s = span.strip()
    if any(op in s for op in SHELL_OPS):
        return True
    if s.startswith("!"):
        return True
    if any(r in s for r in RUNNERS) or LEADING_ONLY.match(s):
        return True
    # A script path, with or without arguments. Bare `validate-stack-routing.py` in a
    # gate check means "run it" — measured on the real corpus, requiring an explicit
    # `python3` prefix mis-flagged every check that named its script that way.
    return bool(SCRIPT_ONLY.match(s) or re.match(r"[\w./\-]+\.(?:py|sh)\s+\S", s))


def command_sweeps_a_set(span):
    """True when the command's scope is plural, or opaque because it runs a program.

    An INVOKER always qualifies: `python3 tests/test-foo.py` names one path but the
    suite behind it may assert over any number of things, and second-guessing that
    is not this script's job. Only an INSPECTOR — grep, ls, find, test, diff — has a
    scope we can read off the command line, so only those must show plurality.
    """
    s = span.strip()

    # Scope signals that don't depend on trusting an invoker.
    def scoped_plural(text):
        if any(t in text for t in ("-r", "--recursive", "*", "?", "$(")):
            return True
        # A pipe only proves plurality if the SOURCE side is plural. `cat one.md | bash
        # -c "grep -q x one.md"` is a single-file inspection wearing a pipeline, and
        # accepting the bare "|" character reopened the loophole from the other end.
        if "|" in text:
            head = text.split("|", 1)[0]
            if any(t in head for t in INVOKERS) or SCRIPT_ONLY.match(head.strip()):
                return True
            if any(t in head for t in ("-r", "--recursive", "*", "?", "$(")):
                return True
            if re.search(r"\s[\w.\-]+/[\w\-]*(\s|$)", head):
                return True
            if len(set(re.findall(rf"[\w./\-]+\.{EXT}\b", head))) > 1:
                return True
        if LEADING_ONLY.match(text.strip()):
            return True
        # A directory argument, with or without a trailing slash. `plugins/foo` is
        # ambiguous between a dir and an extension-less file and syntax cannot tell;
        # treating it as a dir keeps `ls plugins/foo | wc -l` correctly EXECUTABLE, at
        # the cost of the ambiguous-file case (disclosed in the limits above).
        if re.search(r"\s[\w.\-]+/[\w\-]*(\s|$)", text):
            return True
        return len(set(re.findall(rf"[\w./\-]+\.{EXT}\b", text))) > 1

    # An inline script (`bash -c "…"`, `python3 -c "…"`) must not let an invoker launder
    # a narrow inspector. But it must not veto a command that is plural for its OWN
    # reasons either — a pipeline containing `python3 -c` still sweeps whatever the
    # pipeline reads, and treating the payload as the whole story wrongly flagged it.
    inline = INLINE_SCRIPT.search(s)
    if inline:
        return scoped_plural(inline.group(2)) or scoped_plural(s)

    if any(t in s for t in INVOKERS) or SCRIPT_ONLY.match(s):
        return True
    return scoped_plural(s)


def names_artifact(text):
    stripped = re.sub(r"`[^`]*`", " ", text)          # names inside backticks too
    return bool(ARTIFACT.search(text) or DEFINITE_ARTIFACT.search(stripped)
                or DEFINITE_ARTIFACT.search(text))


def classify(check):
    """-> (class, reason)"""
    if re.search(r"\(judgment\)", check, re.I):
        return "JUDGMENT", "explicitly marked for a reader"
    if re.search(r"\(scoped\)", check, re.I):
        # The third sanctioned shape, and the one this script had no answer for. Its own
        # limits section already conceded the category — "the rest were single-file facts
        # where one file really is the whole set" — while still failing them, so an author
        # writing the correct narrow check was told to widen it. Widening a claim past the
        # set it is over does not make it stricter, it makes it unpassable: the check that
        # motivated this marker swept a whole portfolio for a backlog ID that is unique only
        # within one project's register, so it matched two dozen unrelated entries and could
        # never go green whatever the plan did.
        #
        # A marker rather than a cleverer classifier, because the judgment is not syntactic.
        # No amount of reading `grep -l X one/file.md` reveals whether that file is the whole
        # set; only the author knows. So the author asserts it, in the check, where a reviewer
        # can see the sentence and disagree with it — the same bargain `(judgment)` makes.
        return "SCOPED", "author asserts one artifact is the whole set"

    cmds = [s for s in backticked(check) if is_command(s)]
    if cmds:
        # A command plus a SEPARATE prose claim about a different artifact is the same
        # defect arriving by conjunction: the command cannot fail on the prose half, so
        # that half is unverified and rides along on an unrelated green.
        prose = re.sub(r"`[^`]*`", " ", check)
        prose_arts = set(ARTIFACT.findall(prose)) | set(
            m.group(0) for m in DEFINITE_ARTIFACT.finditer(prose))
        cmd_text = " ".join(cmds)
        uncovered = {a for a in prose_arts if a.strip("`") not in cmd_text}
        if uncovered and not SET_WORDS.search(prose):
            return ("INSTANCE-SHAPED",
                    f"command does not cover the artifact claimed in prose "
                    f"({sorted(uncovered)[0]}) — split the check or mark it (judgment)")
        if any(command_sweeps_a_set(c) for c in cmds):
            return "EXECUTABLE", "command sweeps a set"
        if SET_WORDS.search(re.sub(r"`[^`]*`", " ", check)):
            # e.g. "`python3 suite.py` and all five guards green" — the command is
            # narrow but the claim is explicitly plural and command-backed.
            return "EXECUTABLE", "command plus set-quantified claim"
        if names_artifact(check):
            return ("INSTANCE-SHAPED",
                    "command inspects a single literal path — scope it to the set")
        return "EXECUTABLE", "command, no single-artifact claim"

    if names_artifact(check):
        if SET_WORDS.search(re.sub(r"`[^`]*`", " ", check)):
            return "PROSE", "quantified over a set but not executable — write the sweep"
        return ("INSTANCE-SHAPED",
                "names one artifact with no sweep and no (judgment) marker")

    return "PROSE", "no artifact named; not executable"


def _is_continuation(accumulated, line):
    """Is `line` a wrap of the check so far, rather than new content beneath it?

    Joining too eagerly is its own bug: an indented explanatory paragraph or a fenced
    code block under a bullet would be glued onto the check and change its class. The
    discriminator that actually matches the real corpus is an *unterminated* command —
    both wrapped checks in this repo's plans wrap mid-backtick. Beyond that, accept a
    trailing shell/prose continuation operator, or a fragment that does not begin like
    a new sentence.
    """
    if not line.strip() or not re.match(r"^\s+\S", line):
        return False
    stripped = line.strip()
    if stripped.startswith(("```", "~~~", "- ", "* ", "+ ", "> ", "#", "|")):
        return False
    if accumulated.count("`") % 2 == 1:            # mid-command, definitely a wrap
        return True
    if accumulated.rstrip().endswith(("&&", "||", "|", "\\", ",", ":", "(")):
        return True
    # a fragment continues; a new sentence or a labelled note does not
    return bool(re.match(r"[a-z`'\"/.\-]", stripped)) and not re.match(
        r"(Note|NOTE|TODO|Why|See|Rationale|Evidence)\b", stripped)


def gate_checks(text):
    """Extract gate checks, joining wrapped continuation lines.

    A long check routinely wraps onto an indented continuation line, and reading only
    the first line silently changes the verdict in BOTH directions: an unterminated
    backtick hides a real command (a valid check flagged), and a path that lives on the
    second line hides a real single-artifact claim (an invalid check missed). 28 wrapped
    bullets exist across 7 plans in this repo's own corpus, so this is the common case,
    not an edge case.
    """
    out = []
    for m in ANY_GATE_START.finditer(text):
        seg = text[m.end():]
        # A block ends at the next heading or the next gate marker, whichever comes first.
        ends = [x.start() for x in (NEXT_HEADING.search(seg), GATE_MARKER.search(seg)) if x]
        if ends:
            seg = seg[:min(ends)]
        current = None
        for line in seg.splitlines():
            b = BULLET.match(line)
            if b:
                if current:
                    out.append(current)
                current = b.group(2).strip()
            elif current is not None:
                if _is_continuation(current, line):
                    current += " " + line.strip()
                else:
                    out.append(current)
                    current = None
        if current:
            out.append(current)
    return out


SCOPE_FIELD = re.compile(r"^\s*[-*]\s+\*\*Scope:\*\*\s*(.+)$", re.MULTILINE)


def unswept_scopes(text):
    """Stage numbers whose tasks declare a `Scope:` but whose gate sweeps nothing.

    `Scope:` names the set at authoring time; the gate check is what proves the set was
    swept. Declaring one without the other is the failure the field exists to prevent,
    dressed up as compliance — the author enumerated the class and then verified one
    member of it.

    Reported, never failed, and ONLY for stages that declare the field. A plan with no
    `Scope:` anywhere is classified exactly as it was before the field existed, so every
    plan authored before this rule reports identically — the same
    advisory-on-legacy asymmetry `executing-plans` applies to INSTANCE-SHAPED, and for
    the same reason: a check executors learn to route around protects nothing.
    """
    out = []
    stages = re.split(r"\n(?=## Stage )", text)
    for seg in stages:
        m = re.match(r"## Stage (\S+)", seg)
        if not m:
            continue
        if not SCOPE_FIELD.search(seg):
            continue
        checks = gate_checks(seg)
        if not checks:
            continue
        # EXECUTABLE **or** JUDGMENT. The class-predicate rule sanctions exactly two
        # shapes for a set-valued check — the sweep, or the `(judgment)` marker for a
        # claim a reader must genuinely verify. Accepting only the first made this
        # advisory contradict the rule it exists to support, flagging a stage that
        # covered its Scope: the sanctioned second way. An advisory that is wrong on
        # its own stated criteria teaches authors to route around it.
        if not any(classify(c)[0] in ("EXECUTABLE", "JUDGMENT", "SCOPED") for c in checks):
            out.append(m.group(1).rstrip(":"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="validate-gate-checks")
    ap.add_argument("plans", nargs="+", type=pathlib.Path)
    ap.add_argument("--quiet", action="store_true",
                    help="print counts and failures only")
    args = ap.parse_args(argv)

    totals = {"EXECUTABLE": 0, "JUDGMENT": 0, "SCOPED": 0, "INSTANCE-SHAPED": 0, "PROSE": 0}
    failures = []
    examined_files = 0
    empty_files = []
    scope_notes = []

    for path in args.plans:
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            return 2
        raw = path.read_text(encoding="utf-8")
        checks = gate_checks(raw)
        unswept = unswept_scopes(raw)
        if unswept:
            scope_notes.append((path, unswept))
        examined_files += 1
        if not checks:
            empty_files.append(path.name)
        per = {k: 0 for k in totals}
        for c in checks:
            kind, why = classify(c)
            per[kind] += 1
            totals[kind] += 1
            if kind == "INSTANCE-SHAPED":
                failures.append((path, c, why))
        if not args.quiet:
            print(f"{path.name}: {len(checks)} check(s) — "
                  + ", ".join(f"{k.lower()} {v}" for k, v in per.items() if v))

    total = sum(totals.values())
    if total == 0:
        print(f"error: swept {examined_files} file(s) and found 0 gate checks — "
              f"the extraction is broken, or these are not plans", file=sys.stderr)
        return 2

    if failures:
        print(f"\nFAIL: {len(failures)} instance-shaped check(s):", file=sys.stderr)
        for path, c, why in failures:
            print(f"  {path.name}: {c[:96]}\n      → {why}", file=sys.stderr)

    # Name the files that yielded nothing. A batch total hides a file the extractor
    # cannot see — which is exactly how master-plan `**Gate:**` blocks went unnoticed
    # while the aggregate looked healthy.
    if empty_files:
        print(f"\nnote: {len(empty_files)} file(s) yielded 0 gate checks — "
              f"verify they genuinely have no gate: {', '.join(empty_files)}")

    # Advisory, never a failure: it changes no exit code, so a legacy plan is
    # unaffected and a post-rule plan gets told.
    for path, stages in scope_notes:
        print(f"\nnote: {path.name}: stage(s) {', '.join(stages)} declare a Scope: "
              f"but their gate has no executable sweep — the set was named, not swept")

    print(f"\n{total} gate check(s) across {examined_files} file(s): "
          + ", ".join(f"{k.lower()} {v}" for k, v in totals.items()))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
