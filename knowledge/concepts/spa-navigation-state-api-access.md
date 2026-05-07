---
title: "SPA Navigation State and API Access"
aliases: [spa-state, navigate-away-trick, spa-cache-busting, bet365-spa]
tags: [spa, scraping, anti-bot, browser-automation, bet365]
sources:
  - "daily/lcash/2026-04-11.md"
  - "daily/lcash/2026-04-21.md"
  - "daily/lcash/2026-05-05.md"
  - "daily/lcash/2026-05-06.md"
  - "daily/lcash/2026-05-07.md"
created: 2026-04-11
updated: 2026-05-07
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

### Click-Through Navigation Requirement (2026-04-21)

On 2026-04-21, lcash discovered that hash navigation (`window.location.hash = "#/AS/B16/..."`) no longer triggers bet365's MLB API calls. The SPA requires full click-through navigation — real Playwright native clicks on the sidebar, game links, and prop tabs — to trigger the `batchmatchbettingcontentapi` responses. Hash navigation changes the URL but does not fire the SPA's internal routing handlers for the MLB section.

This is a significant escalation from the original hash navigation pattern documented above. Previously, hash navigation worked reliably for racing and NBA (with the navigate-away trick for cache busting). The MLB section now requires genuine user-like click sequences: sidebar → MLB → game → tab → expand markets. Three navigation methods were compared:

1. **Hash navigation** (`window.location.hash`) — no longer triggers MLB API calls; SPA intercepts the hash change but doesn't render game content in the DOM
2. **Synthetic JS clicks** (`el.click()` via `page.evaluate`) — behaves differently from native clicks in SPAs; bet365 may distinguish between synthetic and native event dispatch
3. **Playwright native clicks** (`page.click()`) — generates genuine browser events that pass SPA validation; confirmed working with 333 odds from a single game

### CDP Artifact Detection in Headed Mode

The same investigation revealed that bet365 detects CDP (Chrome DevTools Protocol) connection artifacts even when running in headed mode with `--disable-blink-features=AutomationControlled`. The SPA's sidebar loads normally, but game content areas render blank — network-level API responses still flow (the `batchmatchbettingcontentapi` endpoint IS called), but the SPA's JavaScript fails to render the response into the DOM. This is distinct from the headless detection documented in [[concepts/bet365-headless-detection]], which blocks data at the WS level. CDP artifact detection operates at the DOM rendering level — data is available in the network layer but not in the visible page.

The detection likely examines properties that differ between a CDP-attached Chrome and a normal Chrome instance: the `webdriver` property, Chrome DevTools Protocol endpoint availability, or specific runtime behavior differences. Local Playwright's bundled Chromium is blocked entirely, while real Chrome via `--remote-debugging-port` passes the sidebar check but fails the game content render. The game scraper's existing architecture (capturing API responses via CDP interception rather than reading the DOM) means it can function even when the DOM doesn't render, but market expansion clicks require DOM elements to be present.

### WebSocket Session Binding for API Access (2026-05-06)

On 2026-05-06, lcash discovered a deeper layer of session validation beyond navigation state: bet365's `othersportsmatchmarketscontentapi` endpoint requires an **active WebSocket heartbeat** in the same session. External HTTP clients (curl, httpx, curl_cffi) with correct cookies, NST tokens, and headers receive HTTP 200 with 0 bytes. The server validates that a persistent WS connection at `wss://premws-pt3.bet365.com.au/zap/` is maintaining heartbeats for the session before fulfilling HTTP API requests.

The solution is in-browser `fetch()` via CDP `Runtime.evaluate` — running the HTTP request inside the browser's JavaScript context, which inherits the page's active WS connection. This transforms the browser from a scraping target into a **transport proxy**: the script constructs exact URLs and headers, but delegates the HTTP request to the browser's network stack. See [[concepts/bet365-in-browser-cdp-fetch-transport]] for the full pattern.

This WS session binding is distinct from SPA navigation state (which validates page visit history) and from WS topic authorization (which validates render registrations). It is a third, independent validation layer: "is this HTTP session backed by an active WS heartbeat?"

### Hash URL Navigation Requires JavaScript (2026-05-06)

A deployment finding on 2026-05-06 confirmed that SPA hash-based URLs (`#/AC/B16/...`) must be navigated via `window.location.href = url` in JavaScript, not via CDP `Page.navigate`. The CDP navigation command doesn't trigger the SPA's internal hash router — the URL changes in the address bar but the SPA doesn't process the route change. This was discovered when MLB discovery failed silently because `Page.navigate` to a hash URL produced no API response.

## Related Concepts

- [[concepts/bet365-racing-data-protocol]] - The protocol whose HTTP layer depends on proper navigation state
- [[concepts/cdp-browser-data-interception]] - The interception technique used alongside navigation to capture responses
- [[concepts/bet365-racing-adapter-architecture]] - The adapter architecture shaped by these navigation constraints
- [[concepts/browser-mediated-websocket-streaming]] - WS streaming adopted partly because HTTP access is navigation-dependent
- [[concepts/bet365-in-browser-cdp-fetch-transport]] - The in-browser CDP fetch pattern discovered to bypass WS session binding validation
- [[concepts/bet365-getsplashpods-discovery-routing]] - getsplashpods only fires from `#/HO/`; D/F segments must be derived dynamically; pullpodapi capture needed alongside contentapi
- [[concepts/bet365-istrusted-click-anti-bot]] - isTrusted check on click events: `page.evaluate("el.click()")` silently dropped; CDP mouse events required

## Sources

- [[daily/lcash/2026-04-11.md]] - Discovery that racecoupon returns empty without navigation context (Session 13:54); navigate-away trick achieving 14/14 venues (Session 14:45); SPA cache limit of ~15 navigations (Session 15:05); hash navigation requirement (Session 14:25)
- [[daily/lcash/2026-04-21.md]] - Hash navigation no longer triggers MLB API calls; Playwright native clicks required for full click-through flow (sidebar→MLB→game→tab→expand); synthetic JS `el.click()` fails in SPA; CDP artifacts detected even in headed mode — sidebar loads but game content blank; Playwright bundled Chromium fully blocked, real Chrome via CDP partially blocked (Sessions 10:41, 12:36)
- [[daily/lcash/2026-05-06.md]] - WS session binding: `othersportsmatchmarketscontentapi` returns 200/0b from external curl despite correct cookies+NST; active WS heartbeat required; in-browser CDP `Runtime.evaluate` fetch works because page has active WS; hash URL navigation requires `window.location.href` via JS, not CDP `Page.navigate` — SPA router doesn't process CDP-triggered hash changes (Sessions 00:27, 11:20)
- [[daily/lcash/2026-05-05.md]] - **Stealth Chrome probe approach**: Real Chrome binary (`channel="chrome"`) + stealth JS patches + injected real browser cookies (`pstk`, `swt`, `__cf_bm`) + persistent profile directory bypasses Cloudflare fingerprinting without AdsPower. **MLB tab structure confirmed**: I0 = "Bet Builder" (player props via `betbuilderpregamecontentapi/wizard`, 457 PA records per game), I1 = "Match Betting" (win/ML/totals), I2 = "Innings" (inning-by-inning markets). `matchbettingcontentapi/coupon` (main page load) only returns MG+MA records, not PA player props — must click I0 tab to trigger the betbuilder wizard endpoint. Cloudflare silently drops contentapi calls for fingerprinted browsers — no errors, just empty 200 responses (Sessions 18:57, 22:25)
- [[daily/lcash/2026-05-07.md]] - **getsplashpods only fires from `#/HO/`** — sport-specific URLs (`#/AS/B18/AC/`, `#/AS/AC/B18/`, `#/AS/D48/F10/`) never trigger it; multiple URL formats tested and all failed. **isTrusted click detection**: `page.evaluate("el.click()")` produces `isTrusted=false` which bet365 silently drops; CDP `Input.dispatchMouseEvent` produces `isTrusted=true`. **NST direct fetch confirmed dead**: even with fresh 4s-old NST, bet365 returns 200/0bytes from CDP-initiated fetch; navigation-fired coupon captures remain the only path. **D/F segments dynamic**: D19/F19 for regular season, D48/F10 for playoffs — derived from `PD=` field in getsplashpods, not hardcoded. **SPA warmup**: 4s sleep needed after `domcontentloaded` before hash-nav works. **`pullpodapi` capture needed**: getsplashpods routes through `pullpodapi`, not `contentapi` (Sessions 09:51, 11:54, 13:56, 14:32, 16:30)
