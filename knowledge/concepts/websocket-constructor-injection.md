---
title: "WebSocket Constructor Injection"
aliases: [ws-constructor-wrap, addScriptToEvaluateOnNewDocument, pre-page-load-injection]
tags: [browser-automation, websocket, cdp, reverse-engineering, bet365]
sources:
  - "daily/lcash/2026-04-13.md"
created: 2026-04-13
updated: 2026-04-13
---

# WebSocket Constructor Injection

A browser automation technique using CDP's `Page.addScriptToEvaluateOnNewDocument` to wrap the `WebSocket` constructor before any page JavaScript executes, storing every WebSocket instance the SPA creates in a globally accessible array (`window.__b365_ws_list`). This solves the problem of capturing WebSocket instances that the SPA creates inside closures and never exposes globally, enabling subscription injection and message buffering on the SPA's own authenticated connection.

## Key Points

- `Page.addScriptToEvaluateOnNewDocument` injects JavaScript before any page script runs, allowing the `WebSocket` constructor to be wrapped at creation time
- The wrapper stores every SPA-created WebSocket in `window.__b365_ws_list`, then the adapter picks the open connection targeting `365lpodds`
- Prototype monkey-patching after page load fails because the SPA binds `send` to the instance inside a closure — the wrapper must be in place before the SPA initializes
- Subscriptions are sent via `page.evaluate(ws.send('\x16' + msg))` on the captured WS; messages are received via `ws.addEventListener('message', ...)` which coexists with the SPA's own `onmessage` handler
- Messages are buffered JavaScript-side and polled from Python every 0.5 seconds; a parallel CDP `Network.webSocketFrameReceived` listener runs as backup
- A new WebSocket from the page to `premws-pt1.365lpodds.com` fails with `onerror` because the WS host is cross-origin and cookies aren't sent — hijacking the existing connection is the only path

## Details

### Why Constructor Injection Is Necessary

The bet365 SPA creates its WebSocket connections during initialization and stores the instances inside JavaScript closures — they are never assigned to a global variable or accessible DOM property. After the page loads, there is no way to obtain a reference to the WebSocket object through the page's JavaScript context. Prototype-level monkey-patching (e.g., overriding `WebSocket.prototype.send`) was attempted but failed because the SPA binds `send` to the specific instance at creation time, bypassing any later prototype changes.

Opening a new WebSocket to the same endpoint (`wss://premws-pt1.365lpodds.com/zap/`) from within the page also fails. The WS host (`365lpodds.com`) is a different origin from the page (`bet365.com.au`), so the browser does not send cookies cross-origin. Without the session cookies, the server returns an error via `onerror`. Direct Python WebSocket connections are similarly rejected with HTTP 403 (see [[concepts/browser-mediated-websocket-streaming]]).

The only viable approach is to intercept the WebSocket at construction time — before the SPA's closure captures it — by wrapping the constructor.

### The Technique

The injection uses CDP's `Page.addScriptToEvaluateOnNewDocument` command, which registers JavaScript that executes in every new document context before any page-originating scripts run. The injected script:

1. Saves a reference to the original `WebSocket` constructor
2. Replaces `window.WebSocket` with a wrapper function that: (a) creates a real WebSocket using the saved constructor, (b) stores the instance in `window.__b365_ws_list`, (c) returns the instance to the caller
3. The wrapper is transparent to the SPA — it receives a genuine WebSocket object and functions normally

After page load, the adapter selects the appropriate WebSocket from `window.__b365_ws_list` by filtering for connections to `365lpodds` hosts. It then interacts with the captured connection through two channels:

**Outbound (subscriptions):** `page.evaluate()` calls `ws.send('\x16' + subscriptionPayload)` where `\x16` is the bet365 protocol's subscription prefix. The `send` call executes in the browser's context, inheriting full authentication.

**Inbound (data):** An `addEventListener('message', ...)` handler is attached to the captured WebSocket. This coexists with the SPA's own `onmessage` handler — `addEventListener` and `onmessage` are independent dispatch mechanisms in the WebSocket API. The listener buffers incoming messages in a JavaScript-side array, which Python polls every 0.5 seconds via `page.evaluate()`. A parallel CDP `Network.webSocketFrameReceived` listener captures the same frames at the protocol level as a backup.

### Discovery Endpoint Changes

The same session discovered that bet365 changed its racing discovery endpoint. The old `/contentdata/racecouponcontentapi/T6Splash` is dead. The new endpoint is `/nexttojumpcontentapi/splash` (no `/contentdata/` prefix) and only fires on cold page loads. Reusing an existing tab produces a lighter delta-only response at `/contentdata/nexttojumpcontentapi/splash`. The solution is to open a fresh tab via `ctx.new_page()` for each discovery scan and close it after parsing — the cold-load URL is per-page-session, not per-browser-session.

### Auth Extraction Flow

The complete adapter flow using constructor injection:

1. **Discovery:** Open fresh tab → navigate to racing → intercept full splash response via CDP → close tab
2. **Auth:** On main tab (with injected constructor wrapper already in place), cycle through 5 hash navigations to force a subscription frame. Capture `sync_term` from the `,A_{1452-char-token}` pattern in WS frames
3. **Runner map:** Tab-click capture technique from `bet365_local.py` — click each race tab within each meeting, intercept `racecoupon` HTTP responses via CDP, parse fixture/participant IDs and runner names
4. **Stream:** Send subscription messages on the captured WS, receive and parse odds updates

Page reload kills the WebSocket, so auth extraction (which needs the WS to be alive for frame sniffing) must happen after the constructor injection but before any operation that would reload the page.

## Related Concepts

- [[concepts/browser-mediated-websocket-streaming]] - The broader piggybacking architecture that this technique enables
- [[concepts/bet365-racing-adapter-architecture]] - The adapter that implements this technique for live odds streaming
- [[concepts/cdp-browser-data-interception]] - CDP frame capture used as a backup data channel alongside addEventListener
- [[concepts/bet365-racing-data-protocol]] - The protocol format of messages sent and received on the captured WebSocket
- [[connections/anti-scraping-driven-architecture]] - The defense layers that made constructor injection necessary

## Sources

- [[daily/lcash/2026-04-13.md]] - Full WS constructor injection implementation: `Page.addScriptToEvaluateOnNewDocument` wrapping WebSocket constructor, `window.__b365_ws_list` capture, prototype monkey-patch failure, cross-origin new-WS failure, addEventListener coexistence with onmessage, 0.5s Python polling, discovery endpoint migration, auth extraction flow (Session 15:00 onward)
