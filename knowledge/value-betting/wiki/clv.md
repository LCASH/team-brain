# Closing Line Value (CLV)

## Status: current
## Last verified: 2026-04-09

> The primary leading indicator of long-term profitability.

---

## What CLV Is

CLV measures whether the odds moved in your favor between when you identified the pick and when the game started. If you got better odds than the closing line, you beat the market.

```
CLV% = (your_odds / closing_odds - 1) × 100
```

Positive CLV = market moved toward your position = sharps agreed with you.

---

## Soft CLV vs Sharp CLV

This distinction is critical — we have both.

### Soft CLV (what Bet365 closed at)
- Measures: "Did the soft book adjust toward our pick?"
- Problem: Bet365 barely moves on prop lines. Many props close at the same odds they opened.
- Result: Soft CLV is often 0% or near-zero even when the real edge is significant.
- Column: `clv_pct` on `nba_tracked_picks`

### Sharp CLV (what devigged sharp books closed at)
- Measures: "Was our true odds estimate correct?"
- More meaningful: sharp books actively price props, so movement reflects real information.
- First data (2026-04-09): avg sharp CLV +8.9% vs soft CLV +1.79% on same picks.
- Column: `sharp_clv_pct` on `nba_tracked_picks` (added via `016_sharp_clv.sql`)

**Sharp CLV is the real validation metric.** Soft CLV understates edge significantly.

→ See `docs/clv-analysis-findings.md` for the full 1,000 pick analysis.

---

## Why CLV Converges Faster Than ROI

Research finding (Buchdahl):
- CLV standard deviation ≈ **0.1** per bet
- Profit/loss standard deviation ≈ **1.0** per bet
- CLV converges **~100x faster** in variance terms

Practical impact:

| Sample Size | CLV Signal | ROI Signal |
|-------------|-----------|-----------|
| 50 bets | Statistically significant | Noise |
| 200 bets | Reliable | Directional |
| 400 bets | Strong | Moderate |
| 2,000+ bets | Definitive | Definitive |

This means we can validate a segment (EV bucket, confidence tier, prop type) with far fewer bets using CLV than waiting for ROI to converge.

---

## CLV as Decision Metric

The performance tracking system uses CLV as the primary early indicator:
- **Per-segment CLV** tells you which picks are finding real edge
- **CLV beat rate** (% of picks with positive CLV) is a quality signal — top bettors beat CLV ~75% of the time
- **ROI** is the ultimate confirmation but takes 2,000+ bets to be reliable

→ See [[wiki/performance-tracking]] for the full segmentation design.

---

## Key Findings (from 1,000 pick analysis)

1. Scanner EV overstates edge ~2.6x vs soft CLV. Actual overstatement likely 1.5-2x (soft CLV understates).
2. Higher scanner EV does NOT mean higher real CLV. The 2-4% EV bucket has similar CLV to the 10-15% bucket.
3. The scanner is good at **finding** edges but bad at **sizing** them.
4. Sharp count is the strongest CLV predictor — see [[findings/2026-04-07-clv-1000-picks]].

---

## Related Pages
- [[wiki/performance-tracking]] — How CLV feeds into segmented analysis
- [[wiki/ev-calculation]] — How EV% is computed (the metric CLV validates)
- [[findings/2026-04-07-clv-1000-picks]] — Full CLV analysis findings
- [[findings/2026-04-09-sharp-clv-first-data]] — First sharp CLV results
