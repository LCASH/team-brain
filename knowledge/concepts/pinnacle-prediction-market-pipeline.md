---
title: "Pinnacle Prediction Market Pipeline"
aliases: [pinnacle-pipeline, prediction-markets, virtual-sport, kalshi-polymarket]
tags: [value-betting, pinnacle, prediction-markets, dashboard, integration]
sources:
  - "daily/lcash/2026-04-15.md"
  - "daily/lcash/2026-04-16.md"
  - "daily/lcash/2026-04-18.md"
  - "daily/lcash/2026-04-21.md"
created: 2026-04-15
updated: 2026-04-21
---

# Pinnacle Prediction Market Pipeline

A new theory pipeline in the value betting scanner that uses Pinnacle as the sharp reference to evaluate prediction market books (Kalshi, Polymarket, DraftKings Predictions, Underdog, Crypto.com) as soft books. Committed as `9a0b19d` on 2026-04-15 with dashboard support via a virtual sport pill and a `sportSupabaseFilter()` helper. The pipeline was verified end-to-end with data flowing but zero picks firing — confirmed as correct behavior due to the 3-hour pre-tipoff window constraint.

## Key Points

- Pinnacle serves as the sharp reference for devigging; prediction market platforms are evaluated as soft books for +EV opportunities
- Prediction market book IDs: Kalshi (950), Polymarket (970), DraftKings Predictions (971), Underdog (980), Crypto.com (981/982)
- Dashboard includes a virtual sport pill for the Pinnacle theory — not tied to a single sport but to the theory's cross-sport scope
- Pipeline verified end-to-end: Polymarket (348 markets), Kalshi (168), Pinnacle (402) all visible on VPS
- Zero picks firing confirmed correct — all NBA games were outside the 3-hour pre-tipoff window; no code change needed
- Committed as `9a0b19d` on main: 5 files changed, +177/-28 lines

## Details

### Architecture

The Pinnacle prediction market pipeline extends the existing theory system (see [[concepts/value-betting-theory-system]]) with a new sharp-vs-soft pairing. Traditional theories use OpticOdds sharp books (Pinnacle, Circa) as the "true odds" reference and evaluate Australian retail soft books (Ladbrokes, PointsBet AU, Sportsbet) for +EV. The Pinnacle theory uses Pinnacle directly as the sharp reference and evaluates prediction market platforms as soft books.

This is architecturally significant because it diversifies the system's soft book universe beyond traditional sportsbooks. Prediction markets operate with different pricing mechanisms (order books vs. market-maker spreads), different liquidity profiles, and different regulatory frameworks. Finding +EV on prediction markets relative to Pinnacle's sharp line represents a genuinely different edge source than finding +EV on Australian retail books.

### Book ID Assignment

New book IDs were assigned for the prediction market platforms:
- **Kalshi**: 950
- **Polymarket**: 970
- **DraftKings Predictions**: 971
- **Underdog**: 980
- **Crypto.com**: 981, 982 (two IDs, likely for different product tiers or regions)

These IDs follow the existing convention where traditional sportsbooks use lower ranges (365 for Bet365, 800-series for Australian books) and prediction markets occupy the 900+ range.

### Dashboard Integration

The dashboard was updated with two features:

1. **Virtual sport pill**: Since the Pinnacle theory evaluates prediction markets across sports (not tied to a single sport like NBA or AFL), a virtual sport pill was added to the dashboard. This allows filtering to see only Pinnacle-theory picks without conflating them with sport-specific theory picks.

2. **`sportSupabaseFilter()` helper**: A utility function for constructing sport-specific Supabase queries, ensuring the Pinnacle theory's cross-sport scope is correctly handled in database queries.

### The loadTheories() Discovery

The Pinnacle pipeline verification exposed a critical dashboard bug: the `loadTheories()` JavaScript function was silently dropping `soft_books` and five other fields when mapping Supabase rows to JS objects. This caused the Pinnacle pill to show EV against Australian soft books (Ladbrokes, PointsBet) instead of the intended prediction markets (Kalshi, Polymarket). The fix was deployed in the same commit. See [[concepts/dashboard-client-server-ev-divergence]] for the full bug analysis.

### End-to-End Verification

On 2026-04-15, lcash verified the pipeline after deployment:
- **Data flow confirmed**: Polymarket (348 markets), Kalshi (168 markets), Pinnacle (402 markets) all visible on VPS
- **Zero picks firing**: Confirmed correct. The Pinnacle theory has a 3-hour pre-tipoff window constraint, and all NBA games were either already tipped off (today's) or more than 24 hours out (tomorrow's). No code change needed.
- **Dashboard verified**: Pinnacle pill correctly filtered to prediction markets only after the `loadTheories()` bug fix and hard refresh

### Commit Details

Committed as `9a0b19d` on main — 5 files changed, +177/-28 lines. Includes:
- Prediction market book IDs (Kalshi 950, Polymarket 970, DraftKings Predictions 971, Underdog 980, Crypto.com 981/982)
- Virtual sport pill
- `sportSupabaseFilter()` helper
- The `loadTheories()` bug fix (soft_books, prop_filter, max_line_gap, line_gap_penalty, max_line, excluded_props explicitly mapped)

### Stash/Restore Workflow

The Pinnacle work was committed using a stash/restore pattern to isolate it from pre-existing uncommitted bet365 feature branch work. The uncommitted bet365 coupon endpoint changes (see [[concepts/bet365-nba-coupon-endpoint]]) were stashed, the Pinnacle commit was made on main, and the stash was restored afterward. This avoided mixing unrelated changes in a single commit.

### Multi-Sport Expansion (2026-04-16)

On 2026-04-16, lcash investigated expanding the Pinnacle pipeline beyond NBA to other sports:

**NHL identified as next viable sport.** Three game-line markets overlap between Pinnacle and prediction markets: `total_goals`, `puck_line`, and `moneyline`. Kalshi has 60 `player_goals` entries but NO Pinnacle counterpart for player props — only game-line overlap exists. Game-line pipeline requires architecture changes: `make_market_key()` requires `player_name` which game lines don't have (Phase 2 work, ~400 LOC, estimated 3-5 day effort).

**MLB confirmed non-viable.** All 288 markets across Kalshi, Polymarket, and Crypto.com returned 0 odds entries on OpticOdds. Pinnacle itself only covers 4 MLB game-line markets (no player props). MLB prediction market coverage does not exist on OpticOdds; direct Kalshi/Polymarket native APIs remain an unexplored alternative.

**Soccer deactivated.** 22 soccer theories were deactivated after discovering that soccer moneyline picks showed 20-41% phantom EVs caused by 3-way markets (Home/Draw/Away) being devigged as 2-way (Over/Under). The Draw probability (~23%) was redistributed across both sides. See [[concepts/soccer-three-way-devig-phantom-ev]] for full analysis. 30 phantom picks were voided. Six genuine 2-way leagues retained: NBA, MLB, NHL, Euroleague, CBA, Turkey BSL.

**Pinnacle prop-type sharpness variance.** Dropout logging revealed Pinnacle is not uniformly sharp across prop types: Threes +27.9% ROI (sharp) vs Assists -45.7% to -50.4% (catastrophically weak). min_ev lowered from 5 to 1 to capture marginal edges for trail data. See [[concepts/pinnacle-prop-type-sharpness-variance]] for full analysis.

**Trail capture gap fixed.** Phase B trail capture was excluding prediction-market book IDs from the hardcoded `SOFT_IDS` iteration set. 0% trail coverage for Pinnacle picks was fixed by adding IDs 950, 970, 971, 980-982. See [[concepts/trail-capture-soft-ids-gap]].

**All 6 Pinnacle theories set to 3-hour pre-game window** (was 24h).

### SSE Payload Bloat and Display/Tracking Split (2026-04-16)

Adding game-line markets (moneyline, run_line, total_runs) to the mini PC's core sport pollers caused the SSE payload to balloon from ~2MB to 6-9MB, causing browser parsing timeouts. MLB alone grew from ~2K to 5,040 markets because game lines were pulled across all 52 books instead of the 7 books relevant to the Pinnacle strategy. The fix introduced a permanent architectural separation:

- **Game-line markets reverted from core sport configs** — mini PC stays on player props only, keeping the SSE payload manageable
- **Separate VPS-side Pinnacle pollers** added for NBA/MLB/NHL game lines with a restricted 7-book set (Pinnacle + 6 prediction market platforms)
- **SSE push disabled for ALL Pinnacle pollers** (niche leagues AND core game lines) — they write to state for the tracker but never bloat the SSE stream
- The Pinnacle dashboard pill shows: (1) client-side computed picks from SSE player-prop data, (2) server-tracked picks from Supabase for niche leagues and game lines

See [[concepts/sse-display-tracking-market-separation]] for the full architectural pattern.

### Virtual Pill Rendering Architecture (2026-04-16)

The Pinnacle virtual sport pill's rendering was refined in Session 22:35 after discovering that the initial dual-path approach (client-side computed picks from SSE + server-tracked picks from Supabase) produced incorrect results for the virtual pill specifically. The problem was twofold:

1. **NBA contamination:** The dashboard's `computeEVPicks()` function ran against SSE data (which contains NBA player props from the mini PC). Since the Pinnacle pill isn't sport-specific, the client-side computation produced NBA prop picks evaluated against prediction market soft books — conflating Pinnacle-specific analysis with the main NBA prop pipeline. The result was NBA picks appearing in the Pinnacle view.

2. **Race condition on pill switch:** When switching between sport pills (e.g., NBA → Pinnacle), stale `_storedEVPicks` and theory data from the previous pill persisted in client state. The `ilike.*Pinnacle*` PostgREST filter correctly fetched Pinnacle-specific picks from Supabase, but the stale client-side state rendered first, briefly showing NBA data.

The resolution was to **skip live client-side computation entirely for the Pinnacle virtual pill** and rely exclusively on server-tracked stored picks from Supabase. This is architecturally clean: niche-league and game-line picks are only available via the tracker (they're never in the SSE stream), so the virtual pill was always going to need the stored-picks path. Removing the live computation path eliminates the NBA contamination and simplifies the rendering.

The race condition was fixed by clearing `_storedEVPicks` and cached theories immediately on pill switch, ensuring a clean slate before the new pill's data loads.

A related debugging lesson: the dashboard's `renderStats()` and `renderEV()` functions both independently called `computeEVPicks()`. Fixing the computation logic in one function but not the other left the bug visible through the unfixed path. This "multiple render paths calling the same computation" pattern requires fixing all call sites simultaneously — a single-point fix is insufficient when multiple entry points exist.

### Niche League Pipeline Unblocking (2026-04-16)

Session 23:12 revealed that the Pinnacle pipeline was producing ~10 picks despite 454+ niche league markets with Pinnacle-prediction-market overlap. Three independent bottlenecks compounded to silently kill niche league output:

1. **ACTIVE_SPORTS auto-merge**: The tracker only iterated core sports (`nba`, `mlb`, `nrl`, `afl`) in relay mode, skipping all 29 niche league keys. Fixed by auto-merging all `PINNACLE_LEAGUE_KEYS` when in relay mode.
2. **Sharp freshness cutoff**: The 30s cutoff was tuned for major leagues (5-10s polling) but niche leagues poll every 60s — by the time the tracker reached them, sharp data was silently discarded. Increased to 120s.
3. **SSE filter hiding tracker data**: The browser-crash-prevention SSE filter (see [[concepts/sse-display-tracking-market-separation]]) was also filtering the tracker's market view via the same state-access function. A separate `get_tracker_snapshot()` was added to bypass the SSE filter for the tracker.

After all three fixes, zero picks was confirmed as correct behavior — all niche league games were 27-124 hours away, outside the 24-hour pre-game window. Picks will appear automatically as games enter the window. See [[concepts/niche-league-tracker-pipeline-bottlenecks]] for full analysis.

### Crypto Edge Expansion (2026-04-18)

On 2026-04-18, the prediction market strategy was expanded with a complementary "Crypto Edge" pill that targets markets where prediction markets exist but Pinnacle has no coverage — the inverse of the original Pinnacle pipeline. An OpticOdds scan found 1,535 such markets (1,433 with other sharp books available), with MLB as the goldmine (1,354 markets: Pinnacle doesn't list Hits or HRIs at all). The Crypto Edge pill uses DraftKings/Novig/FanDuel as sharps instead of Pinnacle. See [[concepts/crypto-edge-non-pinnacle-strategy]] for the full strategy.

Combined, the Pinnacle pipeline and Crypto Edge pipeline now generate 215 picks across 14 leagues (NBA 95, MLB 89, plus niche leagues including Japan J1, Korea K1, MLS).

### REST-to-SSE Scaling Migration (2026-04-18)

The pipeline's expansion to 491+ leagues exposed a fundamental REST polling limitation: ~10K API calls/minute would exceed OpticOdds rate limits. The discovery of OpticOdds' SSE streaming endpoint (`/stream/odds/{sport}`) provides a path to cover all leagues per sport with ~15 persistent connections instead of 28+ REST pollers. The scanner was only polling 23 of 491 Kalshi leagues (~5% actual coverage). See [[concepts/opticodds-sse-streaming-scaling]] for the migration plan.

### Forward ROI Validation (2026-04-21)

On 2026-04-21, lcash performed a comprehensive ROI analysis of the Pinnacle prediction market pipeline, confirming it as a profitable strategy: **+8.1% ROI, +92.8 units across 1,146 picks**. The analysis used average positive-EV odds (not peak odds) for a more realistic representation of bettor returns.

Key findings by league: MLB +15.6%, Dota 2 +53.2%, NBA +6.2%, Valorant +37.5%, ATP Tennis +33.0%, China CBA +28.6%. Three losing leagues were identified for deactivation: LoL -31.9%, NHL -21.0%, ATP Challenger -34.3% — saving ~34 units going forward.

Per-prop-type analysis revealed MLB Home Runs as the single best edge at +46.4% ROI (average odds 6.26) and NBA Rebounds at +32.6%. Moneyline was profitable overall (+5.0%, +32.1u) despite NBA moneyline specifically being -6.7% — prediction markets price NBA game outcomes with near-sharp efficiency but misprice player props and non-NBA moneylines.

See [[concepts/pinnacle-prediction-market-roi-breakdown]] for the full breakdown and methodology.

### NBA Tipoff Timing Buffer (2026-04-21)

NBA picks were disappearing from the dashboard "before tip-off" — root cause was that OpticOdds reports the scheduled start time, but actual tip-off is 10-15 minutes later due to pre-game ceremonies and introductions. A 15-minute buffer was added to `_is_game_live()` to match actual tip-off time vs scheduled time, preventing premature filtering of picks that are still actionable.

## Related Concepts

- [[concepts/value-betting-theory-system]] - The theory system that the Pinnacle pipeline extends with a new sharp/soft pairing
- [[concepts/dashboard-client-server-ev-divergence]] - The loadTheories() bug discovered during Pinnacle pipeline verification
- [[concepts/opticodds-critical-dependency]] - Pinnacle data is accessed via OpticOdds; this pipeline depends on OpticOdds having Pinnacle coverage
- [[concepts/bet365-nba-coupon-endpoint]] - The bet365 work stashed/restored around this commit
- [[concepts/soccer-three-way-devig-phantom-ev]] - Soccer expansion blocked by 3-way devig requirement
- [[concepts/pinnacle-prop-type-sharpness-variance]] - Pinnacle sharpness varies by prop type; Threes sharp, Assists weak
- [[concepts/trail-capture-soft-ids-gap]] - Trail capture gap for prediction-market book IDs
- [[concepts/ev-pipeline-dropout-logging]] - The diagnostic tool used to validate pipeline correctness
- [[concepts/sse-display-tracking-market-separation]] - SSE bloat from game-line expansion forced display/tracking split with VPS-side pollers
- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - Three compound bottlenecks silently killing niche league picks: ACTIVE_SPORTS, freshness cutoff, SSE filter
- [[concepts/crypto-edge-non-pinnacle-strategy]] - The complementary strategy targeting non-Pinnacle prediction market gaps
- [[concepts/opticodds-sse-streaming-scaling]] - SSE streaming migration to scale from 23 to 491+ leagues

## Sources

- [[daily/lcash/2026-04-15.md]] - Pinnacle theory committed (9a0b19d, +177/-28 lines): prediction market book IDs (Kalshi 950, Polymarket 970, DraftKings Predictions 971, Underdog 980, Crypto.com 981/982), virtual sport pill, sportSupabaseFilter helper; pipeline verified end-to-end (Polymarket 348, Kalshi 168, Pinnacle 402 markets); zero picks correct (outside 3h window); stash/restore pattern for branch isolation (Sessions 22:03, 22:36)
- [[daily/lcash/2026-04-16.md]] - NHL viable (3 game-line markets, ~400 LOC for game-line support); MLB non-viable (0 prediction market coverage on OpticOdds); soccer deactivated (22 theories, 30 phantom picks voided — 3-way devig needed); Pinnacle prop-type variance: Threes +27.9%, Assists -50.4%; min_ev 5→1; trail capture SOFT_IDS gap fixed; all theories set to 3h window; SSE payload bloated to 6-9MB from game-line expansion (MLB 2K→5,040 markets), fixed by VPS-side Pinnacle pollers with restricted book set and SSE push disabled (Sessions 13:04, 13:38, 16:30, 20:38, 21:31). Virtual pill rendering: skipped live computation entirely, only stored picks; cleared _storedEVPicks on pill switch to fix race condition; multiple render paths (renderStats/renderEV) both calling computeEVPicks independently (Session 22:35). Niche league pipeline unblocked: three compound bottlenecks (ACTIVE_SPORTS iteration, 30s→120s sharp freshness, SSE filter hiding tracker view) silently killed niche league output; post-fix 0 picks confirmed correct (games 27-124h away) (Session 23:12)
- [[daily/lcash/2026-04-18.md]] - Crypto Edge pill launched (1,535 non-Pinnacle markets, MLB 1,354); 215 picks across 14 leagues; only polling 23/491 Kalshi leagues (~5%); SSE streaming endpoint discovered (459KB/15s all leagues per sport); 5-phase REST-to-SSE migration plan; fixture cache limit=100 silently dropped 495/2,400 SSE markets (Sessions 12:31, 13:31, 14:39)
- [[daily/lcash/2026-04-21.md]] - Forward ROI validation: +8.1% ROI, +92.8u across 1,146 picks using average +EV odds methodology; MLB HR +46.4%, NBA Rebounds +32.6%; losing leagues deactivated: LoL -31.9%, NHL -21.0%, ATP Challenger -34.3% (saves ~34u); NBA tipoff 15-min buffer added for scheduled vs actual start time (Sessions 12:01, 17:12)
