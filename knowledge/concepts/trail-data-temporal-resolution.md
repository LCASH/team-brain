---
title: "Trail Data Temporal Resolution"
aliases: [trail-sparsity, pre-fix-trail-data, trail-sampling-interval]
tags: [data-quality, backtesting, value-betting, methodology]
sources:
  - "daily/lcash/2026-04-13.md"
created: 2026-04-13
updated: 2026-04-13
---

# Trail Data Temporal Resolution

Trail entries in the value betting scanner captured before the push cycle fix (~2026-04-13 07:30 UTC) have wider sampling intervals — real observations at ~55-second intervals rather than the sub-2-second intervals achieved after the fix. The critical framing is that these data points are **sparse, not corrupt**: each captured value is genuine, but there are fewer of them per unit time. Most backtesting use cases (CLV, win rate, ROI) are unaffected; only sub-minute tick-level odds movement analysis is degraded.

## Key Points

- Pre-fix trails were captured at ~55s intervals due to the push worker bottleneck (see [[concepts/server-side-snapshot-cache]]); post-fix trails are captured at ~2s intervals
- Each pre-fix data point is a real odds observation — the `captured_at` timestamp reflects when the slow push arrived at the VPS, not when the scraper observed the odds
- Aggregate backtesting (CLV, win rate, ROI by EV bucket) is unaffected — these metrics use scalar fields from the pick record, not tick-level trails
- Sub-minute odds movement reconstruction is not possible from pre-fix data — you cannot determine whether a line moved gradually or jumped between two 55s-apart captures
- The sparsity is sport-agnostic and side-agnostic (not specific to Overs vs Unders), but different sharp coverage patterns across line sizes could create differential effects
- Recommended backtest query filter for clean data: `created_at >= '2026-04-13'`, `sharp_count >= 2`, `triggered_ev BETWEEN 1 AND 30`

## Details

### The Push Cycle Problem

The value betting scanner's push worker aggregates odds from sport servers on the mini PC and pushes them to the VPS, where the tracker writes trail entries. Before the snapshot cache fix, the push cycle took 55 seconds end-to-end — dominated by server-side JSON serialization of large odds payloads (see [[concepts/server-side-snapshot-cache]]). The tracker's sharp freshness cutoff is 30 seconds, meaning that by the time odds arrived at the VPS after a 55-second cycle, many sharp comparisons were already stale. The result was intermittent trail capture: some cycles produced trail entries (when enough sharps were still fresh), others were silently skipped.

This created a selection bias: trail entries were more likely to be captured during periods when sharp odds were stable (so they remained "fresh" through the long push cycle) and less likely during volatile periods (when sharp odds changed before the push arrived). For aggregate analysis this bias is minor, but for time-series reconstruction it means the densest data is from the least interesting periods.

### What's Usable and What's Not

**Usable (unaffected by sparsity):**
- Win rate by EV bucket — uses `triggered_ev` and `outcome` fields on the pick record, not trails
- ROI calculations — uses `triggered_odds` and `outcome`, again pick-level
- CLV (closing line value) — uses the pick's triggered line vs. closing line, both scalar
- Aggregate statistics (count by sport, by prop type, by theory) — pick metadata, not trails

**Degraded (requires post-fix data):**
- Sub-minute odds movement charts — cannot reconstruct continuous line movement
- Time-to-close analysis (how long before game time was the pick triggered) — `captured_at` reflects push arrival, not observation time
- Odds volatility analysis — too few data points per market to calculate meaningful volatility metrics

### The `captured_at` Subtlety

A non-obvious issue: the `captured_at` timestamp in trail entries records when the VPS received the push payload, not when the scraper on the mini PC observed the odds. With a 55-second cycle, these can differ significantly. Post-fix, the difference is at most ~2 seconds, making it negligible. Pre-fix, any analysis that depends on precise timing (e.g., "how far before game time was this line available?") should account for up to 55 seconds of systematic delay.

### Data Cleanup Actions

On 2026-04-13, lcash performed several data integrity operations:
- Deleted 393 picks with `triggered_ev` 50-100% (clearly invalid from line mismatches — see [[concepts/alt-line-mismatch-poisoned-picks]])
- Cleaned 30,507 orphaned `trail_entries` where `pick_id` no longer existed in `nba_tracked_picks` (from both the 393 deletion and an earlier 1,218 deletion)
- Left `sharp_count = 1` picks in the database — to be filtered at query time, not deleted

For backtesting, the recommended join is `trail_entries` joined to `nba_tracked_picks` (not picks alone) for time-series analysis, with the filter `created_at >= '2026-04-13'` to use only post-fix data.

## Related Concepts

- [[concepts/server-side-snapshot-cache]] - The fix that reduced push cycle from 55s to 1.9s, restoring trail temporal resolution
- [[connections/push-latency-trail-quality-cascade]] - How the serialization bottleneck cascaded into trail quality
- [[concepts/alt-line-mismatch-poisoned-picks]] - The separate data quality issue (poisoned EV values) that also required cleanup
- [[concepts/value-betting-operational-assessment]] - The broader operational context in which trail quality was assessed

## Sources

- [[daily/lcash/2026-04-13.md]] - Trail data declared sparse-not-corrupt; `captured_at` reflects push arrival, not observation time; 393 picks + 30,507 orphan trails cleaned; corrected framing from "corrupted" to "lower temporal resolution"; recommended backtest filters (Sessions 08:50, 09:32)
