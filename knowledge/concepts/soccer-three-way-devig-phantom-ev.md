---
title: "Soccer Three-Way Devig Phantom EV"
aliases: [3-way-devig, soccer-phantom-ev, three-way-market, draw-probability-redistribution]
tags: [value-betting, devig, soccer, bug, methodology]
sources:
  - "daily/lcash/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# Soccer Three-Way Devig Phantom EV

Soccer moneyline markets have three outcomes (Home/Draw/Away), but the value betting scanner's parser mapped them as two-way (Home→Over, Away→Under), dropping the Draw entirely. This redistributed the Draw probability (~23%) across both sides, producing phantom EVs of 20-41% on soccer fixtures. When properly 3-way devigged, a sample fixture showed zero edge. All 22 soccer Pinnacle theories were deactivated and 30 phantom picks voided on 2026-04-16. A 3-way devig implementation was deployed the same day, eliminating the phantom EVs — though initial deployment exposed a JS render crash misattributed as a "Supabase Error" in the dashboard.

## Key Points

- Soccer moneyline has 3 outcomes (Home/Draw/Away); the scanner treated it as 2-way (Over/Under), silently dropping the Draw
- The Draw probability (~23%) was redistributed across Home and Away, inflating both sides' implied probabilities and producing 20-41% phantom EVs
- OpticOdds returns all 3 outcomes under `moneyline` market_id (not a separate `moneyline_3-way`) — the data is correct, the parser is wrong
- When properly 3-way devigged, a sample fixture showed zero edge — confirming the EVs were entirely phantom
- 22 soccer Pinnacle theories deactivated, 30 phantom picks voided; 6 genuine 2-way leagues retained (NBA, MLB, NHL, Euroleague, CBA, Turkey BSL)
- The telltale diagnostic sign: implied probabilities summing to ~77% instead of >100%

## Details

### The Mechanism

The value betting scanner's EV pipeline assumes all markets are two-sided (Over/Under pairs). When processing soccer moneyline data from OpticOdds, the parser mapped Home→Over and Away→Under, discarding the Draw outcome entirely. This is catastrophically wrong for soccer, where the Draw typically carries 23-28% probability.

In a correctly 3-way devigged soccer moneyline, the three implied probabilities (after removing vig) sum to 100%. When the Draw is dropped, its probability mass must go somewhere — the 2-way devig formula redistributes it proportionally across the remaining two outcomes. This inflates both Home and Away probabilities, making the "true odds" appear lower than they actually are. Any soft book pricing the same market at its actual odds now appears to offer large positive EV relative to the inflated baseline.

The diagnostic signature is distinctive: the implied probabilities from the 2-way devig sum to approximately 77% (100% minus the ~23% Draw), which should never happen in a properly overround market. A 2-way market's raw implied probabilities should sum to >100% (the bookmaker's margin). Seeing <100% is an immediate flag that outcomes are missing from the model.

### Discovery and Impact

The soccer phantom EVs were discovered on 2026-04-16 during validation of the Pinnacle prediction-market pipeline. Soccer moneyline picks were showing 20-41% EVs — suspiciously high for an efficient market. Investigation revealed that all soccer picks shared the same pattern: Home-side and Away-side both showing large positive EV, with no Draw picks at all.

A manual 3-way devig of a sample fixture confirmed zero edge once the Draw probability was properly included. This proved the EVs were entirely artifacts of the parsing error, not genuine market inefficiencies.

The 30 voided picks had been triggered across multiple soccer leagues — all from Pinnacle theories that had been deployed as part of the prediction-market expansion. All 22 soccer-specific theories were deactivated. Six 2-way leagues (NBA, MLB, NHL, Euroleague, CBA, Turkey BSL) were retained as their moneyline markets genuinely have two outcomes.

### Fix Implementation

The fix required changes across three system layers:

1. **3-way devig function** — extended the multiplicative devig formula to handle three outcomes instead of two. The math is straightforward (same principle, three variables instead of two).
2. **Tracker compute path** — the `tracker.py` evaluation loop was branched for 3-way markets to evaluate Home, Draw, and Away independently instead of the Over/Under pair assumption.
3. **Poller mapping** — the OpticOdds poller was updated to map all three outcomes from the `moneyline` market_id instead of dropping the Draw.

The 3-way devig was deployed on 2026-04-16 (Session 22:35), eliminating the phantom 40%+ EVs on soccer moneylines. However, initial deployment exposed a dashboard rendering bug: the 3-way devig code path triggered a JS render crash that was caught by a broad `try/catch` block wrapping both Supabase fetch AND render logic, causing the error to display as "Supabase Error" instead of identifying the render crash. The fix was to wrap the render logic in its own error boundary, separating fetch failures from render failures.

With the 3-way devig deployed, soccer theories can be re-evaluated for re-activation once forward validation confirms the corrected devig produces accurate EV signals.

### Broader Pattern

This is the third distinct case of a devig method not matching the market's actual structure, joining the AFL `one_sided_consensus` bug (see [[concepts/one-sided-consensus-structural-bias]]) and the AFL circular devig trap (see [[concepts/afl-circular-devig-trap]]). The common thread: when the mathematical model's assumptions about market structure don't match reality, the resulting EV signals are not just wrong but systematically biased in a specific direction, creating confident-looking picks that are guaranteed losers. See [[connections/devig-method-market-structure-mismatch]] for the full pattern analysis.

## Related Concepts

- [[concepts/one-sided-consensus-structural-bias]] - Another devig method applied to the wrong market type (1-sided method on 2-sided AFL Disposals)
- [[concepts/afl-circular-devig-trap]] - Devig against correlated non-sharp books producing phantom CLV — same class of systematic bias
- [[concepts/pinnacle-prediction-market-pipeline]] - The pipeline whose soccer expansion exposed this bug
- [[concepts/value-betting-theory-system]] - The theory system where 22 soccer theories accumulated before the bug was caught
- [[concepts/alt-line-mismatch-poisoned-picks]] - Another phantom EV mechanism from mismatched market data
- [[connections/devig-method-market-structure-mismatch]] - The cross-cutting pattern linking soccer 3-way, AFL one-sided, and AFL circular devig

## Sources

- [[daily/lcash/2026-04-16.md]] - Soccer moneyline picks at 20-41% EV were phantom — 3-way market (Home/Draw/Away) parsed as 2-way (Over/Under), dropping Draw; 3-way devig on sample showed zero edge; 22 soccer theories deactivated, 30 picks voided; 6 genuine 2-way leagues retained (Sessions 16:30, 20:38). 3-way devig implemented and deployed; initial render crash misattributed as "Supabase Error" due to broad catch block; render error boundary added (Session 22:35)
