---
title: "OpticOdds SSE Streaming for League Scaling"
aliases: [sse-streaming, opticodds-sse, rest-to-sse-migration, league-scaling]
tags: [value-betting, architecture, scaling, opticodds, streaming]
sources:
  - "daily/lcash/2026-04-18.md"
created: 2026-04-18
updated: 2026-04-18
---

# OpticOdds SSE Streaming for League Scaling

The value betting scanner's REST polling architecture cannot scale to cover 491+ leagues across prediction markets — it would require ~10K API calls/minute and hit OpticOdds rate limits. The discovery of OpticOdds' SSE (Server-Sent Events) streaming endpoint (`/stream/odds/{sport}`) provides a path to cover all leagues per sport with ~15 persistent connections instead of 28+ REST pollers. A test confirmed 459KB of data in 15 seconds covering all leagues for a single sport, including league IDs, market types, odds, player props, and bet limits.

## Key Points

- REST polling doesn't scale: 491 leagues × multiple polls/min = ~10K API calls/min, exceeding rate limits
- OpticOdds SSE endpoint streams ALL leagues within a sport in a single connection — tested successfully at 459KB/15s
- Current architecture uses 28 separate REST pollers; SSE would replace them with ~15 persistent connections (one per sport)
- SSE data includes league IDs, market types, odds, player props, and bet limits — richer than REST responses
- Kalshi alone covers 272 soccer leagues (scanner polls 22), 96 basketball leagues (scanner polls 4) — ~5% actual coverage vs available
- Plan documented in `brain/findings/2026-04-18-sse-scaling-plan.md` with a 5-phase rollout

## Details

### The Scaling Problem

The Pinnacle prediction-market pipeline (see [[concepts/pinnacle-prediction-market-pipeline]]) and the Crypto Edge strategy (see [[concepts/crypto-edge-non-pinnacle-strategy]]) exposed a fundamental scaling limitation: the scanner only polls 23 of 491 Kalshi leagues (~5% coverage). Expanding to full coverage with REST polling would require one poller per league, each making periodic API calls. At 491 leagues with multiple polls per minute, this produces ~10K API calls/minute — far beyond OpticOdds' rate limits and the scanner's operational capacity.

The user correctly challenged the "97% coverage" claim — the scanner was covering 97% of markets within the 23 polled leagues, but only 5% of all available leagues. The remaining 468 leagues (including 250+ soccer leagues, 92 basketball leagues, plus tennis, esports, golf, cricket, MMA, handball, volleyball) represent untapped prediction market arbitrage opportunities.

### The SSE Solution

OpticOdds provides an SSE streaming endpoint at `/stream/odds/{sport}` that delivers real-time odds updates for ALL leagues within a sport via a single persistent HTTP connection. Unlike REST polling (which returns a snapshot and closes), SSE maintains an open connection and pushes events as odds change.

A test confirmed the endpoint's viability: 459KB of odds data was received in 15 seconds for a single sport, covering all leagues that OpticOdds carries. The data format includes league identifiers, market types, participant names, odds values, player prop details, and bet limits — strictly richer than the REST endpoint responses.

### Architecture Migration Plan

The migration from REST polling to SSE streaming follows a 5-phase plan:

**Phase 1:** Build `OpticOddsStreamConsumer` class — parse incoming SSE events into the market dictionary format the tracker expects.

**Phase 2:** Auto-discover all 491 leagues from `/leagues/active` endpoint — dynamically determine which leagues to stream rather than hardcoding league lists.

**Phase 3:** Replace 28 REST pollers with ~15 SSE stream connections in `main.py` — one connection per sport covers all leagues within that sport.

**Phase 4:** Auto-create Supabase theories per league — as new leagues are discovered, automatically provision theory configurations so the tracker evaluates them.

**Phase 5:** Dashboard auto-expansion for new leagues/sports — the UI dynamically adapts to show whatever leagues have active picks.

### SSE vs REST Tradeoffs

SSE has significant advantages beyond rate limit avoidance: lower latency (events pushed immediately vs. polling intervals), reduced server load (one connection vs. many), and automatic reconnection (built into the SSE protocol). However, SSE connections require persistent processes and may drop during network interruptions, requiring robust reconnection logic with state recovery.

The existing SSE display/tracking separation pattern (see [[concepts/sse-display-tracking-market-separation]]) provides architectural precedent: the scanner already manages SSE connections for pushing data to the dashboard. The OpticOdds SSE integration adds SSE on the *ingest* side of the pipeline — data flows in via SSE from OpticOdds and out via SSE to the dashboard.

### Immediate Impact

Of the 2,400 raw SSE entries received across 52 leagues in initial testing, only 54 made it through the full pipeline. The primary bottleneck was the fixture cache — 495 markets were skipped because the fixture wasn't in cache. This is documented in [[concepts/fixture-cache-silent-market-dropout]]. The SSE data itself is flowing correctly; the downstream pipeline needs to expand to handle the volume.

16 sports showed active markets in the SSE stream, including previously untapped sources: ATP Challenger tennis, Dota 2 esports, NPB Japanese baseball, China CBA basketball, and multiple soccer leagues.

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - OpticOdds remains the sole data provider; SSE streaming deepens operational dependency while expanding coverage
- [[concepts/pinnacle-prediction-market-pipeline]] - The pipeline whose league expansion exposed the REST polling scaling limit
- [[concepts/crypto-edge-non-pinnacle-strategy]] - The strategy that benefits most from expanded league coverage (1,535 non-Pinnacle markets)
- [[concepts/sse-display-tracking-market-separation]] - The existing SSE architecture pattern on the output side; this adds SSE on the ingest side
- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - The tracker-side bottlenecks (ACTIVE_SPORTS, freshness cutoff, SSE filter) that must be resolved for new leagues to produce picks
- [[concepts/fixture-cache-silent-market-dropout]] - The fixture cache limit that silently drops markets from SSE streams

## Sources

- [[daily/lcash/2026-04-18.md]] - REST polling can't scale to 491 leagues (~10K calls/min); SSE endpoint tested at 459KB/15s covering all leagues per sport; only polling 23/491 Kalshi leagues (~5% actual coverage); 16 sports with active SSE markets; 5-phase migration plan documented; 2,400 raw entries → 54 through pipeline (fixture cache bottleneck); plan saved to `brain/findings/2026-04-18-sse-scaling-plan.md` (Session 13:31, 14:39, 14:43)
