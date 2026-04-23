---
title: "Theory-Aware Sharp Book Filtering"
aliases: [sharp-filtering-bug, theory-specific-sharps, devig-all-books-bug, sharp-ids-theory-lookup]
tags: [value-betting, devig, bug, dashboard, architecture]
sources:
  - "daily/lcash/2026-04-23.md"
created: 2026-04-23
updated: 2026-04-23
---

# Theory-Aware Sharp Book Filtering

The value betting scanner's devig function was iterating ALL books (including soft books like Bet365, BetMGM) when computing true odds, instead of filtering to only the theory's configured sharp book IDs. This produced garbage true-odds lines and inflated peak EV values. The fix applied in three places — the trail chart renderer, `computePeakEV`, and the resolver's `_compute_trail_stats` — now looks up the pick's `triggered_by` theory and uses that theory's weight configuration to determine which books are sharp.

## Key Points

- The devig function was using ALL books in the trail data as input — soft books (Bet365, BetMGM, Sportsbet) were treated as sharp references alongside actual sharps (Pinnacle, Circa)
- Different theories define different sharp books via their weights config — any devig calculation that doesn't filter by the theory's sharp IDs produces garbage true odds
- Fix applied in **three independent locations**: chart renderer (line 688), `computePeakEV` (line 188), and resolver's `_compute_trail_stats`
- The pick's `triggered_by` field links to the theory name, which defines the sharp book IDs via its weights configuration
- User spotted the bug via the true odds line looking wrong on expanded trail charts — the devigged true probability was unrealistically volatile because soft book noise was included
- Pre-fix historical trail stats may have incorrect `peak_true_odds` and `closing_true_odds` — a backfill with corrected sharp filtering may be needed

## Details

### The Bug

The value betting scanner evaluates multiple theories, each with its own sharp book configuration. A "Pinnacle" theory uses Pinnacle (book ID 250) as its sole sharp reference. An "Aggressive" theory might use Pinnacle + Circa + BetRivers with different weights. The devig function takes a set of book odds, applies the configured weights, and computes the implied true probability.

The bug was in how the devig function selected which books to include. Rather than filtering trail entries to only the theory's sharp books, it passed ALL available book odds — including soft books like Bet365 (365), BetMGM, Sportsbet (900), Ladbrokes (903), etc. — into the devigging calculation. Soft books have wider margins and less informative pricing than sharp books; including them as "sharp" inputs dilutes the true-odds estimate with noise and produces systematically inaccurate true probabilities.

This manifested visually: when expanding a pick's trail chart, the true odds line showed unrealistic volatility — bouncing around as different soft books' prices entered and exited the devig calculation. A properly filtered devig using only Pinnacle would produce a smooth, slowly-moving true-odds line reflecting genuine market movement.

### Why Three Fix Locations

The devig function is called from three independent code paths, each of which needed the same sharp book filtering fix:

1. **Chart renderer (dashboard JS, line 688)**: When a user clicks to expand a pick's trail chart, the renderer devigs each trail entry to plot the true-odds line. Without theory-aware filtering, the chart showed a noisy true-odds line that obscured the actual market movement.

2. **`computePeakEV` (dashboard JS, line 188)**: The peak EV computation devigs each trail entry to find the moment of maximum `(soft_odds x true_prob - 1)`. Without filtering, soft book noise inflated peak EV values — a soft book's own odds being included in the "true odds" calculation created circular reasoning.

3. **Resolver's `_compute_trail_stats` (Python)**: The server-side resolver computes pre-computed trail statistics (see [[concepts/trail-stats-precomputed-columns]]) at resolution time. Without filtering, the stored `peak_true_odds` and `closing_true_odds` columns contained values polluted by soft book inclusion.

### Theory Lookup Pattern

The fix follows the same pattern in all three locations:

1. Read the pick's `triggered_by` field (e.g., "NBA Pinnacle", "Aggressive")
2. Look up the theory by name in the loaded theories cache
3. Extract the theory's weights configuration (a mapping of book_id → weight)
4. Filter trail entries to only include books present in the weights (these are the sharp books)
5. Pass only the filtered entries to the devig function

This ensures that a Pinnacle theory devigs against Pinnacle only, a multi-sharp theory devigs against its specific sharp set, and no soft book ever contaminates the true-odds calculation.

### Connection to Prior Devig Bugs

This bug is related to but distinct from the devig method-market structure mismatches documented in [[connections/devig-method-market-structure-mismatch]]. Those bugs involved the wrong *mathematical model* being applied (2-way on 3-way markets, one-sided on two-sided markets). This bug involves the wrong *input data* being fed to a correct mathematical model — the devig formula itself was fine, but the books it was devigging against included soft books that should not have been treated as sharp references.

The common thread is that devigging is a garbage-in-garbage-out operation: the output is only as good as the input books' pricing quality and the model's assumptions about market structure.

### Dashboard Staleness Warning

The `MAX_ODDS_AGE_S=180` filter correctly excludes stale trail entries from EV computation even when the dashboard shows a degraded status. The "stale data" warning is cosmetic — it indicates some data channels are slow, but the EV computation only uses entries within the freshness window.

## Related Concepts

- [[concepts/value-betting-theory-system]] - Theories define which books are sharp via their weights configuration; the fix reads this configuration at devig time
- [[connections/devig-method-market-structure-mismatch]] - A parallel class of devig errors: wrong model (3-way as 2-way, one-sided on two-sided) vs wrong input data (soft books in sharp set)
- [[concepts/trail-stats-precomputed-columns]] - The pre-computed trail stats columns whose accuracy depends on correct sharp filtering
- [[concepts/dashboard-client-server-ev-divergence]] - Another case where client-side computation diverged from server-side due to missing theory configuration
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV's reliability depends on correct sharp book identification; this fix ensures CLV is computed against the intended sharp reference
- [[concepts/pinnacle-prop-type-sharpness-variance]] - Different theories use different sharps because Pinnacle isn't uniformly sharp across prop types; theory-aware filtering enables this per-theory sharpness calibration

## Sources

- [[daily/lcash/2026-04-23.md]] - User spotted wrong true odds line on expanded trail charts; deep dive confirmed devig iterating ALL books instead of theory-specific sharps; fix in three places: chart renderer (line 688), computePeakEV (line 188), resolver _compute_trail_stats; theory lookup via triggered_by → weights config → sharp book IDs; MAX_ODDS_AGE_S=180 filter confirmed working correctly; old picks may need backfill with corrected filtering (Session 17:53)
