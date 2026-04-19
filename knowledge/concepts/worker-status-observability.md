---
title: "Worker Status Observability"
aliases: [worker-state-reporting, status-observability, idle-no-fixtures]
tags: [value-betting, observability, operations, monitoring]
sources:
  - "daily/lcash/2026-04-13.md"
  - "daily/lcash/2026-04-19.md"
created: 2026-04-13
updated: 2026-04-19
---

# Worker Status Observability

A fix to the value betting scanner's worker status reporting where the `bet365_mlb_game` worker was hardcoded to report "streaming" regardless of its actual state. Replaced with actual state reporting (`idle_no_fixtures` / `streaming` / `stale` / `error`) so health checks can distinguish between "working but no data available" and "broken." This is a direct response to the silent failure anti-pattern identified in the operational assessment.

## Key Points

- The bet365_mlb_game worker reported hardcoded "streaming" even when no fixtures existed — making it impossible to distinguish idle-but-healthy from broken
- Replaced with four actual states: `idle_no_fixtures` (no games available), `streaming` (actively processing), `stale` (data age exceeds threshold), `error` (scraper failure)
- The `main.py` orchestrator was also overwriting worker status with "streaming" — fixed to preserve the worker's self-reported status
- bet365 publishes MLB pre-game fixtures 6-12 hours before game time, so `idle_no_fixtures` is expected during off-hours
- Deployed to mini PC as commit `88e85c8`, 2 files changed: `scraper/bet365_mlb_game.py` and `main.py`

## Details

### The Problem

During a system health check on 2026-04-13, the bet365_mlb_game worker showed "streaming, 0 odds" — appearing to be broken. Investigation revealed the scraper was functioning correctly; there were simply no bet365 pre-game MLB fixtures available because games were 15-21 hours away. The worker was reporting "streaming" because its status was hardcoded, not derived from actual state. This false signal wastes debugging time and erodes trust in the health check system: operators learn to ignore "streaming" status because it doesn't actually mean anything.

This is a milder variant of the silent failure anti-pattern documented in [[concepts/silent-worker-authentication-failure]]. Where silent auth failures produce zero signal, hardcoded status produces a misleading signal — arguably worse in some ways, because it actively communicates that everything is fine when the actual state is unknown.

### The Fix

The fix introduces four distinct states that the worker self-reports based on its actual operational condition:

- **`idle_no_fixtures`** — the worker is running, connected, and polling, but the upstream source (bet365) has no fixtures for the sport. This is expected behavior during off-hours. For MLB, bet365 typically publishes player props ~2 hours before first pitch.
- **`streaming`** — the worker is actively receiving and processing odds data. This is the only state where "0 odds" would indicate a problem.
- **`stale`** — the worker has data but it exceeds a freshness threshold. This signals degradation without necessarily indicating a crash.
- **`error`** — the worker has encountered an unrecoverable error.

A second change was required in `main.py`: the orchestrator was overwriting whatever status the worker set with a hardcoded "streaming" during its status aggregation loop. This meant even if the worker correctly reported `idle_no_fixtures`, the dashboard would show "streaming." The fix preserves the worker's self-reported status rather than overwriting it.

### Broader Pattern

This fix exemplifies a general observability principle: status should reflect actual state, not intended state. A worker that reports "streaming" because that's what it's supposed to be doing is useless for diagnosis. A worker that reports "idle_no_fixtures" tells the operator exactly what's happening and why, enabling them to distinguish expected idle periods from failures without SSH-ing into the machine.

### Game Scraper Stale Data Despite "Streaming" Status (2026-04-19)

On 2026-04-19, a more severe variant of the status observability problem was discovered in the Bet365 game scraper. The scraper reported `status=streaming` and `age=1s` while its data was 3.7 hours old. Unlike the original `bet365_mlb_game` issue (where the state was genuinely idle), this case involved a Chrome crash that left the scraper returning stale cached data — the process was technically "streaming" (executing its refresh loop), but Chrome was dead and every refresh silently returned the last cached page.

The four-state system (`idle_no_fixtures`, `streaming`, `stale`, `error`) correctly reports the process's operational state but does not validate data freshness. The scraper was in the `streaming` state because its code was running — it just wasn't producing fresh data. The `age=1s` was based on when the cache was last read, not when data was last captured from bet365.

The diagnostic indicator was the `0.0ms` scrape time: a real Chrome page refresh takes at minimum 500ms. A zero-millisecond "scrape" means the code returned cached data without touching Chrome at all. This metric existed in logs but was not surfaced in health checks.

This discovery suggests a fifth state or an additional health dimension: a `data_age` metric that measures the actual freshness of the data being served, independent of process state. A scraper can be `streaming` (process healthy, executing its loop) while simultaneously serving hours-old data. See [[concepts/game-scraper-chrome-crash-recovery]] for the auto-recovery fix.

## Related Concepts

- [[concepts/silent-worker-authentication-failure]] - The more severe variant: workers with zero output instead of misleading output
- [[concepts/value-betting-operational-assessment]] - Weakness #2 (no monitoring) and #4 (silent failures) both addressed by this fix
- [[connections/operational-compound-failures]] - Better status reporting breaks the "silent failures" link in the compound failure chain
- [[concepts/self-evolving-operational-skill]] - The /checkup skill that consumes these status values
- [[concepts/game-scraper-chrome-crash-recovery]] - The Chrome crash auto-recovery fix that addresses the "streaming but stale" failure mode

## Sources

- [[daily/lcash/2026-04-13.md]] - bet365_mlb_game reporting hardcoded "streaming" when idle; replaced with actual states (idle_no_fixtures/streaming/stale/error); main.py was overwriting worker status; deployed as commit 88e85c8; bet365 publishes MLB fixtures 6-12h before game time (Session 16:31)
- [[daily/lcash/2026-04-19.md]] - Game scraper (Bet365 2.0) reported `status=streaming` and `age=1s` while data was 3.7 hours old; the four-state system correctly reports the process state but doesn't validate data freshness; `0.0ms` scrape time is a diagnostic smoking gun for stale cached data (real Chrome refresh takes 500ms+); status must verify data freshness not just process liveness. See [[concepts/game-scraper-chrome-crash-recovery]] for the auto-recovery fix (Sessions 14:57, 20:07)
