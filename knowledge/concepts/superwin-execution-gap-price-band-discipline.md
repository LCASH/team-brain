---
title: "SuperWin Execution Gap and Price Band Discipline"
aliases: [execution-gap, price-band-discipline, scanner-vs-actual-roi, superpick-bet-analysis, bowler-variance]
tags: [superwin, racing, analytics, execution, methodology, operations]
sources:
  - "daily/lcash/2026-05-25.md"
created: 2026-05-25
updated: 2026-05-25
---

# SuperWin Execution Gap and Price Band Discipline

A deep analysis of 189 actual SuperPick bets from the `superpick_bets` table revealed a dramatic execution gap: the scanner showed +15% ROI on tracked opportunities, but actual betting produced **-13.7% ROI (-$3,935 on $28,625 staked)**. The primary cause was systematic price-band non-compliance: 67% of stake went to the $0-5 odds band (unprofitable) while only 41% went to the $5-12 band (the +20-28% ROI sweet spot identified in [[concepts/superwin-racing-profitability-dimensions]]). The $2-3 band alone bled $3,314 at -43% ROI. Bowler-level variance was also significant: Amber Grech 0/8 (-100%), Billy Reynolds -82% vs Kyan Murphy +40%.

## Key Points

- **Scanner +15% ROI but actual bets -13.7% ROI** ($28,625 staked, -$3,935 P/L) — the gap is execution, not edge quality
- **Price band was the #1 failure**: 67% of stake at $0-5 (unprofitable), only 41% at $5-12 (the +20-28% sweet spot) — almost inverted from what data prescribes
- **$2-3 odds band alone bled $3,314** at -43% ROI — short-priced SuperPicks don't generate enough boost value to overcome the vig
- **Bowler variance is real**: Amber Grech 0/8 (-100%), Billy Reynolds -82% ROI vs Kyan Murphy +40%, Rakoia Smith +31% — account-level issues may be a factor (gubbing, timing)
- **Betting stopped during worst variance window** (W13-W14) right before strategy recovered (W15-W16 were +$1,966 combined) — classic variance-driven abandon
- **Tracking metadata gaps**: sport NULL on 87%, field_size NULL on 99% — can't slice on critical dimensions for informed bet selection
- **Confidence scoring IS already built and visible in the UI** — no additional UI work needed (user corrected over-engineering impulse)

## Details

### The Execution Inversion

The scanner's edge-pick theories (see [[concepts/superwin-racing-profitability-dimensions]]) identified $5-12 odds as the strongest single dimension, with the $5-8 sub-band at +28% ROI across 1,000+ picks. The actual bet distribution was almost the inverse:

| Odds Band | % of Stake | Scanner ROI | Actual ROI | Assessment |
|-----------|-----------|-------------|------------|------------|
| $0-3 | ~35% | Negative | **-43%** | Largest bleed — boost can't overcome vig at short prices |
| $3-5 | ~32% | Marginal | ~-10% | Slightly negative — not worth the variance |
| **$5-8** | ~22% | **+28%** | Likely positive | Sweet spot — but under-allocated |
| **$8-12** | ~19% | **+20%** | Likely positive | Strong — but under-allocated |
| $12+ | ~small | Mixed | Mixed | Longshot variance territory |

The execution gap is not about finding edge — the scanner correctly identifies where edge exists. It is about **bet selection discipline**: operators must resist betting on every SuperPick opportunity and restrict to the profitable odds bands.

### Bowler-Level Analysis

Individual bowler (operator account) performance varied dramatically:

| Bowler | Record | ROI | Notes |
|--------|--------|-----|-------|
| Kyan Murphy | — | +40% | Top performer |
| Rakoia Smith | — | +31% | Strong |
| Jake | — | ~+10% | Above average |
| Billy Reynolds | — | -82% | Deep negative |
| Amber Grech | 0/8 | -100% | Zero wins — potentially gubbed or timing issue |

The Amber Grech 0/8 record is statistically unlikely if the underlying opportunities were fair — 8 consecutive losses on boosted props at $5+ odds suggests either account-level issues (bet365/TabTouch gubbing the account's boosts) or systematic timing issues (placing after lines have already moved).

### The Variance Trap

Betting ceased during weeks 13-14, which happened to be the worst variance window. Weeks 15-16 immediately following the stop produced +$1,966 combined — the strategy recovered, but the operators had already stopped. This is a classic behavioral finance pattern: abandoning a positive-EV strategy during a drawdown, then missing the recovery.

The mathematical reality: a +15% ROI strategy with 25% win rate has a standard deviation of ~$75 per $100 bet. Over 189 bets at $150 average stake, the expected profit is +$4,252 but the 95% confidence interval spans -$1,200 to +$9,700. The observed -$3,935 is within 2 standard deviations — unlikely but not impossible, especially when execution diverges from the recommended parameters.

### Tracking Metadata Gaps

The `superpick_bets` table lacks critical dimensions that would enable post-hoc analysis:

- `sport`: NULL on 87% of rows — can't distinguish thoroughbred (profitable) from greyhound (historically weak)
- `field_size`: NULL on 99% — can't apply field-size filters from the hyperparameter sweep
- `heavy_weighted_fav`: NULL on 99% — can't test the favourite-vs-outsider hypothesis
- Scanner context at bet time (EV%, MTJ, race_type, confidence) is not recorded — can't verify that operators selected the recommended picks

### Recommended Operational Changes

Based on the analysis, three immediate changes were identified:

1. **Hard band filter**: No bets where boosted odds < $4 unless EV > 25% — eliminates the -43% ROI $2-3 bleed
2. **Stake-by-band discipline**: $250 maximum only in the $5-15 range; $50 maximum below $4 — sizes exposure to match expected edge
3. **Record scanner context at bet placement**: EV%, MTJ, race_type, confidence, field_size — enables future audit of whether operators followed recommendations

## Related Concepts

- [[concepts/superwin-racing-profitability-dimensions]] - The 10K-pick sweep that identifies the $5-8 odds sweet spot and other profitable dimensions; the execution gap shows these signals aren't being followed in practice
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal that tracks scanner-detected opportunities; the gap between journal ROI and actual bet ROI is the subject of this article
- [[concepts/tabtouch-superpick-boost-fabrication-analysis]] - The boost mechanics (price tiers: 20+→+5.0, 8-20→+1.0, 2-8→+0.5, 1-2→+0.1) explain WHY short-priced bets are unprofitable — the boost is smaller in absolute terms
- [[connections/liquidity-efficiency-inverse-in-betting]] - The liquidity-efficiency inverse explains part of the odds-band effect: short-priced runners are efficiently priced markets where small boosts can't overcome vig

## Sources

- [[daily/lcash/2026-05-25.md]] - 189 actual bets from `superpick_bets`: $28,625 staked, -$3,935 P/L, -13.7% ROI; 67% stake at $0-5 (unprofitable), $2-3 band -$3,314 at -43%; bowler variance: Amber Grech 0/8, Billy Reynolds -82%, Kyan Murphy +40%; betting stopped W13-W14 before recovery W15-W16 (+$1,966); metadata gaps (sport NULL 87%, field_size NULL 99%); confidence scoring already in UI — no additional work needed (Session 10:52)
