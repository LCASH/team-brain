---
title: "Polymarket Gamma MLB Game-Level Market Expansion"
aliases: [gamma-mlb-expansion, polymarket-run-line, polymarket-total-runs, multi-game-collapse-bug, gamma-spread-filter]
tags: [value-betting, polymarket, scraping, mlb, data-quality, prediction-markets]
sources:
  - "daily/lcash/2026-05-28.md"
created: 2026-05-28
updated: 2026-05-28
---

# Polymarket Gamma MLB Game-Level Market Expansion

On 2026-05-28, the Polymarket Gamma scraper (book 972) was extended with MLB Run Line and Total Runs parsers, tripling MLB odds from 308→902 markets. A multi-game collapse bug was discovered where the same team matchup across different dates (e.g., series games) pooled into one `market_key` because Polymarket's `startDate` is market creation date, not game date. A 48-hour future cap on events prevents the collapse. A 30¢ max-spread filter (p75 of spread distribution) skips illiquid Polymarket markets where devig would be noisy.

## Key Points

- **MLB odds tripled 308→902** by adding Run Line and Total Runs parsers alongside existing player props
- **Multi-game collapse bug**: Same team matchup across series dates pooled into one `market_key` because `startDate` ≠ game date — must use `startTime`/`endDate` for game-time filtering
- **48h future cap** prevents collapse by limiting events to upcoming 48 hours — simple, effective, no false negatives for daily betting
- **30¢ max-spread filter** (bid-ask spread threshold at p75 of distribution) skips illiquid markets where the wide spread would produce noisy devig
- **Total Runs uses clean `"Team A vs Team B"` player_name** convention — avoids the existing buggy `"Over N.N"` encoding pattern for game-level markets
- **NBA player props (Points/Rebounds/Assists, ~60 markets) confirmed flowing** via Gamma for NBA Finals
- **Combo props (PRA, P+R etc.) wired but zero Polymarket coverage** — prediction markets stick to single-stat props even during NBA Finals

## Details

### Multi-Game Collapse Mechanism

Polymarket creates separate markets for each game in a series (e.g., OKC@SA Game 1, Game 2, Game 3). However, when the scanner ingests these markets, `market_key = (player, prop_type, side)` has no date component. If two markets for "OKC vs SA Run Line" exist simultaneously (today's game and tomorrow's), they map to the same key. The `startDate` field in Polymarket's API is the market creation date, which can be days before the actual game — making it useless for game-date filtering.

The 48-hour future cap filters events by `startTime` (the actual game start), keeping only events within the next 48 hours. This prevents multi-game collapse because series games 3+ days out are excluded from ingestion entirely. The cap is conservative — no bettor needs prediction market odds for games more than 48 hours away.

### Illiquidity Filter

Polymarket's player prop and game-level markets have highly variable liquidity. Marquee matchups may have $5K+ depth while obscure alt-lines have $2. The 30¢ max-spread filter uses bid-ask spread as a proxy for liquidity: if `ask - bid > 0.30`, the market is too illiquid for reliable devig. The 30¢ threshold was set at the p75 of the observed spread distribution — filtering the worst 25% of markets by liquidity.

### Store Staleness After Deploy

During initial deployment, a Gamma=5.556 vs other=1.61 odds deviation was observed — initially suspected as a scraper bug but traced to stale store data from a prior deploy. The DataStore retained old cached entries that hadn't been cleared on restart. The lesson: always check `updated_at` timestamps before investigating "bad" odds after a deploy.

## Related Concepts

- [[concepts/polymarket-gamma-stale-market-attribution]] - The prior Polymarket Gamma integration that discovered active=true on resolved markets; the MLB expansion builds on the same scraper with game-level market types added
- [[concepts/polymarket-liquidity-enrichment]] - Polymarket CLOB API for liquidity metadata; the 30¢ spread filter is a simpler alternative to full orderbook depth tracking
- [[connections/market-key-dateless-design-recurring-bugs]] - The multi-game collapse is caused by the same dateless market_key design that has produced 7+ prior bugs
- [[concepts/pm-edge-prediction-market-theory]] - PM Edge theories evaluate Polymarket as a soft target; MLB game-level markets expand the evaluation surface

## Sources

- [[daily/lcash/2026-05-28.md]] - MLB odds 308→902 with Run Line + Total Runs parsers; multi-game collapse from `startDate` ≠ game date fixed with 48h future cap; 30¢ max-spread filter at p75; Gamma=5.556 deviation was stale store data not scraper bug; NBA 60 player props confirmed; zero combo prop coverage; `self.sport == "mlb"` gate; 5 commits ahead of origin/main (Session 09:02)

