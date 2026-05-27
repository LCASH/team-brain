---
title: "Connection: WebSocket-First Bookie Onboarding Principle"
connects:
  - "concepts/neds-pointsbet-ws-racing-adapters"
  - "concepts/boostbet-racing-adapter"
  - "concepts/betr-no-websocket-xhr-only-architecture"
  - "concepts/tabtouch-kambi-white-label-sports"
sources:
  - "daily/lcash/2026-05-26.md"
created: 2026-05-26
updated: 2026-05-26
---

# Connection: WebSocket-First Bookie Onboarding Principle

## The Connection

On 2026-05-26, the user established a hard rule for all future bookie onboarding: **"we always optimise for websocket."** This reorders the recon priority for every new sportsbook integration. The rule emerged after the Neds investigation initially concluded WS was in-play-only (wrong subscribe channel), was corrected by the user's domain knowledge ("I see odds moving crazy on the site"), and re-investigation proved WS carries pre-race fixed odds at 137 frames/90s. The principle connects four prior bookie onboarding experiences that each discovered transport architecture differently.

## Key Insight

The non-obvious insight is that **static recon (scanning JS bundles) is insufficient for determining WS presence.** BoostBet's 25 JS bundles showed zero `wss://` references, yet lazy-loaded WS connections are only visible via live DevTools observation. Betr was confirmed zero-WS only after exhaustive CDP capture across 3 separate sessions. The correct methodology is always live browser observation via CDP, never static bundle analysis.

The rule also encodes a **performance hierarchy**: WS adapters (sub-second tick freshness) are 14-60x faster than REST adapters (1-15s polling intervals). For a scanner where odds staleness directly impacts EV calculation accuracy, the transport protocol is the single highest-leverage architectural choice — worth investing 2-4 hours of recon to get right before writing a single line of adapter code.

## Evidence

Four bookie onboarding experiences validate the rule:

| Bookie | WS Recon Method | Finding | Adapter Type |
|--------|----------------|---------|-------------|
| **Betr** (May 19) | Exhaustive 3-session CDP capture | Zero WS confirmed | REST polling (XHR 13-15s) |
| **BoostBet** (May 26) | Static JS + live CDP | Zero WS in bundles, zero in live capture | REST polling |
| **Neds** (May 26) | Live CDP — **wrong channel initially** | WS confirmed on `pricing/prices` channel | REST-first, WS Phase 2 |
| **Pointsbet** (May 26) | Live CDP | Azure SignalR confirmed | REST-first, WS Phase 2 |

The Neds case is the canonical cautionary tale: subscribing to `racing/livemarketupdated` (in-play only) instead of `pricing/prices` (pre-race odds) led to a technically correct but operationally wrong conclusion. The user's domain expertise — knowing that odds visibly move on the Neds website — was the correction signal. **Always capture the browser's actual subscribe payloads** before concluding a WS doesn't carry data.

## The Recon Priority Sequence

1. **Live CDP WS monitoring** — navigate to race pages in AdsPower, monitor `Network.webSocketCreated` and `Network.webSocketFrameReceived` for 2-3 minutes per page state
2. **Characterize subscribe protocol** — capture actual browser subscribe payloads (per-market vs global firehose, auth requirements, channel names)
3. **Verify pre-race data** — confirm WS carries pre-race fixed odds, not just in-play updates (the Neds mistake)
4. **If no WS**: fall back to REST polling or HTML scraping
5. **If WS confirmed**: estimate adapter effort (6hrs for known protocols like Socket.IO, 1-1.5 days for new protocols like SignalR)

## Related Concepts

- [[concepts/neds-pointsbet-ws-racing-adapters]] - The session that established the rule; wrong subscribe channel as the canonical mistake
- [[concepts/boostbet-racing-adapter]] - Pure REST adapter after WS recon confirmed zero WS
- [[concepts/betr-no-websocket-xhr-only-architecture]] - The exhaustive WS investigation (3 CDP sessions) that confirmed betr is XHR-only
- [[concepts/tabtouch-kambi-white-label-sports]] - Kambi Socket.IO push confirmed live-only (no pre-game); same "verify pre-race data" lesson as Neds
- [[concepts/tab-global-ws-rotation-pattern]] - TAB WS exists but has server-side global rotation kills — WS presence alone doesn't guarantee reliability
