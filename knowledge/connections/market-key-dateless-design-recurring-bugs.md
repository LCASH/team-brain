---
title: "Market Key Dateless Design Recurring Bugs"
aliases: [market-key-no-date, market-key-no-line, dateless-key-collisions]
tags: [value-betting, architecture, bug-pattern, market-key]
sources:
  - "daily/lcash/2026-04-26.md"
  - "daily/lcash/2026-05-11.md"
  - "daily/lcash/2026-05-12.md"
created: 2026-05-12
updated: 2026-05-12
---

# Market Key Dateless Design Recurring Bugs

The `market_key` in the value betting scanner uses `(player, prop_type, side)` with no `line` and no `game_date` component. This dateless, lineless design has caused at least THREE independent bugs:

1. **matched-market-line-null-bug** (2026-04-26): `MatchedMarket.to_dict()` had no top-level `line` field — line only existed per-book in BookOdds. Broke ALL pick creation because `_generate_pick_id()` requires line.

2. **dashboard-vig-gate-cross-line-dropout** (2026-05-11): Vig sanity gate rejected markets where Bet365 L=0.5 and sharps L=1.5 coexisted in the same market_key — different lines grouped under one key.

3. **market-key-cross-day-game-start-staleness** (2026-05-12): Same player's prop on different game days maps to same key. Odds updated but `game_start` stayed stuck on first-ever observation. 93% of MLB markets filtered as "live" from 3+ day-old game_start dates.

The pattern: the key was designed for cross-book comparison (grouping the same logical market regardless of line differences), but any field stored at the market level that varies across games or lines becomes a silent staleness/collision risk.

## Connects

- [[concepts/matched-market-line-null-bug]]
- [[concepts/dashboard-vig-gate-cross-line-dropout]]
- [[concepts/market-key-cross-day-game-start-staleness]]
