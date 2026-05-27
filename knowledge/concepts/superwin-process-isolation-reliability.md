---
title: "SuperWin Process Isolation Reliability Architecture"
aliases: [process-isolation, sigabrt-resilience, catalogue-persistence, subprocess-supervisor, crash-containment]
tags: [superwin, architecture, reliability, operations, deployment]
sources:
  - "daily/lcash/2026-05-27.md"
created: 2026-05-27
updated: 2026-05-27
---

# SuperWin Process Isolation Reliability Architecture

On 2026-05-27, recurring SIGABRT crashes in the SuperWin scanner's monolithic Python process (all 8 bookie adapters in one process) motivated an architectural shift from crash investigation to crash containment. Native C extensions (`curl_cffi`, `aiohttp._websocket`, `awscrt`, Playwright) call `abort()` on internal errors, which kills the entire process — taking all 8 bookies offline. The `_guarded_task` wrapper catches Python exceptions but cannot catch native SIGABRT. Four reliability fixes were designed in priority order: (1) catalogue persistence to disk, (2) sports polling as own subprocess, (3) per-bookie subprocess supervisor, (4) restart-storm alerting.

## Key Points

- **Single-process architecture**: All 8 bookie adapters share one Python process; one C extension `abort()` kills everything — 8 bookies offline simultaneously
- **`_guarded_task` gap**: Catches Python exceptions but CANNOT catch native SIGABRT — fundamental gap in the supervisor model
- **89% crash correlation with BonusBank sync was NOT causal** — fixing it didn't stop crashes; likely multiple C extensions trigger the same failure class
- **Correct response**: Don't find the one bug, make crashes **contained** (process isolation) and **invisible** (cache persistence)
- **4-fix deployment order**: #1 catalogue persistence + #4 restart-storm alert today → #2 sports polling subprocess tomorrow → #3 per-bookie supervisor rolling this week
- **`systemd-coredump` installed** — next crash will yield a real C-level stack trace (vs previous Python-level-only diagnostics)

## Details

### The Monolithic Process Problem

The SuperWin racing scanner runs all bookie adapters (TAB, TabTouch, Betfair, Betr, BoostBet, Neds, Pointsbet, Sportsbet, bet365) plus the edge scanner, settlement resolver, and sports polling in a single Python process. This architecture was expedient for development but creates a catastrophic blast radius: when any C extension calls `abort()`, the OS delivers SIGABRT to the process, which terminates immediately without running Python's exception handlers.

The crash frequency was significant — the process was crashing approximately every 8 minutes during the worst period, with `systemd` auto-restart masking the failures. Each restart cleared all in-memory state: the race catalogue, open WS connections, pending settlements, and cached odds — requiring 30-60 seconds of warmup before data flowed again.

### Why Crash Investigation Failed

Initial investigation followed the 89% correlation between BonusBank Sports store updates and SIGABRT crashes. The sync mechanism was converted from async to sync `curl_cffi` and the fix appeared to work. However, crashes continued at the same cadence (next crash at 04:05:15 with identical signature), and the pre-crash "Sports store updated" log line was absent — breaking the correlation.

This demonstrates a general diagnostic principle: when a fix doesn't resolve a SIGABRT, the cause is likely not a single C extension but a failure class shared across multiple extensions. `curl_cffi`, `aiohttp._websocket` (used by Betfair streaming), `awscrt` (used by TabTouch MQTT via Cognito), and Playwright all contain native code that can trigger `abort()`.

### The Four-Fix Architecture

**Fix 1 — Catalogue Persistence (~50 lines):** Snapshot the race catalogue to `.cache/catalogue.json` every 30 seconds. On restart, restore from disk instead of cold-discovering all races. This reduces restart impact from 30-60s warmup to <5s — the crash becomes nearly invisible to operators and edge detection.

**Fix 2 — Sports Polling Subprocess:** Extract the BonusBank/sports polling loop into its own `superwin-sports.service` systemd unit. This removes `curl_cffi` HTTP calls (the most crash-correlated C extension) from the main process blast radius. If sports polling crashes, racing continues unaffected.

**Fix 3 — Per-Bookie Subprocess Supervisor:** The most impactful change. Each bookie adapter runs in its own subprocess managed by a central supervisor (`app/supervisor.py`). Communication uses IPC (pipes or shared memory). A crash in the Betfair adapter's `aiohttp._websocket` kills only the Betfair subprocess — TAB, Sportsbet, and all other bookies continue serving odds. The supervisor auto-restarts crashed workers with exponential backoff.

**Fix 4 — Restart-Storm Alert:** A `/api/v1/status` endpoint tracking restart count per time window, plus a dashboard red banner when restart frequency exceeds a threshold. This makes crash-loop visibility immediate rather than requiring log analysis.

### Deployment Strategy

Rolling deployment, one fix at a time with soak periods:
- Day 1: Fix #1 (catalogue persistence) + Fix #4 (restart alert) — immediate crash resilience + visibility
- Day 2: Fix #2 (sports polling subprocess) — removes most crash-correlated code from main process
- Week: Fix #3 (per-bookie subprocess) — one bookie at a time, soak each for 24h before the next

## Related Concepts

- [[concepts/superwin-dual-model-shim-deployment-crash]] - A prior crash from stale shim missing `bsp_near` field; process isolation would have contained this to Betfair only
- [[connections/permanent-blacklist-no-expiry-anti-pattern]] - In-memory state loss on crash is a related problem; catalogue persistence addresses it for the race catalogue
- [[concepts/v3-scanner-centralized-architecture]] - The value betting scanner's V3 architecture chose monolithic but event-driven; SuperWin is now evolving toward subprocess isolation
- [[concepts/unified-odds-aggregator-pipeline]] - The VB scanner's aggregator solved a similar problem (per-sport push workers replaced by single aggregator); SuperWin is going the opposite direction (monolith → per-bookie subprocesses) because the failure mode is different (native crashes vs Python-level failures)

## Sources

- [[daily/lcash/2026-05-27.md]] - Recurring SIGABRT crashes every ~8 min; _guarded_task catches Python but not native; 89% BonusBank correlation was not causal; 4-fix architecture designed: catalogue persistence, sports subprocess, per-bookie supervisor, restart-storm alert; deployment order locked; systemd-coredump installed for next crash (Sessions 14:08, 14:18)

```
