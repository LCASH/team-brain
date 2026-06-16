---
title: "Trail Depth Regression from Phase B Iteration Scope Narrowing"
aliases: [trail-depth-regression, phase-b-scope-narrowing, trail-depth-vs-coverage, phase-b2-tick-driven-fix]
tags: [value-betting, trail-data, bug, architecture, regression, tracker]
sources:
  - "daily/lcash/2026-06-03.md"
created: 2026-06-03
updated: 2026-06-03
---

# Trail Depth Regression from Phase B Iteration Scope Narrowing

On 2026-06-03, lcash discovered that trail *coverage* was healthy (99.25% of recent picks have trails) but trail *depth* had collapsed: median sharp trail rows per pick dropped from 61 (6-10 days ago) to 1 (today). Root cause: Phase B (the loop adding trail rows to existing picks) only fired meaningfully on the first cycle after an Eve restart, then went silent — subsequent cycles wrote 0 updates to existing picks. The per-cycle `books` dict didn't retain soft-book entries for already-tracked picks, so `_alt_aware_origins_for_soft()` skipped them every cycle.

## Key Points

- Trail coverage at 99.25% (400 picks sampled) masked a depth collapse: median sharp trails per pick dropped from 61 to just 1, demonstrating that coverage and depth are independent health metrics
- Root cause was that Phase B's per-cycle `books` dict only contained entries for newly-evaluated markets, not already-tracked picks; the `_alt_aware_origins_for_soft()` gate always returned empty for existing picks, silently skipping all trail updates
- Diagnostic fingerprint: "0 updated" on every normal cycle plus trail row counts equal to exactly 2x new picks confirmed all writes were creation-only with zero updates to existing picks
- Likely trigger was the 2026-05-28 alt-line rollout commit `28ab39e` which restructured sharp_snap building and inadvertently narrowed Phase B's iteration scope
- Phase B-2 fix iterates `_tracked_ids - inserted_ids` directly, staging `market_key` + `soft_book_id` from Phase A, completely bypassing the per-cycle books dict gate
- Heartbeat code was removed as dead code during investigation — it had been producing synthetic rows that polluted backtest data; the tracker is now pure stream-driven with 250-300 trails/min sustained

## Details

The diagnostic process revealed the regression clearly through a cold-start vs warm-cycle comparison. On cold start (immediately after an Eve restart), Phase B showed 2604 updates because the books dict was fully populated from the initial market scan. On every subsequent warm cycle, updates dropped to exactly 0 because the books dict was rebuilt per-cycle with only newly-evaluated markets. This "works once then dies" pattern is a classic symptom of initialization-dependent state that isn't maintained across iterations. The heartbeat removal during this investigation was a red herring cleanup — the heartbeat had been generating synthetic trail rows to keep picks "alive" but these polluted backtest data with artificial entries that didn't reflect real market movement.

The Phase B-2 architecture solves the problem by decoupling trail iteration from the per-cycle books dict entirely. Instead of relying on books to know which picks need trail updates, Phase B-2 iterates the set difference `_tracked_ids - inserted_ids` directly — every tracked pick that wasn't just created in Phase A gets a trail update. The necessary `market_key` and `soft_book_id` for each tracked pick are derived during cache load via `normalize_player_name` and `normalize_prop_type`, then cached alongside the pick metadata from Phase A. End-to-end throughput after the fix was confirmed at 1000+ trail rows written in approximately 3.5 minutes, restoring the expected depth accumulation rate.

## Related Concepts

- [[concepts/trail-change-detection-architecture]] - The broader trail system that Phase B writes into
- [[concepts/alt-line-mismatch-poisoned-picks]] - The alt-line rollout that likely triggered the scope narrowing
- [[concepts/trail-capture-soft-ids-gap]] - Related trail capture gap involving soft book ID mapping

## Sources

- [[daily/lcash/2026-06-03.md]] - Sessions 10:04 (trail depth regression diagnosis with cold-start vs warm-cycle comparison), 12:54 (Phase B-2 tick-driven fix shipped and throughput confirmed), 13:14 (trail streamer port found redundant with Phase B-2)
