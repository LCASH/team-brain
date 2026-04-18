---
title: "Fixture Cache Silent Market Dropout"
aliases: [fixture-cache-limit, fixture-cache-bottleneck, pagination-dropout, api-limit-dropout]
tags: [value-betting, bug, data-quality, pipeline, scaling]
sources:
  - "daily/lcash/2026-04-18.md"
created: 2026-04-18
updated: 2026-04-18
---

# Fixture Cache Silent Market Dropout

The value betting scanner's fixture cache defaulted to loading 100 fixtures per sport from the `/fixtures/active` API endpoint. When SSE streaming began delivering odds for 491+ leagues across all sports, **495 markets were silently dropped** because their fixtures weren't in the cache — the incoming odds couldn't be mapped to home/away teams. The fix increased the API limit from 100 to 500-1000 per sport. Of 2,400 raw SSE entries across 52 leagues, only 54 made it through the full pipeline — the fixture cache was the primary bottleneck.

## Key Points

- `/fixtures/active` API defaulted to `limit=100` per sport — silently dropping any fixture beyond the 100th
- 495 of 2,400 incoming SSE market entries were skipped because their fixture wasn't in cache — "fixture not found" logged but easy to miss in volume
- The fixture cache is used to map incoming odds to home/away team names for display and pick creation — without a cache entry, the market is invisible to the tracker
- Fix: increase API limit from 100 → 500/1000 per sport to cover all active fixtures across all leagues
- This is a pagination issue masquerading as "no data" — the API returns successfully with 100 fixtures, and the remaining fixtures silently don't exist in the scanner's world
- Theory existence checking on startup is also slow: ~0.2s × 462 theories = ~90s of serial Supabase GET requests (batching needed)

## Details

### The Silent Dropout Mechanism

The scanner's fixture cache is populated on startup by calling the OpticOdds `/fixtures/active` endpoint for each sport. The API accepts a `limit` parameter that defaults to 100 (or was hardcoded to 100 in the scanner). For major leagues (NBA, MLB, NHL), 100 fixtures per sport is sufficient — each league has at most 15-20 games per day. But when the scanner expanded to cover 491 leagues via SSE streaming (see [[concepts/opticodds-sse-streaming-scaling]]), the fixture count per sport exploded: soccer alone has 200+ daily fixtures across its 272 Kalshi-covered leagues.

When an SSE event arrives with odds for a fixture not in the cache, the market processing pipeline cannot determine the home/away teams. Without team names, it cannot create a pick record (which requires `fixture_name`, `player_name`, etc.). The market is logged as "fixture not found" and silently skipped. This produces a misleading picture: the SSE stream is delivering data correctly, the odds parsing works, but 90%+ of markets never reach the tracker.

### Scale of Impact

Of 2,400 raw SSE entries received across 52 leagues in testing, only 54 made it through the full pipeline to become evaluable markets. The breakdown:

- **495 skipped** — fixture not in cache (primary bottleneck)
- **Remaining** — filtered by market type restrictions (moneyline-only currently), live game filters, and other pipeline stages

The 495 fixture-cache dropouts represent genuine arbitrage opportunities that the scanner could have evaluated. These are markets with both sharp and soft book coverage — they were visible to OpticOdds and streamed to the scanner, but invisible to the tracker because of a cache size limitation.

### Fix and Forward Impact

Increasing the fixture cache limit from 100 to 500-1000 per sport should capture all active fixtures across all leagues. The exact limit depends on the sport: soccer (most leagues) may need 500+, while basketball and baseball need 200-300. A dynamic approach that fetches all available fixtures (no limit) would be more robust but may have API latency implications for the startup phase.

After the fixture cache fix, the pipeline is expected to pass significantly more markets through to the tracker. Whether these produce picks depends on the downstream filters (EV threshold, sharp freshness, line gap) and whether games are within the betting window.

### Related Scaling Issue

A separate scaling issue was identified during the same session: the theory existence check on startup performs serial Supabase GET requests — one per theory. With 462 theories (auto-created for many leagues), this takes ~90 seconds (0.2s × 462). Batching these checks into a single query or bulk insert would reduce startup time dramatically. On subsequent starts the check is instant since theories are cached, but first deploy after adding new leagues is painful.

### Pattern: Pagination as Silent Data Loss

This is an instance of a general anti-pattern: API pagination limits that silently truncate results rather than signaling incompleteness. The `/fixtures/active` API returns HTTP 200 with 100 fixtures — a valid, complete-looking response. Nothing in the response indicates that 400 more fixtures exist. The consumer must know to request more (or request all) to get complete data. When the consumer doesn't know the total count, the truncation is invisible.

This parallels the Supabase pagination issue documented in [[concepts/dashboard-client-server-ev-divergence]] where 22 pages of 1,000 picks succeeded at the API layer but choked browser parsing. In both cases, the API works correctly — the issue is the consumer's assumptions about data volume.

## Related Concepts

- [[concepts/opticodds-sse-streaming-scaling]] - The SSE streaming expansion that exposed the fixture cache limit by delivering markets for 491+ leagues
- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - Three other compound bottlenecks (ACTIVE_SPORTS, freshness, SSE filter) that also silently dropped niche league data
- [[concepts/crypto-edge-non-pinnacle-strategy]] - The Crypto Edge strategy whose 1,535-market universe is most affected by fixture cache limits
- [[concepts/dashboard-client-server-ev-divergence]] - A parallel pagination/volume issue where large datasets silently degrade downstream
- [[connections/operational-compound-failures]] - Fixture cache dropout + no alerting = extended invisible data loss

## Sources

- [[daily/lcash/2026-04-18.md]] - Fixture cache API limit=100 silently dropping fixtures; 495/2,400 SSE entries skipped ("fixture not found"); only 54 of 2,400 raw entries through full pipeline; fix: increase limit to 500/1000; theory existence check 0.2s × 462 = ~90s serial GETs (Sessions 14:39, 14:43)
