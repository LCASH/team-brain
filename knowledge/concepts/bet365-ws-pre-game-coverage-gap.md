---
title: "bet365 WebSocket Pre-Game Coverage Gap"
aliases: [ws-pre-game-gap, ov-popular-firehose, ws-vs-http-polling, pre-game-static-lines, hybrid-ws-http-architecture]
tags: [value-betting, bet365, websocket, architecture, scraping, data-quality]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# bet365 WebSocket Pre-Game Coverage Gap

bet365's WebSocket `OV_POPULAR_30_0` topic is a **cross-sport global featured content firehose**, not per-game subscription feeds. It carries whatever bet365 promotes across all sports — live games, featured bets, trending markets — but NOT per-fixture pre-game player prop updates. On 2026-05-07, testing confirmed 0 PA_ID overlap between the WS firehose and the scraper's wizard-mapped player props across NBA, MLB, and NRL. Pre-game prop lines are mostly static until ~30 minutes before tip-off, generating zero WS deltas. This means HTTP polling (10-15s wizard refresh) is required for pre-game odds; WS is only a useful supplement near tipoff when games become featured/in-play.

## Key Points

- **`OV_POPULAR_30_0` / `OVInPlay_30_0`** are global featured firehoses — NOT per-game subscription feeds; carry cross-sport promoted content
- **0 PA_ID overlap** between WS captured frames and wizard-mapped PAs across 275+ frames tested on NBA, MLB, NRL surfaces
- **Pre-game lines are mostly static** hours before tip-off — stable sharp lines generate zero WS deltas, making WS useless for pre-game odds capture
- **Yesterday's "703 updates in 120s" was in-play trading** during NBA Playoffs — time-of-day bound, not generalizable to pre-game
- **Per-fixture WS subscription injection remains impossible** (April 15 session-bound auth finding reconfirmed) — cannot force bet365 to stream specific games' topics
- **Hybrid architecture decided**: add `_refresh_loop` (10-15s HTTP wizard refresh) to `WSNBAOrchestrator` and `WSMLBOrchestrator`; keep WS as free supplement for near-tipoff deltas
- **Sequential `monitor.goto()` cancels previous game's subscriptions** — navigating to game N on the monitor page unsubscribes from game N-1; one-tab-per-game doesn't fix it because topics are global

## Details

### The Investigation

On 2026-05-07, lcash ran multiple WS probe tests to determine whether bet365's WebSocket could replace HTTP polling for pre-game player props:

| Test | Surface | Frames | PA_ID Overlap | Result |
|------|---------|--------|---------------|--------|
| NBA pre-game (CLE@DET) | 275 frames/120s | 1447 NA records | **0 matches** | All from other fixtures |
| NRL active game | 132 frames/60s | Real OD=/HA= values | **0 matches** with our games | Deltas for page's rendered markets only |
| MLB games | Multiple surfaces | Similar pattern | **0 matches** | Same global firehose, not per-game |

The critical insight came from testing methodology: early probes attached to a **new blank tab** (wrong measurement — no page context, no subscriptions), while later probes attached to the **user's actual live tab** (correct measurement — confirmed WS deltas DO flow, but for the page's currently-rendered markets, not our discovered games).

### Why WS Cannot Replace HTTP for Pre-Game Props

Three independent reasons make WS insufficient for pre-game prop scraping:

**1. Global firehose, not per-game feeds.** The `OV_POPULAR_30_0` topic carries content that bet365's editorial team promotes across all sports. A pre-game NBA game hours from tip-off will not be featured unless it's a marquee matchup — and even then, the featured content is typically game-level (moneyline, spread), not player props.

**2. Pre-game lines are static.** Sportsbook player prop lines are set once (typically 12-24 hours before tip-off) and rarely move until sharp action arrives close to game time. A line that doesn't move generates zero WS deltas. The May 6 finding of "703 updates in 120s" occurred during live NBA Playoffs trading — games actively in play with frequent odds movement. Pre-game props hours from tip-off produce near-zero deltas.

**3. Per-fixture subscription injection is impossible.** The session-bound topic authorization documented on April 15 (see [[concepts/bet365-ws-topic-authorization]]) prevents injecting arbitrary `PM{fid}-{pid}` subscriptions. The SPA registers topics via `P-ENDP` frames based on what's rendered on screen. External subscription injection is silently dropped. This was reconfirmed on 2026-05-07: the WS connection uses session-bound auth (signed/encrypted first frame, session-tied `uid`, custom `zap-protocol-v2` subprotocol) that cannot be replayed or forged for arbitrary topic subscriptions.

### The Monitor Page Architecture Flaw

An additional WS limitation was discovered: sequential `monitor.goto(game_url)` in the orchestrator means each navigation cancels the previous game's subscriptions. When the monitor page navigates from Game A to Game B, the SPA unsubscribes from Game A's topics and subscribes to Game B's. Only the last-navigated game's WS topics are active. Creating one tab per game doesn't fix this because WS topics are global (shared across all tabs in the browser session), not per-tab.

### The Hybrid Architecture Decision

Given these limitations, the agreed architecture is:

| Component | Role | Latency |
|-----------|------|---------|
| HTTP wizard refresh (10-15s cycle) | Primary pre-game odds source | 10-15s worst case |
| WS listener (passive) | Supplement for near-tipoff deltas | Sub-second when games are featured |

The `_refresh_loop` will be added to both `WSNBAOrchestrator` and `WSMLBOrchestrator`. Each cycle performs one I99 wizard fetch per game, diffs the response against the PA map, and updates `_live_odds` in place. The WS listener continues running passively — when games approach tip-off and bet365 features them (or they go in-play), WS deltas will arrive and provide sub-second updates that supplement the HTTP polling.

This hybrid approach acknowledges a fundamental architectural reality: the "WS-native scraper" name is aspirational rather than literal. WS provides the subscription framework and the delta update channel, but the actual pre-game data acquisition is HTTP-driven.

### PA_ID Range Observations

PA_IDs are date/time specific, which complicates cross-session matching:

| Context | PA_ID Range |
|---------|------------|
| May 6 live (NBA Playoffs in-play) | 1219xxx |
| May 7 pre-game (hours before tip) | 1224xxx |
| May 7 currently-live (other sports) | 1235-1240xxx |

This means WS frames captured today cannot be matched against yesterday's PA maps — the IDs have rotated. Any WS delta capture must use the same session's wizard-derived PA map for matching.

## Related Concepts

- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native architecture that this article reveals requires HTTP polling supplementation; the "WS-native" name describes the subscription framework, not the data source
- [[concepts/bet365-ws-topic-authorization]] - Session-bound P-ENDP topic authorization prevents per-fixture WS subscription injection — reconfirmed on 2026-05-07
- [[connections/ws-viability-sport-rendering-divergence]] - The racing WS works because each runner gets per-participant render registrations; props don't get individual registrations — this article adds that even the global firehose doesn't carry pre-game props
- [[concepts/bet365-nba-bb-wizard-v3-rewrite]] - The BB wizard (I99) endpoint that the HTTP refresh loop will use; CDN cache TTL ~5min bounds the minimum useful refresh interval
- [[concepts/cdpsession-playwright-pipe-contention]] - The CDPSession pipe contention that must be managed during HTTP refresh cycles on the orchestrator's page
- [[concepts/bet365-in-browser-cdp-fetch-transport]] - NST direct fetch is dead; navigation-fired coupon capture is the only HTTP extraction path

## Sources

- [[daily/lcash/2026-05-07.md]] - OV_POPULAR_30_0 confirmed as cross-sport firehose; 0 PA_ID overlap across 275+ frames on NBA/MLB/NRL; pre-game lines static hours before tipoff; May 6 "703 updates/120s" was in-play trading; monitor.goto() cancels previous game subscriptions; hybrid architecture decided: 10-15s HTTP refresh + passive WS supplement; PA_ID ranges are date-specific (1219xxx May 6 live, 1224xxx May 7 pre-game); WS session-bound auth prevents topic injection; testing on new blank tab vs user's live tab produces different results (Sessions 18:40, 19:20)
