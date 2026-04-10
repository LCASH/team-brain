# Finding: NBA Bet365 Deep Dive

**Date:** 2026-04-10
**Dataset:** 1,000 NBA resolved picks on Bet365 (book 365 + 366 combined), Mar 27 – Apr 10
**Context:** Jay bets Bet365 specifically (good limits). Focus on building confidence in NBA Bet365 picks.

---

## Headlines

**Overall: 500W/452L (52.5%) across 952 decided picks.** Promising but small sample.

## Bet365 vs Bet365 2.0 — Same Book, Same Picks

On overlapping NBA markets (192 picks), results are **identical** — same outcome on every single pick, odds within 0.009. The -1.9% vs +42.8% ROI gap from the all-sport results was entirely caused by MLB longshot props (stolen bases, home runs) in the direct scraper. **For NBA, both sources are equivalent.**

## EV × Sharp Count Matrix (the key view)

| EV Range | 1 sharp | 2 sharps | 3 sharps | 4 sharps | 5+ sharps | ALL |
|----------|---------|----------|----------|----------|-----------|-----|
| **2-3%** | 38 picks, 55% WR | 40, 50% | 5, 60% | 24, 58% | **23, 74% WR** | 137, 57% |
| **3-5%** | 66, 44% | 42, 55% | 15, 60% | 34, 50% | 46, 39% | 209, 48% |
| **5-7.5%** | 37, 54% | **22, 68%** | **8, 88%** | **8, 75%** | 19, 47% | **97, 61%** |
| **7.5-10%** | 16, 44% | **16, 94%** | 3, 67% | 8, 38% | 2, 100% | **45, 64%** |
| **10-15%** | 16, 50% | **11, 91%** | 5, 100% | 1, 0% | 2, 0% | 37, 62% |
| **15%+** | 4, 50% | 11, 64% | 2, 0% | 3, 67% | - | 20, 55% |

### Key observations:
- **5-7.5% EV with 2-4 sharps is the sweet spot** — 68-88% WR across 38 picks
- **2-3% EV with 5+ sharps: 74% WR** — low EV but high confidence = profitable
- **3-5% EV with 5+ sharps: only 39% WR** — anomalous, needs more data
- **7.5-10% with 2 sharps: 94% WR on 16 picks** — very strong but small sample
- **High EV (10%+) with 4-5 sharps: mostly losing** — confirms the false positive finding from the 1,000 pick analysis
- Sample sizes are small (most cells <50 picks). Need 400+ per cell for confidence.

## Prop Type Performance (NBA Bet365)

| Prop | Picks | WR | CLV | Avg EV |
|------|------:|---:|----:|-------:|
| Double Double | 38 | 76.3% | +1.79% | 9.4% |
| Rebounds | 109 | 59.6% | +0.59% | 3.9% |
| Points Rebounds | 143 | 59.4% | +0.62% | 2.8% |
| Points Assists | 114 | 57.0% | +0.35% | 2.7% |
| Points Rebounds Assists | 113 | 53.1% | +0.37% | 2.5% |
| Points | 81 | 46.9% | +1.05% | 4.6% |
| Assists | 91 | 46.2% | +1.08% | 5.1% |
| Threes | 98 | 40.8% | +1.49% | 3.2% |
| Blocks | 11 | 18.2% | -0.36% | 6.3% |

**Blocks are terrible** (-0.36% CLV, 18% WR). Threes have high CLV (+1.49%) but low WR (40.8%) — longshot profile. Combo props (Pts+Reb, Pts+Ast) perform well at lower EV thresholds.

## Theory Performance (NBA Bet365)

| Theory | Picks | WR | CLV |
|--------|------:|---:|----:|
| Conservative | 17 | 100% | +1.69% |
| Calibrated | 44 | 63.6% | +0.10% |
| NBA OLV Challenger | 16 | 62.5% | +1.48% |
| Aggressive | 760 | 51.3% | +0.90% |
| AltLine-V1 | 22 | 50.0% | +1.28% |

Conservative is perfect but tiny (17 picks). Calibrated at 63.6% on 44 picks is promising. Aggressive carries most volume.

## Implications

1. **Bet365 NBA IS profitable at 52.5% WR** — but needs segment filtering
2. **Don't bet blocks on Bet365** — negative CLV, 18% WR
3. **The 5-7.5% EV range with 2+ sharps looks strongest** — 61-88% WR
4. **High EV (10%+) with many sharps = avoid** — false positive signal
5. **Need 4-5x more data** per bucket cell before high confidence decisions
6. **CLV is positive across most segments** — the edge is real, just small on Bet365

---

## Related Pages
- [[wiki/clv]] — Why CLV matters more than WR at small samples
- [[sports/nba]] — NBA-specific findings (all books)
- [[wiki/performance-tracking]] — The tracking system design these findings inform
