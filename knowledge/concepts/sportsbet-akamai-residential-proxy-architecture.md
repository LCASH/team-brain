---
title: "Sportsbet Akamai Residential Proxy Architecture"
aliases: [sportsbet-akamai, akamai-two-door, residential-proxy-scraping, sportsbet-push-client, kasada-cookie-portability]
tags: [superwin, sportsbet, scraping, akamai, proxy, architecture, anti-bot]
sources:
  - "daily/lcash/2026-05-27.md"
created: 2026-05-27
updated: 2026-05-27
---

# Sportsbet Akamai Residential Proxy Architecture

On 2026-05-27, lcash reverse-engineered and deployed a full Sportsbet racing odds pipeline, overcoming Akamai's "two-door" anti-bot architecture. Door 1 (IP/ASN gate) blocks datacenter IPs at the TCP/connection layer before Door 2 (cookies/WAF/Kasada) ever runs. Cookies minted on residential IPs are useless when sent from datacenter IPs because the 397-byte deny fires at the connection layer. The production architecture uses a single Playwright cookie minter (rotating exit IP per refresh) plus a 13-20 way curl_cffi PushClient fan-out with per-IP sticky binding. Each PushClient long-polls Sportsbet's `/push` endpoint for real-time PRICE frames, posting immediately to the VPS ingest endpoint on every response for sub-200ms latency.

## Key Points

- **Akamai "two-door" architecture**: Door 1 (IP/ASN gate) blocks before Door 2 (cookies/WAF) even runs — 397-byte deny is served at the connection layer, making cookie/header tricks useless from datacenter IPs
- **Cookies are TLS-portable but NOT IP-portable**: Playwright-minted cookies work in curl_cffi (chrome131 impersonation) on any residential IP, but fail on ANY datacenter IP regardless of headers
- **Cookies ARE portable across residential IPs** in the same pool — mint on IP A, use on IP B = 200 + valid body
- **Behavioural denylist, not ASN-based**: Mac on Superloop (AS38195, legit AU consumer ISP) got banned after sustained testing — Eve's single IP burned after 80,000 polls/hr in 6 hours
- **One PushClient per race**: Sportsbet `/push` only returns PRICE frames for the focus event; N parallel connections required for N races
- **Per-IP rate cap ~360 polls/hr with 1.5-3s jitter** — Eve's ~80,000/hr that burned in 6 hours is the cautionary benchmark
- **Sticky proxy binding**: `proxy = pool[race_id % len(pool)]` keeps each race on one IP to maintain session continuity with `__cf_bm` cookie warmup
- **Sub-200ms target**: bookie price change → POST to VPS ingest → SSE to frontend ≤ 200ms (50-150ms bookie response + 10ms Tailscale + 5ms SSE)

## Details

### The Two-Door Defense

Akamai's Sportsbet protection operates at two independent layers:

**Door 1 — IP/ASN Gate (TCP layer):** Before the HTTP request is even processed, Akamai checks the source IP's reputation and ASN classification. Datacenter IP ranges (DigitalOcean, AWS, Hetzner, Webshare datacenter pools) receive a 397-byte "Access Denied" HTML page. This check operates below the HTTP layer — no cookie, User-Agent, or TLS impersonation can bypass it because the deny fires before request headers are inspected.

**Door 2 — Kasada Bot Management (Application layer):** For IPs that pass Door 1, Akamai's Kasada fingerprinting validates the client. Playwright and other automation tools are fingerprinted even through residential proxies; curl_cffi with `impersonate="chrome131"` passes cleanly. Cookies minted by legitimate browser sessions on residential IPs carry Kasada validation tokens that are accepted by curl_cffi.

The critical insight is that cookies minted on residential IPs carry Door 2 authentication but cannot bridge Door 1. Sending perfectly valid Kasada-signed cookies from a datacenter IP still triggers the 397-byte deny at Door 1 before Door 2 ever evaluates the cookies.

### IP Reputation is Behavioural

Unlike bet365's Cloudflare (which blocks by ASN — all datacenter IPs are rejected regardless of behavior), Akamai's denylist is behavioural. Eve (DigitalOcean VPS) was initially viable for racing polls but got banned after running unrestricted for 6 hours at ~80,000 polls/hr. More surprisingly, lcash's Mac on Superloop (AS38195 — a legitimate Australian consumer ISP) also got banned after a day of development testing. This means:

1. Any IP can be burned by excessive request volume, including residential
2. Rate limiting must be deployed from request 1, not "deploy then tune"
3. Development probing consumes IP reputation — don't test from IPs you need for production

### The PushClient Architecture

Sportsbet's `/push` endpoint is a long-polling mechanism that returns PRICE frames for a single focused race event per connection. To cover N active races, N parallel PushClient connections are maintained, each bound to a specific residential proxy IP via sticky assignment (`race_id % len(pool)`).

The architecture has three components:

**Cookie Minter (Playwright):** A single Playwright instance periodically (every 25 minutes, before the `__cf_bm` cookie's 30-minute TTL expires) navigates to Sportsbet via a residential proxy, passes Kasada fingerprinting, and exports fresh cookies. These cookies are distributed to all PushClients.

**PushClient Fan-Out (curl_cffi):** 13-20 concurrent curl_cffi connections, each impersonating Chrome 131, each bound to a specific Webshare static residential IP. Each connection long-polls `/push` for its assigned race and immediately POSTs received PRICE frames to the VPS ingest endpoint. No batching — latency target demands immediate forwarding.

**Discovery (REST):** `racing-schedule` HTML scrape (regex-based) for the full day card (630 races), supplemented by `NextEvents` API for active race filtering and race ID assignment.

### Validated Production Metrics

End-to-end pipeline validation on deployment day:
- 23 PushClients active, 926 PRICE frames received, 48 POSTs to VPS (98% success rate)
- Zero 403 errors across all residential proxy IPs
- MAX_CONCURRENT_RACES=50 cap with 25-min cookie refresh cycle
- ~410 MB RAM for 50 concurrent races vs ~1.8 GB for equivalent Playwright pool
- Cold-tier HTML scrape: 232 AU/NZ races parsed in 38 seconds across 16 proxy IPs

### Two-Tier Coverage Architecture

The adapter operates in two tiers:

| Tier | Method | Coverage | Cadence | Purpose |
|------|--------|----------|---------|---------|
| **Hot** | `/push` long-poll PushClients | Top 30 races by proximity | Real-time (~100ms) | Live odds streaming for imminent races |
| **Cold** | HTML scrape via curl_cffi | Full AU/NZ day card (232 races) | Every 5 min | Baseline odds for non-imminent races |

Hot tier covers races approaching jump time with sub-second freshness. Cold tier ensures the full day card has coverage even for races hours away, using regex-based odds extraction from SSR HTML responses.

### Proxy Pool Management

Webshare static residential IPs were tested individually — some IP ranges (92.71.71.x) are geo-blocked by Sportsbet for racing while others (213.201.250.x) work. All production IPs are on Tier-1 ISP ASNs (Level 3/Lumen AS3356) which pass Akamai's Door 1 cleanly. Three bad IPs were identified for replacement.

Per-IP rate cap of ~1,500 requests/hr (360 polls/hr × ~4 endpoints) was chosen based on the inverse of Eve's burn rate. With 13 active IPs, total throughput is ~19,500 requests/hr — sufficient for 50 concurrent races.

## Related Concepts

- [[concepts/betr-sticky-proxy-cloudflare-sessions]] - Betr's Cloudflare is session-aware (cookie warmup sustains 5 req/sec); Sportsbet's Akamai is behavioural (IP reputation degrades over time regardless of cookies)
- [[connections/anti-scraping-driven-architecture]] - bet365's 8-layer defense stack; Sportsbet's 2-door Akamai is structurally different (IP gate + Kasada vs Cloudflare + SPA state + WS auth)
- [[concepts/betr-no-websocket-xhr-only-architecture]] - Betr confirmed zero WebSocket; Sportsbet has a `/push` long-poll mechanism that is effectively real-time without being a WebSocket
- [[concepts/sportsbet-timezone-canonical-id-bug]] - The timezone bug that prevented Sportsbet from merging with Betfair; fixed before this adapter was deployed
- [[connections/websocket-first-bookie-onboarding-principle]] - The WS-first recon rule; Sportsbet's `/push` long-poll is a WS-equivalent that was prioritized for the hot tier

## Sources

- [[daily/lcash/2026-05-27.md]] - Akamai two-door architecture confirmed empirically: residential-mint→datacenter-push definitively doesn't work; behavioural denylist burned Mac Superloop IP and Eve after sustained testing; 20 Webshare static residential IPs acquired, cookies portable across pool; sticky proxy binding + per-IP rate cap deployed (Session 08:59). curl_cffi over Playwright for Kasada bypass; VPS-active adapter over Eve relay; 13 working IPs after geo-block filtering; proxy URL normalization bug fixed (Session 09:47). Full pipeline validated: 23 PushClients, 926 PRICE frames, 48 POSTs at 98% success, zero 403s (Session 08:27). Two-tier architecture: hot /push for top 30 + cold HTML scrape every 5 min for full AU/NZ card; coverage jumped 6→232 AU/NZ races (Session 11:58)

```
