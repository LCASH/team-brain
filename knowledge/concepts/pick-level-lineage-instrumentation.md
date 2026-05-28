---
title: "Pick-Level Lineage Instrumentation"
aliases: [lineage-columns, per-pick-health-metadata, system-health-per-pick, bookie-status-at-detect, scanner-uptime-tracking]
tags: [superwin, racing, observability, data-quality, architecture]
sources:
  - "daily/lcash/2026-05-28.md"
created: 2026-05-28
updated: 2026-05-28
---

# Pick-Level Lineage Instrumentation

On 2026-05-28, lcash added 5 lineage columns to the SuperWin `superwin_edge_picks` table that capture per-pick system health metadata at detection time: `scanner_uptime_secs`, `bookie_fresh_secs`, `betfair_fresh_secs`, `bookie_status_at_detect`, and `service_restarts_30m_at_detect`. This forward-only instrumentation enables correlation between system stability and pick quality — answering "were profitable picks generated during stable or unstable scanner periods?" without requiring retroactive analysis of log files.

## Key Points

- **5 lineage columns**: `scanner_uptime_secs` (process uptime), `bookie_fresh_secs` (per-bookie data freshness), `betfair_fresh_secs` (Betfair lay freshness), `bookie_status_at_detect` (adapter state), `service_restarts_30m_at_detect` (crash frequency)
- **Per-bookie, not system-wide**: `bookie_status_at_detect` and `bookie_fresh_secs` are specific to the bookie on each pick — different picks from different bookies capture different health snapshots
- **Forward-only**: 18,620 historical picks have NULL lineage and cannot be backfilled — lineage depends on runtime state not available from stored data
- **Wrapped in try/except**: Lineage capture failures never break pick persistence — the `sys_ctx` wrapper is purely observational
- **First 30s post-deploy shows NULL `bookie_status_at_detect`** because `_state.get_bookie_status()` hasn't populated yet — harmless startup artifact

## Details

### Motivation

The SuperWin scanner experienced recurring SIGABRT crashes (see [[concepts/superwin-process-isolation-reliability]]) and bookie adapter stalls that affected pick quality. Without per-pick lineage, the only way to assess whether a period of poor ROI was caused by bad luck or system instability was to cross-reference log timestamps against Supabase pick timestamps — a manual, error-prone process. The lineage columns embed the system health context directly into each pick row, making stability-vs-performance correlation a simple SQL query.

### Column Definitions

| Column | Type | Source | Purpose |
|--------|------|--------|---------|
| `scanner_uptime_secs` | float | `time.time() - process_start` | Detects picks from unstable early-restart periods |
| `bookie_fresh_secs` | float | Adapter's `last_fetch_at` | Per-bookie odds staleness at pick creation |
| `betfair_fresh_secs` | float | Betfair adapter's `last_fetch_at` | Fair-value reference staleness |
| `bookie_status_at_detect` | text | `_state.get_bookie_status(bookie)` | Adapter lifecycle state (streaming/fetching/idle/error) |
| `service_restarts_30m_at_detect` | int | Restart counter from status endpoint | Crash-loop frequency indicator |

### Freshness Measurement Gap

A `betfair_fresh_secs=50s` outlier was observed while `tab` showed `fetching` state — suggesting a discrepancy between the freshness gate (which uses per-runner `BookieOdds.updated_at` for EV calculation) and the lineage measurement (which uses adapter-wide `last_fetch_at`). The freshness gate is per-runner granularity; the lineage is per-adapter granularity. A pick could pass the freshness gate (specific runner's odds are fresh) while the lineage shows the adapter as a whole hasn't completed a full cycle recently. This is a known limitation, not a bug — the lineage provides an upper-bound staleness estimate.

### Forward-Only Limitation

The user correctly identified that lineage is forward-only and doesn't help analyze existing data. For retrospective analysis, the existing trail-derived dimensions (`ev_trail`, `detection_count`, `peak_ev_pct`, `minutes_to_jump`) remain the primary tools. Lineage complements these by adding the system-health dimension that trail data cannot capture — a pick's EV trajectory might look healthy while the scanner was in a crash loop, producing that pick from stale cached data.

### Query Pattern

The intended query pattern for stable-vs-unstable ROI comparison:

```sql
SELECT 
  CASE WHEN scanner_uptime_secs > 300 AND service_restarts_30m_at_detect = 0 
       THEN 'stable' ELSE 'unstable' END AS stability,
  COUNT(*), AVG(pnl), SUM(pnl)
FROM superwin_edge_picks
WHERE scanner_uptime_secs IS NOT NULL  -- excludes 18,620 historical NULLs
  AND result IS NOT NULL
GROUP BY 1
```

The initial ROI comparison query was flawed — NULL historical picks were mis-classified as "unstable" due to a bad CASE WHEN. The user caught this immediately, reinforcing that NULL lineage picks must be excluded rather than categorized.

## Related Concepts

- [[concepts/superwin-process-isolation-reliability]] - The SIGABRT crash pattern that motivated lineage — crashes kill all 8 bookies, lineage captures whether picks came from stable or post-restart periods
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal that lineage columns are added to; insert-only pattern preserved
- [[concepts/worker-status-observability]] - The 4-state worker status system that `bookie_status_at_detect` captures per-pick; lineage is the per-pick complement to the aggregate health endpoint
- [[concepts/superwin-execution-gap-price-band-discipline]] - Lineage could reveal whether poor actual ROI correlates with unstable scanner periods or pure price-band non-compliance

## Sources

- [[daily/lcash/2026-05-28.md]] - 5 lineage columns deployed; per-bookie health capture; 18,620 historical NULLs; try/except wrapper; initial ROI query had NULL mis-classification caught by user; betfair_fresh_secs=50s outlier from gate-vs-lineage measurement discrepancy; 4h10m best uptime run (Session 00:03)

