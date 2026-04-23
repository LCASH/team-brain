---
title: "bet365 Size-Gate Stale Odds Bug"
aliases: [size-gate-bug, size-gate-filter, stale-odds-root-cause, session-expiry-detection]
tags: [bet365, scraping, data-quality, bug, value-betting, operations]
sources:
  - "daily/lcash/2026-04-23.md"
created: 2026-04-23
updated: 2026-04-23
---

# bet365 Size-Gate Stale Odds Bug

The bet365 NBA game scraper contained a "size-gate" filter that silently discarded fresh API responses when they were smaller than a cached response, causing the scraper to serve stale or wrong odds. After removing the size-gate, 14/14 markets matched live bet365 prices exactly. Anonymous (not-logged-in) Chrome was confirmed to return correct odds for tested markets. A three-layer session expiry detection system was added to surface when bet365 cookies expire.

## Key Points

- The size-gate filter in the NBA scraper silently discarded fresh `betbuilderpregamecontentapi` responses that were smaller than the last cached response — the real root cause of odds accuracy mismatches
- After removing the size-gate: **14/14 exact matches** verified against a live bet365 screenshot
- Anonymous Chrome gets correct odds for tested markets — logged-in session may only matter for certain market types or bet limits
- Three-layer session expiry detection deployed: scraper checks URL redirects → worker writes `session_expired` flag → server surfaces it on health endpoint and dashboard
- CDP remote debugging only listens on localhost — cannot connect to Chrome DevTools from another machine (e.g., over Tailscale) without SSH tunneling
- bet365 appears to limit one active session per cookie set — injecting the same cookies into two Chrome instances (NBA port 9223 + MLB port 9224) didn't work for both
- Session survived overnight without expiry — cookies are reasonably durable
- MLB scraper doesn't need the size-gate fix (accumulates all responses differently)

## Details

### The Size-Gate Bug

The NBA game scraper (`bet365_game_worker.py`) used the BB wizard endpoint (`betbuilderpregamecontentapi/wizard`) to fetch player prop odds. A size-gate filter compared each new API response's byte size against the previously cached response and discarded the new response if it was smaller. The intent was likely to protect against partial or degraded responses — a reasonable heuristic under the assumption that a complete response is always at least as large as a prior complete response.

This assumption is wrong. bet365's response size varies legitimately depending on market availability, prop count changes, and game state transitions. When a game transitions from pre-game to approaching tip-off, some markets are removed while odds on remaining markets update. The smaller response contains the fresh, correct odds — but the size-gate discards it and continues serving the cached, stale odds from the larger response.

The bug was confirmed by comparing scraped odds against a live bet365 screenshot. Before the fix, multiple markets showed mismatched odds. After removing the size-gate filter, all 14 tested markets matched exactly. This definitively proved the size-gate was the accuracy root cause, not the anonymous-vs-logged-in Chrome hypothesis that had been previously investigated.

### Session Expiry Detection

With the odds accuracy issue resolved, the remaining operational concern was session expiry — when bet365's authentication cookies expire, the scraper would silently fail to access authenticated-only content. A three-layer detection system was deployed:

1. **Scraper layer**: Checks for URL redirects to bet365's login page during page navigation. A redirect indicates the session has expired.
2. **Worker layer**: When the scraper detects expiry, the worker writes a `session_expired` flag to shared state.
3. **Server/dashboard layer**: The health endpoint and dashboard surface a `SESSION EXPIRED` status indicator, alerting the operator to log in again.

The recovery procedure is manual: RDP into the mini PC, open Chrome on the appropriate debugging port (9223 for NBA, 9224 for MLB), and log in to bet365. The scraper auto-attaches to the existing logged-in Chrome session.

### CDP Remote Debugging Limitation

During investigation, lcash attempted to inject bet365 cookies into Chrome on the mini PC remotely via CDP over Tailscale. This approach failed because Chrome's CDP (Chrome DevTools Protocol) debugging port only listens on `localhost` by default — it does not accept connections from other machines on the network, even over Tailscale VPN. The workaround requires SSH tunneling to forward the local CDP port.

Additionally, when cookies were successfully injected into both the NBA Chrome (port 9223) and MLB Chrome (port 9224), only the NBA Chrome accepted the session. The MLB Chrome connection reset, suggesting bet365 limits one active session per cookie set across browser instances.

### Committed as `be447ba`

The size-gate removal and session expiry detection were deployed and pushed as commit `be447ba` on main.

## Related Concepts

- [[concepts/game-scraper-chrome-crash-recovery]] - The Chrome crash auto-recovery addresses a different failure mode (dead Chrome returning cached data); the size-gate bug caused stale data from a live, functioning Chrome
- [[concepts/odds-staleness-pipeline-diagnosis]] - The size-gate is an eighth cause of odds drift, operating at the scraper layer before data enters the pipeline
- [[concepts/dashboard-pick-flashing-stale-odds]] - Pick flashing was partly caused by stale odds from the `captured_at` override; size-gate is a separate stale-odds mechanism at the scraper layer
- [[concepts/bet365-headless-detection]] - Anonymous Chrome getting correct odds suggests that headed mode is sufficient for data access; authentication may only gate bet-limit-specific content
- [[connections/silent-type-coercion-data-corruption]] - The size-gate is another "plausible wrong output" bug — the cached data looked valid, just stale

## Sources

- [[daily/lcash/2026-04-23.md]] - Size-gate removed from NBA scraper; 14/14 exact odds matches after fix; anonymous Chrome confirmed correct for tested markets; three-layer session expiry detection (scraper redirect check → worker flag → server/dashboard indicator); CDP localhost-only limitation; bet365 one-session-per-cookie constraint; MLB scraper unaffected; session survived overnight; committed as `be447ba` (Session 08:30)
