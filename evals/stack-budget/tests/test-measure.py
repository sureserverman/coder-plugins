#!/usr/bin/env python3
"""Hermetic tests for the stack-budget sweep (evals/stack-budget/measure.py).

The sweep exists so that a stack page that applies to a project can never be
dropped from the session-start context without anyone seeing it. So these
cases pin the ways it could pass while measuring nothing:

  - a page the sidecar lists that is neither inlined nor named FAILS (exit 1)
    and names the project;
  - a page both inlined and named, or output over 9,500 characters, FAILS;
  - a page only named passes, and the TSV row lists it under `named`;
  - a project with no sidecar, a hook printing non-JSON, or a hook exiting
    non-zero is a usage-level error (exit 2), never a pass;
  - a registry folder that does not exist is skipped and counted;
  - the last line's counts match the projects swept.

No real hook, no dependence on ~/.claude, W or the vault: every project,
sidecar, registry and a stand-in hook live in a temp dir. The stand-in hook
prints the file `<cwd>/hook-out.txt` verbatim (nothing when it is absent) and
exits with the number in `<cwd>/hook-exit` (0 when it is absent).
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MEASURE = os.path.join(os.path.dirname(HERE), "measure.py")

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


FAKE_HOOK = r'''#!/usr/bin/env python3
import json, os, sys
data = json.loads(sys.stdin.read())
assert data["hook_event_name"] == "SessionStart", data
cwd = data["cwd"]
out = os.path.join(cwd, "hook-out.txt")
if os.path.exists(out):
    with open(out, encoding="utf-8") as fh:
        sys.stdout.write(fh.read())
code = os.path.join(cwd, "hook-exit")
sys.exit(int(open(code).read()) if os.path.exists(code) else 0)
'''


def copy_text(slug, size=200):
    """A synced copy as the real hook inlines it: frontmatter, marker, body."""
    head = (f'---\npaths: ["**/*.x"]\n---\n'
            f'<!-- vault-context:stack-rule source={slug} sha256={"0" * 64} -->\n')
    return head + "b" * max(0, size - len(head))


def named_line(slug):
    return (f"[vault-context] The {slug} stack page applies to this project but did not "
            f"fit in the session-start context; read /stacks/vault-stack-{slug}.md")


def sidecar(slugs):
    lines = ["# Vault context", "", "## Decisions/", "", "- something", ""]
    if slugs is not None:
        lines += ["<!-- vault-context:stacks:start -->", "## Stack rules", "",
                  "Each one is added to a session at its start when the project holds "
                  "a matching file. Open a page to read it.", ""]
        for s in slugs:
            lines.append(f"- **{s}** — `**/*.x` — `/mnt/v/stacks/{s}.md` — related: [[{s}]]")
        lines.append("<!-- vault-context:stacks:end -->")
    lines += ["", "- **notastack** — outside the block, must be ignored", ""]
    return "\n".join(lines) + "\n"


def hook_json(parts):
    ctx = "\n".join(parts)
    return json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                              "additionalContext": ctx}}) + "\n"


class Sweep:
    """A temp world: projects, a registry and the stand-in hook."""

    def __init__(self, root):
        self.root = root
        self.hook = os.path.join(root, "hook.py")
        write(self.hook, FAKE_HOOK)
        self.entries = []

    def project(self, name, slugs=(), out=None, exit_code=None, no_sidecar=False,
                enabled=True):
        p = os.path.join(self.root, "projects", name)
        os.makedirs(p, exist_ok=True)
        if not no_sidecar:
            write(os.path.join(p, ".claude", "vault-context.md"),
                  sidecar(list(slugs) if slugs is not None else None))
        if out is not None:
            write(os.path.join(p, "hook-out.txt"), out)
        if exit_code is not None:
            write(os.path.join(p, "hook-exit"), str(exit_code))
        self.entries.append((p, enabled))
        return p

    def missing(self, name):
        self.entries.append((os.path.join(self.root, "projects", name), True))

    def run(self):
        reg = ["# registry", "", "version: 1", "projects:"]
        for p, en in self.entries:
            reg += [f"  - path: {p}", f"    name: {os.path.basename(p)}",
                    "    area: test", f"    enabled: {'true' if en else 'false'}",
                    "    added: 2026-11-19"]
        regf = os.path.join(self.root, "registry.yaml")
        write(regf, "\n".join(reg) + "\n")
        tsv = os.path.join(self.root, "out", "budget.tsv")
        r = subprocess.run([sys.executable, MEASURE, "--registry", regf, "--hook", self.hook,
                            "--out", tsv], capture_output=True, text=True)
        rows = []
        if os.path.exists(tsv):
            with open(tsv, encoding="utf-8") as fh:
                rows = [ln.rstrip("\n").split("\t") for ln in fh if ln.strip()]
        lines = r.stdout.strip().splitlines()
        return r, rows, (lines[-1] if lines else "")


def row_for(rows, project):
    for row in rows[1:]:
        if row and row[0] == project:
            return dict(zip(rows[0], row))
    return None


def world(fn):
    with tempfile.TemporaryDirectory() as d:
        return fn(Sweep(d))


def no_traceback(r, label):
    check("Traceback" not in r.stderr and "Traceback" not in r.stdout,
          f"{label}: no traceback")


def case_all_inlined():
    print("all applying pages inlined -> 0")

    def go(s):
        p = s.project("a", ["readme", "rust"],
                      out=hook_json([copy_text("readme"), copy_text("rust")]))
        r, rows, last = s.run()
        check(r.returncode == 0, f"exit 0 (got {r.returncode}; {r.stdout} {r.stderr})")
        check(rows and rows[0] == ["project", "applies", "inlined", "named", "chars"],
              f"TSV header (got {rows[:1]})")
        row = row_for(rows, p)
        check(row is not None and row["applies"] == "readme,rust"
              and row["inlined"] == "readme,rust" and row["named"] == "",
              f"row lists both inlined (got {row})")
        want = len(copy_text("readme")) + 1 + len(copy_text("rust"))
        check(row is not None and row["chars"] == str(want), f"chars = {want} (got {row})")
    world(go)


def case_one_named():
    print("one page named -> 0, row lists it under named")

    def go(s):
        p = s.project("a", ["readme", "rust"],
                      out=hook_json([copy_text("readme"), named_line("rust")]))
        r, rows, last = s.run()
        check(r.returncode == 0, f"exit 0 (got {r.returncode}; {r.stdout} {r.stderr})")
        row = row_for(rows, p)
        check(row is not None and row["inlined"] == "readme" and row["named"] == "rust",
              f"rust under named (got {row})")
        check(last == "budget: 1 projects, 1 with a page named, not inlined, 0 skipped",
              f"budget line counts the named project (got {last!r})")
    world(go)


def case_dropped():
    print("a listed page neither inlined nor named -> 1 naming the project")

    def go(s):
        p = s.project("dropper", ["readme", "rust"], out=hook_json([copy_text("readme")]))
        r, rows, last = s.run()
        check(r.returncode == 1, f"exit 1 (got {r.returncode})")
        check(f"FAIL: {p}:" in r.stdout and "rust" in r.stdout,
              f"FAIL line names project and slug (got {r.stdout!r})")
        no_traceback(r, "dropped")
    world(go)


def case_both():
    print("a page both inlined and named -> 1")

    def go(s):
        p = s.project("both", ["rust"],
                      out=hook_json([copy_text("rust"), named_line("rust")]))
        r, rows, last = s.run()
        check(r.returncode == 1, f"exit 1 (got {r.returncode})")
        check(f"FAIL: {p}:" in r.stdout, f"FAIL line names the project (got {r.stdout!r})")
    world(go)


def case_duplicate():
    print("a page emitted twice -> 1")

    def go(s):
        p = s.project("dup", ["rust"],
                      out=hook_json([copy_text("rust"), copy_text("rust")]))
        r, rows, last = s.run()
        check(r.returncode == 1, f"exit 1 (got {r.returncode})")
        check(f"FAIL: {p}:" in r.stdout and "more than once" in r.stdout,
              f"FAIL line names the project and the duplicate (got {r.stdout!r})")
    world(go)


def case_wrong_shape_json():
    print("hook JSON without hookSpecificOutput.additionalContext -> 1")

    def go(s):
        p = s.project("shape", ["rust"], out=json.dumps({"continue": True}) + "\n")
        r, rows, last = s.run()
        check(r.returncode == 1, f"exit 1 (got {r.returncode})")
        check(f"FAIL: {p}:" in r.stdout and "hookSpecificOutput" in r.stdout,
              f"FAIL line names the project and the missing field (got {r.stdout!r})")
        no_traceback(r, "wrong-shape JSON")
    world(go)


def case_extra():
    print("a page inlined that the sidecar does not list -> 1")

    def go(s):
        p = s.project("extra", ["readme"],
                      out=hook_json([copy_text("readme"), copy_text("rust")]))
        r, rows, last = s.run()
        check(r.returncode == 1, f"exit 1 (got {r.returncode})")
        check(f"FAIL: {p}:" in r.stdout, f"FAIL line names the project (got {r.stdout!r})")
    world(go)


def case_over_budget():
    print("output over 9,500 chars -> 1")

    def go(s):
        p = s.project("big", ["readme"], out=hook_json([copy_text("readme", 9501)]))
        r, rows, last = s.run()
        check(r.returncode == 1, f"exit 1 (got {r.returncode})")
        check(f"FAIL: {p}:" in r.stdout, f"FAIL line names the project (got {r.stdout!r})")
        row = row_for(rows, p)
        check(row is not None and row["chars"] == "9501", f"chars 9501 recorded (got {row})")

    def edge(s):
        s.project("edge", ["readme"], out=hook_json([copy_text("readme", 9500)]))
        r, rows, last = s.run()
        check(r.returncode == 0, f"exactly 9,500 chars -> 0 (got {r.returncode}; {r.stdout})")
    world(go)
    world(edge)


def case_no_sidecar():
    print("a project with no sidecar -> 2")

    def go(s):
        p = s.project("bare", no_sidecar=True)
        r, rows, last = s.run()
        check(r.returncode == 2, f"exit 2 (got {r.returncode})")
        check(p in (r.stdout + r.stderr), "error names the project")
        no_traceback(r, "no sidecar")
    world(go)


def case_empty_none():
    print("hook prints nothing, sidecar lists none -> 0")

    def go(s):
        p = s.project("quiet", None)
        p2 = s.project("quiet2", [])
        r, rows, last = s.run()
        check(r.returncode == 0, f"exit 0 (got {r.returncode}; {r.stdout} {r.stderr})")
        row = row_for(rows, p)
        check(row is not None and row["applies"] == "" and row["chars"] == "0",
              f"empty row, chars 0 (got {row})")
        check(row_for(rows, p2) is not None, "empty block also gives a row")
    world(go)


def case_empty_but_listed():
    print("hook prints nothing but sidecar lists one -> 1")

    def go(s):
        p = s.project("silent", ["rust"])
        r, rows, last = s.run()
        check(r.returncode == 1, f"exit 1 (got {r.returncode})")
        check(f"FAIL: {p}:" in r.stdout and "rust" in r.stdout,
              f"FAIL line names project and slug (got {r.stdout!r})")
    world(go)


def case_missing_and_counts():
    print("missing folder skipped and counted; disabled ignored; budget line counts")

    def go(s):
        s.project("a", ["rust"], out=hook_json([copy_text("rust")]))
        s.project("b", ["readme", "rust"],
                  out=hook_json([copy_text("readme"), named_line("rust")]))
        s.project("c", None)
        s.project("off", no_sidecar=True, enabled=False)
        s.missing("gone1")
        s.missing("gone2")
        r, rows, last = s.run()
        check(r.returncode == 0, f"exit 0 (got {r.returncode}; {r.stdout} {r.stderr})")
        check(len(rows) == 4, f"header + 3 rows (got {len(rows)})")
        check(last == "budget: 3 projects, 1 with a page named, not inlined, 2 skipped",
              f"budget line (got {last!r})")
    world(go)


def case_non_json():
    print("hook prints non-JSON -> 2; hook exits non-zero -> 2")

    def go(s):
        s.project("noisy", ["rust"], out="hello, not json\n")
        r, rows, last = s.run()
        check(r.returncode == 2, f"non-JSON exit 2 (got {r.returncode})")
        no_traceback(r, "non-JSON")

    def go2(s):
        s.project("crash", ["rust"], out=hook_json([copy_text("rust")]), exit_code=3)
        r, rows, last = s.run()
        check(r.returncode == 2, f"non-zero hook exit 2 (got {r.returncode})")
        no_traceback(r, "hook exit")
    world(go)
    world(go2)


def case_usage():
    print("usage errors -> 2")
    r = subprocess.run([sys.executable, MEASURE], capture_output=True, text=True)
    check(r.returncode == 2, f"no args exit 2 (got {r.returncode})")
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, MEASURE, "--registry", os.path.join(d, "nope"),
                            "--hook", os.path.join(d, "h"), "--out", os.path.join(d, "o")],
                           capture_output=True, text=True)
        check(r.returncode == 2, f"unreadable registry exit 2 (got {r.returncode})")
        no_traceback(r, "unreadable registry")


def main():
    if not os.path.exists(MEASURE):
        print(f"FAIL: {MEASURE} does not exist")
        sys.exit(1)
    for case in (case_all_inlined, case_one_named, case_dropped, case_both, case_duplicate, case_wrong_shape_json, case_extra,
                 case_over_budget, case_no_sidecar, case_empty_none, case_empty_but_listed,
                 case_missing_and_counts, case_non_json, case_usage):
        case()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
