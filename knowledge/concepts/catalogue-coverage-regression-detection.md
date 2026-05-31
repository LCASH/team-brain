---
title: "Catalogue-Coverage-Based Regression Detection"
aliases: [catalogue-coverage, coverage-regression, tiered-fetch-alerting, rolling-max-baseline]
tags: [superwin, monitoring, alerting, architecture, tiered-fetch]
sources:
  - "daily/lcash/2026-05-30.md"
created: 2026-05-30
updated: 2026-05-30
---

# Catalogue-Coverage-Based Regression Detection

On 2026-05-30, the SuperWin scanner's per-cycle regression detection was replaced with catalogue-coverage-based checks for tiered-fetch bookies (betr, boostbet, tab). The old approach compared `valid_count` per poll cycle, but tiered-fetch adapters rotate hot/warm/cold race subsets each cycle, producing wildly different valid counts that triggered ~100 false alerts per day. The new approach measures how many catalogue races the bookie has data on — a stable, semantically correct metric that reduced alerts from 100 to 1 (the only remaining alert was a legitimate edge-resolver backlog).

## Key Points

- **Per-cycle `valid_count` is wrong for tiered-fetch bookies** — each cycle fetches a different subset (hot/warm/cold rotation), so valid_count swings even when actual odds in `/api/v1/odds` don't fluctuate
- **Catalogue coverage is the correct metric**: how many of the day's known races does this bookie have any data for? Coverage is stable because it's cumulative ("once added, never removed until day rollover")
- **Rolling MAX baseline** prevents transient ingest-ordering blips from lowering the threshold and triggering false positives — the baseline only increases, never decreases within a day
- **Alerts dropped from ~100 to 1** after the refactor — the single remaining alert was a legitimate issue (edge-resolver backlog), making the dashboard actionable
- **Limitation: service restart wipes the catalogue** — no persistence/replay mechanism exists, so coverage drops to 0 on restart and rebuilds organically from incoming data
- **`BookieStatus.race_count`** also swings cosmetically for tiered-fetch adapters on the dashboard sidebar, even though actual odds are stable — flagged as a separate UX fix

## Details

### The Tiered-Fetch Problem

SuperWin's tiered-fetch architecture divides races into tiers based on time-to-jump: hot (≤60min, fetched every ~3s), warm (≤4h, ~9s), and cold (>4h, ~45s). Each poll cycle only fetches one tier's worth of races, rotating through them. This means `valid_count` — the number of markets with fresh data in a given cycle — legitimately varies by 3-10x depending on which tier was just fetched.

The old regression detection compared `valid_count` against a baseline, firing alerts when the count dropped significantly. For non-tiered bookies (single-fetch-all pattern), this works well: a drop in valid_count genuinely signals data loss. For tiered bookies, every cold-tier cycle looks like a 70% regression relative to a hot-tier baseline — pure noise.

### Catalogue Coverage as the Solution

The catalogue tracks all races discovered during the current trading day. Its key property is monotonic growth: once a race is added (via discovery or WS subscription), it stays until the day rolls over. This makes catalogue coverage a stable metric: "this bookie has data on 478 of 578 catalogue races" doesn't swing based on which tier was just fetched.

The rolling MAX baseline ensures the threshold only ratchets upward. If a bookie reaches 478/578 coverage at 11am, it can't fall below that baseline (a drop would indicate genuine data loss). Transient ordering effects — where a race appears in the catalogue before the bookie's first fetch — can't lower the bar.

### Dashboard Noise

A secondary observation: `BookieStatus.race_count` on the dashboard sidebar displays per-cycle counts, not catalogue coverage. For tiered-fetch bookies, this number bounces between ~100 (cold cycle) and ~500 (hot cycle), creating visual noise that suggests instability. The actual odds served via `/api/v1/odds` are stable throughout — the sidebar count is cosmetically misleading. This was flagged as a separate follow-up fix (show catalogue coverage instead of cycle count).

### Restart Gap

The catalogue is in-memory only — a service restart resets it to empty. There is no persistence or replay mechanism. After restart, coverage rebuilds organically as each bookie's discovery and fetch cycles run, typically reaching full coverage within 10-15 minutes. During this window, coverage-based alerts are suppressed (the baseline starts at 0 and only ratchets up). Investigating persistence/replay to eliminate this gap was flagged as a follow-up action item.

## Related Concepts

- [[concepts/tab-cold-start-akamai-discovery-thrashing]] - TAB's tiered-fetch architecture is the primary driver for this change; the COLD_CHUNK=80 backfill pattern creates exactly the per-cycle variance that broke the old detection
- [[concepts/worker-status-observability]] - Prior work replacing hardcoded "streaming" status with actual states; catalogue coverage is the next evolution of bookie health observability
- [[concepts/tab-global-ws-rotation-pattern]] - TAB's WS rotation means the real odds pipeline is stable even when per-cycle counts swing — coverage-based detection correctly captures this
- [[concepts/value-betting-operational-assessment]] - Alert noise masking real issues is a recurring operational theme; this refactor made the dashboard actionable for the first time

## Sources

- [[daily/lcash/2026-05-30.md]] - Session 11:58: Replaced per-cycle regression detection with catalogue-coverage-based checks; tiered-fetch bookies (betr/boostbet/tab) rotate hot/warm/cold subsets causing per-cycle valid_count to swing wildly; catalogue coverage is stable and semantically correct; rolling MAX baseline prevents false-positive threshold lowering; alerts dropped from ~100 to 1; BookieStatus.race_count swings cosmetically; catalogue not persisted across restarts; flagged persistence/replay and sidebar fix as follow-ups
