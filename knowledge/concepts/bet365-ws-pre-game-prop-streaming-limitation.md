---
title: "bet365 WS Pre-Game Prop Streaming Limitation"
aliases: [ws-pre-game-limitation, ov-popular-firehose, ws-http-hybrid, pre-game-static-lines, ws-not-per-game]
tags: [value-betting, bet365, websocket, architecture, scraping, reverse-engineering]
sources:
  - "daily/lcash/2026-05-07.md"
  - "daily/lcash/2026-05-08.md"
created: 2026-05-07
updated: 2026-05-08
---

# bet365 WS Pre-Game Prop Streaming Limitation

bet365's WebSocket topic `OV_POPULAR_30_0` is a **global cross-sport featured content firehose**, NOT per-game subscriptions. On 2026-05-07, extensive probing confirmed that WS frames carry player names, odds (`OD=`), and lines (`HA=`) — but only for content bet365 chooses to feature (promoted games, in-play markets, cross-sport highlights), not for arbitrary pre-game fixtures. Of 275 frames captured in 120 seconds, **0 PA_IDs overlapped** with the scanner's 404 wizard-discovered PAs for specific games. Pre-game player prop lines are essentially static hours before tipoff and generate zero WS delta updates until active trading begins near game time.

## Key Points

- `OV_POPULAR_30_0` / `OVInPlay_30_0` are bet365's **global featured firehose** — carry cross-sport promoted content, not per-game feeds
- 275 WS frames captured, 1,447 NA records streamed — all from other fixtures (soccer, tennis, promoted NBA); target fixture appeared in 1/275 frames
- **0 PA_ID overlap** between WS frames and wizard's 404 PAs for specific pre-game games — WS carries different PA_ID ranges than HTTP wizard responses
- Per-fixture WS subscription injection remains **impossible** (session-bound auth confirmed April 15 — see [[concepts/bet365-ws-topic-authorization]])
- Pre-game lines are **mostly static** — WS deltas only fire when odds actively move, which is rare hours before tipoff; the May 6 "703 updates in 120s" success was during **NBA Playoffs in-play trading**, not generalizable to pre-game
- Current WS orchestrators do ONE wizard fetch per game and never re-fetch — no periodic refresh means line movement between fetches is invisible
- **Agreed architecture**: HTTP refresh loop (10-15s) as primary, WS listener as free supplement for near-tipoff/in-play deltas

## Details

### The OV_POPULAR Firehose

bet365's WebSocket stream on the `OV_POPULAR_30_0` topic delivers a curated feed of content that bet365 promotes across all sports. This includes:
- In-play markets with active trading (high-visibility games)
- Featured pre-game bets (bet365's editorial picks)
- Cross-sport highlights (a soccer goal triggers a WS update even on the NBA page)

This topic is NOT controllable by the client. The SPA subscribes to `OV_POPULAR_30_0` on page load, and bet365's server decides what content to stream. There is no mechanism to request "stream PA updates for game E25635191" — that would require per-fixture subscription injection, which is blocked by session-bound topic authorization (see [[concepts/bet365-ws-topic-authorization]]).

### Testing Methodology Error

A critical testing error was identified and corrected during the investigation: the initial WS probe attached to a **new blank tab**, not the user's existing tab with active page subscriptions. The new tab had no page context and therefore received only the global `OV_POPULAR` feed. When the probe was re-attached to the user's actual live tab (which had bet365's MLB futures page rendered), WS deltas DID flow — 132 frames/60s with real `OD=`/`HA=` values — but for the **currently rendered page's markets** (MLB futures on the D48 landing), not for individually discovered games.

This distinction is architecturally important: WS delivers deltas for whatever the page is currently rendering. The V3 orchestrator's monitor page would need to be navigated to each game individually to receive that game's WS deltas — but sequential `monitor.goto(game_url)` cancels previous subscriptions. Only the last-navigated game's topics persist.

### Pre-Game Line Stationarity

Pre-game player prop lines on bet365 are essentially static until approximately 30-60 minutes before tipoff. The odds are published hours in advance but don't change because:
- No significant sharp action has arrived yet
- bet365's market makers haven't updated their models for late-breaking information
- The CDN cache (documented at ~5+ minute TTL in [[concepts/bet365-nba-bb-wizard-v3-rewrite]]) further dampens any movement

This means WS monitoring of pre-game games would capture zero or near-zero delta updates even if per-game subscription were possible. The line movement that matters — when sharp action moves the market — happens close to game time and is better captured by HTTP polling at 10-15 second intervals.

### PA_ID Range Analysis and Disjoint ID Spaces

PA_IDs are date/time-specific ranges that help identify which era of data a WS frame refers to:
- May 6 live trading: `1219xxx` range
- May 7 pre-game: `1224xxx` range  
- May 7 currently-live: `1235-1240xxx` range

The non-overlap between WS frames (carrying `1235-1240xxx` live PA_IDs) and wizard responses (containing `1224xxx` pre-game PA_IDs) confirms that WS and HTTP serve **fundamentally disjoint data populations** — WS carries actively-trading markets while HTTP wizard returns the full pre-game prop surface. This disjoint ID space is the root cause of ALL "0 PA_ID overlap" findings across every probe test.

Critically, per-G-ID `page.goto(/G{gid}/S^1/)` navigation captures PAs in the **live trading ID space** (`1238xxx` — same as WS), not the static wizard space (`1224xxx`). This is why the MLB scraper's 26 G-ID walk has always produced data that overlaps with WS deltas, while the NBA I99 wizard produces IDs that never overlap. The per-G-ID approach fires both an HTTP `partial?G{gid}` response AND activates SPA WS subscription for that market group simultaneously. See [[concepts/bet365-ws-subscription-injection-viability]] for the full disjoint ID space analysis.

### Betslip HTTP Validation (Not WS)

A significant operational finding from Session 19:51: bet365's "Place Bet" flow validates odds via an HTTP re-fetch at the moment of submission, NOT via real-time WS streaming. The betslip displays live odds from WS updates (via the `BS` betslip topic prefix), but the transactional price comes from HTTP. This means the "live odds" feel in the betslip UI is presentation — sub-second WS accuracy is not required for capturing the same prices bet365 uses for bet placement.

### The Hybrid Architecture Decision

Based on these findings, the agreed architecture for V3 is:

| Layer | Role | Latency | Coverage |
|-------|------|---------|----------|
| **HTTP refresh loop (10-15s)** | Primary data source | 10-15s worst case | All pre-game props, all games |
| **WS listener** | Supplement for live/near-tipoff | Sub-second when available | Only bet365-featured content |

The `_refresh_loop` will be added to both `WSNBAOrchestrator` and `WSMLBOrchestrator`, performing periodic wizard fetches (I99 for NBA, 26 MG hash-navs for MLB) at 10-15 second intervals. WS frames from `OV_POPULAR` will be opportunistically matched against the PA map — any overlap provides a free sub-second update between refresh cycles.

### Yesterday's Findings in Context

The May 6 findings documenting "703 updates in 120s" with WS player prop data (see [[concepts/bet365-ws-native-scraper-architecture]]) were technically correct but **contextually misleading**. Those 703 updates were captured during NBA Playoffs in-play trading — a period of maximum WS activity where bet365 actively streams all in-play markets. The finding was time-bound: WS is valuable during in-play but nearly silent for pre-game hours before tipoff. The V3 architecture must account for both states.

### Horse Race Live Delta Confirmation (Session 23:32)

Session 23:32 provided definitive evidence that WS PM subscriptions DO deliver real-time deltas for volatile/active markets — a live horse race probe (FI=194196581) captured genuine PM U-deltas with `DO=`, `OD=`, and `OH=` fields. The same session's MLB pre-game betslip probe returned EMPTY for all 7 PAs, confirming pre-game dormancy.

This reframes the "pre-game limitation" documented in this article: it is NOT a protocol limitation or a defense mechanism — it is the **correct behavior** of a streaming system when there are no price changes to stream. Pre-game props are static hours before tipoff because sharp action hasn't started. The EMPTY ack means "buffer dormant, nothing has changed" — not "subscribe refused." The architecture consequence: for near-tipoff/live markets, PM subscriptions should be primary (sub-second), with HTTP polling demoted to safety net. See [[concepts/bet365-ws-pm-live-delta-confirmation]] for the complete analysis.

## Related Concepts

- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native scrapers that need HTTP refresh loops added; the "703 updates/120s" finding that was contextually misleading
- [[concepts/bet365-ws-topic-authorization]] - Session-bound P-ENDP topic authorization preventing per-fixture subscription injection; reconfirmed on May 7
- [[concepts/bet365-nba-bb-wizard-v3-rewrite]] - The BB wizard endpoint (I99) that the HTTP refresh loop will use; CDN cache TTL ~5min bounds minimum useful refresh interval
- [[connections/ws-viability-sport-rendering-divergence]] - The sport-rendering divergence that determines WS viability; pre-game prop streaming is non-viable for all sports, not just NBA
- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture where the hybrid HTTP+WS approach will be deployed
- [[concepts/bet365-ws-subscription-injection-viability]] - Deep protocol probe confirming disjoint PA_ID spaces as root cause of 0 overlap; interceptor-on-SPA-WS works for injection; betslip HTTP validation
- [[concepts/bet365-ws-pm-live-delta-confirmation]] - Horse race probe that confirmed PM deltas work for volatile markets, reframing the pre-game limitation as expected behavior rather than a protocol constraint
- [[concepts/bet365-pre-game-http-only-confirmation]] - Definitive May 8 empirical proof: 4 HTTP repricings vs 0 WS deltas on the same PAs in an 11-minute test; concludes the month-long investigation

## Sources

- [[daily/lcash/2026-05-07.md]] - 275 frames captured, 0 PA_ID overlap with 404 wizard PAs; OV_POPULAR_30_0 is global firehose not per-game; per-fixture injection impossible (April 15 reconfirmed); testing methodology error: new blank tab vs existing tab with subscriptions; 132 frames/60s on live tab but for rendered page's markets only; pre-game lines mostly static; PA_ID ranges date-specific (1219xxx live May 6, 1224xxx pre-game May 7, 1235xxx live May 7); agreed hybrid: 10-15s HTTP refresh + WS supplement; yesterday's 703/120s was in-play trading, not generalizable (Sessions 18:40, 19:20). **Disjoint PA_ID spaces confirmed as root cause**: HTTP wizard 1224xxx (static catalog) vs WS 1238-1240xxx (live trading) — fundamentally different populations; per-G-ID page.goto fires HTTP partial + activates WS subscription in live trading space; betslip validates via HTTP re-fetch at "Place Bet" click, not WS; BS prefix for betslip-specific WS topics (Session 19:51). **Horse race live delta confirmation** (Session 23:32): live horse race FI=194196581 captured real PM U-deltas (DO=, OD=, OH=); MLB pre-game betslip probe returned EMPTY for all 7 PAs; EMPTY reinterpreted as "buffer dormant" not "refused"; confirms pre-game limitation is expected behavior (static lines = no deltas), not a protocol constraint; v4 architecture revised for near-tipoff/live markets
- [[daily/lcash/2026-05-08.md]] - **Definitive HTTP-only confirmation**: Stage 9 empirical test — 11-min HTTP-vs-WS comparison found 4 real prop repricings via HTTP, 0 WS pushes despite 1354 active PM subscriptions for those exact PAs. Super observer probe: 1464 PAs across 3 FIs, 12 min, 0 WS deltas, 84 PA removals. Control validation: 2/10 PAs from live fixtures returned real L_U_DELTA within 30s confirming mechanism works. 29,788 PA-minutes of TEX@NYY subscription with zero events — accepted as pre-game equilibrium. Concludes month-long investigation (Sessions 00:36, 07:48, 09:04)
