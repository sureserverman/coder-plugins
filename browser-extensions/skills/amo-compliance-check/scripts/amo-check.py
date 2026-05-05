#!/usr/bin/env python3
# amo-compliance-check amo-check.py — automated AMO compliance checks
# Usage: ./amo-check.py <extension-dir>
# Prints findings grouped by section, then a summary table.
# Exit codes: 0 = no FAIL, 1 = at least one FAIL, 2 = usage error.

import json
import os
import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r"^(0|[1-9][0-9]{0,8})([.](0|[1-9][0-9]{0,8})){0,3}$")
EMAIL_ID_RE = re.compile(r"^[a-zA-Z0-9\-._]*@[a-zA-Z0-9\-._]+$")
GUID_ID_RE = re.compile(r"^\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}$")
URL_RE = re.compile(r'https?://[^\s"\'<>)]+')

VALID_PERMISSIONS = {
    "activeTab", "alarms", "background", "bookmarks", "browserSettings",
    "browsingData", "captivePortal", "clipboardRead", "clipboardWrite",
    "contentSettings", "contextMenus", "contextualIdentities", "cookies",
    "debugger", "declarativeNetRequest", "declarativeNetRequestFeedback",
    "declarativeNetRequestWithHostAccess", "devtools", "dns", "downloads",
    "downloads.open", "find", "geolocation", "history", "identity", "idle",
    "management", "menus", "menus.overrideContext", "nativeMessaging",
    "notifications", "pageCapture", "pkcs11", "privacy", "proxy",
    "scripting", "search", "sessions", "storage", "tabs", "tabHide",
    "theme", "topSites", "unlimitedStorage", "userScripts",
    "webNavigation", "webRequest", "webRequestBlocking",
    "webRequestFilterResponse", "webRequestFilterResponse.serviceWorkerScript",
    "<all_urls>",
}

FORBIDDEN_PERMISSIONS = {"mozillaAddons", "telemetry", "networkStatus"}

findings = []  # (section, severity, detail)

def add(section, severity, detail):
    findings.append((section, severity, detail))

def load_manifest(ext_dir):
    mf = ext_dir / "manifest.json"
    if not mf.exists():
        print(f"error: no manifest.json in {ext_dir}", file=sys.stderr)
        sys.exit(2)
    raw = mf.read_text()
    if re.search(r"/\*.*?\*/", raw, re.DOTALL):
        add("1", "FAIL", "manifest.json contains block comments (not valid JSON)")
    try:
        return raw, json.loads(raw)
    except json.JSONDecodeError as e:
        add("1", "FAIL", f"manifest.json is not valid JSON: {e}")
        sys.exit_code = 1
        return raw, {}

def check_required(m):
    mv = m.get("manifest_version")
    if mv not in (2, 3):
        add("1", "FAIL", f"manifest_version must be 2 or 3 (got {mv!r})")
    name = m.get("name", "")
    if not name:
        add("1", "FAIL", "name is missing or empty")
    elif name != name.strip():
        add("1", "WARN", "name has leading/trailing whitespace")
    elif len(name) > 50:
        add("1", "WARN", f"name exceeds 50 chars ({len(name)})")
    ver = m.get("version", "")
    if not ver:
        add("1", "FAIL", "version is missing")
    elif not VERSION_RE.match(ver):
        add("1", "FAIL", f"version {ver!r} does not match AMO format")

def check_conditional(ext_dir, m):
    has_locales = (ext_dir / "_locales").is_dir()
    default_locale = m.get("default_locale")
    if has_locales and not default_locale:
        add("2", "FAIL", "_locales/ exists but default_locale is not set")
    if not has_locales and default_locale:
        add("2", "FAIL", f"default_locale={default_locale!r} set but no _locales/ directory")
    bss = m.get("browser_specific_settings") or {}
    gecko = bss.get("gecko") or {}
    gid = gecko.get("id")
    if m.get("manifest_version") == 3 and not gid:
        add("2", "FAIL", "MV3 requires browser_specific_settings.gecko.id for AMO")
    elif not gid:
        add("2", "WARN", "browser_specific_settings.gecko.id is recommended")
    if gid and not (EMAIL_ID_RE.match(gid) or GUID_ID_RE.match(gid)):
        add("2", "FAIL", f"gecko.id {gid!r} is not a valid email-like or GUID format")
    if gid and EMAIL_ID_RE.match(gid) and len(gid) > 80:
        add("2", "FAIL", f"gecko.id exceeds 80 chars ({len(gid)})")
    desc = m.get("description")
    if desc is None:
        add("2", "WARN", "description is missing")
    elif len(desc) > 132:
        add("2", "WARN", f"description exceeds 132 chars ({len(desc)})")
    home = m.get("homepage_url", "")
    if "addons.mozilla.org" in home:
        add("2", "WARN", "homepage_url points to addons.mozilla.org (discouraged)")
    if "update_url" in m:
        add("2", "FAIL", "update_url is forbidden for AMO-hosted extensions")
    if "applications" in m:
        add("2", "FAIL", "'applications' is deprecated; use browser_specific_settings")
    smv = gecko.get("strict_min_version", "")
    if smv and "*" in smv:
        add("2", "FAIL", f"strict_min_version {smv!r} must not use wildcard")

def check_icons(ext_dir, m):
    icons = m.get("icons") or {}
    action_icons = {}
    for key in ("action", "browser_action", "page_action"):
        ai = (m.get(key) or {}).get("default_icon")
        if isinstance(ai, dict):
            action_icons.update(ai)
        elif isinstance(ai, str):
            action_icons["action"] = ai
    all_icons = {**icons, **action_icons}
    for size, path in all_icons.items():
        p = ext_dir / path
        if not p.exists():
            add("3", "FAIL", f"icon {path!r} (key {size}) not found")
            continue
        if p.suffix.lower() not in (".png", ".svg"):
            add("3", "WARN", f"icon {path!r} has unexpected extension {p.suffix}")
        if p.suffix.lower() == ".svg":
            txt = p.read_text(errors="ignore")
            if "viewBox" not in txt:
                add("3", "WARN", f"SVG {path!r} missing viewBox attribute")
            if "xmlns" not in txt:
                add("3", "WARN", f"SVG {path!r} missing xmlns attribute")
    sizes = {str(k) for k in icons.keys()}
    if sizes and "48" not in sizes:
        add("3", "WARN", "no 48px icon declared in icons{} (recommended for AMO)")
    if sizes and "96" not in sizes:
        add("3", "WARN", "no 96px icon declared in icons{} (recommended for AMO)")

def iter_files(ext_dir):
    for root, dirs, files in os.walk(ext_dir):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for f in files:
            yield Path(root) / f

def check_files(ext_dir, m):
    binary_exts = {".exe", ".dll", ".so", ".dylib", ".bin"}
    seen_lower = {}
    for p in iter_files(ext_dir):
        rel = p.relative_to(ext_dir)
        parts = rel.parts
        if any(part.startswith(".") for part in parts):
            add("4", "WARN", f"hidden file present: {rel}")
        if p.suffix.lower() in binary_exts:
            add("4", "FAIL", f"flagged binary extension: {rel}")
        lower = str(rel).lower()
        if lower in seen_lower and seen_lower[lower] != str(rel):
            add("4", "FAIL", f"case-only duplicate: {rel} vs {seen_lower[lower]}")
        seen_lower[lower] = str(rel)
    refs = []
    for cs in m.get("content_scripts", []) or []:
        refs.extend(cs.get("js", []) or [])
        refs.extend(cs.get("css", []) or [])
    bg = m.get("background") or {}
    refs.extend(bg.get("scripts", []) or [])
    if bg.get("page"):
        refs.append(bg["page"])
    if bg.get("service_worker"):
        refs.append(bg["service_worker"])
    for war in m.get("web_accessible_resources", []) or []:
        if isinstance(war, str):
            refs.append(war)
        elif isinstance(war, dict):
            refs.extend(war.get("resources", []) or [])
    for r in refs:
        if not r:
            add("4", "FAIL", "empty filename in manifest reference")
            continue
        if "*" in r or "?" in r:
            continue
        if not (ext_dir / r).exists():
            add("4", "FAIL", f"referenced file missing: {r}")

def check_permissions(m):
    perms = (m.get("permissions") or []) + (m.get("host_permissions") or [])
    for p in perms:
        if p in FORBIDDEN_PERMISSIONS:
            add("5", "FAIL", f"privileged/Mozilla-internal permission: {p}")
        if p.startswith("http") or p.startswith("*://") or p == "<all_urls>":
            continue
        if p not in VALID_PERMISSIONS:
            add("5", "WARN", f"unknown or non-standard permission: {p}")
    if "<all_urls>" in perms:
        add("5", "WARN", "<all_urls> requires justification for AMO review")

def grep_files(ext_dir, pattern, exts, skip_dirs=("node_modules", "_locales")):
    hits = []
    rx = re.compile(pattern)
    for p in iter_files(ext_dir):
        if any(part in skip_dirs for part in p.parts):
            continue
        if p.suffix.lower() not in exts:
            continue
        try:
            txt = p.read_text(errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(txt.splitlines(), 1):
            if rx.search(line):
                hits.append((p.relative_to(ext_dir), i, line.strip()[:120]))
    return hits

def check_remote_code(ext_dir, m):
    for rel, ln, line in grep_files(ext_dir, r'<script\s+[^>]*src\s*=\s*["\']((?:https?:)?//)', {".html", ".htm"}):
        add("6", "FAIL", f"{rel}:{ln} remote <script src>: {line}")
    for rel, ln, line in grep_files(ext_dir, r'\beval\s*\(', {".js", ".mjs"}):
        add("6", "FAIL", f"{rel}:{ln} eval(): {line}")
    for rel, ln, line in grep_files(ext_dir, r'new\s+Function\s*\(', {".js", ".mjs"}):
        add("6", "FAIL", f"{rel}:{ln} new Function(): {line}")
    for rel, ln, line in grep_files(ext_dir, r'setTimeout\s*\(\s*["\']', {".js", ".mjs"}):
        add("6", "FAIL", f"{rel}:{ln} setTimeout(string): {line}")
    for rel, ln, line in grep_files(ext_dir, r'setInterval\s*\(\s*["\']', {".js", ".mjs"}):
        add("6", "FAIL", f"{rel}:{ln} setInterval(string): {line}")
    for rel, ln, line in grep_files(ext_dir, r'document\.write\s*\(', {".js", ".mjs"}):
        add("6", "WARN", f"{rel}:{ln} document.write(): {line}")
    csp = m.get("content_security_policy")
    csp_str = csp if isinstance(csp, str) else (csp or {}).get("extension_pages", "")
    if csp_str and "unsafe-eval" in csp_str:
        add("6", "FAIL", f"CSP contains unsafe-eval: {csp_str}")

def check_quality(ext_dir):
    for kw in ("coinhive", "CoinHive", "crypto-loot", "cryptoloot", "jsecoin"):
        for rel, ln, line in grep_files(ext_dir, re.escape(kw), {".js", ".mjs", ".html"}):
            add("7", "FAIL", f"{rel}:{ln} cryptomining reference ({kw}): {line[:80]}")

def check_privacy(ext_dir):
    for rel, ln, line in grep_files(ext_dir, r'["\']http://[^"\'\s]+["\']', {".js", ".mjs", ".html", ".json"}):
        if "localhost" in line or "127.0.0.1" in line:
            continue
        add("8", "WARN", f"{rel}:{ln} HTTP URL (should be HTTPS): {line[:100]}")

def check_mv3(m):
    if m.get("manifest_version") != 3:
        return "N/A"
    bg = m.get("background") or {}
    if bg.get("service_worker") and not bg.get("scripts"):
        add("10", "WARN", "MV3 background.service_worker present without scripts fallback for Firefox")
    if m.get("incognito") == "split":
        add("10", "FAIL", "incognito='split' is unsupported in Firefox")
    return None

SECTION_NAMES = {
    "1": "Manifest Required",
    "2": "Manifest Conditional",
    "3": "Icons",
    "4": "File Structure",
    "5": "Permissions",
    "6": "Security — Remote Code",
    "7": "Security — Code Quality",
    "8": "Data & Privacy",
    "9": "Content Scripts",
    "10": "MV3 Specific",
}

def main():
    if len(sys.argv) != 2:
        print("usage: amo-check.py <extension-dir>", file=sys.stderr)
        sys.exit(2)
    ext_dir = Path(sys.argv[1]).resolve()
    if not ext_dir.is_dir():
        print(f"error: {ext_dir} is not a directory", file=sys.stderr)
        sys.exit(2)
    raw, m = load_manifest(ext_dir)
    check_required(m)
    check_conditional(ext_dir, m)
    check_icons(ext_dir, m)
    check_files(ext_dir, m)
    check_permissions(m)
    check_remote_code(ext_dir, m)
    check_quality(ext_dir)
    check_privacy(ext_dir)
    mv3_na = check_mv3(m)

    for sec, sev, detail in findings:
        print(f"[{sev}] §{sec} {SECTION_NAMES.get(sec, sec)}: {detail}")

    print()
    print("| Section                    | Status | Issues |")
    print("|----------------------------|--------|--------|")
    for sec in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"):
        name = SECTION_NAMES[sec]
        if sec == "10" and mv3_na == "N/A":
            print(f"| {name:<26} | N/A    |        |")
            continue
        sev_list = [s for (x, s, _) in findings if x == sec]
        if any(s == "FAIL" for s in sev_list):
            status = "FAIL"
        elif any(s == "WARN" for s in sev_list):
            status = "WARN"
        else:
            status = "PASS"
        print(f"| {name:<26} | {status:<6} | {len(sev_list):<6} |")

    print()
    print("Note: sections 7 (obfuscation/minification), 9 (content script DOM injection), and 10 (data_collection_permissions)")
    print("require judgment — re-read SKILL.md for nuanced manual checks on top of this automated pass.")

    sys.exit(1 if any(s == "FAIL" for _, s, _ in findings) else 0)

if __name__ == "__main__":
    main()
