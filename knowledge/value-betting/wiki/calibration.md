# Calibration

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> How devig weights and parameters are optimized for accuracy.

---

## The Calibration Target

The scanner's accuracy is measured by how well predicted probabilities match actual outcomes. The primary benchmark is **BetIQ** — Jay has been profiting using BetIQ, so matching their EV is the calibration gold standard.

---

## Metrics

| Metric | Formula | What It Measures | Good Value |
|--------|---------|-----------------|------------|
| **Brier Score** | `mean((pred_prob - actual)^2)` | Probability calibration | < 0.20 |
| **Log Loss** | `-mean(actual*log(pred) + (1-actual)*log(1-pred))` | Probability discrimination | < 0.65 |
| **Hit Rate** | `wins / (wins + losses)` | Simple accuracy | > 52% (for typical odds) |
| **CLV** | `(closing_odds / opening_odds - 1) * 100` | Line movement in our favor | > 0% |
| **ROI** | `(profit / total_wagered) * 100` | Actual profitability | > 0% |
| **RMSE vs BetIQ** | `sqrt(mean((our_ev - betiq_ev)^2))` | Calibration vs benchmark | Lower = better |

**Source:** `ev_scanner/metrics.py` (~3.2KB)

---

## Calibration Tools

### calibrate_weights.py (~34KB)
Grid search + scipy differential evolution to find optimal parameters:
- Sweeps all 4 devig methods × sharp book weight profiles
- Evaluates each combo against historical resolved picks
- Ranks by Brier score (primary) and log loss (secondary)
- Writes top configs to `nba_optimization_runs` as candidate theories

### backtest.py (~34KB)
Simulates the pipeline through a historical period:
- Input: date range, theory config, sport
- Replays odds data, applies devig, generates hypothetical picks
- Measures: hit rate, CLV average, ROI
- Output: `backtest_results/*.json`

### comparator.py (~7.6KB)
Side-by-side comparison of our picks vs BetIQ:
- Matches picks by player + prop + side + line
- Shows: our_ev, betiq_ev, betstamp_ev, delta
- RMSE and average delta in dashboard summary

---

## Known Calibration Findings

### Sharp Book Weights (from BetIQ reverse engineering)
- BetRivers (802) is the sharpest for player props — weight 1.0
- FanDuel (100) and Pinnacle (250) are overrated for props — weight 0
- PropBuilder (125) is underrated — weight 0.95

### EV Gap
Our EV runs 3-10% lower than BetIQ's for shared picks. The gap is likely:
- Different devig method emphasis (BetIQ may lean more additive)
- Different book selection for consensus markets
- Different interpolation approach

### What Works
- Multiplicative + Power blend works well for NBA
- Theory system enables rapid iteration
- Trail_entries provides clean historical data for backtesting

---

## Related Pages
- [[theories]] — What calibration produces
- [[devig-engine]] — What calibration optimizes
- [[ev-calculation]] — The metric being calibrated
