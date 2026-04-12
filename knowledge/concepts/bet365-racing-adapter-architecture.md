---
title: "bet365 Racing Adapter Architecture"
aliases: [bet365-adapter, bet365-local, superwin-bet365]
tags: [architecture, adapter, bet365, racing, superwin]
sources:
  - "daily/lcash/2026-04-11.md"
  - "daily/lcash/2026-04-12.md"
created: 2026-04-11
updated: 2026-04-12
---

# bet365 Racing Adapter Architecture

A local adapter (`bet365_local.py`) that extracts live Australian and New Zealand horse racing data from bet365.com.au via CDP-attached browser automation. The production architecture uses a two-layer approach: one-time HTTP discovery scan for runner name/ID mapping, followed by persistent WebSocket streaming for real-time odds updates.

## Key Points

- Two-layer architecture: HTTP `racecoupon` endpoint provides runner names, jockeys, weights, form, and IDs; WebSocket stream provides live odds updates keyed by those IDs
- Discovery phase uses T6 splash endpoint (no auth needed) to find all racing meetings, then navigates to each meeting and clicks race tabs to trigger HTTP responses captured via CDP
- The adapter evolved through four iterations: two-phase enumerate+fetch → single-pass tab-click → navigate-away per race → WS streaming — each pivot driven by a specific bet365 behavioral discovery
- Final HTTP-only metrics: 14 meetings, 12 loaded, 67 races, 661 runners, 100% odds coverage in ~4 minutes
- Output format matches SuperWin's `Race.to_dict()` interface with `bookie_ids`, `bookie_venues`, and `odds["bet365"]` containing win + place odds

## Details

### Architecture Evolution

The adapter went through four distinct architectural iterations in a single day, each driven by a discovery about bet365's anti-scraping behavior:

**Iteration 1 — Two-Phase Enumerate + Fetch:** Phase 1 clicked all race tabs within a meeting to discover non-sequential F values (race IDs like 192644720, 192644727). Phase 2 used navigate-away pattern to fetch each race individually. Result: 19/28 races in 95s from 3 meetings, but slow (~2.5s per race navigation).

**Iteration 2 — Navigate-Away per Race:** Applied the navigate-away trick (hash to soccer `#/AS/B1/` between each venue) to force fresh HTTP requests. Achieved 14/14 venues with 0 failures in 38 seconds, but only fetched 1 race per meeting (next-to-jump).

**Iteration 3 — Single-Pass Tab-Click:** Discovered that clicking race tabs within a meeting triggers fresh HTTP requests without needing navigate-away between individual races — only between meetings. Navigate to meeting once, click through all race tabs, capture each response via CDP. Result: 67 races from 12 meetings, 661 runners, 100% odds, ~4 minutes. Navigate-away still needed between meetings to prevent SPA caching.

**Iteration 4 — WebSocket Streaming (target architecture):** User directed pivot away from polling/scraping toward live streaming. The browser's WebSocket connection at `wss://premws-pt1.365lpodds.com/zap/` pushes ~7-8 odds updates per second. Independent Python WebSocket connections get 403'd, so the adapter piggybacks on the browser's existing connection by injecting subscription messages via `page.evaluate()` and capturing responses via CDP `Network.webSocketFrameReceived`. HTTP discovery scan still needed once for runner name ↔ participant ID mapping.

### Discovery Phase

The T6 discovery endpoint (`nexttojumpcontentapi/splash T6`) returns all current racing meetings (~30K chars) without requiring authentication or navigation state. Meetings include venue names, race times, and PD identifiers. The correct API path prefix is `/contentdata/` — the existing adapter had been calling without this prefix, which returned empty responses. Racing classification codes in discovery responses: `CL=2030` (horse racing), `CL=2031` (greyhounds), `CL=2032` (harness). Promotional entries with `#P12#` in their PD field should be filtered out.

### Venue Scanning Reliability

The venue scanning phase (HTTP discovery) is subject to reliability issues when the browser's JavaScript context degrades after scanning many venues. During testing on 2026-04-12, the Toowoomba venue consistently caused `page.evaluate()` to hang indefinitely — likely due to SPA state degradation after navigating through 10+ venues. This hang is uncancellable at the individual call level (see [[concepts/playwright-evaluate-uncancellable]]).

The adopted mitigation is a global 4-minute timeout on the entire `build_runner_map()` phase, with mutable containers (`participant_map`, `fixture_participants`) passed as parameters so partial results survive cancellation (see [[concepts/async-global-timeout-partial-results]]). This means the adapter proceeds to streaming with whatever venues were successfully scanned before the hang.

Additionally, stale browser WebSocket connections from repeated process kills cause auth extraction failures. The `x-net-sync-term` and session tokens may reference expired connections, producing silent failures. A fresh browser session (clean AdsPower profile start) is required for reliable full runs.

### Current Limitations

- **Horse racing only** — greyhound (`B4`) and harness (`B3`) meetings require separate discovery queries not yet implemented
- **Cloudflare blocking on VPS** — datacenter IPs and headless browser fingerprints are detected; requires AdsPower with residential proxy for deployment
- **Browser dependency** — adapter requires a live browser session (AdsPower or local Chromium), cannot operate as a standalone HTTP client
- **Race tab detection** — 2/14 meetings failed tab detection (likely fully completed meetings with no active races)
- **Past races** — races that have already jumped return runner data but no odds; this is expected behavior, not a bug
- **Venue scanning hangs** — certain venues (consistently Toowoomba) cause uncancellable `page.evaluate()` hangs after 10+ venues scanned; mitigated by global timeout with partial results

### Deployment Architecture

The adapter runs locally against an AdsPower browser instance. VPS deployment is blocked by Cloudflare — AdsPower with a residential proxy is needed. The `pstk` cookie and `cf_clearance` cookie are the key authentication tokens. The `x-net-sync-term` header rotates every ~55 seconds and must be refreshed from the page's JavaScript context.

## Related Concepts

- [[concepts/bet365-racing-data-protocol]] - The wire protocol consumed by this adapter
- [[concepts/spa-navigation-state-api-access]] - The SPA constraints that shaped the adapter's navigation strategy
- [[concepts/cdp-browser-data-interception]] - The data capture technique at the adapter's core
- [[concepts/browser-mediated-websocket-streaming]] - The target streaming architecture for real-time odds
- [[concepts/playwright-evaluate-uncancellable]] - The uncancellable evaluate issue affecting venue scanning reliability
- [[concepts/async-global-timeout-partial-results]] - The timeout pattern adopted for resilient venue scanning
- [[connections/browser-automation-reliability-cost]] - The broader reliability costs of the browser-mediated approach

## Sources

- [[daily/lcash/2026-04-11.md]] - Full adapter development across sessions 12:39–16:06: four architecture iterations, discovery of /contentdata/ prefix (Session 13:35), navigate-away trick (Session 14:45), single-pass tab-click (Session 15:53), pivot to WS streaming (Session 16:06)
- [[daily/lcash/2026-04-12.md]] - Venue scanning reliability: Toowoomba hang discovery, global timeout + mutable containers solution, stale browser session issues (Session 15:37)
