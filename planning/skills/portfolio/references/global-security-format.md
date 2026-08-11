# global-security.md — format and input contract

`<vault_dir>/Portfolio/global-security.md` is the portfolio-wide security
dashboard: which projects have open CRITICALs, which are trending the wrong way,
which have not been audited. Rebuilt by `portfolio rebuild` via
`scripts/security-scan.py | scripts/security-rollup.py`. **Never edit by hand.**

## Input contract — `security/history.jsonl`

Produced by **sec-audit v1.29+** at
`<vault_dir>/Portfolio/<area>/<name>/security/history.jsonl`, one JSON object per
run. The authoritative definition is sec-audit's own skill body, section 1.5.1;
this is
the consumer's view of it.

| Field | Required | Meaning |
|---|---|---|
| `run_id` | yes | `YYYYMMDD-HHMM` UTC; sorts chronologically |
| `mode` | yes | `full` \| `incremental` \| `feeds` |
| `started_at` / `finished_at` | no | ISO-8601 |
| `plugin_version` | no | |
| `counts` | no | open findings by severity |
| `deltas` | no | `new`/`regressed`/`reverified`/`carried`/`fixed`/`baseline_open`/`total_open`, plus `accepted` and `previously_accepted` (sec-audit v1.34+) |
| `lanes_ran` / `lanes_carried`, `cost` | no | |

Three rules this roll-up must never break:

1. **An optional field that is absent is `null`, never `0`.** "Not measured" and
   "measured zero" are different facts. The scan emits `null`; the render emits
   `?`. A dashboard that shows an unmeasured project as `0 CRITICAL` reports it
   as clean, which is the worst failure this file can have.
2. **`mode: "feeds"` means no code lane ran.** A feed-only run re-checks
   dependency advisories against unchanged code; its counts are carried forward,
   not re-verified. Such rows are marked `⚠` with a legend, and must never be
   presented as an audit.
3. **`total_open` already includes ACCEPTED findings.** "Open and not currently
   suppressed" is `total_open − accepted`. Never treat `accepted` as already
   subtracted.

Unknown keys and unknown `mode` values are passed through, not rejected — the
producer lives in a different repository and will add fields.

## Rendering

Rows are worst-first: open CRITICAL desc, then HIGH, then staleness. An unknown
count sorts as *worse* than a known zero — unmeasured is not clean.

Sections, each emitted only when it has content: the main table; **Never
audited**; **History problems** (malformed `history.jsonl` lines, skipped and
counted); **Could not assess** (a project whose scan raised — one broken project
never aborts the sweep).

## Degradation

The layer is additive. If `security-scan.py` / `security-rollup.py` are missing,
or either fails or times out, `portfolio rebuild` prints one line, leaves any
existing `global-security.md` **intact** (never truncated), and the other
roll-ups are byte-identical. Locked by
`tests/test-security-degradation.py`; behaviour by `tests/test-security-scan.py`.
