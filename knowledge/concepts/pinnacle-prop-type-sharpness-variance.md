---
title: "Pinnacle Prop-Type Sharpness Variance"
aliases: [pinnacle-sharpness, prop-type-edge, pinnacle-brier, per-prop-calibration]
tags: [value-betting, pinnacle, methodology, calibration, prediction-markets]
sources:
  - "daily/lcash/2026-04-16.md"
  - "daily/lcash/2026-04-17.md"
  - "daily/lcash/2026-04-18.md"
  - "daily/lcash/2026-04-19.md"
created: 2026-04-16
updated: 2026-04-19
---

# Pinnacle Prop-Type Sharpness Variance

Pinnacle's sharpness varies dramatically by prop type within the same sport. On NBA player props, Pinnacle-only picks produced -4.2% ROI overall (169 picks), but the breakdown by prop type reveals extreme variance: Threes at +27.9% ROI (36 picks, genuinely sharp) versus Assists at -45.7% to -50.4% ROI (catastrophically weak). Pinnacle's Brier score on props is 0.2695, confirming weak overall calibration. Pinnacle's real strength is game lines (moneyline, spread, total), not player props.

## Key Points

- Pinnacle NBA player props overall: -4.2% ROI (79-86 record, 169 picks), positive CLV (+1.16%) but insufficient edge
- Threes props: **+27.9% ROI** (36 picks) — Pinnacle is genuinely sharp on this market
- Assists props: **-45.7% to -50.4% ROI** — catastrophically weak, actively harmful to include
- Pinnacle Brier score on props: 0.2695 — weak calibration compared to traditional sharps
- Traditional sharps (BetRivers, Hard Rock) outperform Pinnacle on player props: Aggressive theory=130 picks, Calibrated=71, while Pinnacle=0 at min_ev=5
- Blanket "Pinnacle is sharp" assumptions are dangerous — sharpness must be validated per prop type

## Details

### The Uniform Sharpness Assumption

Pinnacle is widely considered the sharpest sportsbook globally, with tight lines, low margins, and high-limit acceptance that makes its prices the industry benchmark for "true odds." This reputation is well-earned for game lines — moneyline, point spread, and totals — where Pinnacle's high liquidity and sophisticated market-making consistently produce lines close to true probabilities.

The value betting scanner's Pinnacle prediction-market theory (see [[concepts/pinnacle-prediction-market-pipeline]]) extended this assumption to player props, using Pinnacle's lines as the sharp reference against prediction market soft books (Kalshi, Polymarket). The assumption was: if Pinnacle is sharp on game lines, it should be sharp on player props too.

### The Per-Prop Breakdown

EV pipeline dropout logging (see [[concepts/ev-pipeline-dropout-logging]]) confirmed the pipeline was working correctly — markets flowed through all stages without errors. The issue was that Pinnacle simply doesn't produce large edges against prediction markets on player props. When min_ev was lowered from 5 to 1 to capture marginal edges, the full breakdown became visible:

| Prop Type | ROI | Record | Assessment |
|-----------|-----|--------|------------|
| Threes | +27.9% | ~36 picks | Genuinely sharp — keep |
| Points | Mixed | ~50 picks | Marginal, needs more data |
| Rebounds | Mixed | ~30 picks | Marginal |
| Assists | -45.7% to -50.4% | ~25 picks | Catastrophically weak — exclude |
| Overall | -4.2% | 79-86 (169) | Negative — props not Pinnacle's strength |

The extreme variance between Threes (+27.9%) and Assists (-50.4%) within the same sport, same bookmaker, and same pipeline demonstrates that "Pinnacle is sharp" is not a property of the book — it's a property of specific markets within the book.

### Why the Variance Exists

Pinnacle's edge comes from its market-making operation: high limits attract sharp bettors, whose action moves the line toward true probability. For player props, this mechanism works differently across prop types. Threes markets attract significant sharp action (threes betting has become a sophisticated analytics-driven market), while Assists markets receive less sharp volume and may be priced more conservatively or less precisely by Pinnacle's algorithms.

Prediction markets (Kalshi, Polymarket) price NBA player props with their own liquidity dynamics. On markets where Pinnacle is weak (Assists), the prediction market prices may actually be closer to true probability than Pinnacle's — meaning the "sharp vs soft" framing is inverted.

### Pipeline Efficiency Confirmation

The dropout analysis confirmed that the low pick count was not a pipeline bug. Of 2,456 total markets: 734 were live-filtered, 855 were prop-type-filtered, 569 had no soft book entry, 50 had line gaps too wide, 298 reached EV evaluation, 247 had negative EV, 1 was below threshold, and 0 passed at min_ev=5. The pipeline correctly evaluated markets; the market was simply efficient enough that Pinnacle devig produced near-zero edges against prediction markets at the prop level.

### Implications for Theory Configuration

The discovery that sharpness varies by prop type has direct implications for theory system design:

1. **Per-prop-type filtering**: The Pinnacle theory should exclude Assists (and potentially other weak prop types) rather than evaluating all props uniformly
2. **Per-prop-type sharp assignment**: Future theory configurations could assign different sharp weights to Pinnacle based on prop type — high weight for Threes, low or zero for Assists
3. **Alternative sharp references**: For prop types where Pinnacle is weak, traditional sharps (BetRivers, Hard Rock) via OpticOdds may be better references than Pinnacle
4. **min_ev=1 trail data**: The lowered threshold captures marginal edges for ongoing calibration analysis, allowing per-prop-type performance to be tracked over time

### Early Resolved Pick Profitability (2026-04-17)

On 2026-04-17, a profitability deep dive on 110 resolved Pinnacle picks provided the first forward validation of the prop-type variance hypothesis. Overall ROI was +0.8% — roughly breakeven, consistent with the -4.2% figure from the 169-pick sample (small sample variance). The per-prop breakdown confirmed the Threes signal:

- **Threes on Sportsbet**: **+28.7% ROI** (n=19) — the strongest individual prop/book combination, consistent with the earlier +27.9% figure and now validated against resolved outcomes rather than just devigged EV estimates
- **Other prop/book combinations**: no statistically significant signal in either direction at the current sample size

The Sportsbet Threes signal is notable because it suggests the edge is not just Pinnacle-specific but book-specific: Sportsbet (book 900) appears to misprice Threes props more than other AU soft books relative to Pinnacle's sharp line. This is consistent with the AFL circular devig analysis (see [[concepts/afl-circular-devig-trap]]) where Sportsbet had the best calibration (50.7% WR) — the implication is that Sportsbet prices different markets with different quality, being accurate on some (AFL Disposals) and exploitable on others (NBA Threes).

With only 110 resolved picks, these results are directional, not conclusive. The recommended threshold for strategy-level conclusions is 400+ resolved picks. The edge may prove to exist only in specific prop/book combinations (Threes on Sportsbet) rather than as a broad Pinnacle-vs-prediction-market phenomenon. Ongoing trail collection at min_ev=1 will provide the data for this determination.

### NHL AU Book Efficiency (2026-04-18)

On 2026-04-18, NHL was added to the dashboard as part of the Pinnacle pipeline expansion. Investigation of 381 NHL markets with sharp data revealed that **Australian soft books are efficient on NHL** — unlike NBA/MLB where AU books lag behind sharp lines, Sportsbet prices NHL props tightly against sharps, producing near-zero exploitable edges at a 2% EV threshold.

Of 354 NHL markets with both sharp and soft book data, only 3 passed the +EV threshold, and all 3 were false positives from line mismatches (not genuine value). This contrasts sharply with NBA and MLB, where hundreds of picks pass the same threshold.

A separate limitation was identified for NHL: **one-sided props (NHL Goals = Over-only) cannot be devigged** with the standard Over/Under pair method used in the dashboard's JavaScript. 168 NHL markets were unpaired because Goals props are inherently one-sided (booking the Under on "Player Scores 0.5+ Goals" is rarely offered). A dedicated one-sided consensus devig method exists server-side but is not yet implemented in the dashboard JS, leaving these markets unevaluable on the client side.

This finding extends the sharpness variance principle from per-prop-type to **per-sport**: market efficiency in AU soft books varies not just by what is being bet (Threes vs Assists) but by which sport is being bet (NBA/MLB exploitable, NHL efficient). The implication is that theory configurations should not assume uniform exploitability across sports, even when using the same sharp-vs-soft pairing methodology.

### NHL Dashboard Integration Confirmation (2026-04-19)

On 2026-04-19, NHL dashboard integration was fully validated. Of 381 NHL markets with sharp data, 309 had no soft book match at all, and the 3 that passed the +EV threshold were all false positives from line mismatches (100%+ EV — a clear interpolation artifact, not genuine value). Most NHL Goals markets are unpaired (Over-only) and require `one_sided_consensus` devig method, which is not yet implemented in the dashboard JS — this explains why the NHL pill shows only 2 dashboard picks.

Adding `nhl` to `ACTIVE_SPORTS` required updating three config layers on the VPS: (1) code defaults, (2) `.env` file, (3) systemd `Environment=` directive. The systemd layer takes highest precedence and was the actual blocker — see [[concepts/configuration-drift-manual-launch]] for the full config precedence analysis. SSE-discovered leagues (auto-appended during `_sse_startup()`) do not need manual addition to ACTIVE_SPORTS, but core sports like NHL do.

## Related Concepts

- [[concepts/pinnacle-prediction-market-pipeline]] - The pipeline that exposed prop-type variance when it produced 0 picks at min_ev=5
- [[concepts/ev-pipeline-dropout-logging]] - The diagnostic tool that confirmed the pipeline was working correctly
- [[concepts/afl-circular-devig-trap]] - Another case where "sharp" book calibration varied dramatically (Bet Right 34% WR vs Sportsbet 50.7%)
- [[concepts/value-betting-theory-system]] - The theory system that needs per-prop-type sharp configuration
- [[concepts/opticodds-critical-dependency]] - Pinnacle data flows through OpticOdds; prop-type weakness adds a quality dimension beyond availability risk
- [[concepts/betting-window-roi-methodology]] - The analytics methodology used to compute the resolved pick profitability figures
- [[concepts/alt-line-mismatch-poisoned-picks]] - Prediction market alt-line mismatches inflate some prop EVs; must be controlled for before drawing profitability conclusions

- [[concepts/tracker-optimistic-id-poisoning]] - NHL game-line expansion triggered the staged IDs bug when game-total markets had empty player_name
- [[concepts/one-sided-consensus-structural-bias]] - One-sided consensus devig is the correct method for NHL Goals (Over-only) but is not yet implemented in the dashboard JS
- [[concepts/resolver-sequential-sport-bottleneck]] - NHL was added to ACTIVE_SPORTS on 2026-04-19, which affects both tracker evaluation and resolver scheduling

## Sources

- [[daily/lcash/2026-04-16.md]] - Pinnacle NBA props -4.2% ROI overall; Threes +27.9%, Assists -45.7% to -50.4%; Brier 0.2695; dropout analysis 2456→0 at min_ev=5; min_ev lowered to 1 for trail capture; traditional sharps (BetRivers, Hard Rock) outperform on props; NHL identified as next viable sport but only game-line overlap (Sessions 13:04, 13:38, 16:30, 20:38)
- [[daily/lcash/2026-04-17.md]] - 110 resolved Pinnacle picks: +0.8% ROI overall; Threes on Sportsbet +28.7% (n=19) is only clear signal; need 400+ picks before strategy-level conclusions; edge may be prop/book-specific not broad (Session 22:16)
- [[daily/lcash/2026-04-18.md]] - Sharp CLV theory ranking across 7,724 resolved picks: AltLine-V1 +28.4% CLV (sharpest), Conservative 72.7% CLV>0 rate (most consistent), Aggressive-Wide -9.3% (no edge despite 62% WR); MLB Calibrated +6.4% CLV and MLB Conservative +6.5% CLV confirmed as sharpest MLB theories; sharp CLV validated as superior to soft CLV (~0% for AU books) (Sessions 17:04, 17:35, 21:07). NHL AU book efficiency: 381 markets, 354 with both sharp+soft, only 3 +EV (all false positives); Sportsbet prices NHL tightly; 168 one-sided Goals markets unevaluable without one-sided devig in dashboard JS (Session 22:20)
- [[daily/lcash/2026-04-19.md]] - NHL dashboard integration confirmed: 309/381 markets had no soft book match; 3 that passed +EV were false positives (100%+ EV from line mismatches); NHL Goals Over-only markets need `one_sided_consensus` devig method (not yet implemented as dashboard-side theory); NHL doesn't warrant special +EV attention — AU soft books too sharp; `nhl` added to ACTIVE_SPORTS across code defaults, .env, and systemd service (Sessions 07:26, 07:57)
