#!/usr/bin/env python3
"""Fixture suite for collect-github.py — run directly (CI convention):
    python3 business/scripts/tests/test-collect-github.py

Mocks the `gh` CLI with a fake executable on PATH and drives collect-github.py
against a throwaway git repo, asserting the best-effort contract: happy path,
no remote, unauthenticated gh, clones-need-push-access (per-metric sentinel),
and a non-GitHub remote. Ends with a lenient live smoke test, skipped when a
real authenticated `gh` isn't present.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "collect-github.py"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


FAKE_GH = r"""#!/usr/bin/env bash
args="$*"
if [[ "$GH_FAKE_MODE" == "unauth" && "$1" == "auth" ]]; then
  echo "You are not logged into any GitHub hosts." >&2; exit 1
fi
if [[ "$GH_FAKE_MODE" == "malformed" ]]; then
  # valid JSON, wrong SHAPE for each endpoint — must degrade, never crash
  case "$args" in
    "auth status") echo "Logged in to github.com"; exit 0;;
    *"repo view"*) echo '[]'; exit 0;;
    *releases*) echo '{"message":"Not Found"}'; exit 0;;
    *traffic/clones*) echo 'null'; exit 0;;
  esac
fi
case "$args" in
  "auth status") echo "Logged in to github.com"; exit 0;;
  *"repo view"*stargazerCount*) echo '{"stargazerCount": 42}'; exit 0;;
  *releases*) echo '[{"assets":[{"download_count":100},{"download_count":30}]}]'; exit 0;;
  *traffic/clones*)
    if [[ "$GH_FAKE_MODE" == "noclones" ]]; then
      echo "gh: HTTP 403: Must have push access to repository (traffic)" >&2; exit 1
    fi
    echo '{"count": 8, "uniques": 5}'; exit 0;;
esac
echo "fake-gh: unhandled: $args" >&2; exit 1
"""

GIT = ["git", "-c", "user.email=t@t", "-c", "user.name=t",
       "-c", "core.hooksPath=/dev/null"]


def make_repo(tmp, remote):
    repo = tmp / "repo"
    repo.mkdir()
    subprocess.run(GIT + ["init", "-q"], cwd=repo, check=True, capture_output=True)
    if remote:
        subprocess.run(GIT + ["remote", "add", "origin", remote],
                       cwd=repo, check=True, capture_output=True)
    return repo


def make_fake_gh(tmp):
    bindir = tmp / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    return bindir


def run_collect(repo, bindir, mode=None):
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
    if mode:
        env["GH_FAKE_MODE"] = mode
    r = subprocess.run([sys.executable, str(SCRIPT), str(repo)],
                       capture_output=True, text=True, env=env)
    return r


def test_happy(tmp):
    repo = make_repo(tmp, "https://github.com/acme/widget.git")
    bindir = make_fake_gh(tmp)
    r = run_collect(repo, bindir)
    check(r.returncode == 0, "happy: exit 0")
    d = json.loads(r.stdout)
    check(d["repo"] == "acme/widget", f"happy: slug acme/widget (got {d['repo']})")
    check(d["values"]["github.stars"] == 42, "happy: stars 42")
    check(d["values"]["github.release_downloads"] == 130,
          f"happy: release_downloads 130 (got {d['values']['github.release_downloads']})")
    check(d["values"]["github.clones_14d"] == 8, "happy: clones_14d 8")
    check(d["reasons"] == {}, f"happy: no sentinels (got {d['reasons']})")


def test_noclones(tmp):
    repo = make_repo(tmp, "git@github.com:acme/widget.git")   # scp-style remote too
    bindir = make_fake_gh(tmp)
    r = run_collect(repo, bindir, mode="noclones")
    d = json.loads(r.stdout)
    check(r.returncode == 0, "noclones: exit 0 (best-effort)")
    check(d["repo"] == "acme/widget", f"noclones: scp-style slug parsed (got {d['repo']})")
    check(d["values"]["github.stars"] == 42, "noclones: stars still collected")
    check(d["values"]["github.clones_14d"] is None, "noclones: clones null")
    check("push access" in d["reasons"].get("github.clones_14d", ""),
          f"noclones: per-metric push-access sentinel (got {d['reasons']})")


def test_unauth(tmp):
    repo = make_repo(tmp, "https://github.com/acme/widget.git")
    bindir = make_fake_gh(tmp)
    r = run_collect(repo, bindir, mode="unauth")
    d = json.loads(r.stdout)
    check(r.returncode == 0, "unauth: exit 0")
    check(all(v is None for v in d["values"].values()), "unauth: all metrics null")
    check("_" in d["reasons"], f"unauth: top-level reason present (got {d['reasons']})")


def test_no_remote(tmp):
    repo = make_repo(tmp, None)
    bindir = make_fake_gh(tmp)
    r = run_collect(repo, bindir)
    d = json.loads(r.stdout)
    check(r.returncode == 0, "no_remote: exit 0")
    check(d["repo"] is None, "no_remote: repo null")
    check("remote" in d["reasons"].get("_", ""), f"no_remote: reason (got {d['reasons']})")


def test_non_github(tmp):
    repo = make_repo(tmp, "https://gitlab.com/acme/widget.git")
    bindir = make_fake_gh(tmp)
    r = run_collect(repo, bindir)
    d = json.loads(r.stdout)
    check(r.returncode == 0, "non_github: exit 0")
    check(d["repo"] is None, "non_github: repo null")
    check("GitHub" in d["reasons"].get("_", ""), f"non_github: reason (got {d['reasons']})")


def test_malformed(tmp):
    """valid-but-wrong-shape JSON from gh must degrade to null + reason, not crash."""
    repo = make_repo(tmp, "https://github.com/acme/widget.git")
    bindir = make_fake_gh(tmp)
    r = run_collect(repo, bindir, mode="malformed")
    check(r.returncode == 0, "malformed: exit 0 (no AttributeError crash)")
    d = json.loads(r.stdout)
    check(all(v is None for v in d["values"].values()), "malformed: all metrics null")
    for metric in ("github.stars", "github.release_downloads", "github.clones_14d"):
        check("unexpected response" in d["reasons"].get(metric, ""),
              f"malformed: {metric} has a shape reason (got {d['reasons'].get(metric)})")


def test_host_anchored(tmp):
    """Host must be exactly github.com — a lookalike or mirror path is rejected."""
    bindir = make_fake_gh(tmp)
    for remote, label in [
        ("https://notgithub.com/acme/widget.git", "lookalike host"),
        ("https://mirror.example.com/proxy/github.com/acme/widget.git", "mirror path"),
    ]:
        sub = tmp / label.replace(" ", "_")
        sub.mkdir()
        repo = make_repo(sub, remote)
        r = run_collect(repo, bindir)
        d = json.loads(r.stdout)
        check(d["repo"] is None, f"host-anchor: {label} not attributed to github.com")
        check("not a GitHub remote" in d["reasons"].get("_", ""),
              f"host-anchor: {label} reason")


def test_credential_redaction(tmp):
    """A token embedded in a non-GitHub remote URL must not leak into output —
    in ANY userinfo placement (https, no-scheme, scp-style bare username)."""
    bindir = make_fake_gh(tmp)
    for remote, label in [
        ("https://oauth2:ghp_SECRETTOKEN123@gitlab.com/acme/widget.git", "https userinfo"),
        ("oauth2:ghp_SECRETTOKEN123@gitlab.com:acme/widget.git", "no-scheme userinfo"),
        ("ghp_SECRETTOKEN123@gitlab.com:acme/widget.git", "bare-username token"),
    ]:
        sub = tmp / label.replace(" ", "_")
        sub.mkdir()
        repo = make_repo(sub, remote)
        r = run_collect(repo, bindir)
        check("ghp_SECRETTOKEN123" not in r.stdout,
              f"redaction: token absent from output ({label})")


def test_live_smoke():
    """Lenient: real gh present+authed → run against this repo, assert structural
    validity only (value OR reasoned sentinel). Skipped otherwise."""
    probe = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if probe.returncode != 0:
        print("  skip  live smoke (no authenticated gh)")
        return
    repo_root = HERE.parents[3]     # coder-plugins repo root
    r = subprocess.run([sys.executable, str(SCRIPT), str(repo_root)],
                       capture_output=True, text=True)
    check(r.returncode == 0, "live: exit 0")
    try:
        d = json.loads(r.stdout)
        ok = ("values" in d and "reasons" in d
              and set(d["values"]) == {"github.stars", "github.release_downloads",
                                       "github.clones_14d"})
        check(ok, "live: well-formed JSON contract")
    except json.JSONDecodeError:
        check(False, "live: stdout is valid JSON")


def main():
    for fn in (test_happy, test_noclones, test_unauth, test_no_remote, test_non_github,
               test_malformed, test_host_anchored, test_credential_redaction):
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
    test_live_smoke()
    if FAILURES:
        print(f"\nFAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK — all collect-github fixture checks passed")


if __name__ == "__main__":
    main()
