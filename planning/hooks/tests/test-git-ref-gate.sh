#!/usr/bin/env bash
# Fixture suite for the opt-in commit gate — run directly (repo convention):
#
#     bash planning/hooks/tests/test-git-ref-gate.sh
#
# WHAT THIS SUITE IS REALLY GUARDING. In a project that opted in (the shim that
# proof-hooks-install.py writes), a task commit cannot land without prove-claim.py
# records for the claims the plan requires — the FIRST claim and every claim that
# names its break "(red if …)" (plan-flip-audit's required_claims). The hook is a
# git reference-transaction hook, so these cases make REAL commits by every route:
# the Cursor port's first gate read the index before the command ran (`-a` slipped
# past) and its second parsed commands (a quoted `;` beat it). Two failures matter
# equally: an unproven task commit landing, and legitimate work blocked — and a
# third that is upstream's own: a project that did NOT opt in being gated at all.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
INSTALL="$HERE/../../skills/executing-plans/scripts/proof-hooks-install.py"
PC="$HERE/../../skills/executing-plans/scripts/prove-claim.py"
GIT_HOOK="$HERE/../git-ref-gate.sh"
T="$(mktemp -d)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); echo "  ok    $1"; }
bad() { fail=$((fail+1)); echo "  FAIL  $1"; [ -n "${2:-}" ] && printf '        | %s\n' "${2:0:700}"; }
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

for f in "$INSTALL" "$PC" "$GIT_HOOK"; do
    [ -f "$f" ] || { echo "FAIL: $f does not exist"; exit 1; }
done

PLAN="$T/vault/2026-10-04-gate-plan.md"; STEM=2026-10-04-gate-plan
mkdir -p "$T/vault"
cat > "$PLAN" <<'EOF'
# Plan

### Task 1.1: calc
- **Status:** [ ]
- `add` returns the sum.
- **Test:** `python3 tests/test_calc.py` — add returns the sum (red if add subtracts); add stays a plain function

### Task 1.2: calc again
- **Status:** [ ]
- `add` returns the sum.
- **Test:** `python3 tests/test_calc.py` — add returns the sum (red if add subtracts); add keeps its sign (red if add drops the sign)
EOF

mkrepo() {  # $1 = path; a repo with calc.py, its test, and a plan in flight
    # --template=: this machine's global template installs a pre-commit hook.
    git init -q -b main --template= "$1"
    printf 'def add(a, b):\n    return a + b\n' > "$1/calc.py"
    mkdir -p "$1/tests" "$1/.claude"
    printf "import sys\nsys.path.insert(0, '.')\nfrom calc import add\nassert add(2, 3) == 5\n" > "$1/tests/test_calc.py"
    printf '__pycache__/\n.claude/\n' > "$1/.gitignore"
    git -C "$1" add -A && git -C "$1" commit -q -m base
    printf '{"plan": "%s", "phase": "task", "stage": 1, "task": "1.1", "updated": "2026-10-04T10:00:00Z"}\n' "$PLAN" > "$1/.claude/plan-progress.json"
}
REPO="$T/repo"; mkrepo "$REPO"
python3 "$INSTALL" --install --repo "$REPO" >/dev/null 2>"$T/inst.err" || bad "fixture: installing the git hook failed" "$(cat "$T/inst.err")"

mkbreak() {  # the break (add subtracts), made from calc.py as it stands now
    python3 - "$REPO" "$T/break.patch" <<'PY'
import subprocess, sys
repo, out = sys.argv[1], sys.argv[2]
f = f"{repo}/calc.py"; s = open(f).read()
open(f, "w").write(s.replace("return a + b", "return a - b"))
open(out, "w").write(subprocess.run(["git", "-C", repo, "diff", "--", "calc.py"],
                                    capture_output=True, text=True).stdout)
open(f, "w").write(s)
PY
}
B="python3 -c 'import ast; ast.parse(open(\"calc.py\").read())'"
prove() {  # prove claim 1 of task $1 (default 1.1) on the staged tree
    mkbreak
    python3 "$PC" claim --repo "$REPO" --plan "$PLAN" --task "${1:-1.1}" --claim 1 --break "$T/break.patch" \
        --test "python3 tests/test_calc.py" --build "$B" >/dev/null 2>"$T/pc.err" \
        || { bad "fixture proof failed" "$(cat "$T/pc.err")"; return 1; }
}
head_of() { git -C "$REPO" rev-parse HEAD; }
n=0
change() {  # a new, staged version of calc.py
    n=$((n+1))
    printf 'def add(a, b):\n    return a + b\n\n\ndef v%s():\n    return %s\n' "$n" "$n" > "$REPO/calc.py"
    git -C "$REPO" add calc.py
}
try_commit() {  # run a commit command in the repo; sets rc and err
    ( cd "$REPO" && bash -c "$1" ) >/dev/null 2>"$T/commit.err"; rc=$?; err="$(cat "$T/commit.err")"
}

echo "git-ref-gate — an opted-in project's task commit needs proof for the code it commits"
echo
echo "the claim set (upstream rule: first claim + named breaks)"

# Catches: the hook allowing a task commit with no records.
change; h=$(head_of)
try_commit 'git commit -q -m "Stage 1 Task 1.1: v1"'
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'Task 1.1 claim 1'; then
    ok "an unproven task commit is refused, naming the missing record"
else bad "unproven task commit must be refused (rc=$rc)" "$err"; fi

# Catches: every claim required (the Cursor rule). Claim 2 names no break, and
# requirement 1 has no record: finding 9 is advisory upstream, so neither blocks.
prove && git -C "$REPO" add proof
try_commit 'git commit -q -m "Stage 1 Task 1.1: v1"'
if [ $rc -eq 0 ] && [ "$(head_of)" != "$h" ]; then
    ok "a task commit proving its first claim lands (unnamed claim 2, no req record)"
else bad "a proven task commit must land (rc=$rc)" "$err"; fi
if printf '%s' "$err" | grep -q 'claim 2'; then
    bad "an unnamed later claim must not even be reported" "$err"
else ok "an unnamed later claim needs no record"; fi
if printf '%s' "$err" | grep -q 'requirement 1'; then
    ok "a requirement with no record is named on stderr (advisory)"
else bad "an unaccounted requirement must be named, not silently passed" "$err"; fi

# Catches: named breaks not required. Task 1.2's claim 2 names its break.
change; prove 1.2 && git -C "$REPO" add proof; h=$(head_of)
try_commit 'git commit -q -m "Stage 1 Task 1.2: v2"'
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'Task 1.2 claim 2: no record'; then
    ok "a claim that names its break '(red if …)' needs its own record"
else bad "a named-break claim without a record must be refused (rc=$rc)" "$err"; fi

# A claim no repo patch can break is recorded as a claim deviation: a valid record
# for the hook, named on stderr — the gate report names it, the audit reports it.
python3 "$PC" deviation --repo "$REPO" --plan "$PLAN" --task 1.2 --claim 2 \
    --why "the sign is checked on the device, outside the repo" >/dev/null 2>"$T/pc.err" \
    || bad "fixture claim deviation failed" "$(cat "$T/pc.err")"
git -C "$REPO" add proof
try_commit 'git commit -q -m "Stage 1 Task 1.2: v2"'
if [ $rc -eq 0 ] && [ "$(head_of)" != "$h" ] && printf '%s' "$err" | grep -q 'outside the repo'; then
    ok "a claim deviation lets the commit land and is named on stderr"
else bad "a claim deviation must be allowed and named (rc=$rc)" "$err"; fi

# Catches: a covered-by citation accepting a claim deviation as proof (Stage 1 I1's
# class). The req record is forged to cite claim 2, which is only disclosed.
change; prove 1.2
python3 "$PC" deviation --repo "$REPO" --plan "$PLAN" --task 1.2 --claim 2 \
    --why "the sign is checked on the device, outside the repo" >/dev/null 2>&1
python3 - "$REPO/proof/$STEM/1.2" <<'PY'
import json, sys
d = sys.argv[1]
c = json.load(open(f"{d}/claim-1.json"))
r = {"schema": 2, "kind": "req", "plan": c["plan"], "task": "1.2", "index": 1,
     "text": "`add` returns the sum.", "fingerprint": c["fingerprint"],
     "created": c["created"], "covered_by_claim": 2}
open(f"{d}/req-1.json", "w").write(json.dumps(r))
PY
git -C "$REPO" add proof; h=$(head_of)
try_commit 'git commit -q -m "Stage 1 Task 1.2: covered by a deviation"'
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'requirement 1: cites claim 2'; then
    ok "a req covered by a claim deviation is refused — a deviation proves nothing"
else bad "covered-by must accept only kind claim (rc=$rc)" "$err"; fi
git -C "$REPO" rm -q --cached "proof/$STEM/1.2/req-1.json"; rm "$REPO/proof/$STEM/1.2/req-1.json"

echo
echo "records are bound to the commit's own tree"

# Catches: the hook fingerprinting any index but the one git commits.
change; prove && git -C "$REPO" add proof
printf '\n# swept in by -a, never proven\n' >> "$REPO/calc.py"
h=$(head_of)
try_commit 'git commit -q -a -m "Stage 1 Task 1.1: v3"'
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'claim 1: proven on a different tree'; then
    ok "git commit -a that sweeps in an unproven edit is refused as stale"
else bad "-a must be checked against the tree git commits (rc=$rc)" "$err"; fi
git -C "$REPO" checkout -q -- calc.py
try_commit 'git commit -q -m "Stage 1 Task 1.1: v3"'
if [ $rc -eq 0 ]; then ok "the same proof, committed without the unproven edit, lands"
else bad "proven commit must land (rc=$rc)" "$err"; fi

# Catches: records not validated. A hand-forged record: red exit 0.
change; prove
python3 - "$REPO/proof/$STEM/1.1/claim-1.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1])); r["red"]["exit"] = 0
open(sys.argv[1], "w").write(json.dumps(r))
PY
git -C "$REPO" add proof; h=$(head_of)
try_commit 'git commit -q -m "Stage 1 Task 1.1: forged"'
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'did not fail'; then
    ok "a forged record (red exit 0) is refused"
else bad "forged record must be refused (rc=$rc)" "$err"; fi

# Catches: records not bound to the plan's wording.
prove && git -C "$REPO" add proof
cp "$PLAN" "$T/plan.bak"
sed -i '0,/add returns the sum (red/s//add returns the total (red/' "$PLAN"
try_commit 'git commit -q -m "Stage 1 Task 1.1: reworded"'
cp "$T/plan.bak" "$PLAN"
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'different wording'; then
    ok "records proving wording the plan has since changed are refused"
else bad "reworded claim must be refused (rc=$rc)" "$err"; fi

# Catches: proof/ as a hiding place.
printf 'x = 1\n' > "$REPO/proof/helper.py"; git -C "$REPO" add proof/helper.py
try_commit 'git commit -q -m "Stage 1 Task 1.1: with a stray file"'
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'proof/helper.py: not a proof record'; then
    ok "a staged file under proof/ that is not a record is refused"
else bad "stray proof/ files must be refused (rc=$rc)" "$err"; fi
git -C "$REPO" rm -q --cached proof/helper.py; rm "$REPO/proof/helper.py"

# Catches: a present-but-stale record waved through because it is not required.
python3 - "$REPO/proof/$STEM/1.1" <<'PY'
import json, sys
d = sys.argv[1]
r = json.load(open(f"{d}/claim-1.json")); r["index"] = 2; r["fingerprint"] = "0" * 64
open(f"{d}/claim-2.json", "w").write(json.dumps(r))
PY
git -C "$REPO" add proof
try_commit 'git commit -q -m "Stage 1 Task 1.1: a stale optional record"'
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'Task 1.1 claim 2'; then
    ok "a record that is present is validated, required or not"
else bad "a present invalid record must be refused (rc=$rc)" "$err"; fi
git -C "$REPO" rm -q --cached "proof/$STEM/1.1/claim-2.json"; rm "$REPO/proof/$STEM/1.1/claim-2.json"
git -C "$REPO" reset -q; git -C "$REPO" checkout -q -- .; git -C "$REPO" clean -qfd proof

echo
echo "every route a commit lands by"
change; h=$(head_of)
for c in 'git commit -q --no-verify -m "Stage 1 Task 1.1: no-verify"' \
         'git commit -q -m "Stage 1 Task 1.1: a; b" --no-verify' \
         'git commit -q -m "task 1.1: lowercase"' \
         'git commit -q -m "Tasks 1.1 and 9.9: a list"' \
         'git commit -q --amend -m "Stage 1 Task 1.1: amended"' \
         'git commit -q -n --amend --no-edit' \
         'c=$(git commit-tree "$(git write-tree)" -p HEAD -m "Stage 1 Task 1.1: plumbing") && git update-ref refs/heads/main "$c"'; do
    try_commit "$c"
    if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'Task 1.1 claim 1'; then
        ok "refused, HEAD unmoved: ${c:0:70}"
    else bad "an unproven task commit must not land by: $c (rc=$rc)" "$err"; fi
done
obj=$(git -C "$REPO" commit-tree "$(git -C "$REPO" write-tree)" -p HEAD -m "Stage 1 Task 1.1: picked")
git -C "$REPO" reset -q --hard
try_commit "git cherry-pick $obj"
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ]; then ok "an unproven task commit cannot land by cherry-pick"
else bad "cherry-pick must be checked (rc=$rc)" "$err"; fi
git -C "$REPO" cherry-pick --abort >/dev/null 2>&1; git -C "$REPO" reset -q --hard

# Catches: records read from the index rather than the commit.
change; prove; t=$(git -C "$REPO" write-tree); git -C "$REPO" add proof; h=$(head_of)
try_commit "c=\$(git commit-tree $t -p HEAD -m 'Stage 1 Task 1.1: records only in the index') && git update-ref refs/heads/main \$c"
if [ $rc -ne 0 ] && [ "$(head_of)" = "$h" ] && printf '%s' "$err" | grep -q 'Task 1.1 claim 1:'; then
    ok "a commit whose own tree lacks the records is refused, whatever the index holds"
else bad "records must be read from the commit (rc=$rc)" "$err"; fi

# Catches: only branch refs checked. On a detached HEAD a commit moves HEAD alone.
git -C "$REPO" reset -q; change; h=$(head_of)
try_commit 'git checkout -q --detach && git commit -q -m "Stage 1 Task 1.1: detached"'
if [ $rc -ne 0 ] && [ "$(git -C "$REPO" rev-parse HEAD)" = "$h" ]; then
    ok "an unproven task commit on a detached HEAD is refused"
else bad "HEAD updates must be checked (rc=$rc)" "$err"; fi
git -C "$REPO" checkout -q main 2>/dev/null

# A proven commit lands by any route: the hook reads only the commit's own tree.
change; prove && git -C "$REPO" add proof; h=$(head_of)
try_commit 'git commit -q --no-verify -m "Stage 1 Task 1.1: proven, no-verify"'
if [ $rc -eq 0 ] && [ "$(head_of)" != "$h" ]; then ok "a proven task commit lands even with --no-verify"
else bad "proven work must land (rc=$rc)" "$err"; fi
change; prove && git -C "$REPO" add proof; h=$(head_of)
try_commit 'c=$(git commit-tree "$(git write-tree)" -p HEAD -m "Stage 1 Task 1.1: proven plumbing") && git update-ref refs/heads/main "$c"'
if [ $rc -eq 0 ] && [ "$(head_of)" != "$h" ]; then ok "a proven task commit lands by commit-tree + update-ref"
else bad "proven plumbing commit must land (rc=$rc)" "$err"; fi
git -C "$REPO" reset -q

echo
echo "it must not block other work"
try_commit 'git commit -q --allow-empty -m "chore: tidy"'
if [ $rc -eq 0 ]; then ok "a commit not naming a task lands"
else bad "non-task commit must land (rc=$rc)" "$err"; fi
change
try_commit 'git commit -q -m "chore: tidy" -m "unrelated to Task 1.1, which stays unproven here"'
if [ $rc -eq 0 ]; then ok "a task named only in the body does not gate the commit"
else bad "the body must not be gated (rc=$rc)" "$err"; fi
change
try_commit 'git commit -q -m "Task 9.9: another plan"'
if [ $rc -eq 0 ]; then ok "a commit naming a task this plan does not have lands"
else bad "other-plan task commit must land (rc=$rc)" "$err"; fi
change
try_commit 'PLANNING_COMMIT_GATE=0 COMMIT_GATE=0 git commit -q -m "Stage 1 Task 1.1: escape"'
if [ $rc -ne 0 ]; then ok "the hook has no environment escape"
else bad "an environment variable must not disable the git hook (rc=$rc)" "$err"; fi
mv "$REPO/.claude/plan-progress.json" "$T/pp.json"
change
try_commit 'git commit -q -m "Stage 1 Task 1.1: no plan in flight"'
if [ $rc -eq 0 ]; then ok "with no plan in flight, a task commit is not this gate's to judge"
else bad "no plan in flight must allow (rc=$rc)" "$err"; fi
ln -s "$T/pp.json" "$REPO/.claude/plan-progress.json"
change
try_commit 'git commit -q -m "Stage 1 Task 1.1: symlinked state"'
if [ $rc -eq 0 ]; then ok "a symlinked plan-progress.json is not trusted as a plan in flight"
else bad "symlinked state must not gate (rc=$rc)" "$err"; fi
rm "$REPO/.claude/plan-progress.json"; mv "$T/pp.json" "$REPO/.claude/plan-progress.json"
# Catches: commits already on a branch re-checked. Two unproven task commits landed
# above while no plan was in flight; a proven one now must not answer for them.
change; prove && git -C "$REPO" add proof; h=$(head_of)
try_commit 'git commit -q -m "Stage 1 Task 1.1: proven, after unproven history"'
if [ $rc -eq 0 ] && [ "$(head_of)" != "$h" ]; then
    ok "only the commits being added are checked, not the branch's history"
else bad "history already on a branch must not block a proven commit (rc=$rc)" "$err"; fi


echo
echo "it must not block reading someone else's history (Stage 3 review I3)"
# Catches: every commit not on a LOCAL branch treated as one being added. A
# teammate's task commit, fetched, must be checkable-out and fast-forwardable.
TEAM="$T/team"; git clone -q --template= "$REPO" "$TEAM"
printf '# teammate\n' >> "$TEAM/calc.py"; git -C "$TEAM" commit -q -am "Stage 1 Task 1.1: teammate"
git -C "$REPO" fetch -q "$TEAM" main:refs/remotes/team/main 2>"$T/f.err" || bad "fixture: fetch failed" "$(cat "$T/f.err")"
h=$(head_of)
try_commit 'git checkout -q --detach team/main'
if [ $rc -eq 0 ]; then ok "checking out a fetched task commit is not refused"
else bad "a fetched commit must be checkable-out (rc=$rc)" "$err"; fi
try_commit 'git checkout -q main && git merge -q --ff-only team/main'
if [ $rc -eq 0 ] && [ "$(head_of)" != "$h" ]; then ok "fast-forwarding to fetched task commits is not refused"
else bad "a fast-forward to fetched commits must land (rc=$rc)" "$err"; fi

echo
echo "it fails open on its own errors (Stage 3 review I4)"
# Catches: a missing python3 aborting every ref update in an opted-in repo.
NOPY="$T/nopy"; mkdir -p "$NOPY"
for b in git bash sh cat readlink dirname env; do ln -s "$(command -v $b)" "$NOPY/$b"; done
change
( cd "$REPO" && PATH="$NOPY" git commit -q -m "Stage 1 Task 1.1: no python" ) >/dev/null 2>"$T/np.err"; rc=$?
if [ $rc -eq 0 ] && grep -q 'python3' "$T/np.err"; then ok "no python3: the update goes through, saying why"
else bad "a missing python3 must fail open with a note (rc=$rc)" "$(cat "$T/np.err")"; fi
# Catches: an uncaught exception in the hook's own code refusing the update. The
# git on PATH vanishes after its first use and PATH holds no other, so the next
# call raises.
FAKE="$T/fakegit"; mkdir -p "$FAKE"
for b in python3 bash cat readlink dirname; do ln -s "$(command -v $b)" "$FAKE/$b"; done
printf '#!/bin/sh\n%s -f "%s/git"\nexec %s "$@"\n' "$(command -v rm)" "$FAKE" "$(command -v git)" > "$FAKE/git"; chmod +x "$FAKE/git"
change
c=$(git -C "$REPO" commit-tree "$(git -C "$REPO" write-tree)" -p HEAD -m "Stage 1 Task 1.1: crash")
( cd "$REPO" && printf '%s %s refs/heads/main\n' "$(git rev-parse HEAD)" "$c" \
    | PATH="$FAKE" bash "$GIT_HOOK" prepared ) >/dev/null 2>"$T/x.err"; rc=$?
if [ $rc -eq 0 ] && grep -q 'commit gate:.*allowing' "$T/x.err"; then ok "an internal error fails open, saying why"
else bad "an uncaught error must fail open (rc=$rc)" "$(cat "$T/x.err")"; fi
git -C "$REPO" reset -q

echo
echo "opt-in: a project without the shim is not gated"
# Catches: the gate reaching a project that never opted in. The plugin's hook file
# exists on disk for every user; only the per-project shim makes git run it.
PLAIN="$T/plain"; mkrepo "$PLAIN"
printf 'def add(a, b):\n    return a + b\n# x\n' > "$PLAIN/calc.py"; git -C "$PLAIN" add calc.py
if git -C "$PLAIN" commit -q -m "Stage 1 Task 1.1: not opted in" 2>"$T/p.err"; then
    ok "a repo without the shim commits an unproven task freely"
else bad "a repo that did not opt in must not be gated" "$(cat "$T/p.err")"; fi
if [ ! -e "$PLAIN/.git/hooks/reference-transaction" ]; then ok "nothing installs the shim by default"
else bad "a fresh repo must carry no shim"; fi

echo
echo "proof-hooks-install.py"
SHIM="$REPO/.git/hooks/reference-transaction"
if [ -x "$SHIM" ] && grep -q "git-ref-gate.sh" "$SHIM"; then
    ok "--install writes an executable shim that execs the plugin's git hook"
else bad "--install must write an executable shim" "$(cat "$SHIM" 2>&1)"; fi
python3 "$INSTALL" --status --repo "$REPO" >"$T/s.out" 2>&1; rc=$?
if [ $rc -eq 0 ] && grep -q '^installed' "$T/s.out"; then ok "--status reports an installed shim (exit 0)"
else bad "--status must report installed (rc=$rc)" "$(cat "$T/s.out")"; fi
before="$(cat "$SHIM")"
python3 "$INSTALL" --install --repo "$REPO" >"$T/s.out" 2>&1
if grep -q 'already installed' "$T/s.out" && [ "$(cat "$SHIM")" = "$before" ]; then
    ok "re-install is a no-op"
else bad "re-install must leave the shim unchanged" "$(cat "$T/s.out")"; fi

# Catches: the marker alone counting as installed. git ignores a hook without its
# exec bit, and an edited shim proves nothing.
chmod a-x "$SHIM"
python3 "$INSTALL" --status --repo "$REPO" >"$T/s.out" 2>&1; rc=$?
if [ $rc -eq 1 ]; then ok "a shim without its exec bit is not installed (exit 1)"
else bad "a non-executable shim must not count as installed" "$(cat "$T/s.out")"; fi
python3 "$INSTALL" --install --repo "$REPO" >/dev/null 2>&1
printf 'exit 0\n' >> "$SHIM"
python3 "$INSTALL" --status --repo "$REPO" >"$T/s.out" 2>&1; rc=$?
if [ $rc -eq 1 ]; then ok "an edited shim is not installed (exit 1)"
else bad "an edited shim must not count as installed" "$(cat "$T/s.out")"; fi
python3 "$INSTALL" --install --repo "$REPO" >/dev/null 2>&1
if [ -x "$SHIM" ] && python3 "$INSTALL" --status --repo "$REPO" >/dev/null 2>&1; then
    ok "--install restores an altered shim"
else bad "re-install must restore the shim"; fi

# Catches: a foreign hook overwritten — the one outcome worse than doing nothing.
F="$T/foreign"; mkrepo "$F"; mkdir -p "$F/.git/hooks"
printf '#!/bin/sh\n# somebody else\nexit 0\n' > "$F/.git/hooks/reference-transaction"
chmod +x "$F/.git/hooks/reference-transaction"
cp "$F/.git/hooks/reference-transaction" "$T/foreign.orig"
python3 "$INSTALL" --install --repo "$F" >"$T/s.out" 2>&1; rc=$?
if [ $rc -ne 0 ] && cmp -s "$F/.git/hooks/reference-transaction" "$T/foreign.orig"; then
    ok "--install refuses a foreign reference-transaction hook and leaves it intact"
else bad "a foreign hook must not be overwritten (rc=$rc)" "$(cat "$T/s.out")"; fi
python3 "$INSTALL" --remove --repo "$F" >/dev/null 2>&1
if cmp -s "$F/.git/hooks/reference-transaction" "$T/foreign.orig"; then
    ok "--remove leaves a foreign hook alone"
else bad "--remove must remove only its own shim"; fi

# Catches: argparse prefix abbreviation — `--rem` ran --remove past the guard's
# text rule (Stage 3 review I1). Only the full flags are accepted.
python3 "$INSTALL" --rem --repo "$REPO" >"$T/s.out" 2>&1; rc=$?
if [ $rc -ne 0 ] && [ -x "$SHIM" ]; then ok "an abbreviated flag (--rem) is refused; the shim stays"
else bad "--rem must not act as --remove (rc=$rc)" "$(cat "$T/s.out")"; fi

# Catches: a foreign hook taken for ours because it mentions the marker (review S3).
F2="$T/foreign2"; mkrepo "$F2"; mkdir -p "$F2/.git/hooks"
printf '#!/bin/sh\n# chains the planning commit gate after its own checks\nexit 0\n' > "$F2/.git/hooks/reference-transaction"
cp "$F2/.git/hooks/reference-transaction" "$T/foreign2.orig"
python3 "$INSTALL" --install --repo "$F2" >"$T/s.out" 2>&1; rc=$?
python3 "$INSTALL" --remove --repo "$F2" >>"$T/s.out" 2>&1
if [ $rc -ne 0 ] && cmp -s "$F2/.git/hooks/reference-transaction" "$T/foreign2.orig"; then
    ok "a foreign hook that merely mentions the marker is not ours"
else bad "the marker must identify only our shim (rc=$rc)" "$(cat "$T/s.out")"; fi

# Catches: a hooks directory shared by other repos (a global core.hooksPath) —
# installing there opts in every repo that uses it (Stage 3 review I2).
SH="$T/shared-hooks"; mkdir -p "$SH"
SA="$T/sa"; mkrepo "$SA"; git -C "$SA" config core.hooksPath "$SH"
python3 "$INSTALL" --install --repo "$SA" >"$T/s.out" 2>&1; rc=$?
if [ $rc -ne 0 ] && [ ! -e "$SH/reference-transaction" ] && grep -q 'outside' "$T/s.out"; then
    ok "a hooks directory outside the repo is refused, nothing written"
else bad "a shared hooks directory must be refused (rc=$rc)" "$(cat "$T/s.out")"; fi

# core.hooksPath and linked worktrees: the shim goes where git will look.
HP="$T/hookspath"; mkrepo "$HP"; git -C "$HP" config core.hooksPath .githooks
python3 "$INSTALL" --install --repo "$HP" >/dev/null 2>&1
if [ -x "$HP/.githooks/reference-transaction" ]; then ok "the shim honours core.hooksPath"
else bad "the shim must go where git runs hooks" "$(find "$HP" -name reference-transaction)"; fi

# A shim whose plugin is gone fails open — and says so, so the gate is never off
# in silence (a plugin update can move the hook's path).
D="$T/dangling"; mkrepo "$D"
python3 "$INSTALL" --install --repo "$D" >/dev/null 2>&1
sed -i "s#$(cd "$HERE/.." && pwd)/git-ref-gate.sh#$T/gone/git-ref-gate.sh#g" "$D/.git/hooks/reference-transaction"
printf '# y\n' >> "$D/calc.py"; git -C "$D" add calc.py
if git -C "$D" commit -q -m "Stage 1 Task 1.1: plugin gone" 2>"$T/d.err" && grep -q 'commit gate is OFF' "$T/d.err"; then
    ok "a shim whose plugin is gone lets commits through, saying the gate is off"
else bad "a dangling shim must fail open loudly" "$(cat "$T/d.err")"; fi

python3 "$INSTALL" --remove --repo "$REPO" >/dev/null 2>&1
if [ ! -e "$SHIM" ]; then ok "--remove deletes our shim"
else bad "--remove must delete the shim"; fi
python3 "$INSTALL" --status --repo "$REPO" >/dev/null 2>&1; rc=$?
if [ $rc -eq 1 ]; then ok "--status after --remove: not installed (exit 1)"
else bad "--status must report not installed after --remove"; fi
python3 "$INSTALL" --install --repo "$T/vault" >"$T/s.out" 2>&1; rc=$?
if [ $rc -ne 0 ] && grep -q 'not a git work tree' "$T/s.out"; then ok "--install outside a work tree is refused"
else bad "a non-repo must be refused (rc=$rc)" "$(cat "$T/s.out")"; fi

echo
echo "passed: $pass   failed: $fail"
[ "$fail" -eq 0 ]
