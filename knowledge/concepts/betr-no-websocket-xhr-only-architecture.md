---
title: "Betr No-WebSocket XHR-Only Architecture"
aliases: [betr-xhr-polling, betr-no-websocket, betr-react-query-polling, betr-14s-interval, betr-residential-relay]
tags: [superwin, betr, scraping, architecture, reverse-engineering, polling, racing]
sources:
  - "daily/lcash/2026-05-19.md"
created: 2026-05-19
updated: 2026-05-19
---

# Betr No-WebSocket XHR-Only Architecture

On 2026-05-19, lcash performed exhaustive browser transport analysis on betr (bluebet) confirming that betr uses **zero WebSocket, SignalR, SSE, or Service Worker connections** for odds delivery. The web UI polls via XHR (`/Race?eventId=...`) at ~13-15 second intervals using React Query's `refetchInterval: 13000`. SignalR exists in betr's JavaScript bundle but only initializes for user-account events (winner/settled notifications), not price streaming. This means the SuperWin scanner's 1Hz polling is **14x faster than betr's own web UI**, creating an asymmetric detection edge on price movements.

## Key Points

- **Zero WebSocket/SignalR/SSE for odds delivery** — confirmed across 3 separate CDP capture sessions (logged-out, logged-in, betslip interaction) spanning 17+ minutes on live race pages
- **Pure XHR polling at ~13-15s intervals** via React Query `refetchInterval: 13000` on `/Race?eventId=...` endpoint — this IS betr's production architecture, not a degraded fallback
- **Our 1Hz adapter is 14x faster** — catches price movements (Pacific Pixie 29→34, Finnish Girl 12→11 within 36 seconds) that betr's own UI wouldn't show for another 10+ seconds
- **SignalR in bundle is user-account only** — initializes for winner/settled push notifications, NOT price updates; a red herring that consumed investigation time
- **Cloudflare rate-limits by IP reputation, not session/cookie** — VPS datacenter IPs get 1015 errors at 1Hz; residential IPs sustain 10 req/sec with zero throttling (6,000/6,000 success rate from local Mac)
- **Dell mini PC residential relay is the correct architecture** — same pattern as `bet365_stream.py`; Dell polls at 10Hz from residential AU IP, POSTs to VPS `/api/v1/ingest/betr`

## Details

### The Transport Investigation

The investigation was triggered by a user conviction that betr must use WebSocket for live odds. Three independent verification methods were used:

**Method 1 — CDP Network monitoring via AdsPower (profile k19yb91n):** 17 minutes of monitoring across multiple race pages with Network.webSocketCreated, Network.webSocketFrameReceived, and Network.webSocketClosed event listeners. Result: zero WebSocket connections to any betr domain.

**Method 2 — JavaScript constructor hooking:** Monkey-patched `window.WebSocket` constructor and `window.fetch` inside the live betr page to log all connection attempts. Result: zero WebSocket constructor calls; only XHR/fetch calls observed at ~13-15 second intervals.

**Method 3 — Bundle analysis:** Searched betr's JavaScript bundle for SignalR, WebSocket, and EventSource references. SignalR IS present but only initializes for user-account push notifications (bet settlement, winner announcements) — not for odds streaming.

### Auxiliary Endpoints Discovered

Beyond the primary `/Race?eventId=...` polling endpoint, several auxiliary endpoints were identified during the investigation:

| Endpoint | Purpose |
|----------|---------|
| `/Next5Races` | Discovery: upcoming races across all venues |
| `/MarketMovers` | Price movement highlights |
| `/Fav4` | Favourite runner data |
| `/flucs` | **Historical price fluctuation per runner** — useful for steamer detection/backtesting |
| `/StatwarsMasterEvents` | Statistical analysis data |

The `/flucs` endpoint is particularly valuable: it returns historical price moves per runner, enabling detection of "steamers" (runners whose odds are shortening rapidly, often indicating inside information or sharp action).

### Cloudflare IP-Reputation Rate Limiting

The rate-limiting investigation revealed a critical architectural constraint:

| Approach | Success Rate | Median Latency | Notes |
|----------|-------------|----------------|-------|
| VPS direct (1Hz) | Blocked (1015) | N/A | Cloudflare 60s ban from datacenter IP |
| VPS via Webshare proxies | ~93% | ~400ms | 7/100 IPs from `161.123.215.*` blocked |
| Local Mac residential (1Hz) | 100% | 57ms | Zero throttling over 6,000 requests |
| Local Mac residential (10Hz) | 100% | ~80ms | Sustained 10 req/sec for 10 minutes |

Cloudflare's rate limiting is **IP-reputation based, not cookie/session based** — valid browser cookies from an authenticated session don't help once the IP is flagged as datacenter. This is the same ASN-level blocking pattern documented for bet365 in [[connections/anti-scraping-driven-architecture]], confirming it's a Cloudflare platform behavior rather than a per-site configuration.

### The Residential Relay Architecture

Given the IP-reputation blocking, the correct architecture is a residential relay via the Dell mini PC (at `100.67.233.95` via Tailscale):

1. **Dell mini PC** (residential AU IP) polls betr at 1-10Hz
2. Batches odds updates and POSTs to **VPS** at `/api/v1/ingest/betr`
3. VPS ingests into catalogue → edge scanner → dashboard

This eliminates proxy overhead (200-400ms/request), proxy quarantine bookkeeping, and 429 risk entirely. The pattern is identical to the bet365 racing stream relay (`bet365_stream.py`) documented in [[concepts/bet365-racing-adapter-architecture]].

### Proxy Operational Findings

While proxies were tested as a fallback, several operational issues were discovered:

- **WebShare credentials were stale** — proxy pool had rotated but same user:pass; TabTouch had been silently running in DIRECT mode, masking the failure
- **CRLF line endings** from WebShare's downloaded proxy list broke shell `read` — trailing `\r` corrupted every URL
- **7/100 proxies** from `161.123.215.*` subnet were Cloudflare-blocked
- **Proxy timeout reduced** from 10s→4s with 60s quarantine for dead proxies — eliminated 18s stalls that were the real cause of betr polling slowness (not protocol)

Post-fix proxy metrics: median hot fetch 0.21s, max dropped from 18.26s→6.92s, slow cycles from 10%→4.5%.

### betr Frontend Architecture

betr's web UI uses Next.js with SSR/ISR (Server-Side Rendering / Incremental Static Regeneration) and React Query's SWR pattern for client-side data fetching. The `refetchInterval: 13000` setting means the browser re-fetches odds every 13 seconds. This is actually **slower** than traditional polling-based sportsbook UIs — most competitors poll every 5-10 seconds.

The implication for edge detection: our adapter at 1-2 second intervals has a consistent 11-13 second head start on any price movement compared to what a betr customer sees in their browser. At 10Hz from a residential relay, this extends to detecting sub-second price shifts that the betr UI won't show for 13+ seconds.

## Related Concepts

- [[concepts/betr-bluebet-api-integration]] - The betr API integration for value-betting sports props; this article covers the racing-specific transport investigation confirming no WebSocket path exists
- [[connections/anti-scraping-driven-architecture]] - Cloudflare IP-reputation blocking on betr follows the same ASN-level pattern as bet365; residential IPs get fundamentally different treatment than datacenter IPs
- [[concepts/bet365-racing-adapter-architecture]] - The `bet365_stream.py` Dell→VPS relay pattern that the betr residential relay replicates
- [[concepts/tabtouch-domain-migration-mqtt]] - TabTouch racing uses AWS IoT MQTT for live odds; betr has no equivalent — the only transport is REST polling
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting infrastructure that betr edge picks feed into; 1Hz detection edge creates a meaningful head-start for pick creation

## Sources

- [[daily/lcash/2026-05-19.md]] - Three exhaustive CDP capture sessions confirming zero WebSocket: logged-out, logged-in, and with betslip interaction; SignalR in bundle is user-account only (winner/settled notifications); betr polls `/Race?eventId=...` every ~13s via React Query `refetchInterval: 13000`; Pacific Pixie 29→34, Finnish Girl 12→11 captured within 36 seconds of movement (Session 14:18). Cloudflare rate-limits by IP reputation: VPS 1015'd at 1Hz, local Mac 100% at 10Hz (6,000/6,000); residential relay via Dell mini PC is the correct architecture (Session 16:47). WebShare proxies stale — TabTouch silently in DIRECT mode; CRLF in proxy lists; 7/100 from blocked subnet; proxy timeout 10s→4s with 60s quarantine (Session 13:47). `betr_stream.py` for Dell polling at 10Hz with batch POST to VPS ingest (Session 16:47)
