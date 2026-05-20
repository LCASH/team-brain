---
title: "Polymarket Gamma Stale Market Attribution Bug"
aliases: [polymarket-gamma-stale, polymarket-settled-active, polymarket-past-game-filter, gamma-scraper-guards]
tags: [value-betting, polymarket, scraping, data-quality, bug, prediction-markets]
sources:
  - "daily/lcash/2026-05-20.md"
created: 2026-05-20
updated: 2026-05-20
---

# Polymarket Gamma Stale Market Attribution Bug

On 2026-05-20, the dashboard showed Anthony Harden Rebounds at 1000.000 odds — traced to settled Polymarket markets (bid=$0.000/ask=$0.001) being merged into future games via `(player, prop, side, line)` market_key collision. Polymarket leaves resolved markets flagged `active=true closed=false acceptingOrders=true` for **days** after game completion. 100% of Polymarket Gamma's (book 972) 87 NBA markets were from past games (49-90 hours old), inflating a "+335% coverage" claim that was entirely stale resolved data.

## Key Points

- Polymarket's API flags resolved markets as `active=true closed=false acceptingOrders=true` for days after settlement — unreliable for determining market status
- **100% of Gamma's 87 NBA markets were from past games** (49-90h old) — what appeared as fresh coverage was entirely stale data
- `market_key = (player, prop, side, line)` has no date component — settled markets from past games map to the same key as future games, overwriting live odds with $0.001 ask prices
- **Fix**: `POLYMARKET_GAMMA_MAX_PAST_GAME_AGE_HOURS=3` (past-game filter on `startDate`) + extreme-price filter (bid ≤ 0.005 / ask ≥ 0.995) — both guards applied before data enters the DataStore
- Polymarket only lists player-prop markets for **marquee games** (e.g., Game 1 of a series), not every game — subsequent games get only moneyline/spread/total (3 markets)
- The "+335% coverage uplift" claim from an earlier session was **retracted** — must verify data is current before claiming coverage gains

## Details

### The Attribution Mechanism

The DataStore uses `market_key = (player, prop, side, line)` without a date component (see [[connections/market-key-dateless-design-recurring-bugs]]). When Polymarket Gamma delivers odds for a player prop from a game that ended 3 days ago, the market_key matches the same player's current prop and overwrites the DataStore entry. The settled Polymarket odds ($0.001 ask for a resolved "No" market, or $0.999 for a resolved "Yes") replace the live odds from other books, producing phantom 1000.000 decimal odds on the dashboard.

This is the same market_key collision pattern that caused the `game_start` staleness bug (see [[concepts/market-key-cross-day-game-start-staleness]]) and the bet365 alt-line collision (see [[concepts/bet365-same-book-alt-line-collision]]), but from a different source: stale external data rather than stale internal metadata.

### Why Polymarket Markets Stay "Active"

Polymarket's prediction market model differs from traditional sportsbook markets. On traditional books, markets are delisted or settled within minutes of game completion. Polymarket's CLOB-based markets persist in an `active=true` state for days after resolution because:

1. The order book remains open for residual position unwinding
2. Settlement and claiming are separate on-chain operations that happen asynchronously
3. The API reflects the on-chain state (market contract exists) not the betting state (game over)

This means the standard "is this market active?" check (`active && !closed && acceptingOrders`) — which works for traditional sportsbooks — produces false positives for every resolved Polymarket market. The correct filter uses `startDate` + age comparison rather than trusting the activity flags.

### Coverage Measurement Lesson

The session retracted a "+335% coverage" claim made earlier about Polymarket Gamma. The 87 markets that appeared as new coverage were all stale resolved data from past games. This illustrates a general measurement trap: **when evaluating coverage gains from a new data source, verify the data is current before claiming uplift.** Stale resolved markets inflate counts dramatically because every completed game's markets persist as phantom coverage.

### Selective Marquee Game Listings

Investigation revealed that Polymarket only lists player-prop markets for marquee games — typically the first game of a playoff series or high-profile regular season matchups. Subsequent games in the same series may only get 3 markets (moneyline, spread, total). This makes Polymarket Gamma's player-prop coverage inherently sparse and unpredictable. The scraper remains enabled (`ENABLE_POLYMARKET_GAMMA=1`) to auto-capture when Polymarket posts new marquee game props, but operators should not expect consistent coverage across all games.

## Related Concepts

- [[connections/market-key-dateless-design-recurring-bugs]] - The dateless market_key design enables cross-game collisions when any source emits stale data; this is a sixth documented manifestation
- [[concepts/market-key-cross-day-game-start-staleness]] - Same collision pattern from a different cause: internal `game_start` stuck on old dates vs external stale market data from Polymarket
- [[concepts/polymarket-liquidity-enrichment]] - The Polymarket CLOB API that Gamma consumes; liquidity metadata from this API could help identify resolved markets (zero liquidity = settled)
- [[concepts/pm-edge-prediction-market-theory]] - PM Edge theories target Polymarket as a soft book; stale resolved data from Gamma could contaminate PM Edge if not filtered
- [[connections/silent-type-coercion-data-corruption]] - 1000.000 decimal odds from settled markets are "plausible wrong output" that pass validation and only look obviously wrong at the display layer

## Sources

- [[daily/lcash/2026-05-20.md]] - Harden Rebounds at 1000.000 odds traced to settled Polymarket markets (bid=$0.000/ask=$0.001) merged into future games via market_key collision; 100% of Gamma's 87 NBA markets from past games (49-90h old); Polymarket flags resolved markets active=true/closed=false/acceptingOrders=true for days; past-game filter (3h) + extreme-price filter deployed; "+335% coverage" claim retracted; marquee-game-only prop listing pattern; commit `2c780a1` (Session 17:33)
