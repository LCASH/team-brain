---
title: "Betr Sticky Proxy Cloudflare Session Architecture"
aliases: [sticky-proxy, cloudflare-session-aware, betr-proxy-architecture, cf-bm-cookie-continuity, proxy-session-persistence]
tags: [superwin, betr, scraping, cloudflare, proxy, architecture]
sources:
  - "daily/lcash/2026-05-21.md"
created: 2026-05-21
updated: 2026-05-21
---

# Betr Sticky Proxy Cloudflare Session Architecture

Cloudflare's bot detection for betr (bluebet) is **session-aware, not just rate-aware**. Stateless round-robin proxy rotation at 10 req/sec from a single IP triggers a ban after ~90 requests. The same IP with a persistent cookie jar (`__cf_bm` warmup) sustains 5 req/sec indefinitely (1,500/1,500 clean). The breakthrough architecture assigns a deterministic proxy per race (hash of eventId → fixed proxy), with each proxy maintaining its own `aiohttp` session and cookie jar. This provides ~460 req/sec headroom across 93 WebShare IPs, far exceeding the residential relay alternative (10 req/sec ceiling, single point of failure).

## Key Points

- **Cloudflare is session-aware**: stateless 10/sec from one IP → banned after 90 reqs; same IP with persistent cookies at 5/sec → 1,500/1,500 clean — `__cf_bm` cookie warmup makes proxy traffic look like a real user
- **Residential IP is NOT unlimited**: Dell's residential IP got 1015'd after cumulative load from Mac tests + smoke test — the "residential = free pass" assumption was wrong
- **Sticky proxy per race**: deterministic `hash(eventId) → proxy_index` assigns each race to a fixed proxy with its own aiohttp session + cookie jar
- **Auto-refresh sessions every 25 min** (before `__cf_bm` 30-min TTL); 429 → quarantine proxy 2 min + auto-reassign to next proxy
- **460 req/sec headroom** across 93 WebShare IPs vs 10 req/sec residential ceiling — 46x more throughput, spread across many IPs, no single point of failure
- **Betr ingest endpoint + passive adapter were built then immediately deprecated** — sticky proxy made VPS-side scraping viable, eliminating need for Dell relay

## Details

### The Session-Aware Detection Mechanism

The initial assumption was that Cloudflare rate-limits by IP and request volume. Testing proved this wrong: the detection is session-aware. A fresh connection to betr's API without cookies is treated as a potential bot. Each request from a cookieless connection counts toward a per-IP bot score. After ~90 requests (at any rate), the IP is temporarily banned with a 1015 error.

With a persistent cookie jar, the first request establishes a `__cf_bm` cookie — Cloudflare's bot management session token. Subsequent requests from the same IP carrying this cookie are treated as a continuation of a legitimate session, dramatically increasing the per-IP tolerance. The same IP that was banned after 90 stateless requests sustained 1,500 requests at 5/sec with cookie continuity.

This means **each proxy IP needs its own cookie warmup before production traffic flows**. The sticky proxy architecture handles this naturally: each proxy's dedicated aiohttp session accumulates its `__cf_bm` cookie on the first request and maintains it across the session's lifetime.

### The Sticky Proxy Architecture

Rather than round-robin rotation (which breaks session continuity on every request), the sticky proxy assigns each race to a specific proxy deterministically:

1. `proxy_index = hash(eventId) % len(proxies)` — same race always routes to same proxy
2. Each proxy has its own `aiohttp.ClientSession` with a persistent `CookieJar`
3. Sessions are refreshed every 25 minutes (5 minutes before `__cf_bm`'s 30-minute TTL)
4. On 429 response: quarantine the proxy for 2 minutes, auto-reassign the race to the next available proxy
5. At 5 req/sec per proxy × 93 proxies = ~460 req/sec theoretical maximum

This design achieves two things: (1) cookie continuity makes each proxy look like a persistent user session, and (2) deterministic mapping prevents multiple races from colliding on the same proxy during rate-limit recovery.

### Why Sticky Proxy Over Dell Relay

Two architectures were evaluated:

| Dimension | Dell Relay (Option A) | Sticky Proxy (Option B) |
|-----------|----------------------|------------------------|
| Throughput | 10 req/sec (single residential IP) | ~460 req/sec (93 proxy IPs) |
| Resilience | Single point of failure (Dell) | Distributed across 93 IPs |
| Latency | +100ms per hop (Dell → VPS) | +200-400ms (proxy overhead) |
| Infra cost | Dell must be running | WebShare subscription |
| Complexity | Ingest endpoint + adapter needed | Proxy pool management |

Option B was chosen because the throughput advantage (46x) and resilience (93 IPs vs 1) outweigh the slightly higher per-request latency. The Dell relay architecture (identical to `bet365_stream.py`) was built and immediately deprecated once the sticky proxy proved viable.

### Residential IP Limitations

A critical finding: even Dell's residential IP was 1015'd after cumulative load from development testing. The "residential IP = unlimited access" assumption that held for betr's initial 6,000-request Mac test broke down under sustained multi-source load. Cloudflare tracks cumulative request patterns per IP over time, not just instantaneous rate — a residential IP used for heavy automated traffic eventually triggers the same detection as a datacenter IP.

## Related Concepts

- [[concepts/betr-no-websocket-xhr-only-architecture]] - The transport investigation confirming betr is XHR-only; sticky proxy enables VPS-side XHR polling without the Dell relay originally planned
- [[concepts/betr-bluebet-api-integration]] - The betr API integration that the sticky proxy serves; no anti-bot protection beyond Cloudflare's `__cf_bm` session management
- [[connections/anti-scraping-driven-architecture]] - Cloudflare's session-aware detection is the same platform as bet365's IP-reputation blocking, but with different behavior: bet365 blocks datacenter IPs outright, betr tolerates them with proper session continuity
- [[concepts/bet365-racing-adapter-architecture]] - The Dell → VPS relay pattern that was considered and rejected for betr in favor of sticky proxy

## Sources

- [[daily/lcash/2026-05-21.md]] - Single WebShare proxy at 10 req/sec banned after ~90 requests; residential 6000/6000 at 10/sec; persistent cookie jar (`__cf_bm` warmup) sustained 1500/1500 at 5/sec; sticky-proxy-session chosen over Dell relay; 460 req/sec headroom across 93 IPs; betr ingest endpoint built and immediately deprecated; Dell residential IP also 1015'd after cumulative load (Session 09:43)
