#!/usr/bin/env python3
"""collect-amo — best-effort free addons.mozilla.org metrics for `track`.

Given an AMO addon id (slug, numeric id, or extension GUID), collects what the
public AMO API gives away for free — daily users, weekly downloads, and rating
count/average — with no authentication. Emits ONE JSON document on stdout:

    {"addon": "<slug>|null", "collected": "<YYYY-MM-DD>",
     "values":  {"amo.daily_users": N|null, "amo.downloads_last_week": N|null,
                 "amo.rating_count": N|null, "amo.rating_average": N|null},
     "reasons": {"<metric or _>": "<why it's null>"}}

Best-effort by contract (references/collector-contract.md): every source
degrades to a null value + a reason sentinel; the script exits 0 even when
nothing could be collected (unknown addon, network down, rate-limited). Only a
usage error (wrong argument count) exits non-zero. The `track` skill folds
`values` into metrics.md as the `amo.*` entries and surfaces `reasons`.

Note `amo.rating_average` is a float, not a count — the only non-integer metric
here, and deliberate: an average is the number a listing target is set against.
"""
import importlib.util
import re
import sys
from pathlib import Path

_HELPER = Path(__file__).resolve().parent / "_collector.py"
_spec = importlib.util.spec_from_file_location("_collector", _HELPER)
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)

METRICS = ["amo.daily_users", "amo.downloads_last_week",
           "amo.rating_count", "amo.rating_average"]

# AMO accepts three id forms. Validating against them up front does double duty:
#   1. an id that cannot be a legal AMO id is refused, so a hostile argument
#      never reaches the `addon` SUBJECT field — the one field redaction cannot
#      rewrite, since it must stay the true id to be useful;
#   2. a VALIDATED id is safe to echo verbatim, which matters because AMO's
#      primary GUID form is `name@domain` (uBlock0@raymondhill.net) and the
#      generic userinfo redactor would strip it to `raymondhill.net`, throwing
#      away the identifying half of the id in every reason.
# `\Z`, not `$`: Python's `$` also matches immediately before ONE trailing
# newline, so `ublock-origin\n` would validate and carry a raw newline into a
# reason — and metrics.md is a line-oriented format, where an embedded newline
# can split or fabricate a line. This is the gap that made "a validated id is
# safe to echo verbatim" not quite true.
AMO_ID_RE = re.compile(
    r"^(?:[a-z0-9][a-z0-9._~-]*"                     # slug or numeric id
    r"|\{[0-9a-f-]{36}\}"                            # {uuid} GUID
    r"|[a-z0-9][a-z0-9._-]*@[a-z0-9][a-z0-9.-]*)\Z",  # name@domain GUID
    re.IGNORECASE)
AMO_ID_MAX = 255

# Test seam: the suite points this at a localhost stub so CI never makes a live
# call. Unset in normal use — the real public endpoint is the default, and a
# non-loopback override is refused (see _collector.test_base).
_BASE = c.test_base("AMO_TEST_BASE", "https://addons.mozilla.org")
ADDON_API = _BASE + "/api/v5/addons/addon/{addon}/"


def collect(addon):
    if not addon:
        return c.document("addon", None, METRICS,
                          reasons={"_": "no addon id given"})
    if addon.startswith("-"):
        # Distinct from the empty case: an id WAS given, it just can't be one
        # (a leading dash is an option, not an addon) — saying "no addon id
        # given" for `--help` told the operator the wrong thing.
        return c.document("addon", None, METRICS,
                          reasons={"_": f"{c.safe_label(addon)} looks like a "
                                        f"command-line option, not an addon id"})
    if len(addon) > AMO_ID_MAX or not AMO_ID_RE.match(addon):
        # Refuse anything that cannot be a legal AMO id, rather than carrying
        # it. Only THIS reason redacts — the argument is untrusted here, and a
        # rejected id is exactly where a userinfo string would otherwise land.
        return c.document("addon", None, METRICS,
                          reasons={"_": f"{c.safe_label(addon)} is not a valid "
                                        f"AMO addon id (slug, numeric id, or GUID)"})
    # Past validation the id is safe to echo verbatim; encode for the URL, where
    # a raw unicode or space-bearing id would raise outside every degrade path.
    url = ADDON_API.format(addon=c.quote_id(addon))
    data, err = c.get_json(url, not_found_reason=f"addon {addon} not found on AMO")
    if err:
        # Whole-collection failure: one reason explains every null at once.
        return c.document("addon", None, METRICS, reasons={"_": err})
    if not isinstance(data, dict):
        return c.document("addon", None, METRICS,
                          reasons={"_": "unexpected response shape (not an object)"})

    values, reasons = {}, {}
    # Top-level scalars.
    for key, field in (("amo.daily_users", "average_daily_users"),
                       ("amo.downloads_last_week", "weekly_downloads")):
        val, reason = c.dig(data, field)
        values[key] = val
        if reason:
            reasons[key] = f"{key}: {reason}"
    # Nested under `ratings`. A brand-new addon legitimately has no ratings
    # block yet — that is a null with a reason, never a zero standing in for
    # "nobody has rated this", which would silently satisfy a rating target.
    for key, field, cast in (("amo.rating_count", "count", int),
                             ("amo.rating_average", "average", float)):
        val, reason = c.dig(data, "ratings", field, cast=cast)
        values[key] = val
        if reason:
            reasons[key] = f"{key}: {reason}"

    # BOTH branches must be validated. The fallback (`addon`) passed AMO_ID_RE
    # at the top — but the PRIMARY branch is upstream-supplied, and an untrusted
    # response is exactly as untrusted as an argument. Without this check a
    # response carrying `{"slug": "evil\ninjected: 999"}` put a raw newline in
    # the subject field of a line-oriented, committed metrics.md — defeating the
    # `\Z` anchoring done for the argument path one function above.
    upstream = data.get("slug")
    slug = upstream if (isinstance(upstream, str)
                        and len(upstream) <= AMO_ID_MAX
                        and AMO_ID_RE.match(upstream)) else addon
    if slug is addon and isinstance(upstream, str):
        reasons["_"] = (f"upstream slug {c.safe_label(upstream)} is not a valid "
                        f"AMO id; reporting the requested id instead")
    return c.document("addon", slug, METRICS, values, reasons)


def main(argv):
    if len(argv) != 2:
        c.usage("usage: collect-amo.py <addon-slug-id-or-guid>")
    c.emit(collect(argv[1]))


if __name__ == "__main__":
    main(sys.argv)
