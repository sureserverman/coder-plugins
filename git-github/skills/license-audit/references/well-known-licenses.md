# Well-Known License Reference

Consult this table during Phase 2a of the license audit. If a dependency is listed here, use the stated license and skip the registry lookup.

| Package | License | Source |
|---|---|---|
| alpine (base image) | MIT | Alpine Linux project |
| debian / ubuntu (base images) | Various (base: GPL-2.0+) | Debian/Ubuntu projects |
| tor | BSD-3-Clause | The Tor Project |
| socat | GPL-2.0-only | Gerhard Rieger |
| haproxy | GPL-2.0-or-later | Willy Tarreau |
| stunnel | GPL-2.0-or-later | Michal Trojnara |
| tini | MIT | Thomas Orozco |
| nginx | BSD-2-Clause | Nginx Inc. |
| curl | MIT (curl license) | Daniel Stenberg |
| openssl | Apache-2.0 | OpenSSL Project |
| libressl | ISC + OpenSSL legacy | OpenBSD Foundation |
| busybox | GPL-2.0-only | BusyBox project |
| musl libc | MIT | musl project |
| glibc | LGPL-2.1-or-later | GNU project |
| bash | GPL-3.0-or-later | GNU project |
| python | PSF-2.0 (permissive) | Python Software Foundation |
| node / nodejs | MIT | OpenJS Foundation |
| go (stdlib) | BSD-3-Clause | The Go Authors |
| rust (stdlib) | MIT OR Apache-2.0 | Rust Foundation |
| redis | BSD-3-Clause (pre-7.4) / SSPL+RSALv2 (7.4+) | Redis Ltd. |
| postgresql | PostgreSQL (permissive) | PostgreSQL Global Dev Group |
| obfs4proxy | BSD-2-Clause | The Tor Project |
| lyrebird | BSD-2-Clause | The Tor Project |
| snowflake | BSD-3-Clause | The Tor Project |
| webtunnel | BSD-3-Clause | The Tor Project |

If a package isn't listed here, fall through to Phase 2b (registry lookups) and 2c (WebSearch).
