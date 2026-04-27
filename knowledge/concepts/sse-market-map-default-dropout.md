---
title: "SSE Market Map Default Moneyline Dropout"
aliases: [market-map-default, sse-moneyline-only, sse-player-prop-dropout, sse-consumer-misconfiguration]
tags: [value-betting, sse, pipeline, bug, configuration, scaling]
sources:
  - "daily/lcash/2026-04-27.md"
created: 2026-04-27
updated: 2026-04-27
---

# SSE Market Map Default Moneyline Dropout

The SSE consumer in `server/main.py` was created without a `market_map` parameter, causing line 781 to default to `{"moneyline": "Moneyline"}`. This silently dropped ALL player prop data for every non-NBA/MLB league — 50+ basketball and baseball leagues worldwide had zero player prop flow despite active SSE streams, correct fixture caches, and properly configured theories. The scanner was evaluating only moneyline markets for these leagues, missing the vast majority of +EV opportunities. Simultaneously, the SSE sportsbooks were configured with only 7 books (Pinnacle + prediction markets), excluding all AU soft books, and auto-created theories restricted `soft_books` to prediction markets only.

## Key Points

- Line 781 in `server/main.py` defaults `market_map` to `{"moneyline": "Moneyline"}` when none is passed — SSE consumer at lines 1224-1230 was created without one
- Result: ALL player props silently dropped for 50+ international leagues, with only moneyline data flowing — invisible because moneyline markets were present
- SSE sportsbooks were too narrow: only 7 books (Pinnacle + prediction markets) instead of 13 (adding US sharps + AU soft books)
- Auto-created Pinnacle theories restricted `soft_books` to prediction markets only (950, 970, 971, 980, 981, 982) — AU soft books (900-903) were excluded, preventing evaluation of AU book mispricing on non-NBA/MLB leagues
- All three issues compounded: even if one was fixed alone, the other two would still produce zero picks — all three needed fixing simultaneously
- 169 theories patched with expanded soft_books in a single batch operation

## Details

### The Three Compound Failures

The investigation started from a simple observation: 360 clean +EV picks existed for NBA (284) and MLB (76), but zero picks from any other league despite 182 active theories covering 50+ basketball and baseball leagues worldwide. Three independent causes were identified:

**1. Market map default (the most damaging).** The `OpticOddsSSEConsumer` class accepts an optional `market_map` parameter that defines which market types to parse from the SSE stream. When omitted, the constructor defaults to moneyline only. The SSE consumer for non-NBA/MLB leagues was instantiated without this parameter, so it parsed and forwarded only moneyline data — silently discarding player_points, player_rebounds, player_assists, player_threes, and every other player prop type. This is a fourth independent bottleneck for niche leagues, alongside the three documented in [[concepts/niche-league-tracker-pipeline-bottlenecks]].

**2. Sportsbook set too narrow.** The SSE streams were configured with only 7 sportsbooks: Pinnacle (250) plus 6 prediction market platforms (Kalshi 950, Polymarket 970, etc.). This excluded all US sharp books (FanDuel, DraftKings, BetRivers) and all AU soft books (Sportsbet 900, Bet Right 901, Ladbrokes 903). Even if player props were flowing, the tracker couldn't find enough book overlap for meaningful EV computation. Expanded to 13 books.

**3. Theory soft_books misconfiguration.** The `_auto_create_theories()` function creates theory rows in Supabase for newly discovered leagues. These auto-created theories hardcoded `soft_books` to only prediction market IDs. When a Japanese B1 League or KBO market had AU soft book odds available, the theory wouldn't evaluate them because the soft book ID wasn't in its configured set. All 169 affected theories were patched with expanded soft_books lists.

### Why This Went Undetected

Each failure produced a subtle, valid-looking output that didn't trigger investigation:

- **Moneyline data was present** — the SSE stream appeared healthy because moneyline markets were flowing, fixture counts looked correct, and theory evaluation ran without errors
- **Zero niche league picks looked normal** — niche leagues are expected to have lower pick volume, so "zero picks from Korea KBL" didn't raise alarms
- **The dashboard showed correct NBA/MLB data** — the core sports used different pollers (REST, not SSE) with proper market maps, masking the SSE consumer's misconfiguration

This follows the scanner's established "zero output, zero errors" silent failure pattern documented across multiple articles. The absence of player props is a valid state ("sport doesn't have props on OpticOdds"), making it impossible to distinguish "misconfigured consumer" from "no data available" without explicit market-type-level health monitoring.

### Fix and Verification

The fix had three parts: (1) pass the full `market_map` (all player prop types) when creating SSE consumers, (2) expand the sportsbook set from 7 to 13, (3) patch 169 theories with expanded `soft_books` lists. Verification requires waiting for international fixtures to go live — European (Euroleague, Spain ACB) and Asian (KBO, NPB, Japan B1) leagues have games at different times than NBA/MLB.

### Watchdog Fix Bundled

In the same session, lcash discovered the watchdog was broken since March 25 — disabled schtask, wrong Python path, and `subprocess.Popen` launches without env vars. This was the root cause of recurring server deaths where processes restarted without SPORT env var (see [[concepts/watchdog-environment-stripping]]). Fixed to use `schtasks /Run` which executes the batch file with all env vars preserved.

## Related Concepts

- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - Three other compound bottlenecks (ACTIVE_SPORTS, freshness cutoff, SSE display filter) that silently killed niche league output; this is a fourth at the SSE consumer layer
- [[concepts/opticodds-sse-streaming-scaling]] - The SSE streaming architecture that this misconfiguration undermined; the 491-league scaling plan only works when the consumer parses all market types
- [[concepts/trail-capture-soft-ids-gap]] - Same anti-pattern: hardcoded configuration silently excludes new data types; SOFT_IDS excluded prediction markets, market_map excluded player props
- [[concepts/value-betting-theory-system]] - Auto-created theories inheriting restrictive soft_books configurations; theory creation must be audited for completeness
- [[connections/operational-compound-failures]] - Three independent misconfigurations compounding to produce zero output — a classic instance of the compound failure pattern

## Sources

- [[daily/lcash/2026-04-27.md]] - 360 +EV picks for NBA/MLB but zero from 50+ other leagues despite 182 theories; SSE market_map default at line 781 dropping all player props; sportsbooks expanded 7→13; 169 theories patched with expanded soft_books; watchdog broken since March 25 (Session 15:23)
