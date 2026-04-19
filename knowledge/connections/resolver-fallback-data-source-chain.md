---
title: "Connection: Resolver Fallback Data Source Chain"
connects:
  - "concepts/resolver-sequential-sport-bottleneck"
  - "concepts/afltables-player-stats-fallback"
  - "concepts/opticodds-critical-dependency"
  - "concepts/silent-worker-authentication-failure"
sources:
  - "daily/lcash/2026-04-19.md"
created: 2026-04-19
updated: 2026-04-19
---

# Connection: Resolver Fallback Data Source Chain

## The Connection

OpticOdds returns fixture scores for most sports but zero player-level results for NRL and AFL, forcing the resolver into sport-specific HTML scraper fallbacks (NRL.com for tries, AFLTables for disposals and goals). These fallbacks are significantly slower than OpticOdds API calls, and the resolver's sequential sport processing architecture amplifies this cost: a single slow fallback blocks resolution of every sport behind it in the queue.

## Key Insight

The non-obvious insight is that the **data source quality gap** (OpticOdds has fixture scores but not player stats for certain sports) combines with the **resolver's scheduling architecture** (sequential, not parallel) to create a disproportionate operational impact. Any sport with a slow fallback becomes a bottleneck for ALL sports, regardless of how fast their resolution would be independently.

This creates an asymmetric dependency chain:

1. **OpticOdds has the data** → sport resolves in seconds (NBA, MLB, most SSE leagues)
2. **OpticOdds lacks the data** → fallback scraper takes 5-30 seconds per game (NRL, AFL)
3. **Fallback scraper is slow + sport has stale dates** → blocks all subsequent sports for the entire cycle

NRL with 7 stale dates (April 3-6, April 9) consumed the full resolver cycle, leaving AFL and 485+ SSE leagues with 4,019 unresolved picks. The data quality issue (gap #2) is manageable in isolation — a 30-second scrape is fine for a single game. It becomes a systemic problem only because the sequential architecture (gap #3) allows one slow sport to monopolize the resolver.

This parallels the ACTIVE_SPORTS bottleneck in the tracker (see [[concepts/niche-league-tracker-pipeline-bottlenecks]]): both are cases where a sequential iteration pattern causes independent tasks to block each other, and both would be solved by parallelization.

## Evidence

The full chain was traced on 2026-04-19:

- **OpticOdds gap confirmed**: Returns 0 player results for both NRL (`player_tries`) and AFL (`player_disposals`, `player_goals`). Only fixture scores work for these sports.
- **NRL fallback slowness**: `_fetch_nrl_try_stats` scrapes NRL.com for try data — multiple HTTP requests per game, ~5-10 seconds per fixture. 7 stale dates × multiple games per date = minutes of blocking.
- **AFL fallback built**: AFLTables scraper created for Disposals and Goals. Each game page fetch + parse takes 2-5 seconds — fast enough individually, but would compound with stale dates.
- **Resolver queue state**: 36 picks resolved today, 4,019 unresolved backlog. The 4,019 are not unresolvable — they're unprocessed because the NRL fallback consumed the cycle before reaching AFL and SSE leagues.
- **SSE league resolution confirmed viable**: OpticOdds `/fixtures/results` returns scores for EPL and other leagues. The SSE league picks are blocked by queue position, not by missing data.

## The Fix Surface

The chain can be broken at two points:

1. **Parallelize the resolver** — each sport runs independently, so NRL's slowness only affects NRL. This is the robust fix. Sports can be resolved via `asyncio.gather()` since they share no state.

2. **Fix the stale NRL dates** — clear the 7 stale dates (Apr 3-6, Apr 9) to reduce NRL's per-cycle cost. This is a one-time cleanup, not a permanent fix — new stale dates can accumulate if the NRL fallback fails intermittently.

Both should be done: parallelize for long-term robustness, and clear stale dates for immediate backlog reduction.

## Related Concepts

- [[concepts/resolver-sequential-sport-bottleneck]] - The sequential architecture that amplifies slow fallbacks into system-wide blocking
- [[concepts/afltables-player-stats-fallback]] - The AFL fallback built on 2026-04-19 to fill OpticOdds' player stat gap
- [[concepts/opticodds-critical-dependency]] - OpticOdds as the primary data source whose per-sport gaps force fallback architectures
- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - Parallel pattern: ACTIVE_SPORTS sequential iteration blocking niche leagues in the tracker
- [[connections/operational-compound-failures]] - The resolver chain is a resolver-specific instance of the compound failure pattern: data gap × sequential scheduling × no prioritization
