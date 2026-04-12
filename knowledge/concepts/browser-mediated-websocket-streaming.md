---
title: "Browser-Mediated WebSocket Streaming"
aliases: [ws-piggybacking, browser-ws-injection, websocket-piggyback]
tags: [websocket, browser-automation, streaming, anti-bot, bet365]
sources:
  - "daily/lcash/2026-04-11.md"
created: 2026-04-11
updated: 2026-04-12
---

# Browser-Mediated WebSocket Streaming

A pattern for consuming real-time WebSocket data from services that reject direct connections. Instead of opening an independent WebSocket from a script, the script piggybacks on an existing browser's WebSocket connection — injecting subscription messages via JavaScript execution and capturing responses via CDP frame interception. This approach inherits the browser's authenticated session, bypassing connection-level authentication and anti-bot measures.

## Key Points

- bet365 rejects independent Python WebSocket connections with HTTP 403 — the server validates browser-specific headers, cookies, and TLS fingerprints
- Piggybacking injects subscription messages into the browser's existing WS connection via `page.evaluate()`, which sends from the browser's authenticated context
- Responses are captured via CDP `Network.webSocketFrameReceived` rather than high-level Playwright APIs (which miss pre-existing connections)
- The browser's WS connection carries ~7-8 odds updates per second across all subscribed markets, delivering ~126KB in 30 seconds
- The browser only subscribes to the currently-viewed race by default — custom subscriptions must be injected for broader coverage

## Details

### Why Direct WebSocket Fails

When attempting to open a WebSocket connection directly from Python (e.g., using `websockets` or `aiohttp`) to bet365's streaming endpoint at `wss://premws-pt1.365lpodds.com/zap/`, the server returns HTTP 403. This is not simply a missing authentication header — bet365's WebSocket infrastructure validates the TLS fingerprint, HTTP headers, cookie jar, and likely the connection's origin context. Replicating all of these programmatically is fragile and subject to breakage as bet365 updates its anti-bot measures.

### The Piggybacking Architecture

Instead of fighting the authentication, the adapter reuses the browser's existing WebSocket connection. The browser (running in AdsPower with anti-detection fingerprinting) has already established and authenticated the WebSocket. The adapter interacts with it through two channels:

1. **Outbound (subscriptions):** `page.evaluate()` executes JavaScript in the page context that sends subscription messages through the browser's existing WebSocket object. The subscription format is `PM{fixture_id}-{participant_id}` for individual runner odds streams.

2. **Inbound (data):** CDP's `Network.webSocketFrameReceived` event fires for every frame received on any WebSocket connection, providing the raw frame payload. The adapter filters for odds-related messages (containing `PM` prefixes and `U|` or `F|` data markers).

This architecture means the adapter never directly touches the WebSocket — it operates entirely through the browser as a proxy. The browser handles authentication, reconnection (connections rotate every ~80 seconds), and TLS negotiation.

### Subscription Scope

By default, the browser's bet365 client only subscribes to WebSocket feeds for the race currently displayed on screen. During a 30-second capture window, only 4 fixture IDs were observed in WS traffic despite 48 races being available. To get comprehensive odds streaming, the adapter must inject subscriptions for all fixture/participant ID pairs discovered during the initial HTTP discovery scan. The participant IDs from the `racecoupon` endpoint map directly to the WS subscription format.

### ID Resolution Challenge

WebSocket odds updates arrive as `PM{fixture}-{participant}U|DO=30/1;` — containing only numeric IDs, not runner names. The adapter must maintain a mapping table from the initial HTTP `racecoupon` scan that associates each `{fixture}-{participant}` pair with a runner name, barrier position, and other metadata. Without this mapping, the streaming data is uninterpretable.

## Related Concepts

- [[concepts/bet365-racing-data-protocol]] - The protocol format used in both subscription and response messages
- [[concepts/cdp-browser-data-interception]] - The CDP technique that enables frame capture from the piggybacked connection
- [[concepts/bet365-racing-adapter-architecture]] - The adapter architecture that combines HTTP discovery with WS streaming
- [[concepts/spa-navigation-state-api-access]] - The HTTP discovery scan that provides the ID mapping needed for WS interpretation

## Sources

- [[daily/lcash/2026-04-11.md]] - Python WS connection returning 403 (Session 16:06); piggybacking architecture via page.evaluate() and CDP (Session 16:06); browser default subscription scope limited to current race (Session 16:06); 7-8 updates/sec throughput (Session 16:06)
