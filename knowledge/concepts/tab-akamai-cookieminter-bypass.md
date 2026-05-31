---
title: "TAB Akamai CookieMinter Bypass"
aliases: [tab-cookieminter, akamai-cookie-harvest, tab-tier25, tab-curl-cffi-cookies, aka-a2-cookie]
tags: [superwin, tab, scraping, akamai, architecture, anti-bot, curl-cffi]
sources:
  - "daily/lcash/2026-05-31.md"
created: 2026-05-31
updated: 2026-05-31
---

# TAB Akamai CookieMinter Bypass

On 2026-05-31, lcash prototyped and deployed a "Tier 2.5" CookieMinter bypass for TAB's Akamai-protected API. The TAB competition endpoint (`api.beta.tab.com.au`) returns HTTP 403 to plain `curl_cffi` with chrome131 TLS fingerprint because Akamai requires cookies set by JavaScript execution on the SPA — TLS fingerprint alone is insufficient. The fix harvests cookies from the already-loaded Playwright page (specifically `AKA_A2=A`), then uses `curl_cffi` with chrome131 impersonation plus those cookies to call the API directly. This bypasses the 30-second Tier 3 interceptor wait entirely when it works, falling back to existing tiers on failure.

## Key Points

- `api.beta.tab.com.au` returns **403 to curl_cffi with chrome131** despite `www.tab.com.au` returning 200 — the API requires Akamai cookies set by SPA JavaScript, not just TLS fingerprint
- **Only 1 cookie needed: `AKA_A2=A`** — Playwright page already has it after navigation; harvesting is trivial
- **Tier 2.5** runs after existing Playwright navigation, harvests cookies from the page context, calls API with curl_cffi → HTTP 200, 30 races returned on first test
- Bypasses the **30-second interceptor wait** that Tier 3 (page.evaluate) requires — discovery is much faster when CookieMinter fires
- Falls back to existing tiers (Tier 3 page.evaluate, Tier 4 REST) on failure — no regression risk
- Long-term fix is a full Sportsbet-style CookieMinter (Playwright harvests cookies periodically → curl_cffi uses them for all API calls) — estimated 4-6 hour build, deferred

## Details

### The Two-Endpoint Asymmetry

TAB's Akamai protection operates differently on its main site versus its API:

| Endpoint | curl_cffi chrome131 | Result |
|----------|-------------------|--------|
| `www.tab.com.au` | HTTP 200 | Full HTML page — Akamai accepts TLS fingerprint alone |
| `api.beta.tab.com.au` | HTTP 403 | Blocked — requires JS-set cookies from SPA execution |

This asymmetry exists because `www.tab.com.au` serves static HTML that Akamai's bot management evaluates client-side (setting cookies like `AKA_A2` via JavaScript challenge-response). The API endpoint then validates those cookies on every request. Without executing the SPA's JavaScript to pass the Akamai challenge, no cookies are set, and the API rejects the request regardless of TLS fingerprint quality.

This is architecturally similar to the Sportsbet Akamai "two-door" defense documented in [[concepts/sportsbet-akamai-residential-proxy-architecture]], but simpler: Sportsbet's Akamai also validates IP reputation (Door 1), while TAB's API appears to gate only on cookie presence (cookies from any IP work).

### The CookieMinter Tier 2.5 Approach

The existing TAB discovery flow uses Playwright to navigate to `www.tab.com.au`, which executes Akamai's JavaScript challenges and sets the required cookies. Previously, Tier 3 (page.evaluate with fetch()) was the primary data extraction path — it works because the in-page fetch inherits the cookies, but it requires a 30-second wait for the Akamai interceptor to settle.

Tier 2.5 exploits the fact that the cookies are already available after navigation:

1. Playwright navigates to `www.tab.com.au` (existing step)
2. **Harvest cookies** from the page context — specifically `AKA_A2=A`
3. **Call API via curl_cffi** with chrome131 TLS fingerprint + harvested cookies → HTTP 200
4. Parse response (30 races returned on first test)

This is faster than Tier 3 because curl_cffi makes a direct HTTP request without the 30-second interceptor settling time. The cookie harvest is trivial — a single `page.context.cookies()` call.

### Tier 2.5 in the Discovery Stack

The TAB adapter's discovery uses a tiered fallback architecture:

| Tier | Method | Speed | Reliability |
|------|--------|-------|-------------|
| 2.5 | Cookie-mint + curl_cffi | Fast (~2s) | Depends on cookies being fresh |
| 3 | page.evaluate(fetch) | Slow (~30s wait) | Reliable when page is healthy |
| 4 | REST direct | Fast | Only works if Akamai cookies cached |

Tier 2.5 runs after navigation, before the 30-second interceptor wait. If it succeeds, the entire interceptor wait is skipped. If it fails (stale cookies, Akamai challenge changed), the adapter falls through to Tier 3 and 4 as before. This ensures no regression — the worst case is the same as before Tier 2.5 was added.

### Relationship to Sportsbet CookieMinter

The Sportsbet Akamai integration (see [[concepts/sportsbet-akamai-residential-proxy-architecture]]) uses a more sophisticated CookieMinter pattern: a dedicated Playwright instance periodically refreshes cookies (every 25 minutes before `__cf_bm` cookie TTL expires), and a pool of curl_cffi PushClients use those cookies for all API calls. The TAB Tier 2.5 is a lightweight version of the same concept — harvesting cookies from the existing navigation rather than maintaining a separate minting process.

A full Sportsbet-style CookieMinter for TAB (estimated 4-6 hours to build) would decouple cookie harvesting from the discovery flow entirely, enabling curl_cffi-only API access without Playwright in the critical path. This is deferred because Tier 2.5 is sufficient: TAB's adapter already navigates with Playwright for WS subscription setup, so harvesting cookies from that navigation adds negligible overhead.

### curl_cffi TLS Fingerprint

curl_cffi's `impersonate="chrome131"` provides TLS fingerprint matching (JA3/JA4 hash, HTTP/2 settings, cipher suites) that Akamai's bot management accepts. This is the same library used for Sportsbet (Kasada bypass), Betr (Cloudflare bypass), and Twitter scraping. The key insight is that `curl_cffi` passes the TLS layer of Akamai's validation — it is specifically the cookie layer that requires JavaScript execution, which Playwright provides.

## Related Concepts

- [[concepts/tab-cold-start-akamai-discovery-thrashing]] - The discovery thrashing that motivated this fix; CookieMinter reduces Akamai pressure by succeeding faster and making fewer retry requests
- [[concepts/sportsbet-akamai-residential-proxy-architecture]] - Sportsbet's full CookieMinter architecture (dedicated Playwright minter + PushClient pool); the TAB Tier 2.5 is a lightweight variant of the same pattern
- [[concepts/betr-sticky-proxy-cloudflare-sessions]] - Betr's Cloudflare cookie warmup (`__cf_bm`) is conceptually similar: both require JS-set cookies for API access, both use curl_cffi for the actual requests
- [[concepts/tab-scraper-threshold-markets]] - TAB's REST API that the CookieMinter accesses; same `/sports/Basketball/competitions/NBA?jurisdiction=NSW` endpoint
- [[concepts/tab-global-ws-rotation-pattern]] - TAB's WS pipeline that CookieMinter-enabled discovery bootstraps; faster discovery means faster WS subscription setup after rotation kills

## Sources

- [[daily/lcash/2026-05-31.md]] - curl_cffi probe: www.tab.com.au returns 200 but api.beta.tab.com.au returns 403 — Akamai requires JS-set cookies; CookieMinter prototype: Playwright harvests AKA_A2=A cookie → curl_cffi with chrome131 + cookie → HTTP 200, 30 races; shipped as Tier 2.5 — runs after nav, bypasses 30s interceptor wait; full Sportsbet-style CookieMinter deferred (~4-6h); Webshare proxy pool for TabTouch dead (8/8 HTTP 000) (Sessions 20:01, 21:05)
