---
title: "Worker Status Observability"
aliases: [worker-state-reporting, status-observability, idle-no-fixtures]
tags: [value-betting, observability, operations, monitoring]
sources:
  - "daily/lcash/2026-04-13.md"
created: 2026-04-13
updated: 2026-04-15
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

## Related Concepts

- [[concepts/silent-worker-authentication-failure]] - The more severe variant: workers with zero output instead of misleading output
- [[concepts/value-betting-operational-assessment]] - Weakness #2 (no monitoring) and #4 (silent failures) both addressed by this fix
- [[connections/operational-compound-failures]] - Better status reporting breaks the "silent failures" link in the compound failure chain
- [[concepts/self-evolving-operational-skill]] - The /checkup skill that consumes these status values

## Sources

- [[daily/lcash/2026-04-13.md]] - bet365_mlb_game reporting hardcoded "streaming" when idle; replaced with actual states (idle_no_fixtures/streaming/stale/error); main.py was overwriting worker status; deployed as commit 88e85c8; bet365 publishes MLB fixtures 6-12h before game time (Session 16:31)
