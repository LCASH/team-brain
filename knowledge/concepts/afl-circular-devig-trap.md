---
title: "AFL Circular Devig Trap"
aliases: [circular-devig, phantom-sharps, retail-consensus-bias, afl-sharp-gap]
tags: [value-betting, devig, afl, methodology, data-quality]
sources:
  - "daily/lcash/2026-04-14.md"
created: 2026-04-14
updated: 2026-04-14
---

# AFL Circular Devig Trap

AFL player prop betting in the value betting scanner suffered a -34.2% flat-bet ROI over 964 settled picks despite showing +1.16% average CLV — a CLV/ROI paradox caused by circular devigging. The system's "sharp" books for AFL (Bet Right, PointsBet AU, PickleBet, plus US books like FanDuel/DraftKings/BetRivers) are all correlated retail shops, not independent market makers. Devigging against their prices produces self-referential "true odds" that systematically overstate Over probabilities, creating phantom +EV signals.

## Key Points

- AFL record: 270-694 (28% WR), -34.2% flat-bet ROI, despite +1.16% avg CLV — CLV is meaningless when the closing line isn't sharp
- No genuine AFL market maker exists on OpticOdds — Pinnacle doesn't price AFL player props, and Betfair Exchange is not available via the API
- US sportsbooks (FanDuel, DraftKings, BetRivers) are not independent price-makers for AFL — they wholesale prices from AU markets, so using them as "sharps" creates circular devig
- Raw data confirmed the Over bias: Disposals Overs hit 41.5% vs implied ~50%; Goals Overs only 32.6%
- Bet Right (34.0% WR) and PickleBet (34.5% WR) — both weighted 1.0 as "sharps" — had the worst calibration; Sportsbet hit 50.7% (near-fair)
- 83% of AFL picks used `one_sided_consensus` devig method, never calibrated against outcomes

## Details

### The CLV/ROI Paradox

Closing Line Value (CLV) is the gold standard metric in sports betting: if you consistently beat the closing line, you should be profitable long-term because the closing line at sharp books converges to the true probability. The AFL system showed +1.16% average CLV — suggesting the picks were finding genuine value. But the actual P/L was deeply negative at -34.2% ROI.

The resolution of the paradox is that CLV is only meaningful when the closing line is sharp. A "sharp" closing line reflects the market's best estimate of true probability, informed by significant liquidity, professional bettors, and market-maker pricing. AFL player props on OpticOdds have none of these: the books labeled as "sharp" in the system's configuration are Australian retail operators (Bet Right, PointsBet AU, PickleBet) and US books that copy AFL prices from AU wholesalers. "Beating the close" against these phantom sharps means beating a biased reference point — the system was consistently finding "value" relative to a systematically wrong baseline.

### The Circular Devig Mechanism

The devigging process works as follows: (1) collect odds from multiple "sharp" books, (2) remove the margin (vig) to estimate the true probability, (3) compare soft book odds against the true probability to calculate EV. When the "sharp" books are themselves biased — e.g., systematically pricing Disposals Overs too long — the devigged "true probability" inherits that bias. The resulting EV calculation identifies bets where the soft book is priced differently from the biased consensus, not bets with genuine positive expected value.

Concretely: if all five "sharp" books price a player's Disposals Over at implied 55% when the true probability is 42%, the devigged "true odds" will estimate something near 55%. A soft book pricing the same market at implied 48% appears to offer +EV because 48% < 55%. But the actual hit rate is ~42%, making the bet deeply -EV despite the positive signal.

### Why US Books Don't Help

A natural assumption is that US sportsbooks (FanDuel, DraftKings, BetRivers) operate as independent price-makers and would provide a diverse signal for AFL markets. In practice, these books do not have internal AFL expertise. They source their AFL player prop prices from Australian wholesale providers — likely the same wholesalers that supply AU retail books. This means that FanDuel's AFL Disposals line is not an independent opinion; it is a mark-up on the same wholesale price that Bet Right and PickleBet use. Adding US books to the "sharp" pool increases the count of books but not the diversity of price signals, making the consensus more confident in the same biased direction.

### Raw Data Evidence

A raw CSV export of 14,567 rows across 23 AFL fixtures (March 6-28) independently confirmed the systematic Over bias:

- **Disposals Overs:** 41.5% actual hit rate vs ~50% implied by "sharp" consensus
- **Goals Overs:** 32.6% actual hit rate — even worse calibration
- **Disposals Unders:** 51.1% actual hit rate — Unders slightly over-performing implied
- **Per-book calibration:** Bet Right 34.0% WR, PickleBet 34.5% WR (worst), Sportsbet 50.7% WR (near-fair)

The per-book calibration results suggest that Sportsbet (book 900), while listed as a soft book, is a better price reference for AFL than either Bet Right or PickleBet — both weighted 1.0 as sharps.

### Empirical Edge-Finding as Alternative

Since no true market maker exists for AFL player props, traditional devigging cannot produce reliable true-probability estimates. The recommended alternative is empirical edge-finding: slicing historical data by (market, side, book, odds bucket) and comparing actual hit rates to implied probabilities directly, bypassing the devig step entirely. This approach finds "retail consensus errors" — bets where a specific book consistently misprices relative to observed outcomes — rather than "true value" relative to a sharp reference.

This is an honest framing: without Pinnacle or Betfair Exchange pricing AFL player props, the system cannot determine true probabilities. It can only identify exploitable biases in specific books' pricing relative to empirical outcomes.

### Data Limitations

The cached AFL data has real limitations for this analysis: no time-series data (only opening and closing line snapshots), Bet365 barely present (3/23 fixtures), only Goals and Disposals markets available, and opening line captures may not reflect the production trigger moment. The confidence scorer has never been run on AFL (0/1000 picks have confidence values).

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - OpticOdds is the sole source of AFL "sharp" odds, and none of its AFL books are genuine market makers
- [[concepts/one-sided-consensus-structural-bias]] - The devig method used on 83% of AFL picks is also structurally broken for two-sided markets
- [[concepts/value-betting-theory-system]] - The theory configuration system that allowed 6 theories to accumulate without calibration audit
- [[concepts/pick-dedup-multi-theory-limitation]] - Pick dedup hid which theories were actually driving AFL picks
- [[connections/circular-devig-provider-dependency]] - How OpticOdds dependency and the absence of AFL market makers create this trap

## Sources

- [[daily/lcash/2026-04-14.md]] - AFL 270-694 record, -34.2% ROI, +1.16% CLV paradox; no genuine AFL sharps on OpticOdds; US books wholesale from AU; raw 14,567-row CSV confirmed Over bias (Disposals 41.5%, Goals 32.6%); Bet Right/PickleBet worst calibration, Sportsbet near-fair at 50.7%; empirical edge-finding recommended as alternative (Sessions 11:24, 13:19)
