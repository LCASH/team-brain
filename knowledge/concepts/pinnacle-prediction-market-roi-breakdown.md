---
title: "Pinnacle Prediction Market ROI Breakdown"
aliases: [prediction-market-roi, pinnacle-roi-analysis, sport-prop-roi, league-deactivation]
tags: [value-betting, analytics, roi, prediction-markets, pinnacle, methodology]
sources:
  - "daily/lcash/2026-04-21.md"
created: 2026-04-21
updated: 2026-04-21
---

# Pinnacle Prediction Market ROI Breakdown

A comprehensive ROI analysis of the Pinnacle prediction market pipeline — using Pinnacle as the sharp reference against Kalshi and Polymarket as soft books — showing **+8.1% ROI and +92.8 units across 1,146 picks**. The analysis revealed extreme variance by sport, league, and prop type, with MLB Home Runs as the most profitable edge (+46.4% ROI) and several leagues identified for deactivation (LoL -31.9%, NHL -21.0%, ATP Challenger -34.3%). The ROI methodology was updated to use average positive-EV odds instead of peak odds for more realistic bettor economics.

## Key Points

- Overall Pinnacle vs prediction markets: **+8.1% ROI, +92.8 units, 1,146 picks** — a clearly profitable strategy
- **MLB Home Runs** is the single best edge: +46.4% ROI at average odds of 6.26 — Kalshi/Polymarket massively overprice Home Run props
- **NBA Rebounds** strong at +32.6% ROI — Pinnacle is sharper than prediction markets on rebounds
- Moneyline overall still profitable (+5.0% ROI, +32.1u) even though NBA moneyline specifically is -6.7% — prediction markets price NBA game outcomes better than props
- **Losing leagues to deactivate:** LoL (-31.9%), NHL (-21.0%), ATP Challenger (-34.3%) — saves ~34 units going forward
- **Profitable leagues:** MLB (+15.6%), Dota 2 (+53.2%), NBA (+6.2%), Valorant (+37.5%), ATP Tennis (+33.0%), China CBA (+28.6%)
- ROI metric changed from peak odds to average +EV odds — more realistic representation of actual bettor returns

## Details

### Methodology Update: Average +EV Odds

The trail ROI page previously calculated ROI using peak odds — the highest odds observed during the entire trail period. This overstated returns because a bettor would need to place the bet at the exact moment of peak pricing, which is rarely achievable. The updated methodology uses **average positive-EV odds** across the entire +EV window, representing the expected odds a bettor would realistically achieve by placing the bet at an arbitrary point within the window.

This change affects all trail ROI metrics (headers, cards, and calculations on `trail-roi.html`) and produces more conservative but more honest ROI figures. The +8.1% overall ROI is computed using this corrected methodology.

### Per-Sport/League Breakdown

The analysis focused exclusively on Pinnacle-sharp theories against prediction market soft books (Kalshi/Polymarket), excluding other book combinations that would dilute the signal:

| League | ROI | Assessment |
|--------|-----|------------|
| MLB | **+15.6%** | Strong — driven by Home Run prop edge |
| Dota 2 | **+53.2%** | Very strong — small sample, monitor |
| NBA | **+6.2%** | Profitable — prop edges offset moneyline losses |
| Valorant | **+37.5%** | Strong — small sample, monitor |
| ATP Tennis | **+33.0%** | Strong — small sample, monitor |
| China CBA | **+28.6%** | Strong — small sample, monitor |
| LoL | **-31.9%** | Losing — deactivate |
| NHL | **-21.0%** | Losing — deactivate |
| ATP Challenger | **-34.3%** | Losing — deactivate |

The esports results (Dota 2, Valorant positive; LoL negative) are surprising given OpticOdds' limited esports coverage (see [[concepts/opticodds-critical-dependency]]). The positive results may reflect pricing inefficiency in thin markets, but the small samples warrant monitoring before drawing strategy-level conclusions.

### Per-Prop-Type Analysis

Within profitable leagues, specific prop types carry the edge while others are efficiently priced:

| Prop Type | ROI | Avg Odds | Assessment |
|-----------|-----|----------|------------|
| MLB Home Runs | **+46.4%** | 6.26 | Best single edge — prediction markets massively overprice |
| NBA Rebounds | **+32.6%** | — | Pinnacle sharper than prediction markets |
| Moneyline (overall) | +5.0% | — | Profitable aggregate, but varies by sport |
| NBA Moneyline | -6.7% | — | Prediction markets price NBA outcomes well |
| Goals | ~0% | — | No edge — drop |
| Draws | ~0% | — | No edge — drop |
| Strikeouts | -9.1% | — | Slightly negative — monitor |

The MLB Home Runs finding is notable because it aligns with the Crypto Edge analysis (see [[concepts/crypto-edge-non-pinnacle-strategy]]) which identified MLB as the goldmine for prediction market edges. Home Runs at average odds of 6.26 are high-variance bets where prediction markets consistently overprice relative to Pinnacle's sharp line — likely because prediction market participants overweight the excitement factor of home runs.

### Moneyline Divergence

The moneyline result contains an important nuance: overall moneyline is profitable (+5.0%, +32.1u) despite NBA moneyline specifically being -6.7%. This means non-NBA moneyline markets (MLB, soccer, esports) are significantly more profitable, carrying the aggregate. Prediction markets price NBA game outcomes with near-sharp efficiency (consistent with the finding in [[concepts/pinnacle-prop-type-sharpness-variance]] that AU books are efficient on NHL), but are less efficient on other sports' game outcomes.

### League Deactivation Decision

Three losing leagues were identified for immediate theory deactivation in Supabase:

1. **LoL (-31.9%)** — despite being the only esport with odds on OpticOdds, prediction markets price LoL efficiently against Pinnacle
2. **NHL (-21.0%)** — consistent with prior finding that AU books are efficient on NHL; prediction markets similarly efficient
3. **ATP Challenger (-34.3%)** — lower-tier tennis markets don't have exploitable Pinnacle edges against prediction markets

Deactivating these leagues saves an estimated ~34 units of future losses. The deactivation is theory-level (Supabase update, no code change), reversible if market conditions change.

### Trail Coverage Context

Bet365 2.0 trail coverage was at 17% (up from 4% after the pre-seeding bug fix documented in [[concepts/trail-preseeding-coverage-bug]]), but structurally limited at ~10-11% daily regardless of timeframe. This coverage level is sufficient for aggregate ROI analysis but limits individual pick-level trail quality. The 1,146 picks used in this analysis have sufficient trail data for the average +EV odds calculation, though some picks may rely on fewer trail entries than ideal.

### Pending Resolution

360 picks (mostly from Apr 20-21) were pending resolution at the time of analysis. Resolving these will sharpen the per-league and per-prop breakdowns. The MLB and NBA figures are the most statistically robust given their larger sample sizes; esports and niche league results should be treated as directional signals until sample sizes reach 400+ picks per league.

## Related Concepts

- [[concepts/pinnacle-prediction-market-pipeline]] - The pipeline producing the picks analyzed in this breakdown; the ROI validates the strategic thesis
- [[concepts/pinnacle-prop-type-sharpness-variance]] - Per-prop sharpness variance confirmed and extended: Pinnacle is sharper on MLB HRs and NBA Rebounds than prediction markets
- [[concepts/crypto-edge-non-pinnacle-strategy]] - The complementary strategy targeting non-Pinnacle prediction market gaps; MLB identified as goldmine in both analyses
- [[concepts/betting-window-roi-methodology]] - The ROI methodology framework (closing odds, dedup, window filtering) applied here with the peak→average odds update
- [[concepts/sharp-clv-theory-ranking]] - CLV rankings provide the "why" behind the ROI — theories with high sharp CLV should produce positive ROI
- [[concepts/value-betting-theory-system]] - Theory deactivation for losing leagues uses the code-free Supabase configuration

## Sources

- [[daily/lcash/2026-04-21.md]] - ROI metric changed from peak odds to average +EV odds; Bet365 2.0 trail coverage at 17% (up from 4%) but structurally ~10-11%; Pinnacle vs prediction markets overall: +8.1% ROI, +92.8u, 1,146 picks; MLB HR +46.4% (avg odds 6.26), NBA Rebounds +32.6%, moneyline +5.0% (+32.1u); profitable leagues: MLB +15.6%, Dota 2 +53.2%, NBA +6.2%, Valorant +37.5%, ATP +33.0%, CBA +28.6%; losing leagues: LoL -31.9%, NHL -21.0%, ATP Challenger -34.3%; deactivation saves ~34u; Goals/Draws no edge; Strikeouts -9.1%; NBA ML -6.7% despite overall ML positive; 360 pending picks (Session 12:01)
