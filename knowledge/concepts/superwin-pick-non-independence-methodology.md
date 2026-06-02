---
title: "SuperWin Pick Non-Independence and Effective Sample Size"
aliases: [pick-non-independence, effective-sample-size, day-as-unit-testing, correlated-picks-ci-correction]
tags: [superwin, racing, methodology, statistics, analytics]
sources:
  - "daily/lcash/2026-06-01.md"
created: 2026-06-01
updated: 2026-06-01
---

# SuperWin Pick Non-Independence and Effective Sample Size

On 2026-06-01, a deep statistical validation of SuperWin edge-pick theories revealed that **picks within the same racing day are not independent** — they share venue conditions, jockey form, track state, and bookie pricing cycles. The effective sample size is approximately 40 independent game-days, not 27,000 picks. All prior confidence intervals were ~26x too tight, invalidating most theory-level significance claims. The correct methodology going forward is day-as-unit t-testing.

## Key Points

- **Picks are NOT independent**: Same-day picks share venue, track, weather, jockey, and bookie pricing state — standard pick-level CIs assume independence and are ~26x too tight
- **Effective sample size ~40 days**, not 27K picks — day-as-unit t-test is the honest methodology
- **Prior CIs invalidated**: Most "statistically significant" theory findings (10 edge theories, multiple "winning formulas") were based on massively over-confident intervals
- **OL_ltp "single most valuable signal" was 100% suspension-LTP artifact** — proven dead with live detection-time data; the most celebrated finding was leakage
- **Confirmation Score collapsed**: +40% ROI headline → +5.2% OOS with flagship cells inverting — another overfit artifact
- **Two methodology errors created the false-theory edifice**: (a) using settlement-time ltp/bsp as staking signals = leakage, (b) treating correlated picks as independent = massively overconfident CIs
- **Deploy Gate 1 confirmed**: skip odds < 4 (day-t ≈ 2.78, inverse is significant bleeder)
- **Deploy Gate 3 confirmed**: run-2nd-3rd only if ev_pct ≥ 10 (flips −6.7% → +32–65% OOS, monotonic)

## Details

### The Independence Violation

Standard statistical testing for betting strategies treats each pick as an independent trial. For the SuperWin racing scanner, this assumption is fundamentally wrong. A typical racing day produces 200-400 picks across 8-15 venues. Picks within the same venue share track conditions, weather, and bookie pricing states. Picks from the same bookie share pricing algorithm updates. Picks in the same time window share jockey availability and market sentiment.

The correlation structure means that a "significant" result on 27,000 picks (t ≈ 15.0 at pick-level) may be completely non-significant when correctly computed at the day level (t ≈ 0.6 with 40 effective observations). The 26x CI inflation comes from the ratio of sqrt(27000) / sqrt(40) — the standard error scales with the square root of the sample size, and using the wrong sample size produces CIs that are sqrt(27000/40) ≈ 26 times too narrow.

### What Survived the Correction

Despite the CI widening, two deploy gates maintained statistical significance at the day level:

**Gate 1 (skip odds < 4)**: Day-level t ≈ 2.78 for the positive side, and the inverse (betting only odds < 4) is a significant bleeder. This kills the favourite-longshot bias that was inverted in this dataset — longshots realize above implied win rate, favorites below. The "long favorites" pattern isn't just variance; it's negative-EV.

**Gate 3 (run-2nd-3rd ev_pct ≥ 10)**: Flips -6.7% ROI to +32-65% ROI in out-of-sample validation, with monotonic relationship between EV threshold and profitability.

### What Did Not Survive

- **Confirmation Score**: The +40% ROI headline collapsed to +5.2% OOS with flagship cells inverting — pure overfit from slice-testing at pick level
- **OL_ltp signal**: "The single most valuable signal" was 100% a suspension-LTP artifact. When tested with live detection-time data (not settlement-time), the signal is dead. This was leakage: using post-settlement Betfair LTP as a pre-bet staking signal
- **Full back+lay hedging**: A leakage tautology — the back price was built from the leaky ev_pct field
- **ML meta-labels**: Strictly dominated by the single hand-set odds threshold (Gate 1); five quant lenses confirmed every clever overlay was leakage or overfit

### The Anti-Pattern: "Every Question Gets an Answer"

A meta-observation about AI-assisted analysis: the LLM always produces a confident answer to "what's the winning formula?" — it never responds "the data doesn't support any conclusion yet." This amplifies the multiple comparison problem: the operator asks, the LLM searches for the best combination (which always exists in random data), and the operator treats the response as validated finding rather than a data-mining artifact. The discipline: treat every LLM-generated edge analysis as a hypothesis requiring out-of-sample validation on held-out time windows.

## Related Concepts

- [[concepts/multiple-comparison-edge-validation-trap]] - The over-fitting analysis from May 30 that first identified the anti-pattern; this article quantifies the CI correction
- [[concepts/superwin-racing-profitability-dimensions]] - The 16-dimension analysis whose findings are now reclassified — day-level significance replaces pick-level
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal whose data was used for the validation; insert-only pattern preserved first-detection odds
- [[concepts/superwin-execution-gap-price-band-discipline]] - Scanner vs actual execution gap; now understood in context of which gates actually survive day-level testing

## Sources

- [[daily/lcash/2026-06-01.md]] - 5-agent quant lens fan-out verified 9 of 20 candidates, confirmed 7; effective sample size ~40 days not 27K picks; day-as-unit t-test methodology adopted; OL_ltp dead (suspension-LTP artifact); Confirmation Score +40%→+5.2% OOS; Gate 1 (odds<4, t≈2.78) and Gate 3 (r2r ev≥10) confirmed; two methodology errors identified (leakage + independence violation); "every question gets an answer" anti-pattern (Session 15:04)
