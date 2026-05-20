---
title: "Connection: Stale Process State and Phantom Liveness"
connects:
  - "concepts/adspower-wayland-gui-session-recovery"
  - "concepts/v3-startup-login-verification-gap"
  - "concepts/stale-in-memory-import-writer-leak"
  - "concepts/worker-status-observability"
  - "concepts/bet365-session-login-detection-gap"
sources:
  - "daily/lcash/2026-05-18.md"
created: 2026-05-18
updated: 2026-05-18
---

# Connection: Stale Process State and Phantom Liveness

## The Connection

Three independently discovered bugs on 2026-05-18 share a single root pattern: a process, API, or system component reports itself as healthy/active while its actual operational state has fundamentally degraded. Each produces zero useful output while passing standard liveness checks. The pattern is "phantom liveness" — the system is technically alive but operationally dead.

## Key Insight

The non-obvious insight is that **liveness checks and health checks measure different things, and conflating them creates dangerous blind spots.** Liveness answers "is the process running?" Health answers "is the process producing correct output?" All three bugs passed liveness checks while failing health checks — but no health checks existed for the specific failure modes.

| Bug | What Reports "Alive" | What's Actually Wrong | Data Impact |
|-----|---------------------|----------------------|-------------|
| **AdsPower phantom-active** | AdsPower API: `status=Active, port=33865` | No Chrome process bound to port | Zero markets for the sport |
| **v3 stale session assumption** | v3 process running, health endpoint responsive | bet365 cookies expired, discovery returns empty | Zero markets for 3+ days |
| **Stale in-memory import** | Legacy service writing picks to Supabase | Python process has old tracker.py in `sys.modules` | 661 duplicate rows with wrong hash version |

Each failure looks healthy at a different layer of abstraction:
- The AdsPower bug looks healthy at the **API layer** (HTTP 200 with port number)
- The v3 session bug looks healthy at the **process layer** (PID alive, memory allocated)
- The stale import bug looks healthy at the **data layer** (picks flowing into Supabase)

Standard monitoring that checks any single layer would miss at least two of these failures. Effective monitoring must verify the **end-to-end data path**: correct code version → authenticated session → data flowing → output correct.

## The General Pattern

These three bugs are instances of a broader pattern that pervades the value betting scanner's operational history:

- **Game scraper "streaming" with 3.7h stale data** (see [[concepts/worker-status-observability]]): process alive, status = "streaming", but Chrome dead and serving cached data
- **Logged-out bet365 returning empty responses** (see [[concepts/bet365-session-login-detection-gap]]): session expired, responses structurally identical to "no data available"
- **Push workers orphaned** (see [[concepts/push-worker-orphan-accumulation]]): 12 workers "running" but flooding VPS with redundant traffic

The common thread: **the system's own health reporting is based on conditions (process alive, task registered, API responding) that are necessary but not sufficient for correct operation.** Every phantom liveness bug requires adding a new sufficiency check — AdsPower needs CDP port verification, v3 needs login state verification, and the import leak needs hash version verification.

## Prevention Architecture

A defense-in-depth approach would layer three types of checks:

1. **Liveness** (exists already): Is the process running? Is the port bound? Does the API respond?
2. **Readiness** (partially exists): Is the session authenticated? Is the code version correct? Is the data fresh?
3. **Correctness** (mostly missing): Does the output match expected hash versions? Are market counts in expected ranges? Is the resolver producing expected column values?

The Phase 10 hash version monitor built on 2026-05-18 is an example of a correctness check — it verifies that the output (pick hash format) matches the expected code version. Similar correctness checks for session state (verify `aaat` cookie presence after Chrome "already running" detection) and Chrome spawning (verify CDP `/json` responds after AdsPower API success) would catch the other two bugs.

## Evidence

All three bugs were discovered in a single day (2026-05-18) during routine health checks and debugging:

- **09:30**: NBA Chrome phantom-active since May 15 restart; AdsPower reported active on port, no Chrome process existed
- **09:30**: v3 startup detected Chrome "already running" since May 15 restart, skipped login check, sat idle for 3+ days
- **12:04**: Legacy `value-betting.service` started 8 min before position-model commit, wrote v1 picks for 3+ days alongside v3's v2 picks

The clustering suggests that a systematic health audit (rather than symptom-driven investigation) would have caught all three sooner. The Phase 10 monitor was built as a permanent detection mechanism for the import leak; analogous monitors for the other two bugs are recommended.

## Related Concepts

- [[concepts/adspower-wayland-gui-session-recovery]] - AdsPower API reporting phantom-active state when Chrome never spawned
- [[concepts/v3-startup-login-verification-gap]] - v3 assuming Chrome running = authenticated session
- [[concepts/stale-in-memory-import-writer-leak]] - Running process using old in-memory code despite new code on disk
- [[concepts/worker-status-observability]] - The established pattern of false-healthy status reporting; phantom liveness is the extreme variant
- [[concepts/bet365-session-login-detection-gap]] - Login detection gap during active scraping; the v3 startup gap is the startup-time variant
- [[connections/operational-compound-failures]] - Phantom liveness bugs compound with missing monitoring to create extended invisible degradation

## Sources

- [[daily/lcash/2026-05-18.md]] - Three phantom liveness bugs discovered in single day: AdsPower phantom-active (Session 09:30), v3 stale session (Session 09:30), stale in-memory import (Session 12:04); each passed liveness checks while producing zero useful output or wrong output; Phase 10 monitor built for import leak detection
