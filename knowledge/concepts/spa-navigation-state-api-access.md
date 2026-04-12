---
title: "SPA Navigation State and API Access"
aliases: [spa-state, navigate-away-trick, spa-cache-busting, bet365-spa]
tags: [spa, scraping, anti-bot, browser-automation, bet365]
sources:
  - "daily/lcash/2026-04-11.md"
created: 2026-04-11
updated: 2026-04-12
---

# SPA Navigation State and API Access

bet365's single-page application tracks navigation state server-side, causing API endpoints to return empty responses unless the browser has followed the expected navigation flow. This is a form of implicit anti-scraping that requires specific workarounds: hash navigation to preserve SPA state, and a "navigate-away" pattern to bust the internal cache.

## Key Points

- bet365's `racecoupon` endpoint returns HTTP 200 with 0 bytes unless the browser has navigated through the Racing tab first — even with correct headers, cookies, and URL
- `page.goto()` destroys SPA state; `window.location.hash = "..."` preserves it — all navigation must use hash changes
- Direct `page.evaluate(fetch(url))` also fails — the server validates navigation context, not just request parameters
- After ~15 hash navigations, the SPA caches responses internally and stops making HTTP requests — solved by periodic `page.reload()` every ~12 races
- The "navigate-away" trick (hashing to `#/AS/B1/` soccer page before each venue) forces the SPA to make fresh `racecoupon` HTTP requests

## Details

### The Navigation State Problem

bet365's SPA maintains server-side session state that tracks which pages the user has visited. The `racecoupon` API endpoint — which returns full race card data including runners, odds, jockeys, and form — validates this state before returning data. A request that lacks proper navigation context receives an HTTP 200 response with an empty body. This behavior persists even when the request exactly replicates a browser's headers, cookies, URL parameters, and referrer. The validation is not based on individual request properties but on the cumulative navigation history of the session.

This was discovered empirically by lcash during bet365 adapter development. The first attempts to fetch racecoupon data via direct HTTP calls (both from Python and via in-page `fetch()`) returned empty despite correct credentials. Only when navigation was performed by clicking through the Racing tab in the actual SPA did the endpoint return data (12,741 chars for a full race card). This ruled out header/cookie issues and pointed to server-side session tracking.

### Hash Navigation vs page.goto()

Playwright's `page.goto()` triggers a full page load that destroys the SPA's internal state, including authentication tokens and navigation context. The correct approach is hash navigation via `window.location.hash = "#/AS/B2488/..."`, which the SPA intercepts and handles as an internal route change without a page reload. This preserves all session state while changing the displayed content.

### The Navigate-Away Cache Busting Pattern

After navigating to several racing venues (approximately 15 hash changes), the SPA begins serving cached data instead of making new HTTP requests. This means CDP response interception captures nothing for subsequent venues. The solution is a two-part pattern:

1. **Between meetings**: Navigate to a non-racing page (`#/AS/B1/` — soccer) before each racing venue. This forces the SPA to treat the next racing navigation as "fresh," triggering a new HTTP request.
2. **Periodic reloads**: Every ~12 races during batch operations, call `page.reload()` followed by re-navigating to the Racing tab to reset the SPA's internal cache entirely.

The navigate-away pattern reduced per-meeting fetch failures from ~50% (without) to 0% (with), while the periodic reload handles the longer-term cache accumulation. Combined, the approach achieved 14/14 Australian horse racing meetings with 100% odds coverage in 38 seconds.

### PD Suffix Variants

Race identifiers use PD (page descriptor) values with context-dependent suffixes: `#K^6#` for meeting-level discovery, `#G9#H0#L9#X^T#` for race-level browser navigation. Using the wrong suffix variant produces empty responses even with correct navigation state.

## Related Concepts

- [[concepts/bet365-racing-data-protocol]] - The protocol whose HTTP layer depends on proper navigation state
- [[concepts/cdp-browser-data-interception]] - The interception technique used alongside navigation to capture responses
- [[concepts/bet365-racing-adapter-architecture]] - The adapter architecture shaped by these navigation constraints
- [[concepts/browser-mediated-websocket-streaming]] - WS streaming adopted partly because HTTP access is navigation-dependent

## Sources

- [[daily/lcash/2026-04-11.md]] - Discovery that racecoupon returns empty without navigation context (Session 13:54); navigate-away trick achieving 14/14 venues (Session 14:45); SPA cache limit of ~15 navigations (Session 15:05); hash navigation requirement (Session 14:25)
