---
title: "SuperWin Racing Profitability Dimensions"
aliases: [racing-profitability, harness-dominance, liquidity-goldmine, mode-analysis, edge-theories]
tags: [superwin, racing, analytics, methodology, backtesting]
sources:
  - "daily/lcash/2026-04-27.md"
  - "daily/lcash/2026-04-29.md"
  - "daily/lcash/2026-04-30.md"
created: 2026-04-27
updated: 2026-04-30
---

# SuperWin Racing Profitability Dimensions

A comprehensive 16-dimension profitability analysis across 487 SuperWin edge picks revealed clear, actionable signals for optimal betting filters. The analysis was performed on 2026-04-27 across race type, bookie, mode, liquidity, EV band, detection timing, CLV direction, and composite filters. The dominant finding is that **harness racing generates 83% of all profit from only 21% of picks** at +152% ROI, and the **$750-$1K Betfair liquidity band** is the goldmine at +170% ROI with +28% CLV.

## Key Points

- **Harness = 83% of all profit** from 21% of picks. 27% win rate, +152% ROI. Harness markets are structurally less efficient than thoroughbred or greyhound
- **Market efficiency cliff at ~$1,500 matched**: below = +62% ROI, above = -9% ROI. The $750-$1K liquidity band is the optimal zone at +170% ROI
- **Cash Multiplier mode (TAB, 1.1x boost)** has highest win rate (24%) and best ROI (+70.3%) with lowest avg liquidity ($1,523) — finds edge in thin markets
- **SuperPicks** generates most picks but lowest CLV (+4%) — edge partly manufactured by boost, not purely market mispricing
- **Normal odds mode** has best CLV (+14.2%) — when it fires, the bookie is genuinely mispriced
- **EV sweet spot is 12-15%**: below 12% is noise (-18.7% ROI), above 15% is unreliable (breakeven)
- **4-5 detection scans = sustained edge** at +108% ROI; single scans are noise
- **Positive CLV = real edge**: +164u/+54% ROI (positive CLV) vs +23u/+13% (CLV<=0)
- **Optimal composite filter**: Cash Multiplier + Harness + liq >= $500 + scans >= 2 = **339% ROI** (17 picks, 47% WR — small sample, needs validation)

## Details

### Race Type Analysis

The most striking finding is the dominance of harness racing. Across all 487 picks:

| Race Type | % of Picks | Win Rate | ROI | % of Profit |
|-----------|-----------|----------|-----|-------------|
| Harness | 21% | 27% | +152% | 83% |
| Thoroughbred | ~40% | ~20% | +21.9% | ~10% |
| Greyhound | ~39% | ~15% | -29.3% | Negative |

Harness markets are structurally less efficient for several reasons: lower overall betting volume, fewer sophisticated bettors, and less market-maker coverage on Betfair. The TAB and TabTouch price harness events using internal models rather than reacting to exchange prices, creating persistent mispricings that the scanner can detect.

Greyhounds are consistently unprofitable despite appearing to offer edge — the high-frequency racing (dozens of events per day) and thinner markets mean that detected edges evaporate faster than they can be acted upon.

### Liquidity Bands

The liquidity-efficiency inverse documented in [[connections/liquidity-efficiency-inverse-in-betting]] is confirmed with more granular data:

| Betfair Matched | ROI | CLV | Assessment |
|-----------------|-----|-----|------------|
| $200-$500 | +40% | +10% | Low liquidity, real edge but execution risk |
| $500-$1K | +62% | +15% | Sweet spot — enough liquidity, thin enough for edge |
| **$750-$1K** | **+170%** | **+28%** | Goldmine band |
| $1K-$5K | ~0% | +5% | Edge eroding from increased efficiency |
| $5K+ | -40.5% | -5% | Efficient markets — boost cannot overcome vig |

The $750-$1K band is where edge and executability intersect: enough Betfair liquidity to confirm the market exists and is tradeable, but thin enough that bookie mispricings haven't been arbitraged away.

### Mode Analysis

Three distinct edge modes produce picks with different characteristics:

| Mode | Win Rate | ROI | CLV | Mechanism |
|------|----------|-----|-----|-----------|
| Cash Multiplier | 24% | +70.3% | +8% | TAB 1.1x boost on thin markets |
| SuperPicks | 18% | +38.6% | +4% | Boosted odds from bookie promotions |
| Normal odds | 16% | +25% | +14.2% | Genuine bookie mispricing, no boost |

Cash Multiplier's edge comes from finding markets where TAB's flat 1.1x multiplication creates value. The low avg liquidity ($1,523) confirms it finds edge in thin markets where the 10% boost overcomes thin margins. SuperPicks generates the most volume but its edge is partly manufactured by the boost itself — the CLV is lower because the underlying mispricing is smaller. Normal odds has the best CLV because every detected edge represents genuine bookie mispricing without any boost assistance.

### Detection Scan Persistence

How many consecutive scan cycles detect the same opportunity:

| Scans | ROI | Assessment |
|-------|-----|------------|
| 1 | ~0% | Noise — fleeting data artifact |
| 2-3 | +40% | Real but unstable edge |
| **4-5** | **+108%** | Sustained edge — market confirms |
| 6+ | +50% | Edge starting to close, market catching up |

A single detection scan is unreliable — it could be a momentary data lag, a Betfair tick glitch, or a scanner artifact. When the same edge persists across 4-5 scans (20-25 seconds at 5s intervals), it represents a genuine, sustained mispricing that the market hasn't yet corrected. Beyond 6 scans, the market begins to correct (either the bookie adjusts or Betfair moves), reducing the edge.

### Edge Theories Document

10 backtesting theories were codified in `edge-pick-theories.md` for weekly validation as the sample grows:

1. Harness-only filter
2. Cash Multiplier + Harness composite
3. Liquidity $500-$1K band
4. Detection scans >= 3
5. CLV-positive filter
6. EV band 12-15%
7. Mode-specific (Normal odds only)
8. Time-of-day (early morning vs afternoon)
9. Venue-specific (some venues consistently profitable)
10. Cash Multiplier + Harness + liq >= $500 + scans >= 2 (optimal composite)

### Day 6 Theory Validation and Fragility (Session 22:52)

The evening of 2026-04-27 produced the worst single-day result in the scanner's history: **341 picks, 44 winners, -112 units**. Cumulative P/L dropped from +181u to +68.8u across 769 total picks. Several theories built on the initial 487-pick dataset were directly contradicted:

| Theory | Initial Finding | Day 6 Result | Assessment |
|--------|----------------|-------------|------------|
| Theory 5 ($8-12 odds sweet spot) | Strongest odds band | **$3-5 was only profitable range**; longshots ($8-20) collapsed to 1.5% WR | Contradicted — likely overfitted |
| Theory 6 (5-10min MTJ) | Recommended window | **1-2min MTJ was ONLY profitable window** (+129% ROI, 35% WR) | Contradicted — near-jump edges stronger |
| Harness dominance | 83% of profit, +152% ROI | **-30u today** (first losing day), ROI halved from 152% to 69% | Weakened — downgraded STRONG to MODERATE |
| Sunday-is-best | Best day historically | **Worst day recorded** (-112u) | Contradicted |

The **CLV paradox** is the most analytically important finding: CLV was +12% on the day (genuine mispricings were found), but results were -109u on CLV>0 picks. This demonstrates that positive CLV is a necessary condition for edge but not sufficient for daily profitability — variance over 341 picks (3x normal volume from time gate removal + evening greyhounds) can overwhelm a real edge in a single session.

The 341-pick volume itself was a consequence of removing the 2-minute time gate (see [[concepts/superwin-edge-pick-backtesting]]) and capturing evening greyhound meetings. Higher volume amplifies variance in both directions — the same time gate removal that captured profitable 1-2min MTJ picks also exposed the scanner to 3x the usual loss potential.

The best-performing filter on this difficult day was **Cash Multiplier + liquidity >= $750 + MTJ < 2 minutes**, producing 38% win rate and +93% ROI — a different optimal combo than the initial analysis suggested (which emphasized scans >= 2 and liq >= $500).

### Current Sample Limitations

769 picks across 6 days provides a larger dataset but the Day 6 results underscore the danger of premature theory formation. The initial 487-pick analysis identified clear signals that appeared robust (harness dominance, $8-12 odds, 5-10min MTJ) — but a single bad day contradicted three of the ten codified theories. The harness dominance and $750-$1K goldmine remain the most durable signals, but even harness showed its first losing day. An estimated 2,000+ picks (~2-3 more weeks) are needed before strategy-level decisions should be made, and theory validation should focus on signals that survive bad days rather than optimize for good days.

## Related Concepts

- [[concepts/superwin-edge-pick-backtesting]] - The backtesting infrastructure that produced this data; the analysis is the empirical output of the system documented there
- [[connections/liquidity-efficiency-inverse-in-betting]] - The $5K+ = -40.5% ROI finding confirms and extends the liquidity-efficiency inverse pattern across a larger dataset
- [[concepts/scanner-warmup-false-ev-guard]] - The warmup guard prevents false picks from contaminating this analysis; confirmed working during multiple service restarts on 2026-04-27
- [[concepts/sharp-clv-theory-ranking]] - CLV as primary metric for theory ranking; positive CLV correlates strongly with profitability (54% ROI vs 13% when CLV<=0)
- [[concepts/trail-change-detection-architecture]] - Trail data underpins the detection scan analysis; the 3% EV-change threshold means scan persistence measures genuine sustained edge, not just repeated observation of the same cached value

## Sources

- [[daily/lcash/2026-04-27.md]] - Comprehensive 16-dimension profitability analysis across 487 picks: harness=83% of profit from 21% of picks (+152% ROI), $750-$1K Betfair liquidity goldmine (+170% ROI, +28% CLV), Cash Multiplier best mode (+70.3% ROI), 4-5 detection scans = +108% ROI, EV sweet spot 12-15%, positive CLV = +54% ROI, optimal composite filter at 339% ROI (17 picks); 10 theories codified in edge-pick-theories.md (Session 13:36). Day 6 validation: 341 picks, -112u worst day; 3 of 10 theories contradicted ($8-12 odds → $3-5 profitable, 5-10min MTJ → 1-2min only profitable, harness first losing day -30u ROI halved to 69%); CLV paradox +12% CLV but -109u; volume amplification from time gate removal; Cash Multi + liq≥750 + MTJ<2 = 38% WR, +93% ROI; cumulative 769 picks +68.8u (Session 22:52)
- [[daily/lcash/2026-04-29.md]] - Expanded to 8D matrix with trail-derived dimensions (EV trajectory, volatility, lay depth, speed to peak); 60% of picks lack trail data (45% pre-deploy Apr 23-26, 15% single-scan); 3% EV threshold NOT the bottleneck (only 19 picks blocked); single-scan picks confirmed noise at -29% ROI / -43u; **Harness + $12-20 + liq$500-1.5K + mtj 2-10min + sc2+** = 485% ROI on 10 picks; CLV is portfolio filter not pick predictor (76% of profit from CLV≥15%); CLV×Liquidity interaction: liq $500-1.5K + CLV 0-10% = +128% ROI; ev_flat + vol_med consistently profitable (Session 12:02)
- [[daily/lcash/2026-04-30.md]] - 993-pick reassessment: efficiency cliff at $1.5K now **negative** (-2.1% ROI on 388 picks above threshold) — not just low edge, actively losing money. Normal mode underperforming (-5% ROI, -11u) while Cash Multiplier (+20% ROI) and SuperPicks (+20.4% ROI) carry portfolio. Best single day: +91.9u, +45% ROI on 215 picks (45 winners). 8D combos have insufficient sample (10-39 picks each) — need 50+. Next reassessment milestone: 2,000 picks (est. next week). Broader theories (T1-T4 at 150-320 picks) are reliable signal; 8D combos are hypothesis-stage (Sessions 12:30, 15:51)
