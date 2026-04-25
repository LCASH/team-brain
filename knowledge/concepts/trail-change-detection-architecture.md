---
title: "Trail Change-Detection Recording Architecture"
aliases: [change-only-trails, trail-threshold, odds-change-detection, trail-blind-spots, heartbeat-trails]
tags: [value-betting, trail-data, architecture, data-quality, methodology]
sources:
  - "daily/lcash/2026-04-25.md"
created: 2026-04-25
updated: 2026-04-25
---

# Trail Change-Detection Recording Architecture

The value betting scanner's trail system uses a **change-only recording model**: soft trails write only when odds or line values change by more than 0.001, and sharp trails write only when any sharp book's odds hash changes. This design minimizes I/O but creates blind spots — you cannot distinguish "odds were stable for 2 hours" from "the scraper stopped watching for 2 hours." Sharp trails update ~7x more frequently than soft trails because 5+ sharp books means more frequent hash changes across the aggregate.

## Key Points

- Soft trails record when `abs(current_odds - cached_odds) > 0.001` or line changes — pure delta detection
- Sharp trails record when any sharp book's odds hash changes — with 5+ books, at least one usually moves, producing ~7x more frequent writes than soft
- Average sharp trail gap is 12 seconds (best case), average soft trail gap is 37 seconds (best case) — based on 500-pick sample
- Trail distribution is **bimodal**: some picks have 50-700 entries (hours of tracking, active odds movement), many have just 1-2 (newly created or illiquid props)
- For ROI backtesting, change-only is sufficient (opening and closing odds are captured); for "optimal bet timing" analysis, interpolation or periodic heartbeat entries would be needed
- Closing odds may be hours stale if nothing moved — the last trail entry could be from 3 hours before game time if the line was static

## Details

### The Recording Mechanism

Phase B of the tracker runs on every cycle and checks each tracked pick's current market state against its cached state. For soft book trails, the comparison is straightforward: if the decimal odds or line value has changed by more than 0.001 (a threshold that filters floating-point noise while catching any meaningful price movement), a new trail entry is written. For sharp book trails, the mechanism is hash-based: the odds from all configured sharp books are concatenated and hashed, and a new entry is written if the hash differs from the cached version.

The 0.001 threshold is a deliberate design choice. Without it, floating-point arithmetic noise (e.g., 1.8500000001 vs 1.85) would produce phantom trail entries that consume storage without representing real market movement. The threshold is small enough that any genuine odds change (minimum tick sizes at sportsbooks are typically 0.01 or larger) will be captured.

### Why Sharp Trails Are Denser

Sharp trails update approximately 7 times more frequently than soft trails because of a mathematical property: with N independent sharp books each making independent pricing decisions, the probability that *at least one* book changes its price in any given cycle is much higher than the probability that *a specific soft book* changes its price. With 5 sharp books (Pinnacle, Circa, DraftKings, BetRivers, Novig), even small movements on any one book trigger a hash change and a trail write. A single soft book must independently move for its trail to update.

In the 500-pick sample analyzed on 2026-04-25, sharp trails averaged 7.1 entries per pick with a best-case gap of 12 seconds between entries. Soft trails averaged 3.0 entries per pick with a best-case gap of 37 seconds. The 90th percentile of trail coverage showed picks with 50-700+ entries — these are picks tracked during active pre-game windows where odds moved frequently.

### Blind Spots and Timing Analysis

The change-only model creates two distinct blind spots:

**1. Stable period ambiguity.** A gap of 2 hours between two trail entries could mean either (a) the odds were genuinely stable for 2 hours (no movement to record), or (b) the scraper was down, Chrome had crashed, or the push pipeline was stuck. There is no way to distinguish these cases from trail data alone without correlating with system health logs.

**2. Stale closing odds.** The "closing odds" for a pick is defined as the last trail entry before game start. If the soft book's odds didn't change in the final 3 hours before tip-off (common for low-attention props), the closing odds reflect a snapshot from 3 hours ago, not the actual price at game time. For liquid markets (NBA points totals, popular player props), this is rarely an issue because odds move frequently. For illiquid markets (niche props, small-market games), the closing snapshot may be significantly stale.

### Bimodal Distribution

The trail entry count distribution is strongly bimodal. The two clusters are:

- **1-2 entries (low cluster):** Newly created picks that haven't been tracked through a full pre-game window, or illiquid props where odds never moved after initial detection.
- **50-700+ entries (high cluster):** Picks tracked through multiple hours of active pre-game odds movement, with both sharp and soft odds changing regularly.

Picks in the low cluster have limited backtesting value at the individual level — they capture the opening snapshot but provide no odds evolution data. Picks in the high cluster have rich time-series data suitable for optimal timing analysis, CLV curve reconstruction, and peak EV identification.

### Heartbeat Entry Proposal

A periodic heartbeat mechanism was discussed on 2026-04-25: writing a trail entry every 10-15 minutes even if odds haven't changed, marked with a flag indicating "no change, heartbeat only." This would resolve the stable-period ambiguity (a gap with heartbeats means stable; a gap without heartbeats means monitoring was down) and provide tighter closing-odds snapshots for illiquid markets. The tradeoff is increased storage I/O — the scanner tracks thousands of picks, and a 10-minute heartbeat would add ~6 entries/hour/pick during the tracking window. The proposal was presented but not yet decided.

## Related Concepts

- [[concepts/trail-data-temporal-resolution]] - The push-cycle-driven trail sparsity issue (55s intervals pre-fix, 2s post-fix) is a different mechanism from change-detection sparsity; both affect trail density but from different causes
- [[concepts/trail-preseeding-coverage-bug]] - The pre-seeding bug prevented baseline trail writes entirely — a more severe failure than change-detection sparsity
- [[concepts/trail-stats-precomputed-columns]] - Pre-computed trail stats (peak_ev, avg_ev, closing_true_odds) depend on trail entries existing; change-only recording means some picks have insufficient data for reliable stats
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV computation uses trail data as the closing reference; stale closing odds from change-only recording reduce CLV precision for illiquid markets
- [[concepts/betting-window-roi-methodology]] - The 3h betting window filter uses "earliest trail entry within 3h" — change-only recording means the first entry in the window may be significantly after the 3h mark

## Sources

- [[daily/lcash/2026-04-25.md]] - Trail health deep dive: 90% of 500 picks have trails; sharp trails avg 7.1 entries/pick (12s best gap), soft trails avg 3.0 entries/pick (37s best gap); bimodal distribution; change-only recording creates timing analysis blind spots; heartbeat proposal discussed but not yet decided; closing odds may be hours stale for illiquid props (Session 07:58)
