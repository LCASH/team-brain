---
title: "Market Key Dateless Design Recurring Bugs"
aliases: [market-key-no-date, market-key-no-line, dateless-key-collisions]
tags: [value-betting, architecture, bug-pattern, market-key]
sources:
  - "daily/lcash/2026-04-26.md"
  - "daily/lcash/2026-05-11.md"
  - "daily/lcash/2026-05-12.md"
  - "daily/lcash/2026-05-15.md"
  - "daily/lcash/2026-05-20.md"
  - "daily/lcash/2026-05-22.md"
created: 2026-05-12
updated: 2026-05-22
---

# Market Key Dateless Design Recurring Bugs

The `market_key` in the value betting scanner uses `(player, prop_type, side)` with no `line` and no `game_date` component. This dateless, lineless design has caused at least SEVEN independent bugs:

1. **matched-market-line-null-bug** (2026-04-26): `MatchedMarket.to_dict()` had no top-level `line` field — line only existed per-book in BookOdds. Broke ALL pick creation because `_generate_pick_id()` requires line.

2. **dashboard-vig-gate-cross-line-dropout** (2026-05-11): Vig sanity gate rejected markets where Bet365 L=0.5 and sharps L=1.5 coexisted in the same market_key — different lines grouped under one key.

3. **market-key-cross-day-game-start-staleness** (2026-05-12): Same player's prop on different game days maps to same key. Odds updated but `game_start` stayed stuck on first-ever observation. 93% of MLB markets filtered as "live" from 3+ day-old game_start dates.

4. **bet365-same-book-alt-line-collision** (2026-05-15): bet365 emits 3 O/U lines per player (low/main/high alt) under the same market group. All three map to the same market_key → last-write-wins race → random alt-line stored → phantom +130% EV. Fixed with `_tag_main_lines()` post-processor.

5. **co-ou-parser-conflation-phantom-picks** (2026-05-15): CO milestone markets (1+ HR at line 0.5) and standard O/U markets (HR Over 0.5) mapped to the same `prop_type` key. Milestone odds paired against O/U sharps producing phantom +20.84% EV with 9% actual win rate. 72% of recent MLB Bet365 picks were phantoms. Fixed with `_CO` suffix on milestone prop_types.

6. **polymarket-gamma-stale-market-attribution** (2026-05-20): Polymarket leaves resolved markets flagged `active=true` for days after game completion. Settled markets (bid=$0.000/ask=$0.001) from past games merge into future games via the dateless market_key — the same player's prop from 3 days ago overwrites today's odds. First instance caused by an external data source emitting stale cross-day data (prior five were all internal). Fixed with `POLYMARKET_GAMMA_MAX_PAST_GAME_AGE_HOURS=3` + extreme-price filter.

7. **nba-milestone-prop-collision-bug** (2026-05-22): NBA bet365 wizard parser emits both milestone props ("20+ Points" at line 19.5) and standard O/U as `prop_type="Points" side="Over"` — the identical bug fixed for MLB on May 15 with `_CO` suffix, but the NBA game scraper parser at `bet365_game.py` lines 229-241 was never updated. Additionally, 5 alt lines (17.5, 24.5, 30.5, 37.5, 49.5) per player all land on the same market_key with last-write-wins. SGA Points soft trail oscillated between line=23.5 and line=37.5 as the diagnostic signal.

The pattern: the key was designed for cross-book comparison (grouping the same logical market regardless of line differences), but any field stored at the market level that varies across games, lines, or market structures becomes a silent staleness/collision risk.

## Connects

- [[concepts/matched-market-line-null-bug]]
- [[concepts/dashboard-vig-gate-cross-line-dropout]]
- [[concepts/market-key-cross-day-game-start-staleness]]
- [[concepts/bet365-same-book-alt-line-collision]]
- [[concepts/co-ou-parser-conflation-phantom-picks]]
- [[concepts/polymarket-gamma-stale-market-attribution]]
- [[concepts/nba-milestone-prop-collision-bug]]
