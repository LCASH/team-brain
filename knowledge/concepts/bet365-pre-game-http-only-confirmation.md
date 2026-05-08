---
title: "bet365 Pre-Game Props Confirmed HTTP-Only"
aliases: [pre-game-http-only, ws-pre-game-definitive, pre-game-no-ws-deltas, http-polling-permanent]
tags: [value-betting, bet365, websocket, architecture, reverse-engineering, empirical]
sources:
  - "daily/lcash/2026-05-08.md"
created: 2026-05-08
updated: 2026-05-08
---

# bet365 Pre-Game Props Confirmed HTTP-Only

On 2026-05-08, lcash ran definitive empirical tests confirming that bet365 does NOT push pre-game player prop odds changes via WebSocket — even with correct PM subscription format, valid auth tokens, and 1354 active PA subscriptions across 4 fixture IDs. An 11-minute HTTP-vs-WS comparison (Stage 9) found **4 real prop repricings via HTTP polling but zero WS pushes** despite active PM subscriptions for those exact PAs. Separately, a 12-minute "super observer" probe on fixture E25665124 (1464 PAs across 3 FIs) captured 0 WS price deltas and 0 HTTP odds changes but 84 PA removals (market suspensions). This concludes a month-long investigation (April 15 — May 8) into bet365's WS streaming architecture for pre-game props.

## Key Points

- **Stage 9 definitive test**: 11-min HTTP T0/T1 diff found 4 real prop repricings; WS listener with 1354 active PM subscriptions captured 0 deltas for those same PAs — conclusive proof pre-game props are HTTP-polled only
- **29,788 PA-minutes of subscription time** on TEX@NYY with zero WS price events — accepted as genuine pre-game equilibrium (not protocol failure) after control fixtures showed real WS deltas
- **Control validation**: 2/10 PAs from live fixtures returned real `L_U_DELTA` pushes within 30 seconds, confirming the subscription mechanism works — the issue is pre-game market state, not protocol
- **WS subscribe format confirmed**: Client sends `PM{FI}-{PA_ID}`, server responds on `L{FI}-{PA_ID}_30_0` topic — asymmetric format between subscribe and delivery
- **Delta payload format**: `\x15L{FI}-{PA_ID}_30_0\x01U|OD=...;HA=...;SU=...|` — parser regex: `\x15L(\d+)-(\d+)_30_0\x01U\|([^|]+)`
- **SPA default broadcast topics** (`OVInPlay_30_0`, `OV_POPULAR_30_0`) never carry pre-game MLB fixture data — passive monitoring alone is useless for pre-game
- **EMPTY acks growing across refresh waves** (60→180→235→300) confirm subscriptions are accepted — server maintains state but doesn't push

## Details

### The Definitive Stage 9 Test

The most conclusive test was an 11-minute simultaneous comparison of HTTP polling vs WS monitoring on the same fixture. HTTP snapshots were taken at T0 and T1, with a diff applied to detect any odds changes. The WS listener had 1354 active PM subscriptions for all PAs in the fixture.

Result: HTTP diff found 4 prop repricings (genuine odds movements on specific player lines). The WS listener captured 0 delta pushes for any of those 4 PAs during the same window. This is the strongest possible evidence that pre-game prop odds changes are delivered via HTTP CDN refresh only — bet365's WS infrastructure does not push pre-game prop deltas even when the market is actively repricing.

### Super Observer Probe

A complementary test subscribed to 1464 PAs across 3 fixture ID variants for fixture E25665124, capturing both WS frames and HTTP snapshots over 12 minutes. Results: 0 WS price deltas, 0 HTTP odds changes, but 84 PA removals (market suspensions/closures). This confirmed that the WS stream does carry market-level events (suspensions) but not price deltas for pre-game props.

Two new WS frame prefixes were also discovered (0x31 and 0x23) — likely control-plane or session routing messages, not data delivery.

### Control Fixture Validation

To ensure the subscription mechanism itself was working, 10 PAs from 5 actively-pushing live fixtures were subscribed. 2 of 10 returned real `L_U_DELTA` pushes within 30 seconds — confirming the subscribe format is correct and the server processes injected subscriptions. The 20-50% hit rate in any 30-second window is normal for individual PA pushes (even on busiest live fixtures, individual PAs only push 5-11 times/min).

### Architecture Implications

This conclusively confirms the v4 hybrid architecture:

| Market State | Primary Source | Latency |
|-------------|---------------|---------|
| **Pre-game (hours out)** | HTTP wizard refresh (30s NBA, 60s MLB) | 30-60s |
| **Pre-game (near tipoff)** | HTTP wizard refresh (accelerated) | 15-30s |
| **Live/in-play** | WS PM subscriptions | Sub-second |

The transition from HTTP-primary to WS-primary happens when markets become volatile (near tipoff or live). Pre-game lines are effectively static — sharps haven't started active trading — so HTTP polling at 30-60s intervals captures all meaningful price changes.

### Month-Long Investigation Summary

| Date | Finding | Status |
|------|---------|--------|
| Apr 15 | P-ENDP session-bound topic authorization blocks prop WS | Correct |
| May 6 | 703 updates/120s via WS (in-play trading) | Correct but not generalizable |
| May 7 | 4-sport injection: 100% ack, 0% deltas | Correct for pre-game |
| May 7 | Horse race probe: PM deltas work for volatile markets | Correct — live markets stream |
| **May 8** | **Stage 9: 4 HTTP repricings, 0 WS deltas on same PAs** | **Definitive — pre-game = HTTP only** |

## Related Concepts

- [[concepts/bet365-ws-pre-game-prop-streaming-limitation]] - The broader analysis of pre-game WS limitations; this article provides the definitive empirical confirmation
- [[concepts/bet365-ws-pm-live-delta-confirmation]] - Horse race probe confirmed WS works for volatile markets; this article confirms it does NOT work for pre-game
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native scraper architecture that must use HTTP refresh loops for pre-game data
- [[concepts/bet365-ws-subscription-injection-viability]] - The 4-sport injection test (May 7) that preceded this definitive test; EMPTY ack semantics confirmed as "dormant buffer"
- [[concepts/bet365-mlb-wizard-first-regression-fix]] - The wizard-first HTTP approach that this finding validates as the correct pre-game architecture

## Sources

- [[daily/lcash/2026-05-08.md]] - Stage 9 empirical test: 11-min HTTP-vs-WS comparison found 4 real prop repricings via HTTP, 0 WS pushes despite 1354 active PM subscriptions — definitive proof pre-game props are HTTP-only (Session 09:04). Super observer probe: 1464 PAs across 3 FIs, 12 min, 0 WS deltas, 0 HTTP changes, 84 PA removals; two new frame prefixes 0x31/0x23 discovered (Session 07:48). Control validation: 2/10 PAs from live fixtures returned real L_U_DELTA within 30s confirming mechanism works; 29,788 PA-minutes of TEX@NYY subscription time with zero events — accepted as pre-game equilibrium (Session 00:36). WS subscribe/response format asymmetry: client PM{FI}-{PA_ID}, server L{FI}-{PA_ID}_30_0; EMPTY acks growing 60→180→235→300 across refresh waves (Session 00:36)
