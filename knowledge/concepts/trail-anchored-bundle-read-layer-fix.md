---
title: "Trail Anchored Bundle Read-Layer Fix"
aliases: [anchored-bundle, trail-staleness-leak, soft-anchored-join, two-stream-trail-model, temporal-mismatch-fix]
tags: [value-betting, trail-data, architecture, data-quality, methodology]
sources:
  - "daily/lcash/2026-05-15.md"
created: 2026-05-15
updated: 2026-05-15
---

# Trail Anchored Bundle Read-Layer Fix

The value betting scanner's trail system uses a two-stream independent recording model: soft trail rows and sharp trail rows are written independently whenever their respective odds change. On 2026-05-15, lcash identified a **staleness leak in the read layer**: when downstream consumers (resolver, replay engine, CLV computation) reconstruct "soft + sharp at time T" by independently querying the latest-before-T from each stream, the results can be temporally mismatched — e.g., a soft row from 15 minutes ago paired with a fresh sharp row. The fix is a read-layer `anchored_bundle()` helper that enforces soft-anchored temporal alignment: find the latest soft row ≤ T, then find the latest sharp row ≤ that soft row's `captured_at`.

## Key Points

- **Storage is correct** — the two-stream change-triggered model exactly captures when soft and sharp odds changed; no storage redesign needed
- **Bug is read-layer only** — naive "latest row ≤ T" queries on each stream independently create temporal mismatch between soft and sharp snapshots
- **`anchored_bundle(pick_id, at)`** enforces the rule: find latest soft row ≤ T, then find latest sharp row ≤ that soft row's `captured_at` — guarantees temporal consistency
- **Change-only storage has a powerful property**: between two consecutive rows, state is guaranteed unchanged — "latest row ≤ T" queries are exact, not approximate
- **Sharp stream preserved independently** for sharp-pattern analysis (drift, steam, fade) — orthogonal to soft-anchored queries for backtesting and CLV
- **Fallback for missing soft rows**: use `opening_odds` from picks table at `triggered_at` as the implicit first soft row
- The tracker cadence is **event-driven (1-5s cycles)** via `change_event.wait()` with 5s heartbeat — not the 30s-polled model previously assumed in documentation

## Details

### The Staleness Leak

The trail system writes soft and sharp rows independently on change detection. When soft book odds for a pick change by >0.001, a soft trail row is written with the current odds and `captured_at` timestamp. When any sharp book's odds hash changes, a sharp trail row is written. These streams operate at different cadences — sharp trails update ~7x more frequently than soft (see [[concepts/trail-change-detection-architecture]]).

The problem manifests at read time. When the resolver needs to compute closing-line value, it queries "what were the soft odds and sharp odds at game start time T?" The naive approach queries each stream independently:

```
soft_close = latest soft_trail row WHERE captured_at ≤ T
sharp_close = latest sharp_trail row WHERE captured_at ≤ T
```

If the soft book's last change was 15 minutes before T and the sharp books changed 2 seconds before T, the resolver pairs 15-minute-old soft odds with 2-second-old sharp odds. The sharp odds at the 15-minute-ago mark may have been significantly different from the 2-second-ago mark — the devigged true probability computed from the 2-second sharp snapshot does not represent the market state when the soft odds were last observed.

### The Anchored Bundle Solution

The `anchored_bundle(pick_id, at)` helper enforces temporal consistency:

1. Find the latest soft trail row with `captured_at ≤ T` → call this `soft_snap`
2. Find the latest sharp trail row with `captured_at ≤ soft_snap.captured_at` → call this `sharp_snap`
3. Return `(soft_snap, sharp_snap)` as a temporally aligned pair

This guarantees that the sharp snapshot reflects the market state at or before the soft observation — never after. The devigged true probability computed from `sharp_snap` is the correct reference for evaluating `soft_snap`'s odds.

The change-only recording model enables this guarantee: between two consecutive soft rows, the soft odds are unchanged (guaranteed by the recording threshold). Between two consecutive sharp rows, the sharp consensus is unchanged. Finding the "latest row ≤ T" returns the exact state at time T, not an approximation.

### Impact on Existing Consumers

Three consumers need the anchored bundle wired in:

| Consumer | Current Behavior | After Fix |
|----------|-----------------|-----------|
| **Resolver closing-line** | Independent latest-before-T queries | Anchored bundle at game_start |
| **Replay engine** | Per-soft-row EV trajectory | Anchored bundle per soft snapshot |
| **CLV computation** | Sharp close independent of soft close | Anchored bundle at closing timestamp |

The replay engine benefits most: instead of computing EV at each soft trail entry using potentially mismatched sharp data, each soft entry gets its own sharp anchor. This produces a per-soft-row EV trajectory that accurately reflects the true opportunity available at each moment.

### Sharp Stream Independence

The sharp trail stream is preserved independently for a different class of analysis: sharp-pattern detection. Questions like "did Pinnacle steam this line?" (steady movement in one direction), "was there a sharp fade?" (reversal), or "how fast did the sharp consensus form?" require the full sharp trail without soft anchoring. These analyses are orthogonal to backtesting/CLV, which requires soft-anchored alignment.

### Quantification from Phase 8 Audit

The 9-phase tracker audit (Session 15:36) quantified the staleness leak: NBA soft trail match rate was only 52.6% (target 99%), and sharp-lag outliers reached 597s for NBA and 1,149s for MLB. These wide windows confirm that the temporal mismatch between independently-queried streams can be significant — minutes, not seconds — for illiquid props or during periods where soft books don't move but sharps actively reprice.

### Documentation Correction

A significant correction was made to the tracker documentation during the same session: the tracker cadence is **event-driven** (`change_event.wait()` with `MIN_CYCLE_INTERVAL = 1.0s` and 5s heartbeat timeout), NOT polled at 30s intervals as previously diagrammed. The event-driven design means trails are written within seconds of actual odds changes, making the temporal precision of the anchored bundle meaningful — if the tracker polled every 30s, a 2-second sharp mismatch would be noise within the polling granularity.

## Related Concepts

- [[concepts/trail-change-detection-architecture]] - The two-stream change-only recording model that the anchored bundle reads from; sharp trails 7x denser than soft, creating the asymmetry that the bundle resolves
- [[concepts/trail-stats-precomputed-columns]] - Pre-computed trail stats (peak_ev, closing_true_odds) computed by the resolver at resolution time; the anchored bundle improves accuracy of these computations
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV is the primary validation metric; the anchored bundle ensures CLV computation uses temporally consistent sharp/soft pairs
- [[concepts/tracker-pipeline-7-phase-audit]] - Phase 8 (bundle alignment) quantified the mismatch: NBA 52.6% match rate, sharp-lag outliers up to 1,149s for MLB
- [[concepts/per-soft-book-temporal-lineage]] - Per-book temporal lineage ensures soft `captured_at` reflects actual observation time (not push-cycle heartbeat); the anchored bundle consumes these honest timestamps

## Sources

- [[daily/lcash/2026-05-15.md]] - Identified staleness leak in two-stream trail join: naive latest-before-T queries create temporal mismatch between soft and sharp; storage correct (change-only model), bug is read-layer only; `anchored_bundle(pick_id, at)` helper designed; tracker cadence corrected to event-driven 1-5s (not 30s polled); sharp stream preserved for independent analysis; finding documented in `brain/findings/2026-05-14-tracker-anchored-bundle-design.md` (Session 14:58)
