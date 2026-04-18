---
title: "Crypto Edge Non-Pinnacle Strategy"
aliases: [crypto-edge, non-pinnacle-prediction-markets, pinnacle-coverage-gaps, reverse-arb]
tags: [value-betting, strategy, prediction-markets, dashboard, architecture]
sources:
  - "daily/lcash/2026-04-18.md"
created: 2026-04-18
updated: 2026-04-18
---

# Crypto Edge Non-Pinnacle Strategy

A new betting strategy ("Crypto Edge" pill) in the value betting scanner that targets prediction market opportunities where Pinnacle has no coverage. Instead of using Pinnacle as the sharp reference (the standard approach), this strategy uses DraftKings, Novig, FanDuel, Hard Rock, and BetRivers as sharps against prediction market soft books. The thesis is that everyone arbitrages Pinnacle → prediction markets, so those edges close fast; markets where prediction markets exist but Pinnacle doesn't face less competition, producing longer-lasting edges.

## Key Points

- OpticOdds scan found **1,535 markets** where prediction markets have coverage but Pinnacle doesn't; 1,433 of those have other sharp books available
- MLB is the goldmine (1,354 markets): Pinnacle doesn't list Hits or Hits/Runs/RBIs prop types at all, and covers only 74/249 MLB HR players
- Sharp book hierarchy: DraftKings (1.0), Novig (0.9), FanDuel (0.8), Hard Rock (0.7), BetRivers (0.7)
- Soft books: Kalshi, Polymarket, Polymarket USA, DraftKings Predictions, Underdog, Crypto.com
- Theory config uses `exclude_sharp_books: [250]` filter to skip any market Pinnacle already covers — preventing overlap with the existing Pinnacle pill
- Full tracking + trails + resolver enabled from day 1 for immediate backtesting capability

## Details

### The Strategic Thesis

The Pinnacle prediction-market pipeline (see [[concepts/pinnacle-prediction-market-pipeline]]) uses Pinnacle as the sharp reference to find +EV against prediction markets. While conceptually sound, this approach faces a competitive headwind: Pinnacle is the most widely used sharp reference in the industry, so edges against prediction markets where Pinnacle has coverage are arbitraged away quickly by other value bettors using the same reference.

The Crypto Edge strategy inverts this: find markets where prediction markets (Kalshi, Polymarket) offer odds but Pinnacle doesn't have coverage at all. In these markets, other value bettors who rely on Pinnacle as their sharp reference cannot participate — they literally can't see these markets. This creates a higher barrier to entry and potentially longer-lasting edges.

The name "Crypto Edge" reflects the prediction market platforms' cryptocurrency heritage (Polymarket, Kalshi) and distinguishes the pill from the "Pinnacle" pill on the dashboard.

### Coverage Gap Analysis

A scan of OpticOdds revealed significant gaps in Pinnacle's prop coverage:

- **MLB**: 1,354 markets without Pinnacle coverage. Pinnacle doesn't list Hits or Hits/Runs/RBIs prop types at all — these are among the most liquid prediction market props. For Home Runs, Pinnacle covers only 74 of 249 players that prediction markets offer.
- **NBA**: Blocks, Steals, and Double Double props have prediction market coverage but limited or no Pinnacle coverage
- **NHL**: Game-line markets (totals, puck line, moneyline) have partial gaps

The 1,535 total gap markets represent a substantial universe — comparable in size to the Pinnacle pipeline's full market count. Of these, 1,433 (93%) have at least one other sharp book available (DraftKings, Novig, FanDuel, etc.), making devigging possible even without Pinnacle.

### Sharp Book Hierarchy

Without Pinnacle, the sharp reference is constructed from US-facing sportsbooks known for sharp pricing:

| Book | Weight | Rationale |
|------|--------|-----------|
| DraftKings | 1.0 | Highest liquidity among US books, sharpest pricing |
| Novig | 0.9 | Low-margin book, designed to be close to true odds |
| FanDuel | 0.8 | Second-largest US book, competitive pricing |
| Hard Rock | 0.7 | Emerging sharp reputation |
| BetRivers | 0.7 | Established pricing infrastructure |

This hierarchy is less sharp than Pinnacle, which means the devigged "true odds" will be noisier. However, the thesis is that even noisy sharp references can find genuine edges against prediction markets that are mispriced relative to the broader sports betting market consensus.

### Dashboard Integration

The Crypto Edge pill is separate from the existing Pinnacle pill, giving each strategy its own dashboard view. Three Crypto Edge theories were created (NHL, MLB, NBA), and 215 picks were generated across 14 leagues within the first day — including niche leagues like Japan J1, Korea K1, and MLS that the Pinnacle pipeline also covers.

A cosmetic issue was noted: the "SHARPS: 3" display on some picks is misleading — it shows the count of theories that evaluated the market (3 Crypto Edge theories: NHL, MLB, NBA), not the count of distinct sharp books. The underlying EV calculation is correct; only the display label needs fixing.

### No Immediate Picks as Expected State

The Crypto Edge pill showing 0 picks on its first cycle is the expected behavior — it means the filters are working and not letting garbage through. Prediction market odds often only appear close to game time, so markets 14+ hours out may show no prediction market coverage. Edges are expected to appear as games enter the 24-hour pre-game window.

## Related Concepts

- [[concepts/pinnacle-prediction-market-pipeline]] - The existing Pinnacle pipeline that Crypto Edge complements by targeting non-Pinnacle markets
- [[concepts/value-betting-theory-system]] - The theory system that enables code-free creation of new strategies via Supabase rows
- [[concepts/opticodds-critical-dependency]] - OpticOdds provides the market data for both Pinnacle and Crypto Edge pipelines; its coverage gaps (what it doesn't carry) define the ceiling
- [[concepts/pinnacle-prop-type-sharpness-variance]] - Pinnacle's per-prop sharpness variance is why some props lack Pinnacle coverage entirely
- [[concepts/ev-pipeline-dropout-logging]] - The dropout logging pattern that would help validate Crypto Edge pipeline health

## Sources

- [[daily/lcash/2026-04-18.md]] - Strategic thesis: flip Pinnacle→prediction market approach; 1,535 markets without Pinnacle, 1,433 with other sharps; MLB goldmine (1,354 markets, Hits/HRIs missing from Pinnacle entirely); sharp hierarchy DK(1.0)/Novig(0.9)/FD(0.8)/HR(0.7)/BR(0.7); `exclude_sharp_books: [250]` filter; 215 picks across 14 leagues; "SHARPS: 3" display bug is cosmetic (Sessions 12:31, 13:31, 14:39)
