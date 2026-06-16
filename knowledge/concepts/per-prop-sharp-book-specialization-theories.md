---
title: "Per-Prop Sharp Book Specialization and Theory Deployment"
aliases: [per-prop-sharps, sharp-specialization, nba-prop-specialists, theory-deployment-june-2026, book-id-mapping-completion]
tags: [value-betting, methodology, sharp-books, theory-system, deployment, devig]
sources:
  - "daily/lcash/2026-06-03.md"
created: 2026-06-03
updated: 2026-06-03
---

# Per-Prop Sharp Book Specialization and Theory Deployment

On 2026-06-03, lcash deployed 4 new value-betting theories to production based on a comprehensive 5-window sharpness calibration study. The key finding: different sportsbooks are sharp on different prop types — there is no universally sharpest book. PointsBet AU (903) is a combo specialist, TAB (908) is a single-stat specialist, Sportsbet (900) is the Points/Threes anchor, Hard Rock (803) excels at combos + Threes player-correlation, and BetMGM (800) is the Assists specialist. Novig (192) drops from #1 at closing to #11 at the stake window — a "late-sharpener" useless for live betting. Power devig won approximately 71% of #1 spots across the full sport-by-prop matrix.

## Key Points

- 4 theories deployed to production: MLB-Counts-Coolbet-v1, MLB-Batters-BetMGM-v1, NBA-Single-TAB-Sportsbet-v1, MLB-Hits-MultiBook-v1 — all using power devig
- All 10 previously-unidentified book IDs were mapped: 804 Fanatics, 805 Betway, 806 Unibet, 809 Heritage, 810 theScore, 811 Bodog, 812 LowVig — these were already present in production code but missing from analysis scripts
- Coolbet (397), Sportsbet (900), Neds (901), PointsBet AU (903), and TAB (908) added to `SHARP_BOOK_IDS` — safe because the engine defaults to weight 0.0 for unweighted books at engine.py:294
- `v3/core/models.py` and `ev_scanner/models.py` had drifted (v3 was missing BetOnline 813) — both files were synced as part of the deployment
- Power devig is used universally rather than per-prop optimization — over-fitting on noise-level Brier score differences has negative expected value
- Per-prop NBA theories (Assists, Combos, Rebounds-only) deferred until backtest sample size exceeds 10 picks, expected in approximately 2-3 weeks

## Details

The NBA sharp specialist breakdown reveals meaningful specialization across books. PointsBet AU dominates combo props (PRA, PR, PA) while TAB leads on single-stat props (Points, Rebounds, Assists individually). Sportsbet anchors the Points and Threes markets, Hard Rock shows strength in combo and Threes player-correlation markets, and BetMGM owns the Assists niche. This specialization pattern means that a single-sharp-book theory leaves significant edge on the table — the optimal approach is per-prop-type sharp selection, which the new theories implement. The decision to skip per-prop devig method optimization was deliberate: while shin and power devig showed different Brier scores across prop types, the differences fell within bootstrap confidence intervals, making per-prop devig selection pure over-fitting on noise.

The theories use a "shadow tracker" deployment model where the theories themselves serve as the shadow — picks flow through the existing engine and tracker infrastructure, accumulating trail data and results without any real money at risk. The validation plan has three phases: a 24-48 hour volume check to confirm picks are generating at expected rates, a 2-week PnL comparison against backtest projections using the same market conditions, and a 3-week true out-of-sample test with a pre/post 2026-06-15 split to ensure no lookahead bias from the calibration study. Only after passing all three gates would theories be promoted to live betting.

## Related Concepts

- [[concepts/sharp-clv-theory-ranking]] - The sharpness calibration methodology used to identify per-prop specialists
- [[concepts/theory-aware-sharp-book-filtering]] - How the engine filters sharp books per theory
- [[concepts/trail-change-detection-architecture]] - Trail system that validates theory performance over time

## Sources

- [[daily/lcash/2026-06-03.md]] - Sessions 09:20, 09:28, 09:41 (sharpness calibration study and book ID mapping), 11:02, 11:47 (theory deployment iterations and validation plan)
