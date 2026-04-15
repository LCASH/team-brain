---
title: "bet365 NBA Coupon Endpoint Dual-Capture"
aliases: [coupon-endpoint, dual-endpoint-capture, i99-i0-alternation, bb-wizard-plus-coupon]
tags: [bet365, nba, scraping, performance, value-betting]
sources:
  - "daily/lcash/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# bet365 NBA Coupon Endpoint Dual-Capture

A scraping optimization for the bet365 NBA game scraper that supplements the existing BB wizard endpoint with the coupon endpoint, using alternating I99/I0 tab navigation to capture 332 odds per game. The dual-endpoint strategy catches cache invalidations at offset moments, providing 5-15 seconds of additional freshness improvement beyond poll interval reduction alone. This was built as part of the HTTP-poll optimization path adopted after the WS probe proved NBA prop streaming non-viable.

## Key Points

- The coupon endpoint provides a second HTTP data source alongside the BB wizard, increasing odds coverage to 332 per game
- Alternating I99/I0 tab navigation triggers coupon endpoint responses that standard hash navigation misses
- Dual endpoint capture catches cache invalidations at offset moments — BB wizard and coupon responses arrive at different times, so the fresher of the two is used
- Provides 5-15s additional freshness improvement beyond just reducing the poll interval (15s→8s)
- Yes/no markets (Double Double, Triple Double) are confirmed parseable from the coupon endpoint — percentages convertible to decimal odds

## Details

### Background: The HTTP-Poll Optimization Path

After the WS probe on 2026-04-15 proved that bet365 NBA player prop odds cannot be streamed via WebSocket (see [[concepts/bet365-ws-topic-authorization]]), the recommended path forward was HTTP-poll optimization. Three parameter changes were planned: (1) reduce `_REFRESH_INTERVAL` from 15s to 8s, (2) eliminate the 30s hash-skip blackout in `server/main.py`, and (3) parallelize per-game fetching. The coupon endpoint adds a fourth, more substantive architectural improvement that exploits bet365's internal content delivery structure.

WebSocket streaming was conclusively ruled out for player props because bet365 enforces session-bound topic authorization — props are bulk-fetched via the BB wizard HTTP endpoint and never receive individual per-prop render registrations required for WS subscriptions (see [[connections/ws-viability-sport-rendering-divergence]]). This makes HTTP polling the permanent architecture for prop data, justifying deeper investment in polling optimization.

### The Coupon Endpoint

bet365's NBA game pages serve data through multiple internal endpoints. The BB wizard (`betbuilderpregamecontentapi/wizard`) returns player prop data in a single response and has been the game scraper's primary data source. The coupon endpoint provides odds through a different internal path, triggered by specific tab navigation sequences.

The alternating I99/I0 tab navigation pattern triggers coupon endpoint responses that standard hash navigation misses. By cycling between these tab states, the scraper captures responses from both endpoints within each poll cycle. Since the two endpoints have independent cache invalidation schedules, their responses may contain odds at different timestamps — the scraper takes the fresher of the two, reducing effective staleness.

### Freshness Improvement Mechanism

The dual-endpoint strategy provides 5-15 seconds of additional freshness improvement beyond poll interval reduction alone. The mechanism is straightforward: if the BB wizard response is 8 seconds old and the coupon response is 3 seconds old (because its cache was invalidated more recently), the scraper uses the coupon data. Over many poll cycles, this statistical advantage compounds into a meaningful reduction in average odds age.

Combined with the other HTTP-poll optimizations (8s polling interval, no hash-skip blackout), the expected end-to-end latency improvement is from 15-65s down to approximately 5-10s — approaching the practical limits of HTTP polling.

### Yes/No Market Expansion

The coupon endpoint also revealed that yes/no markets (Double Double, Triple Double) emit parseable data — percentages convertible to decimal odds. These markets were previously listed as "deliberately NOT done" but were confirmed viable during implementation. Parsing these markets would expand the scanner's coverage of exotic prop types. The implementation requires probing what format bet365 uses for the percentage field (`OD=` decimal or a dedicated `PC=` field).

### Branch Structure

The full bet365 NBA scraper improvement was organized into three commits on a feature branch (`bet365-nba-coupon-endpoint`):
1. Kill 30s hash-skip + drop refresh interval 15s→8s (parameter changes)
2. Coupon endpoint parser + alternating I99/I0 navigation (new data source, 332 odds/game)
3. `source_captured_at` end-to-end plumbing with color-coded age display (diagnostic layer — reinstating the Layer A approach reverted earlier in the day)

Deployment to mini PC and VPS awaiting user go-ahead as of end-of-day 2026-04-15.

## Related Concepts

- [[concepts/odds-staleness-pipeline-diagnosis]] - The staleness diagnosis that identified HTTP-poll optimization as the path forward; Layer A reinstated as commit 3
- [[concepts/bet365-ws-topic-authorization]] - The WS probe failure that drove the pivot to HTTP-poll optimization
- [[concepts/bet365-mlb-lazy-subscribe-migration]] - MLB uses a different endpoint migration; coupon is NBA-specific
- [[connections/ws-viability-sport-rendering-divergence]] - The architectural divergence that necessitates HTTP polling for props
- [[concepts/server-side-snapshot-cache]] - The server-side optimization that reduces the push cycle portion of end-to-end latency

## Sources

- [[daily/lcash/2026-04-15.md]] - Dual endpoint capture (BB wizard + coupon) with alternating I99/I0 navigation yielding 332 odds/game and 5-15s freshness improvement; yes/no markets confirmed parseable; three-commit branch structure; part of HTTP-poll optimization path after WS probe failed for props (Session 22:36)
