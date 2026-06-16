---
title: "PM Edge Prediction Market Theory"
aliases: [pm-edge, prediction-market-edge-detection, pm-vs-sharp-consensus, kalshi-tail-premium, pm-strict-theory]
tags: [value-betting, prediction-markets, theory, kalshi, polymarket, methodology]
sources:
  - "daily/lcash/2026-05-19.md"
  - "daily/lcash/2026-05-27.md"
  - "daily/lcash/2026-06-03.md"
created: 2026-05-19
updated: 2026-06-03
---

# PM Edge Prediction Market Theory

On 2026-05-19, lcash designed and deployed "PM Edge" theories that compare prediction market (PM) odds as the soft side against the scanner's sharp devigged consensus as truth. This is the inverse of the existing "Crypto Edge" theories (see [[concepts/crypto-edge-non-pinnacle-strategy]]), which use PMs as the truth anchor. The thesis: prediction markets systematically misprice tail events (longshot player props) relative to the sharp sportsbook consensus, creating exploitable +EV opportunities especially on obscure HR (Home Run) markets via Kalshi.

## Key Points

- **Inverse of Crypto Edge**: PM Edge uses PM books (Kalshi, Polymarket) as soft targets devigged against sharp consensus (Pinnacle 1.0, Novig 0.8, FD 0.5, DK 0.5, PB 0.4) — Crypto Edge does the opposite
- **First live cycle produced 45 picks** — 43 Kalshi, 1 Polymarket, 1 Polymarket USA; heavy concentration on MLB HR Over 0.5 with EVs 25-60%
- **Kalshi tail pricing premium**: Kalshi pays a longshot premium on obscure HR markets (e.g., Tristan Peters HR O0.5 at Kalshi 15.57 vs sharp consensus ~9.2) — the signal is real but execution risk is high (thin orderbooks)
- **Phased rollout**: Phase 1 = Strict theories (exact line match, min_ev 3%, min_sharps 2); Phase 2 = Loose variants (+-0.5 line gap, 2% EV) if Strict CLV is positive; Phase 3 = per-PM-book split after 7+ days
- **Concentration risk**: 43/45 picks are Kalshi HR O0.5 — correlated within a slate (weather/park effects), so ~30 picks/night is really 10-15 effective independent samples
- **Backtest will overstate real EV**: picks record top-of-book `opening_odds`, but actual Kalshi depth on obscure HR markets is likely ~$50 — execution at stake gets worse price

## Details

### Theory Design

Two theories were inserted into Supabase's `nba_optimization_runs` table:

- **NBA PM Edge — Strict**: Targets NBA prediction market mispricing against sharp consensus
- **MLB PM Edge — Strict**: Targets MLB prediction market mispricing — the primary edge surface

Both use multiplicative devig with `min_sharps=2` (devigging with only 1 book is too noisy for auto-tracking). Sharp weights mirror the topdown `SHARP_BOOKS` composition: Pinnacle 1.0, Novig 0.8, FanDuel 0.5, DraftKings 0.5, PropBuilder 0.4. Soft books are all prediction market platforms: Kalshi (950), Polymarket (970), Polymarket USA (971), DraftKings Predictions (971), Underdog (980), Crypto.com (981/982).

The key architectural difference from standard theories: PM Edge compares PM odds against the *devigged consensus* (blended multi-book true probability), which is stricter than comparing against any single sharp book. This produces fewer but more defensible picks.

### The Kalshi Tail Premium

Dry-eval on 0 NBA games (thin May off-season slate) and 14 MLB games produced 31-33 picks, all concentrated on Kalshi HR Over 0.5 for low-profile players with EVs ranging 25-60%. The mechanism: Kalshi's prediction market participants systematically overprice the excitement/narrative value of home runs for obscure players. Sharp sportsbooks (Pinnacle, DraftKings) price these events closer to their actuarial probability. The gap creates a consistent longshot premium where Kalshi pays 15.57 on an event the consensus prices at ~9.2.

This pattern is consistent with the finding in [[concepts/pinnacle-prediction-market-roi-breakdown]] that MLB Home Runs is the single best edge at +46.4% ROI — Kalshi's pricing inefficiency on HR markets appears structural rather than transient.

### Execution and Backtesting Risks

Three risks were identified that could make the edge smaller than backtesting suggests:

1. **Thin orderbook liquidity**: Kalshi's obscure HR markets likely have ~$50 of available depth. The pick records `opening_odds` at top-of-book, but placing $100 would move the price significantly. Phase 2 plans an orderbook snapshot side-table (Kalshi `/markets/{ticker}/orderbook`, Polymarket CLOB API) to capture depth at pick-fire time.

2. **PM trail density unknown**: If Kalshi picks get <=2 trail entries before game_start, CLV computes against entry odds (circular/useless). Trail density must be spot-checked after the first overnight cycle.

3. **PM market survivorship**: Investigation in the same day's Session 12:44 found a dramatic survivorship cliff — 70% of PM markets delist within 90 minutes of detection. Only 16.7% remain listed at game time. This is a market characteristic, not a data bug, but it means many picks may not be actionable at execution time.

### Price Validation Strategy

Three approaches were discussed for verifying PM prices are actually fillable:

1. **Orderbook snapshots at pick time** (Phase 2) — automated capture of top-of-book depth when picks fire
2. **Trade replay from on-chain/API data** (Phase 3) — Polymarket positions are on-chain; Kalshi has API
3. **Manual spot-check** (Phase 1) — check 5-10 picks' actual Kalshi depth in the first 24-48 hours

### Surprise Moneyline Picks

The first live cycle included 2 unexpected Moneyline picks alongside the 43 HR/Bases/Hits props. This is worth investigating — PM moneyline pricing may have different characteristics than prop pricing, and the presence of moneyline picks suggests the theory is finding edge beyond just the HR tail premium.

### Route Persistence Issue

The `/topdown-pm` dashboard route for viewing PM Edge picks was lost during a redeploy because it wasn't committed to git — only added via SCP. This follows the deployment drift pattern documented in [[concepts/configuration-drift-manual-launch]]: any file not in version control will eventually be lost.

## Related Concepts

- [[concepts/crypto-edge-non-pinnacle-strategy]] - The inverse strategy: uses PMs as truth anchor against non-Pinnacle sharps. PM Edge uses PMs as soft targets against sharp consensus
- [[concepts/pinnacle-prediction-market-pipeline]] - The original Pinnacle-vs-PM pipeline; PM Edge extends this by using multi-book consensus instead of Pinnacle alone as the sharp reference
- [[concepts/pinnacle-prediction-market-roi-breakdown]] - MLB HR +46.4% ROI from Pinnacle pipeline; PM Edge targets the same Kalshi tail premium from a different angle
- [[concepts/polymarket-liquidity-enrichment]] - Polymarket CLOB API provides liquidity metadata; PM Edge needs similar depth data from Kalshi to validate fillability
- [[concepts/value-betting-theory-system]] - PM Edge theories created via Supabase rows following the code-free theory pattern; `cache_bust_ts` column bump needed to force tracker cache refresh
- [[connections/liquidity-efficiency-inverse-in-betting]] - PM Edge's concentration in thin/obscure markets is a specific instance of the liquidity-efficiency inverse

### First Statistical Audit (2026-05-27)

A comprehensive 9-day audit of 2,924 resolved MLB PM picks revealed a breakthrough finding: **Pinnacle in the sharp set is a side-direction signal**, not a confidence signal. Under picks with Pinnacle produce +37.3% ROI (t=2.80) while Over picks with Pinnacle produce -28.8% (t=-2.39). The signal replicated independently across Kalshi, Polymarket, and Polymarket USA. The initial "drop Kalshi" theory was wrong — Kalshi works under winning filters (+58.4% ROI with Under + Pinnacle).

Structural fixes confirmed: drop HR/Bases/Hits props (t=-2.73 losses), drop `one_sided_fallback` devig (-20.9%), drop solo-DraftKings-sharp picks (-39.5%). Three v2 theories proposed: broad v2 (~550-600 picks), Game Lines Premium (~150-180 picks), Pinnacle-Anchored Under (~50-70 picks, projected +40-55% ROI). See [[concepts/pm-edge-statistical-audit-pinnacle-side-signal]] for the full analysis.

### Polymarket Gamma Env Var Gate Failure (2026-05-27)

The Polymarket Gamma scraper (book 972) stopped firing after 2026-05-21 because `ENABLE_POLYMARKET_GAMMA=1` was never added to the v3 batch launchers (`start-v3.bat`, `run_v3.bat`). This is a recurring env-var gate failure pattern (see [[concepts/configuration-drift-manual-launch]]): feature lands with `ENABLE_X` gate, env var never wired into launcher, next restart silently disables. Without Gamma, Kalshi was the only PM book quoting player counting stats — the "Kalshi is bleeding" diagnosis may partly be a data-gap artifact. Fixed in commit `1600994`.

### PM Monitoring Infrastructure Audit (2026-06-03)

On 2026-06-03 (Session 08:47), a deep quantitative audit of PM monitoring infrastructure revealed several critical findings:

**Kalshi is the dominant PM volume source** — 6,150 picks in 30 days (75% of PM-soft volume), arriving entirely via OpticOdds SSE relay with no direct scraper needed. The prior code inventory incorrectly labeled Kalshi as having "no active scraper" because it checked for scraper files rather than recognizing OO SSE as the data path.

**PM Edge ROI collapses at day-as-unit**: The flagship MLB PM Edge — Strict theory showed 5,060 picks at +2.66% ROI headline, but this **collapses to t=0.36** when computed at the day-as-unit level (bootstrap 95% CI [−11.0%, +17.8%]). The pick-count-CI artifact (√(5060/15) ≈ 18× naive CI tightening) disappears when correcting for intra-day correlation.

**Polymarket liquidity enrichment is completely dead** — 0/605 fill rate for `poly_liquidity` despite the module being wired into the tracker. Diagnosed as the largest infrastructure gap.

**414 Pinnacle niche-league theories auto-spawned**, ~399 with zero picks in 30 days — dead weight on pipeline evaluation cycles.

The only statistically significant PM cell was Underdog Predictions (65 picks, 6 days, +14.4% ROI, t=+2.18) — borderline n requiring pre-registered forward holdout before shipping. The Bases prop on PM books was near-significant negative (t=−1.70, ROI −9.6%), mechanistically plausible because casual HR narratives juice Over lines.

## Sources

- [[daily/lcash/2026-05-19.md]] - PM Edge theory design: PM odds as soft vs sharp consensus; 4 theories designed (only Strict pair shipped Phase 1); sharp weights Pin 1.0/Nov 0.8/FD 0.5/DK 0.5/PB 0.4; multiplicative devig, min_sharps=2; dry-eval 31-33 MLB picks (all Kalshi HR O0.5, EVs 25-60%); first live cycle 45 picks (43 Kalshi); Tristan Peters 15.57 vs sharp ~9.2; concentration risk in correlated HR markets; backtest will overstate EV due to thin orderbook depth; `cache_bust_ts` bump for tracker refresh; Phase 2: Loose theories + orderbook snapshots; Phase 3: per-PM-book split (Sessions 11:38, 12:13). Survivorship cliff: 70% PM markets delist within 90min, only 16.7% remain at game_start; Novig 12.4% >5pp divergence from consensus; empty soft trail rows mostly <15% (Session 12:44). `/topdown-pm` route lost on redeploy — not committed to git (Session 12:13)
- [[daily/lcash/2026-05-27.md]] - 9-day audit of 2924 resolved MLB PM picks: Pinnacle as side-direction signal (Under +37.3% t=2.80, Over -28.8% t=-2.39); cross-book replication across Kalshi/Polymarket/Polymarket USA; "drop Kalshi" retracted; HR/Bases/Hits structurally unprofitable; 3 v2 theories proposed (Session 15:26). Polymarket Gamma env var gate failure: ENABLE_POLYMARKET_GAMMA missing from v3 batch launchers; scraper dead since May 21; fixed commit 1600994 (Session 17:08)
- [[daily/lcash/2026-06-03.md]] — Session 08:47: PM monitoring audit; Kalshi 6,150 picks/30d (75% PM-soft volume) via OO SSE; MLB PM Edge — Strict ROI collapses to t=0.36 at day-as-unit; Polymarket liquidity enrichment 0/605 fill rate; 414 auto-spawned Pinnacle theories (~399 dead); Underdog Predictions borderline significant (t=+2.18); Bases prop near-significant negative (t=−1.70)
