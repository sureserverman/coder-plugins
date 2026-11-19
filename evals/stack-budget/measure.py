#!/usr/bin/env python3
"""measure.py — sweep every registry project through vault-context's session-start hook.

For each `enabled: true` project in the registry it compares the stack pages the
project's sidecar says apply (the `## Stack rules` block of
`<project>/.claude/vault-context.md`) with what the hook really emits: copies
inlined whole (their `vault-context:stack-rule source=<slug>` marker) and copies
only named (`The <slug> stack page applies to this project but did not fit`).

    measure.py --registry FILE --hook FILE --out TSV

Writes a TSV (project, applies, inlined, named, chars) and prints, last,
`budget: <n> projects, <k> with a page named, not inlined, <m> skipped`.

Exit 0 when every project's listed pages equal inlined plus named, the two do
not overlap, and the output is at most 9,500 characters; 1 otherwise, one
`FAIL: <project>: <why>` line each; 2 on a usage error, an unreadable registry,
a project with no sidecar, or a hook that exits non-zero or prints something
that is neither empty nor JSON. A registry folder that does not exist is
skipped and counted. Standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys

BUDGET = 9500
HOOK_TIMEOUT = 60
SIDECAR = os.path.join(".claude", "vault-context.md")
STACKS_START = "<!-- vault-context:stacks:start -->"
STACKS_END = "<!-- vault-context:stacks:end -->"
SLUG_LINE = re.compile(r"^- \*\*([a-z0-9-]+)\*\* —")
INLINED = re.compile(r"^<!-- vault-context:stack-rule source=([a-z0-9-]+)[ >]", re.M)
NAMED = re.compile(r"The ([a-z0-9-]+) stack page applies to this project but did not fit")


class Fatal(Exception):
    """An exit-2 condition: the sweep cannot say anything trustworthy."""


def _value(raw):
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    return v


def read_registry(path):
    """Paths of the `enabled: true` entries, in registry order."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        raise Fatal(f"cannot read registry {path}: {e}")
    entries, cur = [], None
    for line in lines:
        s = line.strip()
        if s.startswith("- path:"):
            cur = {"path": _value(s[len("- path:"):]), "enabled": None}
            entries.append(cur)
        elif cur is not None and s.startswith("enabled:"):
            cur["enabled"] = _value(s[len("enabled:"):]).lower()
    if not entries:
        raise Fatal(f"registry {path} lists no `- path:` entries")
    return [e["path"] for e in entries if e["enabled"] == "true"]


def sidecar_slugs(project):
    """Slugs of the sidecar's Stack rules block; [] when there is no block."""
    path = os.path.join(project, SIDECAR)
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        raise Fatal(f"{project}: no sidecar at {path}")
    except (OSError, UnicodeDecodeError) as e:
        raise Fatal(f"{project}: cannot read sidecar {path}: {e}")
    slugs, inside = [], False
    for line in lines:
        if line.strip() == STACKS_START:
            inside = True
        elif line.strip() == STACKS_END:
            inside = False
        elif inside:
            m = SLUG_LINE.match(line)
            if m:
                slugs.append(m.group(1))
    return slugs


def run_hook(hook, project):
    """additionalContext the hook emits for `project` (None when it prints nothing).

    Returns (context, problem): problem is a string when the output is JSON of
    the wrong shape (a FAIL, not a fatal error)."""
    payload = json.dumps({"cwd": project, "hook_event_name": "SessionStart"})
    cmd = [sys.executable, hook] if hook.endswith(".py") else [hook]
    try:
        r = subprocess.run(cmd, input=payload, capture_output=True, text=True,
                           timeout=HOOK_TIMEOUT, cwd=project)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Fatal(f"{project}: hook {hook} did not run: {e}")
    if r.returncode != 0:
        tail = r.stderr.strip().splitlines()[-1:] or [""]
        raise Fatal(f"{project}: hook exited {r.returncode}: {tail[0]}")
    out = r.stdout.strip()
    if not out:
        return None, None
    try:
        data = json.loads(out)
    except ValueError:
        raise Fatal(f"{project}: hook printed something that is not JSON: {out[:80]!r}")
    hso = data.get("hookSpecificOutput") if isinstance(data, dict) else None
    ctx = hso.get("additionalContext") if isinstance(hso, dict) else None
    if not isinstance(ctx, str) or hso.get("hookEventName") != "SessionStart":
        return None, "hook JSON has no hookSpecificOutput.additionalContext for SessionStart"
    return ctx, None


def chars(s):
    # UTF-16 code units, as the hook and Claude Code count them.
    return len(s.encode("utf-16-le")) // 2


def judge(applies, inlined, named, size):
    """Why this project fails, as a list of reasons; [] when it passes.

    The dropped-page rule lives here: every page the sidecar lists must be
    either inlined or named, never silently left out."""
    why = []
    a, i, n = set(applies), set(inlined), set(named)
    dropped = sorted(a - i - n)
    if dropped:
        why.append(f"applies but neither inlined nor named: {','.join(dropped)}")
    both = sorted(i & n)
    if both:
        why.append(f"both inlined and named: {','.join(both)}")
    extra = sorted((i | n) - a)
    if extra:
        why.append(f"emitted but not listed in the sidecar: {','.join(extra)}")
    dup = sorted({s for s in inlined if inlined.count(s) > 1}
                 | {s for s in named if named.count(s) > 1})
    if dup:
        why.append(f"emitted more than once: {','.join(dup)}")
    if size > BUDGET:
        why.append(f"output is {size} characters, over {BUDGET}")
    return why


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--registry", required=True)
    ap.add_argument("--hook", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if not os.path.isfile(args.hook):
        print(f"ERROR: hook {args.hook} is not a file", file=sys.stderr)
        return 2

    try:
        projects = read_registry(args.registry)
    except Fatal as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    rows, fails, errors = [], [], []
    swept = with_named = skipped = 0
    for project in projects:
        if not os.path.isdir(project):
            skipped += 1
            continue
        try:
            applies = sidecar_slugs(project)
            ctx, problem = run_hook(args.hook, project)
        except Fatal as e:
            errors.append(str(e))
            continue
        swept += 1
        text = ctx or ""
        inlined = INLINED.findall(text)
        named = NAMED.findall(text)
        size = chars(text)
        if named:
            with_named += 1
        rows.append((project, ",".join(applies), ",".join(inlined), ",".join(named), str(size)))
        why = judge(applies, inlined, named, size)
        if problem:
            why.insert(0, problem)
        for w in why:
            fails.append(f"FAIL: {project}: {w}")

    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write("project\tapplies\tinlined\tnamed\tchars\n")
            for row in rows:
                fh.write("\t".join(row) + "\n")
    except OSError as e:
        print(f"ERROR: cannot write {args.out}: {e}", file=sys.stderr)
        return 2

    for f in fails:
        print(f)
    for e in errors:
        print(f"ERROR: {e}")
    print(f"budget: {swept} projects, {with_named} with a page named, not inlined, "
          f"{skipped} skipped")
    if errors:
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
