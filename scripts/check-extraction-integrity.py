#!/usr/bin/env python3
"""Catch what extraction breaks that a diff cannot see.

Moving prose out of a monolith into `references/` silently invalidates two
things that were correct in the single file (BL-039):

  DEAD-PATH          a relative path or link that resolved from the monolith's
                     directory and resolves from nowhere one level down.
  DEIXIS-POSITIONAL  "the rules above", "the flow below" — position words whose
                     referent stayed in the trunk. Checked in `references/*.md`
                     only: inside a single trunk, "above" genuinely resolves.
  DEIXIS-SECTION     an unqualified `§ Some Heading` naming no heading in this
                     file and no file the reader could open. Checked everywhere,
                     trunks included — that is where BL-039 found one.

What it deliberately does NOT flag, because a guard that cries wolf gets its
findings allowlisted wholesale and then guards nothing:

  - `below \x60standard\x60`, `above ~5 minutes`, `below the standard plan` — these are
    comparisons and rankings, not positions. The distinguishing feature is what
    FOLLOWS the word: a backticked token, a number, or a tier name.
  - `\x60../SKILL.md\x60 § Stage structure` — a § qualified by a path or by the word
    "trunk" tells the reader where to look, which is the whole point.
  - A positional word whose referent IS resolvable in the same file (a heading,
    bold run, or table caption matching the noun phrase).

Scans `*/skills/*/SKILL.md` and `*/skills/*/references/*.md` from the repo root.
Paths under `tests/` or `fixtures/` are excluded (test data, not shipped prose).
A finding is suppressed only by an exact `path:CODE:token` entry in
`scripts/extraction-integrity-allow.txt` — never by a bare path, so allowlisting
one known instance cannot hide the next one in the same file.

Read-only: never writes to the repo. Exit 0 when clean, 1 when any finding.
"""
import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWLIST_PATH = os.path.join(REPO_ROOT, "scripts", "extraction-integrity-allow.txt")

EXCLUDE_PARTS = ("/tests/", "/fixtures/")

# A path-ish string: has a separator or a known extension, and no spaces.
PATH_EXTS = (".md", ".py", ".sh", ".json", ".txt", ".yml", ".yaml", ".toml")

BACKTICK_RE = re.compile(r"`([^`\n]+)`")
MDLINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

# Words that make "above"/"below" a comparison rather than a position.
TIER_WORDS = (
    "high", "standard", "light", "none", "medium", "low",
    "critical", "important", "the standard", "threshold", "budget", "baseline",
)

# noun phrase + position word, e.g. "the gate rules above", "Context resets below"
POSITIONAL_RE = re.compile(
    r"(?P<noun>[A-Za-z][A-Za-z'’\-]*(?:\s+[A-Za-z][A-Za-z'’\-]*){0,3})\s+"
    r"(?P<word>above|below)\b",
    re.IGNORECASE,
)
SEE_RE = re.compile(r"\(?\bsee\s+(?P<word>above|below)\b\)?", re.IGNORECASE)

SECTION_RE = re.compile(r"§\s*(?P<name>[^.,;)\n]+)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.M)


def normalize(s):
    """Lowercase, strip markdown emphasis and punctuation, collapse whitespace."""
    s = re.sub(r"[*_`\"'“”‘’]", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def load_allowlist(path=ALLOWLIST_PATH):
    allowed = set()
    if not os.path.exists(path):
        return allowed
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            entry = line.split("#", 1)[0].strip()
            if entry:
                allowed.add(entry)
    return allowed


def list_allowlisted(path=ALLOWLIST_PATH):
    """The allowlist's entries, verbatim and in file order."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            entry = line.split("#", 1)[0].strip()
            if entry:
                out.append(entry)
    return out


def is_pathish(tok):
    if not tok or " " in tok or "\t" in tok:
        return False
    if tok.startswith(("http://", "https://", "mailto:", "#", "/", "~")):
        return False
    if tok.startswith("$") or "${" in tok:
        return False          # ${CLAUDE_PLUGIN_ROOT}/... is resolved at runtime
    if "*" in tok:
        return False          # a glob is a pattern, not a path to resolve
    if tok.endswith(PATH_EXTS):
        return True
    return False


# Structural names that mark a token as a reference to a file in THIS repo.
INTERNAL_MARKERS = ("/references/", "references/", "/skills/", "skills/",
                    "/scripts/", "scripts/", "/agents/", "agents/")


def is_internal_ref(tok):
    """True when the token points at another file in this repo's own tree.

    Skill prose cites paths in the *user's* project constantly — `fastlane/
    metadata/android/en-US/title.txt`, `docs/f-droid/<applicationId>.yml`,
    `app/build.gradle` — and those never resolved from here and never should.
    Measured on this tree, treating every path-ish token as internal produced
    847 findings of which ~18 belonged to the defect class; the other 829 were
    target-project paths, tree-diagram filenames and `<placeholder>` templates.
    An allowlist that size is not a guard, so the discriminator is structural:
    a cross-reference to a plugin file names `SKILL.md`, or sits under one of
    this repo's own structural directories.
    """
    if "<" in tok or ">" in tok:
        return False                      # templated placeholder, not a path
    if tok.endswith("SKILL.md"):
        return True
    marked = f"/{tok}"
    return any(m in marked for m in INTERNAL_MARKERS)


# A position word qualified by one of these is describing physical space or a
# ranking, not a place in the document: "slightly above the avatar's head",
# "on API 25 and below", "ranking it above a populated key".
SPATIAL_QUALIFIERS = ("slightly", "just", "directly", "immediately", "well",
                      "far", "and", "or", "sits", "ranking", "rank", "ranked")
PRONOUNS = ("it", "them", "this", "that", "these", "those", "one", "which", "you")
# Nouns that name a structure rather than a titled section: resolvable only by
# looking for the structure itself, not by matching a heading.
STRUCTURAL_NOUNS = {
    "table": re.compile(r"^\s*\|", re.M),
    "list": re.compile(r"^\s*(?:[-*+]|\d+\.)\s", re.M),
    "form": re.compile(r"^\s*\|", re.M),
    "diagram": re.compile(r"^\s*```", re.M),
    "block": re.compile(r"^\s*```", re.M),
    "example": re.compile(r"^\s*```", re.M),
}


def _comparison_context(text, end):
    """True when what follows the position word makes it a comparison."""
    rest = text[end:end + 40].lstrip()
    if not rest:
        return False
    if rest[0] in "`~":
        return True
    m = re.match(r"(?:about\s+|roughly\s+|~)?(\d)", rest)
    if m:
        return True
    low = rest.lower()
    return any(low.startswith(w) for w in TIER_WORDS)


def _spatial_or_ranking(noun):
    """True when the noun phrase makes this a physical or ordering relation."""
    words = noun.lower().split()
    if not words:
        return True
    if words[-1] in SPATIAL_QUALIFIERS or words[-1] in PRONOUNS:
        return True
    return False


def _structure_present(text, noun, word):
    """For 'the table below' / 'the list above': does that structure exist here?

    A referent that is genuinely present in this same file is not the BL-039
    defect — that defect is a referent left behind in the trunk. Checking for
    the structure rather than a heading is what makes a generic noun decidable.
    """
    last = noun.lower().split()[-1] if noun.split() else ""
    pattern = STRUCTURAL_NOUNS.get(last)
    if pattern is None:
        return False
    return bool(pattern.search(text))


def _resolves_locally(text, noun):
    """True when the noun phrase names something present in this same file."""
    n = normalize(noun)
    if not n:
        return False
    # Drop leading articles/determiners so "the gate rules" matches "Gate rules".
    n = re.sub(r"^(the|a|an|its|this|that|these|those|one|each|every|normal|same)\s+", "", n)
    if len(n) < 4:
        return False
    hay = normalize(text)
    # Count occurrences: one is the reference itself, so it must appear twice.
    return hay.count(n) >= 2


def plugin_root(relpath, root):
    """The plugin directory a repo-relative file belongs to.

    `business/skills/business-plan/SKILL.md` -> `<root>/business`, which is what
    a plugin-rooted `references/foo.md` citation resolves against.
    """
    parts = relpath.split("/")
    return os.path.join(root, parts[0]) if len(parts) > 1 else root


def scan_file(relpath, text, root):
    """Findings for one file. `relpath` is repo-relative; `root` resolves paths."""
    findings = []
    is_reference = "/references/" in f"/{relpath}"
    filedir = os.path.dirname(os.path.join(root, relpath))
    lines = text.split("\n")

    headings = [normalize(h) for h in HEADING_RE.findall(text)]

    in_fence = False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue

        # --- DEAD-PATH -------------------------------------------------
        toks = [m.group(1) for m in BACKTICK_RE.finditer(line)]
        toks += [m.group(1) for m in MDLINK_RE.finditer(line)]
        # Inside a fence there are no backticks to delimit anything: the whole
        # line is a command, and its bare arguments are paths the reader will
        # actually run. BL-039's sharper half lives here.
        if in_fence:
            toks += line.split()
        for tok in toks:
            cand = tok.split("#", 1)[0].strip()
            if not is_pathish(cand) or not is_internal_ref(cand):
                continue
            # Three addressing conventions are all legitimate here, so a token
            # is dead only when it resolves under none of them:
            #   file-relative   `../review-scope.md` from a references/ file
            #   plugin-rooted   `references/plan-format.md` from a SKILL.md,
            #                   the DEC-009 form — business-plan has no
            #                   skill-level references/ dir and the file lives
            #                   at business/references/
            #   repo-rooted     a fenced command, which runs from the checkout
            # Picking one and flagging the rest is the guard being wrong about
            # which contract the string serves — BL-039's own sharper lesson.
            bases = [filedir, plugin_root(relpath, root), root]
            if not any(os.path.exists(os.path.normpath(os.path.join(base, cand)))
                       for base in bases):
                findings.append({
                    "path": relpath, "line": i, "code": "DEAD-PATH",
                    "token": cand, "text": line.strip()[:120],
                })

        # --- DEIXIS-POSITIONAL (reference files, prose only) -----------
        # Inside a fence, "checked above" is a SAFETY comment about the lines
        # of code above it, and "# see below" annotates a YAML key. Both refer
        # to the listing, not to the document, so neither is extraction deixis.
        if is_reference and not in_fence:
            seen_spans = []
            for m in POSITIONAL_RE.finditer(line):
                if _comparison_context(line, m.end()):
                    continue
                noun = m.group("noun")
                if _spatial_or_ranking(noun):
                    continue
                if _structure_present(text, noun, m.group("word")):
                    continue
                if _resolves_locally(text, noun):
                    continue
                token = f"{noun.split()[-1]} {m.group('word')}".lower()
                seen_spans.append(m.start())
                findings.append({
                    "path": relpath, "line": i, "code": "DEIXIS-POSITIONAL",
                    "token": token, "text": line.strip()[:120],
                })
            for m in SEE_RE.finditer(line):
                if any(abs(m.start() - s) < 30 for s in seen_spans):
                    continue
                findings.append({
                    "path": relpath, "line": i, "code": "DEIXIS-POSITIONAL",
                    "token": f"see {m.group('word')}".lower(),
                    "text": line.strip()[:120],
                })

        # --- DEIXIS-SECTION (everywhere) -------------------------------
        for m in SECTION_RE.finditer(line):
            before = line[:m.start()]
            # Qualified by a path or by the word "trunk" -> the reader can follow it.
            tail = before[-70:]
            if "trunk" in tail.lower():
                continue
            if any(is_pathish(t.split("#", 1)[0].strip())
                   for t in BACKTICK_RE.findall(tail)):
                continue
            name = normalize(m.group("name"))
            if not name:
                continue
            if any(name in h or h in name for h in headings if h):
                continue
            findings.append({
                "path": relpath, "line": i, "code": "DEIXIS-SECTION",
                "token": m.group("name").strip()[:60],
                "text": line.strip()[:120],
            })

    return findings


def discover(root, scope):
    """Repo-relative SKILL.md and references/*.md paths, sorted."""
    out = []
    base = os.path.join(root, scope) if scope else root
    if not os.path.isdir(base):
        return out
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            marker = f"/{rel}"
            if any(p in marker for p in EXCLUDE_PARTS):
                continue
            if fn == "SKILL.md" or "/references/" in marker:
                out.append(rel)
    return sorted(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check-extraction-integrity")
    ap.add_argument("--root", default=REPO_ROOT)
    ap.add_argument("--allowlist", default=None)
    ap.add_argument("--scope", default=None,
                    help="repo-relative subtree to restrict the scan to")
    ap.add_argument("--list-allowlisted", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    allow_path = args.allowlist or os.path.join(args.root, "scripts",
                                                "extraction-integrity-allow.txt")

    if args.list_allowlisted:
        for entry in list_allowlisted(allow_path):
            print(entry)
        return 0

    allowed = load_allowlist(allow_path)
    files = discover(args.root, args.scope)

    findings, suppressed = [], []
    for rel in files:
        with open(os.path.join(args.root, rel), encoding="utf-8") as fh:
            text = fh.read()
        for f in scan_file(rel, text, args.root):
            key = f"{f['path']}:{f['code']}:{f['token']}"
            (suppressed if key in allowed else findings).append(f)

    if args.json:
        print(json.dumps({"scanned": len(files), "findings": findings,
                          "suppressed": len(suppressed)}, indent=2))
    else:
        # honest-gates: always print what was examined, so an empty sweep
        # cannot read as a pass that covered something.
        scope_note = f" under {args.scope}" if args.scope else ""
        print(f"Scanned {len(files)} file(s){scope_note}; "
              f"{len(findings)} finding(s), {len(suppressed)} allowlisted.")
        for f in findings:
            print(f"  {f['path']}:{f['line']}  {f['code']}  [{f['token']}]")
            print(f"      {f['text']}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
