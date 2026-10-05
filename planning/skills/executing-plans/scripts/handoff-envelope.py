#!/usr/bin/env python3
"""Write and check the files a supervised session handoff leaves for remote-agents.

Why this exists: when a plan executor hands off to a fresh session, remote-agents
(the supervisor that launched it) must learn that the handoff is ready, whether the
fresh session took it, and why it failed if it did not. Files under
<root>/.claude/handoffs/ are that channel. This script is the one writer and the one
reader on the planning side, so the protocol is spelled in one place.

Subcommands, each with `--root <repo>`:

    new-id           print `h-` + 20 lowercase hex chars (secrets.token_hex(10))
    ready            write <id>.ready.json     (event HANDOFF_READY)
    accept           write <id>.accepted.json  (event HANDOFF_ACCEPTED)
    fail             write <id>.failed.json    (event HANDOFF_FAILED, --code required)
    verify           exit 0 when the handoff checks out, else print a failure code, exit 3
    request-pending  exit 0 when request.json asks this managed session to hand off, else 1

Protocol, version 1. Every envelope has exactly these keys:

    {"protocol": "remote-agents-handoff", "version": 1, "event": ...,
     "handoff_id": ..., "managed_session_id": ..., "timestamp": ..., "plan": ...}

`failed` adds `failure_code`. `plan` is an absolute path (os.path.abspath of --plan).
`fail` takes --plan as optional, so its key set stays the same: `plan` is null when
--plan is not given. `managed_session_id` is $REMOTE_AGENTS_SESSION_ID. `timestamp` is
ISO-8601 UTC, `YYYY-MM-DDTHH:MM:SSZ`. request.json (written by remote-agents) is
`{"protocol", "version", "managed_session_id", "requested_at"}`.

Ids. A handoff id matches ^h-[0-9a-f]{20}$; a --handoff-id that does not exits 2. A
managed session id is checked with remote-agents' own rule
(src/remote_agents/ports/session_identity.py, _SAFE_SESSION_ID): 1-128 chars of
[A-Za-z0-9_-].

Unsupervised. `ready`, `accept` and `fail` write nothing, print `unsupervised` and exit
0 when REMOTE_AGENTS_SESSION_ID is unset or empty. Set but invalid: nothing written,
exit 1.

Writes follow context-usage.py's write_sidecar. The root opens as a directory; then
`.claude` and `handoffs` each open O_NOFOLLOW | O_DIRECTORY relative to the parent fd
(made with mkdir there first if missing) and must be owned by this user. The bytes go
to a fresh O_EXCL | O_NOFOLLOW temp file beside the target, and a rename puts it in
place, so a link planted at the name is replaced, never written through. The first
write also creates handoffs/.gitignore containing `*`. A refused write prints
`refused` to stderr and exits 1.

Reads open each component O_NOFOLLOW (the file also O_NONBLOCK) and refuse: a link,
anything but a regular file, more than 4096 bytes, non-JSON, a protocol other than
`remote-agents-handoff`, a version other than 1, a handoff id failing its pattern, an
invalid managed session id. A refused read counts as absent.

verify --handoff-id ID --plan PATH checks, in this order, and prints the first failure:

    no-ready         <id>.ready.json is absent or refused, is not HANDOFF_READY, or
                     names another handoff id
    plan-missing     the plan file cannot be read
    id-mismatch      the plan's LAST `**RESUME HERE` block has no `handoff_id:` line,
                     or its first one names another id
    cwd-mismatch     realpath of the block's `cwd:` value != realpath(root)
    branch-mismatch  the block's `branch:` value != `git -C <root> branch --show-current`

A block runs from a line starting `**RESUME HERE` to the next such line, the next
markdown heading, or end of file. Within it the first `handoff_id:`, `cwd:` and
`branch:` fields are read wherever they sit on a line (the template puts `plan:`,
`cwd:` and `branch:` on one line); the value is the next whitespace-free token with
backticks stripped, so list markers, backticks and a trailing `(at abc1234)` note are
tolerated. A path containing spaces is not supported.

Importable: request_pending(root, env) -> bool, for context-usage.py to load through
importlib (the hyphenated filename prevents a plain import).

Exit codes: 0 ok; 1 refused write / no pending request; 2 bad CLI usage; 3 verify failed.

Stdlib only.
"""
import argparse
import datetime
import json
import os
import re
import secrets
import stat
import subprocess
import sys

PROTOCOL = "remote-agents-handoff"
VERSION = 1
ENV_VAR = "REMOTE_AGENTS_SESSION_ID"
CLAUDE_DIR = ".claude"
HANDOFF_DIR = "handoffs"
REQUEST = "request.json"
MAX_READ_BYTES = 4096
HANDOFF_ID_RE = re.compile(r"h-[0-9a-f]{20}")
SESSION_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,128}")
FAILURE_CODES = ("id-mismatch", "no-ready", "cwd-mismatch", "branch-mismatch", "plan-missing")
EVENTS = {"ready": ("HANDOFF_READY", "ready"),
          "accept": ("HANDOFF_ACCEPTED", "accepted"),
          "fail": ("HANDOFF_FAILED", "failed")}

BLOCK_START = re.compile(r"^\s*\*\*RESUME HERE")
MD_HEADING = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
FIELD_RE = {k: re.compile(r"(?<![\w-])" + k + r":\s*`?([^\s`]+)")
            for k in ("handoff_id", "cwd", "branch")}


def valid_handoff_id(v):
    return isinstance(v, str) and HANDOFF_ID_RE.fullmatch(v) is not None


def valid_session_id(v):
    return isinstance(v, str) and SESSION_ID_RE.fullmatch(v) is not None


def new_id():
    return "h-" + secrets.token_hex(10)


def _close_all(fds):
    for fd in fds:
        try:
            os.close(fd)
        except OSError:
            pass


def read_handoff_file(root, name):
    """The parsed <root>/.claude/handoffs/<name> as a dict, or None for any refusal.

    Opened one component at a time: root, then `.claude` and `handoffs` with
    O_NOFOLLOW | O_DIRECTORY, then the file with O_NOFOLLOW | O_NONBLOCK (a FIFO
    would otherwise block the open). Checked on the open fd: a regular file of at most
    MAX_READ_BYTES. Then the protocol, the version and any id it carries.
    """
    fds = []
    try:
        fds.append(os.open(root, os.O_RDONLY | os.O_DIRECTORY))
        for d in (CLAUDE_DIR, HANDOFF_DIR):
            fds.append(os.open(d, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=fds[-1]))
        fds.append(os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fds[-1]))
        st = os.fstat(fds[-1])
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_READ_BYTES:
            return None
        raw = os.read(fds[-1], MAX_READ_BYTES + 1)
        if len(raw) > MAX_READ_BYTES:
            return None
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    finally:
        _close_all(fds)
    if (not isinstance(data, dict) or data.get("protocol") != PROTOCOL
            or type(data.get("version")) is not int or data["version"] != VERSION):
        return None
    if "handoff_id" in data and not valid_handoff_id(data["handoff_id"]):
        return None
    if not valid_session_id(data.get("managed_session_id")):
        return None
    return data


def request_pending(root, env):
    """True when <root>/.claude/handoffs/request.json is valid and its
    managed_session_id equals env[REMOTE_AGENTS_SESSION_ID]; False otherwise,
    including when the variable is unset."""
    sid = env.get(ENV_VAR)
    if not valid_session_id(sid):
        return False
    data = read_handoff_file(root, REQUEST)
    return data is not None and data.get("managed_session_id") == sid


def _open_owned_dir(name, parent_fd):
    """Open `name` under parent_fd without following a link, creating it if missing;
    it must be this user's. Returns the fd or raises."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
        fd = os.open(name, flags, dir_fd=parent_fd)
    if os.fstat(fd).st_uid != os.getuid():
        os.close(fd)
        raise PermissionError(f"{name} is not owned by this user")
    return fd


def write_handoff_file(root, name, body):
    """Write `body` (bytes) to <root>/.claude/handoffs/<name>. Returns whether it was
    written; never raises."""
    fds, tmp = [], f".{name}.{os.getpid()}.tmp"
    try:
        fds.append(os.open(root, os.O_RDONLY | os.O_DIRECTORY))
        fds.append(_open_owned_dir(CLAUDE_DIR, fds[-1]))
        fds.append(_open_owned_dir(HANDOFF_DIR, fds[-1]))
        hfd = fds[-1]
        try:
            gfd = os.open(".gitignore", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                          0o600, dir_fd=hfd)
            try:
                os.write(gfd, b"*\n")
            finally:
                os.close(gfd)
        except FileExistsError:
            pass
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                     dir_fd=hfd)
        try:
            os.write(fd, body)
        finally:
            os.close(fd)
        os.replace(tmp, name, src_dir_fd=hfd, dst_dir_fd=hfd)
        tmp = None
        return True
    except Exception:
        return False
    finally:
        if tmp is not None and len(fds) == 3:
            try:
                os.unlink(tmp, dir_fd=fds[-1])
            except OSError:
                pass
        _close_all(fds)


def envelope(event, handoff_id, session_id, plan, failure_code=None):
    body = {"protocol": PROTOCOL, "version": VERSION, "event": event,
            "handoff_id": handoff_id, "managed_session_id": session_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
                                          .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "plan": os.path.abspath(plan) if plan is not None else None}
    if event == "HANDOFF_FAILED":
        body["failure_code"] = failure_code
    return body


def last_block(text):
    """The lines of the last RESUME HERE block in `text`, or None when there is none."""
    blocks, cur = [], None
    for line in text.splitlines():
        if BLOCK_START.match(line):
            cur = [line]
            blocks.append(cur)
        elif MD_HEADING.match(line):
            cur = None
        elif cur is not None:
            cur.append(line)
    return blocks[-1] if blocks else None


def block_field(lines, key):
    for line in lines:
        m = FIELD_RE[key].search(line)
        if m:
            return m.group(1)
    return None


def current_branch(root):
    try:
        r = subprocess.run(["git", "-C", root, "branch", "--show-current"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def verify(root, handoff_id, plan):
    """None when the handoff checks out, else the failure code."""
    ready = read_handoff_file(root, f"{handoff_id}.ready.json")
    if (ready is None or ready.get("event") != "HANDOFF_READY"
            or ready.get("handoff_id") != handoff_id):
        return "no-ready"
    try:
        with open(plan, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return "plan-missing"
    lines = last_block(text)
    if lines is None or block_field(lines, "handoff_id") != handoff_id:
        return "id-mismatch"
    cwd = block_field(lines, "cwd")
    if cwd is None or os.path.realpath(os.path.expanduser(cwd)) != os.path.realpath(root):
        return "cwd-mismatch"
    branch = current_branch(root)
    if not branch or block_field(lines, "branch") != branch:
        return "branch-mismatch"
    return None


def handoff_id_arg(text):
    if not valid_handoff_id(text):
        raise argparse.ArgumentTypeError(f"not a handoff id (^h-[0-9a-f]{{20}}$): {text!r}")
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(prog="handoff-envelope")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new-id", help="print a fresh handoff id")
    p.add_argument("--root", required=True)
    for cmd in ("ready", "accept"):
        p = sub.add_parser(cmd, help=f"write <id>.{EVENTS[cmd][1]}.json")
        p.add_argument("--root", required=True)
        p.add_argument("--handoff-id", required=True, type=handoff_id_arg)
        p.add_argument("--plan", required=True)
    p = sub.add_parser("fail", help="write <id>.failed.json")
    p.add_argument("--root", required=True)
    p.add_argument("--handoff-id", required=True, type=handoff_id_arg)
    p.add_argument("--code", required=True, choices=FAILURE_CODES)
    p.add_argument("--plan", help="plan file (recorded as null when omitted)")
    p = sub.add_parser("verify", help="check a handoff; exit 3 with a failure code")
    p.add_argument("--root", required=True)
    p.add_argument("--handoff-id", required=True, type=handoff_id_arg)
    p.add_argument("--plan", required=True)
    p = sub.add_parser("request-pending", help="exit 0 when a handoff is requested of us")
    p.add_argument("--root", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "new-id":
        print(new_id())
        return 0
    if args.cmd == "request-pending":
        return 0 if request_pending(args.root, os.environ) else 1
    if args.cmd == "verify":
        code = verify(args.root, args.handoff_id, args.plan)
        if code is None:
            return 0
        print(code)
        return 3

    sid = os.environ.get(ENV_VAR)
    if not sid:
        print("unsupervised")
        return 0
    if not valid_session_id(sid):
        print(f"refused: {ENV_VAR} is not a valid session id", file=sys.stderr)
        return 1
    event, suffix = EVENTS[args.cmd]
    body = envelope(event, args.handoff_id, sid, args.plan, getattr(args, "code", None))
    name = f"{args.handoff_id}.{suffix}.json"
    if not write_handoff_file(args.root, name, (json.dumps(body) + "\n").encode("utf-8")):
        print(f"refused: could not write {name} under {args.root}/.claude/handoffs",
              file=sys.stderr)
        return 1
    print(os.path.join(os.path.abspath(args.root), CLAUDE_DIR, HANDOFF_DIR, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
