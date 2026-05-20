---
title: "Neds Entain API Reconnaissance"
aliases: [neds-api, entain-platform, neds-scraper-recon, ladbrokes-au-shared-platform, neds-socket-io]
tags: [value-betting, sportsbook, scraper, reverse-engineering, entain, recon]
sources:
  - "daily/lcash/2026-05-18.md"
created: 2026-05-18
updated: 2026-05-18
---

# Neds Entain API Reconnaissance

On 2026-05-18, lcash performed initial reconnaissance on Neds (api.neds.com.au) as a potential new soft book for the value betting scanner. Neds runs on the **Entain platform** — the same platform powering Ladbrokes AU (book_id 902) — meaning a single scraper could serve both brands with a brand/host selector. Direct API access returns HTTP 500; the endpoint requires SPA-driven browser session context (likely cookie/CSRF validation). Live odds updates flow via Socket.IO at `push.neds.com.au` (EIO=4). The scraper will piggyback on AdsPower-backed Chrome using the in-browser `fetch()` pattern.

## Key Points

- `api.neds.com.au` returns **HTTP 500 to direct curl** — requires SPA browser session context (cookies, CSRF tokens, or session binding)
- Neds is **Entain platform** = same as Ladbrokes AU (902) — one scraper could serve both brands with a host/brand parameter swap
- Live odds updates via **Socket.IO** at `push.neds.com.au` (Engine.IO protocol version 4)
- Planned scraper approach: in-browser `fetch()` via AdsPower Chrome (same pattern as [[concepts/bet365-in-browser-cdp-fetch-transport]])
- AdsPower browser on Eve needed Wayland env vars harvested to come alive (profile `k19yb91n` on CDP port 38101) — see [[concepts/adspower-wayland-gui-session-recovery]]
- Recon findings documented in `brain/findings/2026-05-18-neds-recon.md` with 5 open questions

## Details

### Platform Identification

Neds is owned and operated by Entain, the same company that operates Ladbrokes Australia. Both brands share the same underlying sportsbook platform, meaning their API structures, market offerings, and data formats are likely identical or near-identical. This creates an efficiency opportunity: building one Entain platform scraper with a configurable host parameter (`api.neds.com.au` vs `api.ladbrokes.com.au`) could provide data from two soft books for the development cost of one.

Ladbrokes AU is already tracked as book_id 902 in the scanner's book configuration. Neds would receive a new book_id, allowing the devig pipeline to evaluate both books independently while sharing scraper infrastructure.

### API Access Constraints

Unlike the Betr/BlueBet API (which is fully open, see [[concepts/betr-bluebet-api-integration]]) or the Kambi API (which requires no auth, see [[concepts/tabtouch-kambi-white-label-sports]]), the Neds API requires an active browser session. Direct HTTP requests to `api.neds.com.au` endpoints return HTTP 500 — not 403 (blocked) or 401 (unauthorized), but 500 (server error), suggesting the API expects session-specific headers or cookies that aren't present in bare requests.

This access pattern is similar to bet365's `othersportsmatchmarketscontentapi` (see [[concepts/bet365-in-browser-cdp-fetch-transport]]) where an active WebSocket heartbeat was required for HTTP responses. The Neds API may have a similar session-binding mechanism, or it may simply require CSRF tokens and session cookies from the SPA's login flow.

### Implementation Approach

The planned implementation uses AdsPower-backed Chrome on Eve with in-browser `fetch()` via CDP `Runtime.evaluate` — the same transport pattern proven for bet365's multi-sport enumeration. The browser maintains the authenticated session; Python constructs the API URLs and drives the fetch calls via CDP.

An open question is whether Neds login unlocks additional markets beyond anonymous browsing. Some Australian soft books offer the same markets to logged-in and anonymous users; others gate player props behind authentication.

### Open Questions

Five open questions from the reconnaissance need resolution before building the scraper:
1. Does Neds login unlock additional player prop markets?
2. What is the exact API endpoint structure for NBA/MLB player props?
3. Does the Ladbrokes AU API use the same endpoint patterns?
4. Can Socket.IO push be used for pre-game prop updates (or only live)?
5. What is the prop type naming convention relative to the scanner's `EV_NAME_MAP`?

## Related Concepts

- [[concepts/betr-bluebet-api-integration]] - Betr's open API is the opposite extreme: no auth, no browser needed. Neds requires SPA browser context
- [[concepts/bet365-in-browser-cdp-fetch-transport]] - The in-browser fetch pattern that will be used for Neds scraping; same AdsPower + CDP Runtime.evaluate approach
- [[concepts/tabtouch-kambi-white-label-sports]] - Another white-label platform (Kambi) with a public API; Entain's API is session-gated unlike Kambi's open access
- [[concepts/adspower-wayland-gui-session-recovery]] - AdsPower on Eve needed Wayland env var harvesting before Chrome could launch for Neds recon

## Sources

- [[daily/lcash/2026-05-18.md]] - Neds API returns 500 to direct curl; Entain platform = same as Ladbrokes AU (902); Socket.IO at push.neds.com.au (EIO=4); in-browser fetch via AdsPower planned; AdsPower needed Wayland env vars; 5 open questions in brain findings doc; NRL/AFL deprioritized, focus on NBA + MLB (Session 10:06)
