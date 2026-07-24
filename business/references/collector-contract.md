# Collector contract — `business/scripts/collect-*.py`

The contract every per-channel metric collector must meet, extracted from the
reference implementation `collect-github.py` (BL-002). A collector is a
**deterministic script** on the determinism boundary: it gathers numbers, makes
no judgments, and hands the `track` skill a document to fold into `metrics.md`.

## 1. Interface

```
python3 business/scripts/collect-<channel>.py <target> [<target> …]
```

One JSON document on **stdout**, nothing else:

```json
{"<subject key>": "<identity>|null",
 "collected": "YYYY-MM-DD",
 "values":  {"<channel>.<metric>": <number>|null, …},
 "reasons": {"<metric key>|_": "<why it is null>", …}}
```

- `values` **always carries every metric key the collector knows**, present with
  `null` when uncollected. A caller must never have to distinguish "absent" from
  "failed" — absence is not a state this contract has.
- `collected` is the local date the run happened.
- The subject key names what was measured (`repo` for GitHub, `package` for npm,
  `addon` for AMO). Null when the target could not even be identified.

## 2. Best-effort by contract

This is the property that matters most: **a collector never fails the run.**

- Every source degrades to a **null value plus a reason sentinel**. Never a
  partial document, never an exception to the caller, never a zero standing in
  for "unknown" — a null metric is *couldn't collect*, not `0`.
- **Exit 0 even when nothing at all collected** (no network, unknown package,
  rate-limited, malformed response). The metrics are a nice-to-have; the
  operator's `track` run must continue and prompt for what's missing.
- **Only a usage error exits non-zero** (wrong argument count). That is the sole
  non-zero path.
- A malformed-but-valid-JSON upstream response (wrong shape, `null`, an error
  envelope where a list was expected) is a degrade, not a crash. Assume the API
  will change shape without telling you.

## 3. Reason shapes

Two, and callers branch on them:

- **`reasons["_"]`** — one whole-collection failure explaining every null at
  once (target not identifiable, network unreachable, dependency missing). When
  all values are null, a caller checks `"_"` first.
- **`reasons["<channel>.<metric>"]`** — a per-metric failure while siblings
  succeeded (e.g. a metric behind an auth wall the others don't need).

Reasons are short, human-facing, and safe to commit — they land in `metrics.md`
in front of the operator.

## 4. Secret redaction

Any URL, remote, or target echoed into a reason **must have userinfo stripped
first**. Remotes and API URLs commonly embed tokens, and reasons are written to
a file that gets committed. Redaction is scheme-independent: strip any
`<userinfo>@` run whether or not a `//` precedes it, so scp-style
(`git@host:path`) and no-scheme (`oauth2:TOKEN@host:path`) forms are covered too.
Truncate long echoed values.

## 5. Metric-key namespace

Keys are **`<channel>.<metric>`**, matching `github.stars`. The channel prefix is
the collector's own name — `npm.*`, `amo.*`, `github.*`, with `manual.*` reserved
for figures no collector reaches (`metrics-format.md` § Conventional metric
names). The scanner's parse contract already accepts any `<source>.<metric>` key,
so **a new channel needs no scanner change** — the prefix is a naming convention
that keeps metrics diffable under stable keys, and a `BUSINESS.md` target
matching by bare suffix (`metric: downloads`) resolves through the same
suffix-plus-precedence rule as every other metric.

Pick metric suffixes that describe the measurement including its window
(`npm.downloads_last_week`, `github.clones_14d`) — a bare `downloads` that
silently means "this week" here and "all time" there is not diffable.

## 6. Channel shortlist (BL-002)

Built first because they are **public, unauthenticated and free**:

| Channel | Endpoint | Auth |
|---|---|---|
| npm | `api.npmjs.org/downloads/point/…` + `registry.npmjs.org` | none |
| AMO | `addons.mozilla.org/api/v5/addons/addon/…` | none |

Deferred, and why: **Play** needs Google Play Console API service-account
credentials (a per-project secret, not a free public endpoint); **donation
platforms** vary per platform with no common API, and several require an
authenticated account. Both are worth doing but are a different shape of work —
credential handling — from a public read.

## 7. Testing a collector

Match `tests/test-collect-github.py`'s approach — no pytest, plain assertions,
run directly, non-zero exit on failure. Cover at minimum:

1. **Happy path** against a recorded fixture (never a live call in CI).
2. **Unknown/missing target** → nulls + reason, **exit 0**.
3. **Network failure** → nulls + reason, **exit 0**.
4. **Malformed upstream response** → nulls + reason, exit 0, no traceback.
5. **Usage error** → non-zero.

Assert the exit code explicitly in cases 2–4. That a total failure still exits 0
is the contract's whole point and the easiest thing to regress.

## 8. Implementation note

`_collector.py` is a shared helper implementing §2–§4 (HTTP-with-degrade, reason
accumulation, redaction, document emission) for collectors written against this
doc. **This document, not the helper, is the contract** — `collect-github.py`
predates the helper, implements the same contract directly, and is deliberately
left alone: it is covered by a passing suite, and retrofitting a working
collector buys no behavior. A new collector should use the helper.
