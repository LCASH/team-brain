---
title: "TabTouch Domain Migration and MQTT Architecture"
aliases: [tabtouch-migration, tabtouch-mqtt, tabtouch-architecture, tabtouch-mobi-to-com-au]
tags: [superwin, tabtouch, racing, mqtt, architecture, reverse-engineering]
sources:
  - "daily/lcash/2026-04-18.md"
  - "daily/lcash/2026-04-26.md"
created: 2026-04-18
updated: 2026-04-26
---

# TabTouch Domain Migration and MQTT Architecture

TabTouch retired its `tabtouch.mobi` domain (now returns NXDOMAIN) and migrated to `tabtouch.com.au` with a fundamentally different architecture: server-side rendered (SSR) HTML with embedded JSON (`var model`), Knockout.js client-side rendering, and AWS IoT MQTT over WebSocket for real-time price updates via Cognito anonymous authentication. The entire Webshare proxy infrastructure used for the old domain was unnecessary for the new domain — the new site serves public, no-auth responses.

## Key Points

- `api.tabtouch.mobi` returns NXDOMAIN — the domain is dead, not blocked. All proxy debugging (datacenter IPs, rotating residential, CloudFront blocking) was a complete red herring
- New architecture: SSR HTML with `var model` JSON embedded → Knockout.js renders → AWS IoT MQTT pushes real-time price changes
- Key endpoints: `/api/raceinfo/nextraces` for discovery, `/racing/{date}/{meetingId}/{raceNum}` for full race card with odds in `pool.legs[0].starters` (fields: `fixedWinDiv`, `fixedPlaceDiv`)
- AWS IoT MQTT config: Cognito identity pool `ap-southeast-2:06357b04-f346-4414-b089-...`, push capabilities include `pushdata-pricechange: True` and `pushdata-raceclose: True`
- No proxy needed — new domain serves public data without authentication
- MQTT streaming confirmed production-ready: 721 updates in 8.5 minutes, 36 races with live odds, Cognito token refresh at 50 min

## Details

### The Red Herring Investigation

On 2026-04-18, lcash spent significant debugging time investigating why TabTouch was inaccessible. The initial hypothesis was a proxy/blocking issue: Webshare residential proxies returned 502 Bad Gateway through CloudFront, and the direct VPS IP was also blocked. Testing 10 different proxy IPs across multiple ranges all failed, suggesting CloudFront had blocked the entire Webshare IP range.

This investigation was entirely misguided. The root cause was not blocking — the `api.tabtouch.mobi` domain had been retired. An NXDOMAIN (non-existent domain) response means the domain no longer has DNS records, not that requests are being blocked. The proxy infrastructure, bandwidth limit investigation (Webshare dashboard showed 6MB/1TB used, so the 402 `bandwidthlimit` error was stale/misleading), and CloudFront blocking analysis were all irrelevant.

This is a debugging lesson: when a service becomes unreachable, check whether the domain itself resolves before investigating proxy, firewall, or blocking issues. A 502 through a proxy to a dead domain can look identical to a 502 from blocking.

### New Site Architecture

The new `tabtouch.com.au` site uses a three-layer architecture:

**Layer 1 — Server-Side Rendering:** Race card pages are rendered server-side with embedded JSON in a `var model` JavaScript variable. This JSON contains the full race card including runner names, barriers, jockeys, and current fixed odds (`fixedWinDiv` for win, `fixedPlaceDiv` for place).

**Layer 2 — Client-Side Rendering:** Knockout.js reads the `var model` JSON and renders the interactive UI. This is a lighter framework than bet365's SPA — the initial page load contains all data, unlike bet365 which requires navigation-state-dependent API calls.

**Layer 3 — Real-Time Updates:** AWS IoT MQTT over WebSocket pushes real-time price changes to connected clients. The MQTT connection uses Cognito anonymous authentication (no user credentials required), with the identity pool ID and region embedded in `globals.eventNotificationApiSettings`. The config reveals push capabilities: `pushdata-pricechange: True`, `pushdata-raceclose: True`, with a balance poll interval of 30 seconds.

### Recommended Implementation Path

A two-phase adapter strategy was recommended:

**Phase 1 (immediate):** Build a page-parse adapter that fetches SSR HTML, extracts the `var model` JSON, and parses odds from `pool.legs[0].starters`. This requires no proxy (public data), no browser automation, and reuses the existing `_parse_racecoupon_response`-style parser pattern. Discovery uses `/api/raceinfo/nextraces`.

**Phase 2 (later):** Implement MQTT WebSocket connection for real-time odds streaming. This requires implementing AWS Cognito anonymous auth flow and subscribing to price-change topics. The MQTT path provides sub-second updates vs. polling latency.

### Production Validation

The MQTT streaming path was confirmed production-ready during a SuperWin diagnosis run: 721 price updates received in 8.5 minutes across 36 races with live odds. Cognito token refresh occurs at the 50-minute mark. A startup `TimeoutError`/`CancelledError` was observed during service restart but the `_guarded_task` architecture auto-recovered — confirming the isolation design works as intended.

### Proxy Infrastructure Assessment

The discovery that TabTouch no longer requires proxies raises the question of whether the Webshare subscription is still needed for other adapters. If TabTouch was the primary consumer, the monthly subscription may be unnecessary overhead.

### TabTouch Sports: A Completely Separate Platform (2026-04-26)

On 2026-04-26, lcash discovered that TabTouch's sports betting section is powered by **Kambi** — a B2B white-label sportsbook platform — at `ap.offering-api.kambicdn.com`. This is entirely separate from the racing MQTT platform documented above. TabTouch is effectively two products under one brand: a proprietary racing platform (AWS IoT MQTT + Cognito + Knockout.js) and a Kambi-powered sports platform (REST API + Socket.IO push, zero authentication required).

The Kambi API is dramatically simpler than both the racing platform and other soft book integrations — no auth, no cookies, full player names, stable participant IDs, and 242 player prop markets from a single NBA game endpoint. See [[concepts/tabtouch-kambi-white-label-sports]] for the complete analysis of the sports platform.

## Related Concepts

- [[concepts/tabtouch-kambi-white-label-sports]] - TabTouch's sports betting is powered by Kambi, a completely separate platform from the racing MQTT system documented here
- [[concepts/bet365-racing-adapter-architecture]] - The bet365 racing adapter uses a much more complex browser-mediated architecture; TabTouch's public API is dramatically simpler
- [[concepts/bet365-headless-detection]] - bet365 requires headed Chrome; TabTouch requires no browser at all for Phase 1
- [[connections/anti-scraping-driven-architecture]] - TabTouch has minimal anti-scraping compared to bet365's 6-layer defense stack
- [[concepts/browser-mediated-websocket-streaming]] - MQTT is TabTouch's equivalent of bet365's WebSocket streaming, but with public Cognito auth instead of session-bound topic authorization

## Sources

- [[daily/lcash/2026-04-18.md]] - `api.tabtouch.mobi` NXDOMAIN (dead domain, not blocked); proxy debugging was red herring; new site SSR + Knockout.js + AWS IoT MQTT; endpoints: `/api/raceinfo/nextraces` discovery, `/racing/{date}/{meetingId}/{raceNum}` race card; Cognito anonymous auth `ap-southeast-2:06357b04-...`; no proxy needed; two-phase adapter plan; MQTT confirmed: 721 updates/8.5min, 36 races live, token refresh at 50min (Sessions 13:36, 14:09, 15:54)
- [[daily/lcash/2026-04-26.md]] - TabTouch sports section discovered to be Kambi white-label platform at `ap.offering-api.kambicdn.com`, completely separate from racing MQTT; two independent streaming systems (MQTT + Socket.IO) under one brand (Session 22:10)
