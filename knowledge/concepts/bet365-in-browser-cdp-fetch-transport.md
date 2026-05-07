---
title: "bet365 In-Browser CDP Fetch Transport"
aliases: [in-browser-fetch, cdp-runtime-evaluate-fetch, ws-session-binding, othersports-endpoint-constraint]
tags: [bet365, scraping, cdp, browser-automation, architecture, reverse-engineering]
sources:
  - "daily/lcash/2026-05-06.md"
created: 2026-05-06
updated: 2026-05-07
---

# bet365 In-Browser CDP Fetch Transport

On 2026-05-06, lcash discovered that bet365's `othersportsmatchmarketscontentapi` endpoint requires an active WebSocket heartbeat session to serve data — valid cookies and NST tokens alone are insufficient. External HTTP clients (curl, httpx, curl_cffi) receive HTTP 200 with 0 bytes regardless of credentials. The solution is running `fetch()` inside the browser page via CDP `Runtime.evaluate`, which inherits the browser's active WS session context and returns full API responses. This creates a transport architecture where the AdsPower browser serves as a persistent session host, and all data extraction happens via in-browser JavaScript fetch calls driven from Python.

## Key Points

- `othersportsmatchmarketscontentapi` returns **200/0b from external curl** even with correct cookies + NST — the server validates that an active WS heartbeat exists from the same session
- **In-browser `fetch()` via CDP `Runtime.evaluate`** works because the page already has an active WS connection to `wss://premws-pt3.bet365.com.au/zap/`
- This is NOT a cookie/header problem — it's a **session binding** problem: the server ties HTTP endpoint access to WS heartbeat liveness
- The browser maintains a persistent WS connection that sends heartbeat messages; when the WS is alive, HTTP requests from that page context are fulfilled
- **60 sports enumerated** via `leftnavcontentapi/allsportsmenu`; full multi-sport data extraction confirmed: AFL 15 events, NRL 14 events, AFL Women's 12 events
- Responses use bet365's binary protocol format (`~VS~` record separator, `~VT~` field separator) — not JSON
- Most endpoints (`leftnavcontentapi`, `websiteroutingdatacontentapi`) do NOT require NST — cookies alone suffice; only `matchmarketscontentapi` variants validate it

## Details

### The WS Session Binding Discovery

The investigation began with attempts to call `othersportsmatchmarketscontentapi` from external HTTP clients. Every approach returned HTTP 200 with an empty body:

| Approach | Result |
|----------|--------|
| curl with cookies + NST | 200, 0 bytes |
| curl_cffi with Chrome impersonation | 200, 0 bytes |
| httpx with full headers | 200, 0 bytes |
| `page.evaluate('fetch(...)')` inside browser | **Full response data** |

The critical difference is that the in-browser fetch runs in the page's JavaScript context, which has an active WebSocket connection to `wss://premws-pt3.bet365.com.au/zap/`. The WS connection sends periodic heartbeat messages. bet365's backend apparently validates that the requesting session has an active WS heartbeat before serving data on certain HTTP endpoints.

This is distinct from all previously documented defense layers: it's not Cloudflare (network), not headless detection (application), not SPA navigation state (routing), and not WS topic authorization (subscription). It's a new constraint: **HTTP endpoint access gated on WS connection liveness**.

### Architecture: CDP as Transport Layer

The production architecture keeps AdsPower running as a persistent browser session and drives all API calls through CDP:

1. **Browser session**: AdsPower profile stays open with bet365 loaded — maintains cookies, WS heartbeat, and session state
2. **Python driver**: Uses CDP `Runtime.evaluate` to execute `fetch(url, {headers})` inside the page context
3. **Response extraction**: The fetch response is decoded from the CDP call result; responses are in bet365's binary `~VS~`/`~VT~` protocol format, not JSON
4. **Session management**: If the CDP WebSocket to AdsPower drops, reconnect and re-navigate

This eliminates the need for external HTTP clients (curl_cffi, httpx) for data extraction. The browser handles all authentication, session management, and WS heartbeat maintenance. The Python layer only needs to construct fetch URLs and parse responses.

### Multi-Sport Enumeration Results

Using the in-browser fetch approach, all available sports were enumerated:

- **`leftnavcontentapi/allsportsmenu`**: Returns 60 sports with IDs and URL paths (no NST needed, cookies only)
- **Sport-specific endpoints**: Each sport fires either `splashcontentapi/getsplashpods` or `othersportsmatchmarketscontentapi/coupon` depending on the sport
- **Confirmed working**: AFL (15 events, 14 upcoming + 1 in-play), NRL (14 events), AFL Women's (12 events), plus NBA, MLB, Tennis, Cricket, Soccer, Ice Hockey, Boxing, MMA, Golf

### Endpoint NST Requirements

Not all endpoints require the NST token:

| Endpoint | NST Required | Notes |
|----------|-------------|-------|
| `leftnavcontentapi/allsportsmenu` | No | Cookies only |
| `websiteroutingdatacontentapi/routingdata` | No | 16KB manifest, 106 endpoints |
| `pullpodapi/gethomepagepods` | No | Needs `boot: 1` header |
| `matchmarketscontentapi` | Yes | Standard match content |
| `othersportsmatchmarketscontentapi` | Yes + active WS | Requires WS session binding |

## Related Concepts

- [[concepts/bet365-xcft-token-hmac-forgery]] - The token formula that could enable standalone WS clients; in-browser fetch bypasses the need for token forgery entirely since the browser manages auth
- [[concepts/spa-navigation-state-api-access]] - SPA cache must be reset between sports via `/HO/` navigation; the in-browser fetch transport adds a new constraint layer beyond navigation state
- [[connections/anti-scraping-driven-architecture]] - WS session binding is a seventh defense layer not previously documented
- [[connections/ws-session-binding-defense-layer]] - The full analysis of how WS session binding interacts with other defense layers
- [[concepts/cdp-browser-data-interception]] - CDP `Runtime.evaluate` is the same mechanism used here, but applied to `fetch()` calls rather than response interception
- [[concepts/bet365-multi-sport-dynamic-enumeration]] - The enumeration system built on top of this transport layer

## Sources

- [[daily/lcash/2026-05-06.md]] - `othersportsmatchmarketscontentapi` returns 200/0b from external curl; in-browser CDP fetch works because page has active WS; 60 sports enumerated; binary protocol decoded (~VS~/~VT~); SPA cache reset via /HO/ between sports; NST not required for most endpoints; architecture: AdsPower as persistent session host, CDP Runtime.evaluate as transport (Sessions 00:27, 01:36)
