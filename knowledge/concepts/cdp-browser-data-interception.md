---
title: "CDP Browser Data Interception"
aliases: [cdp-interception, chrome-devtools-protocol-capture, cdp-websocket-capture]
tags: [cdp, browser-automation, websocket, scraping, reverse-engineering]
sources:
  - "daily/lcash/2026-04-11.md"
created: 2026-04-11
updated: 2026-04-12
---

# CDP Browser Data Interception

Chrome DevTools Protocol (CDP) provides low-level access to browser internals for intercepting both HTTP responses and WebSocket frames. When attaching to an existing browser session (e.g., via AdsPower), CDP-level interception is required because Playwright's high-level APIs (`page.on('websocket')`) only capture connections established after the script attaches, missing pre-existing connections.

## Key Points

- `page.on('websocket')` only fires for **new** WebSocket connections — it misses connections established before the script attached to the browser
- CDP's `Network.webSocketFrameReceived` event captures frames from all active WebSocket connections, including pre-existing ones
- CDP listeners must be registered **before** triggering navigation to capture the initial response for a page
- HTTP response interception via CDP captures the full response body, enabling programmatic extraction of data from SPA-mediated API calls
- AdsPower provides a CDP endpoint for attaching to anti-detection browser profiles, bypassing Cloudflare and bot detection

## Details

### The Pre-Existing Connection Problem

When automating a browser that is already open and connected to a service (a common scenario with AdsPower anti-detection browsers), Playwright's `page.on('websocket')` event handler is insufficient. This API only fires when a new WebSocket connection is established through the page. If the page already has active WebSocket connections — as bet365 does with its rotating main data and push notification sockets — the handler never fires. This was discovered when initial CDP attachment captured 0 WebSocket events despite active data streaming visible in the browser.

The solution is to use CDP directly via `CDPSession` in Playwright. The `Network.webSocketFrameReceived` event fires for every frame received on any WebSocket connection, regardless of when it was established. This provides complete visibility into all WebSocket traffic:

```javascript
// CDP-level interception (captures all frames)
cdpSession.on('Network.webSocketFrameReceived', handler)

// vs Playwright high-level (misses pre-existing connections)
page.on('websocket', handler)  // Only new connections
```

### HTTP Response Interception

CDP also enables capturing HTTP response bodies that would otherwise be consumed internally by the SPA. When bet365's racing pages navigate to a venue, the SPA makes a `racecoupon` HTTP request internally. CDP's `Network.responseReceived` event combined with `Network.getResponseBody` allows extracting the full response content programmatically. This is critical because direct `fetch()` calls from within the page fail due to SPA navigation state validation.

### Timing and Registration Order

A subtle but important requirement: CDP event listeners must be registered before the navigation or action that triggers the data flow. If a listener is registered after `page.evaluate('window.location.hash = ...')`, the initial HTTP response for that navigation may be missed. This caused early adapter versions to miss the first race's data in each venue until the listener registration was moved before the navigation call.

### AdsPower Integration

AdsPower is an anti-detection browser platform that provides Selenium/Playwright-compatible CDP endpoints for each browser profile. By connecting to AdsPower's local API (`http://local.adspower.net:50325/api/v1/browser/start`), the adapter attaches to a browser session with residential proxy routing and fingerprint randomization already configured. This bypasses Cloudflare's datacenter IP detection and headless browser fingerprinting that blocks direct VPS-based automation. The tradeoff is a dependency on a local or remote AdsPower instance.

## Related Concepts

- [[concepts/bet365-racing-data-protocol]] - The protocol whose data is captured via CDP interception
- [[concepts/spa-navigation-state-api-access]] - Navigation patterns that CDP interception must coordinate with
- [[concepts/bet365-racing-adapter-architecture]] - The adapter that uses CDP as its primary data capture layer
- [[concepts/browser-mediated-websocket-streaming]] - WS streaming built on top of CDP frame interception

## Sources

- [[daily/lcash/2026-04-11.md]] - Discovery that `page.on('websocket')` misses pre-existing connections (Session 13:20); CDP frame interception capturing 73,810-char snapshot (Session 13:20); listener registration timing requirement (Session 15:53); AdsPower CDP attachment workflow (Session 13:20)
