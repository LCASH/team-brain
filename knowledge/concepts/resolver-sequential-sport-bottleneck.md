---
title: "Resolver Sequential Sport Bottleneck"
aliases: [resolver-bottleneck, sequential-resolver, nrl-blocking-resolver, sport-queue-bottleneck]
tags: [value-betting, resolver, architecture, performance, operations]
sources:
  - "daily/lcash/2026-04-19.md"
created: 2026-04-19
updated: 2026-04-19
---

# Resolver Sequential Sport Bottleneck

The value betting scanner's resolver processes sports sequentially in a fixed order. When NRL — which has 7 stale dates requiring a slow NRL.com fallback scraper — is early in the queue, it blocks ALL subsequent sports (AFL, 485+ SSE-discovered leagues) from resolving. On 2026-04-19, the resolver had resolved 36 picks with a 4,019 unresolved backlog, primarily because NRL's slow fallback consumed the entire resolver cycle before reaching other sports.

## Key Points

- The resolver processes sports one at a time in a fixed order; NRL with 7 stale dates (Apr 3-6, Apr 9) and a slow fallback scraper consumed the full cycle
- AFL and 485+ SSE-discovered leagues were completely blocked — their picks accumulated in a 4,019 unresolved backlog
- SSE league resolution IS architecturally supported — OpticOdds `/fixtures/results` returns fixture scores for SSE leagues (confirmed for EPL), so the issue is purely queue position
- `get_unresolved_dates()` only checks `game_date < today` — today's games won't attempt resolution until tomorrow, which is by design
- Auto-discovered SSE sport configs are created during `_sse_startup()` and ARE available in `SPORT_CONFIGS` by the time the resolver runs
- Esports resolution (LoL, Valorant, CS2, Dota) is uncertain — OpticOdds may not have fixture results for these leagues

## Details

### The Sequential Architecture Problem

The resolver's main loop iterates through sports in a fixed sequence, calling each sport's resolution function before moving to the next. Each sport resolution function calls `get_unresolved_dates()` to find dates with pending picks, then attempts to fetch results from OpticOdds' `/fixtures/results` endpoint. For most sports, this is fast — OpticOdds returns scores, the resolver grades picks, and moves on.

NRL breaks this pattern because OpticOdds returns 0 player results for NRL player props (specifically tries). The resolver falls back to scraping NRL.com directly (`_fetch_nrl_try_stats`), which is significantly slower per game. With 7 stale dates in the queue (April 3-6 and April 9), each requiring multiple HTTP requests to NRL.com, the NRL resolver function consumed the entire cycle time. Sports scheduled after NRL in the iteration order — AFL, NHL, and all 485+ SSE-discovered leagues — never got a turn.

This is a classic head-of-line blocking problem. A single slow sport blocks every sport behind it, regardless of how fast those sports could resolve independently. The total backlog of 4,019 picks is not because resolution is broken — it's because the queue never reaches the blocked sports.

### SSE League Resolution

A key finding is that SSE-discovered leagues (Euroleague, CBA, Turkey BSL, EPL, J-League, K-League, etc.) are fully resolvable through OpticOdds. The `/fixtures/results` endpoint was confirmed to return fixture scores for EPL and other soccer leagues. The resolution architecture supports these leagues — the blocking is purely a queue scheduling problem.

Auto-discovered SSE sport configurations are created during `_sse_startup()` at server initialization. These configs are stored in `SPORT_CONFIGS` and are available when the resolver runs its loop. No manual addition of SSE leagues to the resolver is needed.

### Esports Gap

OpticOdds may not provide fixture results for esports leagues (League of Legends, Valorant, CS2, Dota 2). This is an untested gap — the `/fixtures/results` endpoint needs to be probed for esports sport IDs. If OpticOdds lacks esports results, a fallback data source (similar to NRL.com for NRL tries and AFLTables for AFL stats) would be needed. This is lower priority since esports pick volume is currently small.

### Recommended Fixes

Two complementary approaches would eliminate the bottleneck:

1. **Parallelization**: Process sports concurrently using `asyncio.gather()` or a task pool, so NRL's slowness doesn't block other sports. Each sport's resolver is independent (no shared state between sports), making parallelization straightforward.

2. **Priority ordering / stale date handling**: Skip or deprioritize sports with many stale dates, resolving current dates first across all sports before returning to clear the backlog. Alternatively, fix or skip the specific stale NRL dates (Apr 3-6, Apr 9) that are clogging the queue.

Either approach would unblock the 4,019 pick backlog. Parallelization is the more robust long-term solution since any future sport with a slow fallback scraper would cause the same blocking pattern.

## Related Concepts

- [[concepts/afltables-player-stats-fallback]] - The AFL fallback scraper built to handle OpticOdds' lack of AFL player stats; a slow fallback would create the same blocking pattern if AFL had many stale dates
- [[concepts/opticodds-critical-dependency]] - OpticOdds returns 0 player results for NRL and AFL, forcing sport-specific fallback scrapers that are slower
- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - A parallel compound-bottleneck pattern: ACTIVE_SPORTS iteration blocking niche leagues from the tracker, similar to sequential resolver blocking
- [[connections/resolver-fallback-data-source-chain]] - How OpticOdds player stat gaps drive fallback architectures that amplify the sequential bottleneck

## Sources

- [[daily/lcash/2026-04-19.md]] - Resolver investigation: 36 resolved today, 4,019 backlog; NRL 7 stale dates with slow NRL.com fallback blocks all subsequent sports; SSE league resolution confirmed supported (EPL fixture scores via OpticOdds); esports resolution uncertain; auto-discovered SSE configs available in SPORT_CONFIGS; parallelization recommended (Session 08:37)
