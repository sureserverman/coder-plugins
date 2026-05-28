#!/usr/bin/env python3
"""Find likely user-facing hardcoded strings in source code.

This is a heuristic scanner — high recall, moderate precision. It is the
LLM's job, in a downstream step, to filter the output for actual
user-facing strings (vs log messages, error messages thrown to devs,
assertion text, fixture data, etc).

Output: TSV — file<TAB>line<TAB>likelihood<TAB>snippet
where likelihood is one of: high, medium, low.

Likelihood is raised when the surrounding source matches a UI-call
context (setText, Text(...), JSX children, alert, toast, console.log
INSIDE a UI file, etc.). It is lowered when the file looks like tests,
config, generated code, logging, or migrations.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "target", "build", "dist",
    ".gradle", ".dart_tool", ".venv", "venv", "__pycache__",
    ".next", ".nuxt", ".cache", ".idea", ".vscode", "coverage",
    "fixtures", "__fixtures__", "__snapshots__",
}

SKIP_NAME_PATTERNS = [
    re.compile(r"\.test\."),
    re.compile(r"\.spec\."),
    re.compile(r"_test\."),
    re.compile(r"_spec\."),
    re.compile(r"\.min\."),
    re.compile(r"\.generated\."),
    re.compile(r"\.g\."),
    re.compile(r"\.pb\."),
    re.compile(r"\.d\.ts$"),
]

# Languages we look at
UI_EXT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".vue", ".svelte",
    ".py", ".rb", ".go", ".rs", ".java", ".kt", ".kts",
    ".swift", ".m", ".mm",
    ".dart", ".php", ".cs", ".cpp", ".cc", ".h", ".hpp",
    ".lua", ".scala",
    ".html", ".xml",
}

# Patterns that suggest a UI call site within ~3 lines before the string.
UI_CONTEXT_RE = re.compile(
    r"\b("
    r"setText|setTitle|setLabel|setPlaceholder|setError|setHint|setContentDescription|"
    r"Text\s*\(|Button\s*\(|Label\s*\(|AppBar|Alert|Toast|Snackbar|"
    r"alert\s*\(|confirm\s*\(|prompt\s*\(|"
    r"showDialog|showSnackbar|showToast|"
    r"placeholder=|title=|label=|description=|aria-label=|"
    r"setAttribute\(\s*['\"](title|placeholder|alt|aria-label)['\"]"
    r")\b",
    re.I,
)

# Patterns that suggest a NON-UI call (log/error/debug)
LOG_CONTEXT_RE = re.compile(
    r"\b(log|logger|logging|debug|info|warn|warning|error|critical|trace|"
    r"print|println|fmt\.Print|panic|raise|throw\s+new\s+Error|"
    r"assert|assertEquals|assertTrue|assertFalse|expect\s*\(|"
    r"console\.(log|debug|info|warn|error|trace))\b",
    re.I,
)

# String literal extraction — keep it boring and language-agnostic. Match
# double-quoted, single-quoted, and backtick-quoted strings on a single line.
# (Multi-line strings are deliberately ignored — too noisy.)
STRING_RES = [
    re.compile(r'"((?:[^"\\\n]|\\.){2,})"'),
    re.compile(r"'((?:[^'\\\n]|\\.){2,})'"),
    re.compile(r"`((?:[^`\\\n]|\\.){2,})`"),
]

# Reject strings that look technical / non-user-facing
TECH_REJECT_RES = [
    re.compile(r"^https?://"),
    re.compile(r"^[a-z][a-z0-9_]*$"),                     # snake_case identifier
    re.compile(r"^[A-Z][A-Z0-9_]*$"),                     # CONST identifier
    re.compile(r"^[a-z]+(?:[A-Z][a-z0-9]*)+$"),           # camelCase identifier
    re.compile(r"^[\d.,:\s+\-=*/%()_]+$"),                # numeric / punctuation only
    re.compile(r"^[/.][a-zA-Z0-9_./\-]+$"),               # paths
    re.compile(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_./\-+]+$"),   # MIME-like
    re.compile(r"^\\?[ntrsv0]$"),                         # escape sequences
    re.compile(r"^[#$%&*+\-./<=>?@\\^_`|~]+$"),           # operators
    re.compile(r"^[a-zA-Z_]\w*\([^)]*\)$"),               # function call lit
    re.compile(r"^\{.*\}$"),                              # JSON-ish
    re.compile(r"^<[^>]+>$"),                             # single XML/HTML tag
    re.compile(r"^[A-Za-z0-9+/=]{40,}$"),                 # base64-ish
    re.compile(r"^[0-9a-fA-F]{8,}$"),                     # hex / hash
    re.compile(r"\\[a-zA-Z]"),                            # regex-like
    re.compile(r"^%[a-zA-Z0-9.\-+ #]*[sdifguxXeEoc]$"),   # printf spec alone
    re.compile(r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b", re.I),  # SQL
]


def is_user_facing_candidate(s: str) -> bool:
    s = s.strip()
    if len(s) < 3:
        return False
    if "\n" in s:
        return False
    for pat in TECH_REJECT_RES:
        if pat.match(s):
            return False
    # Must contain at least one space, OR two letters and a vowel — a crude
    # "looks like a word" filter.
    has_space = " " in s
    letters = sum(1 for c in s if c.isalpha())
    has_vowel = any(c in "aeiouAEIOU" for c in s)
    if not has_space and not (letters >= 4 and has_vowel):
        return False
    return True


def context_likelihood(lines: list[str], lineno: int) -> str:
    """high / medium / low based on surrounding 5 lines."""
    start = max(0, lineno - 3)
    end = min(len(lines), lineno + 2)
    window = "\n".join(lines[start:end])
    if UI_CONTEXT_RE.search(window):
        return "high"
    if LOG_CONTEXT_RE.search(window):
        return "low"
    return "medium"


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    out: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        # Cheap line-level rejects
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "*", "--")):
            continue
        if "import " in stripped or "require(" in stripped:
            continue
        for pat in STRING_RES:
            for m in pat.finditer(line):
                s = m.group(1)
                if not is_user_facing_candidate(s):
                    continue
                likelihood = context_likelihood(lines, i)
                out.append((i + 1, likelihood, s))
    return out


def walk(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(p in SKIP_DIRS for p in rel_parts):
            continue
        if path.suffix.lower() not in UI_EXT:
            continue
        name = path.name
        if any(p.search(name) for p in SKIP_NAME_PATTERNS):
            continue
        yield path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--framework", help="(advisory — currently unused; future per-framework tuning)")
    ap.add_argument("--min", choices=["high", "medium", "low"], default="medium",
                    help="minimum likelihood to report (default: medium)")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    min_rank = {"low": 0, "medium": 1, "high": 2}
    min_v = min_rank[args.min]

    for f in walk(root):
        rel = f.relative_to(root)
        for lineno, likelihood, snippet in scan_file(f):
            if min_rank[likelihood] < min_v:
                continue
            # TSV — escape tabs/newlines in snippet
            snip = snippet.replace("\t", " ").replace("\n", " ")
            print(f"{rel}\t{lineno}\t{likelihood}\t{snip}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
