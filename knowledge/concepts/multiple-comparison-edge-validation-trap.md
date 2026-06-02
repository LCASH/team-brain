---
title: "Multiple Comparison Edge Validation Trap"
aliases: [over-fitting-trap, signal-slice-false-positives, honest-math-reckoning, multiple-comparison-problem, edge-hypothesis-validation]
tags: [superwin, racing, analytics, methodology, anti-pattern, backtesting]
sources:
  - "daily/lcash/2026-05-30.md"
  - "daily/lcash/2026-06-01.md"
created: 2026-05-30
updated: 2026-06-01
---

# Multiple Comparison Edge Validation Trap

On 2026-05-30, the first full day of data after the resolver PnL formula fixes (see [[concepts/resolver-pnl-formula-mug-run2nd3rd-bugs]]) produced an honest aggregate: **-339u / -34.1% ROI on 994 settled picks**. The previous day's reported +198u / +20% ROI was NOT a clean signal — it was partial-day data overlaying picks placed under broken math (mug mode back-only PnL, run-2nd-3rd hardcoded slug). This revealed that the "winning formula" analysis (e.g., BoostBet run-2nd-3rd +44.9% ROI on 127 picks) was **over-fitted pattern matching** from ~100 single-signal slices with no out-of-sample validation. Testing ~100 signal slices then ~30 compound rules surfaces false positives by chance — the multiple comparison problem.

## Key Points

- **-339u / -34.1% ROI on 994 settled picks** — first honest-math day after resolver fix vs prior reported +198u / +20% ROI (broken math)
- **~100 signal slices produced confident "formulas"** that were actually over-fitted noise: every dimension (race_type, bookie, edge, mtj_band, ev_band, liq_band, CLV, overlay) was sliced independently, then ~30 compound rules tested
- **Anti-pattern identified: "every time you asked a question, I produced an answer"** — the LLM's tendency to always give a confident response amplifies the multiple comparison trap; honest uncertainty is better than confident wrong answers
- **Staking decisions paused for 7-14 days** until honest-math data accumulates — no deploying "winning formulas" to Venom without out-of-sample validation on a held-out time window
- **Edge-research skill catalog's 9 "learnings" reclassified as hypotheses** — pre-seeded from one day's data under broken math, should be treated as hypotheses pending validation, not findings
- **Correcting measurement can reveal losses**: don't celebrate math fixes as wins until recalibrated data accumulates — the fix exposed that previously "profitable" edges were actually losing

## Details

### The Measurement Correction Reckoning

The resolver PnL formula fixes deployed on 2026-05-29 (see [[concepts/resolver-pnl-formula-mug-run2nd3rd-bugs]]) corrected two bugs: mug mode was computed as back-only (ignoring the lay-leg offset), and run-2nd-3rd settlement was hardcoded to one bookie slug. The combined effect was a dramatic PnL swing — numbers that had looked profitable under broken math turned negative under correct math.

The critical lesson is temporal: the +198u / +20% ROI reported on May 29 was a partial-day result overlaying picks that had been tracked under the old (incorrect) PnL formulas. Those picks' PnL values hadn't been retroactively corrected yet. The May 30 result (-339u / -34.1%) represents the first full day where all settled picks have correct PnL — and it was deeply negative.

This creates a dangerous cognitive trap: the operator sees "yesterday we were +20%, today we're -34%" and attributes the change to bad luck or market conditions. In reality, yesterday's number was wrong and today's is the first honest measurement.

### The Multiple Comparison Problem

The SuperWin edge analysis (see [[concepts/superwin-racing-profitability-dimensions]]) had been systematically slicing the pick universe across ~16 dimensions: race_type, bookie, edge_mode, mtj_band, ev_band, liquidity_band, CLV, overlay, same_race_count, detection_count, bf_drift, trail_len, and more. Each dimension was tested for performance independently (~100 single-signal slices), then promising signals were combined into ~30 compound rules.

At 100 independent tests with a 5% significance threshold, approximately 5 tests will appear "significant" by pure chance. When compound rules are built from the "significant" single-signal findings, the false positive rate compounds further because the rules are constructed to fit the observed data — a textbook case of over-fitting.

Specific examples of likely false positives:
- **BoostBet run-2nd-3rd +44.9% ROI on 127 picks** — appeared as the strongest edge, but under corrected PnL the run-2nd-3rd mode as a whole swung from -258.7u to -138.7u
- **"CANNON" configuration** (+24.9% ROI on 1,599 picks) — a compound filter combining race-superpicks + tabtouch + odds $5-8 that may be over-fitted to the training window
- **Greyhound $5-8 +30.9% ROI on 1,137 picks** — contradicted the prior "greyhound is weak" finding from an earlier 487-pick sample, suggesting both findings are noise at different sample sizes

### The LLM Amplification Factor

A meta-observation unique to AI-assisted analysis: the LLM (Claude) will always produce an answer to "what's the winning formula?" — it will never respond "the data doesn't support any conclusion yet." This creates a collaboration trap where:

1. The operator asks "which combination of filters produces the best ROI?"
2. The LLM searches the data, finds the best-performing combination (which always exists, even in random data)
3. The operator treats the response as a validated finding rather than a data-mining artifact
4. Staking decisions are made on the "finding"

The corrective discipline: treat every LLM-generated edge analysis as a hypothesis requiring out-of-sample validation. The LLM is an excellent tool for hypothesis generation (finding patterns in data) but its output is NOT validation (confirming patterns are real). The validation step — testing on held-out time windows — must be enforced by the operator, not delegated to the LLM.

### The Pause Protocol

Based on this experience, a staking-decision pause protocol was established:

1. **After any measurement correction** (resolver fix, settlement fix, PnL formula change): pause staking decisions for 7-14 days
2. **Before deploying any "winning formula"** to Venom (automated betting): require out-of-sample validation on a held-out time window (minimum 500 picks not used in the analysis)
3. **Reclassify all findings from pre-correction data** as hypotheses, not conclusions
4. **Demand negative results**: if the LLM analysis never produces "no edge found," the operator should be suspicious

### Quantitative Validation and Leakage Identification (2026-06-01)

On 2026-06-01, a comprehensive 5-agent quant validation (microstructure, ML/leakage, probability/calibration, derivatives/hedging, statistics/regime) systematically falsified the remaining overfit signals and identified the root methodology errors:

**OL_ltp was pure leakage**: The "single most valuable signal" (Betfair last traded price at settlement) was a suspension-LTP artifact. When tested with live detection-time data — the only data available at bet placement — the signal is completely dead. Using settlement-time Betfair data as a pre-bet staking signal is definitional leakage.

**Confirmation Score collapsed**: The +40% ROI headline (from the May 25 hyperparameter sweep) dropped to +5.2% out-of-sample with flagship cells inverting sign. The score was overfit to the training window's specific slate composition.

**ML meta-labels dominated by single threshold**: Five independent quant lenses confirmed that every ML-based signal overlay was either leakage (using post-settlement data) or strictly dominated by the single hand-set odds threshold (Gate 1: skip odds < 4).

**Two root methodology errors** created the entire false-theory edifice: (a) using settlement-time ltp/bsp as staking signals = temporal leakage, and (b) treating correlated within-day picks as independent = ~26x CI inflation. See [[concepts/superwin-pick-non-independence-methodology]] for the full statistical correction.

## Related Concepts

- [[concepts/superwin-racing-profitability-dimensions]] - The 16-dimension analysis that produced the over-fitted "formulas"; the honest-math day data forces reclassification of all prior findings
- [[concepts/resolver-pnl-formula-mug-run2nd3rd-bugs]] - The PnL formula fixes that revealed the true (negative) aggregate ROI; all pre-fix profitability numbers are unreliable
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal whose insert-only pattern preserves first-detection odds; contaminated by broken PnL formulas until May 29 fix
- [[concepts/racing-mult-clv-blindness-settlement-audit]] - The racing-mult audit from the same day showing -26% ROI with inverse EV correlation — consistent with the over-fitting diagnosis
- [[concepts/superwin-execution-gap-price-band-discipline]] - The execution gap analysis (scanner +15% but actual -14%) is a separate phenomenon from the measurement correction; both contribute to the real vs apparent performance divergence

## Sources

- [[daily/lcash/2026-05-30.md]] - First honest-math day: -339u/-34.1% ROI on 994 settled picks; prior +198u/+20% was partial-day over broken math; "winning formula" for BoostBet run-2nd-3rd was over-fitted from ~100 signal slices; edge-research 9 learnings reclassified as hypotheses; anti-pattern "every question gets an answer"; 7-14 day staking pause (Session 09:53)
- [[daily/lcash/2026-06-01.md]] - 5-agent quant lens confirmed: OL_ltp "single most valuable signal" was 100% suspension-LTP artifact (leakage); Confirmation Score collapsed +40%→+5.2% OOS with flagship cells inverting; ML meta-labels strictly dominated by single odds threshold; full back+lay hedging is leakage tautology; two methodology errors identified (settlement-time leakage + pick independence violation ~26x CI inflation); day-as-unit t-test adopted as honest methodology (Session 15:04)
