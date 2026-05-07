---
title: "MLB v3 Recently-Closed Cache Deadlock"
aliases: [recently-closed-cache, cache-pollution-deadlock, 3-strike-cache-deadlock, scraper-stuck-state]
tags: [value-betting, bet365, mlb, scraping, bug, reliability, architecture]
sources:
  - "daily/lcash/2026-05-02.md"
created: 2026-05-02
updated: 2026-05-02
---

# MLB v3 Recently-Closed Cache Deadlock

The bet365 MLB v3 scraper's 3-strike close logic combined with the `_recently_closed` game cache creates an unrecoverable stuck state. When a game page returns zero odds on three consecutive refreshes (e.g., because the Chrome session was temporarily logged out or the API was transiently unavailable), the scraper closes the game tab and adds the game ID to `_recently_closed`. On the next rediscovery cycle, the discovery logic sees the game in `_recently_closed` and skips it — even though the underlying condition (login wall, API outage) may have resolved. The result is permanently zero odds for affected games until the server process is restarted.

## Key Points

- 3-strike close logic works correctly in isolation: if a game page returns 0 records on 3 consecutive refreshes, the tab is closed to free resources
- `_recently_closed` cache prevents rediscovery from immediately reopening a just-closed game — intended to avoid thrashing
- **Deadlock**: 3-strike close + recently-closed cache = games that fail transiently can never reopen, even after conditions improve
- The root cause was that Network.onResponseReceived event capture wasn't returning data — not an API availability issue (odds were visible on the bet365 website)
- Server restart was the only fix — cleared the `_recently_closed` cache and allowed fresh game page creation
- After restart, 1,000+ MLB picks immediately started generating across all 5 theories, confirming the data was always available

## Details

### The Failure Mechanism

The MLB v3 scraper (see [[concepts/mlb-parallel-scraper-workers]]) uses raw CDP WebSocket connections to manage game pages. Each game page periodically refreshes to capture fresh API responses via `Network.responseReceived` events. When a refresh returns zero odds records, the scraper increments a failure counter for that game. After 3 consecutive failures (the "3-strike" threshold), the scraper closes the game tab to free Chrome resources and prevent wasted refresh cycles.

The closed game ID is added to `_recently_closed` — an in-memory set that persists for the lifetime of the server process. This cache exists to prevent a pathological cycle: rediscovery detects the game → opens a new tab → 3 strikes → closes tab → rediscovery reopens → repeat. Without the cache, transient API issues would cause rapid tab creation/destruction cycles that destabilize Chrome.

The deadlock occurs because the cache has no expiry or condition-based invalidation. Once a game enters `_recently_closed`, it stays there permanently. If the underlying condition resolves (Chrome logs back in, API recovers, CDN cache refreshes), the scraper never learns about it because rediscovery skips the game entirely.

### Discovery on 2026-05-02

On 2026-05-02, lcash investigated why the MLB scraper was producing zero odds despite 14 games being available on bet365 AU. The scraper was running healthily (process alive, tabs open on game pages) but `Network.onResponseReceived` was not capturing API responses. Initial investigation explored multiple hypotheses: API endpoint changes, Cloudflare blocking CDP requests, 200-character response filter, and login wall interference.

The breakthrough came from restarting the MLB server via `schtasks /Run /TN MLB_Server`. The restart cleared all in-memory state including `_recently_closed`, and the scraper immediately began producing data: 1,000+ MLB picks across all 5 theories (MLB Crypto Edge, Pinnacle, 4-Book Power, Novig+BR Additive, Calibrated). This confirmed the data had been available the entire time — the scraper was preventing itself from accessing it.

### Why Restart Was Faster Than Deep Investigation

The investigation consumed significant time exploring wrong hypotheses (API changes, Cloudflare, response filters) before the restart proved the cache was the issue. This illustrates a general debugging principle for stateful scrapers: when the data source is confirmed available (visible on the website) but the scraper reports zero records, check in-memory state caches before investigating network-level issues. A clean state reset is both a diagnostic tool (confirms the issue is state, not infrastructure) and an immediate fix.

### Prevention

Three approaches could prevent this deadlock:

1. **TTL on `_recently_closed`** — expire entries after a configurable window (e.g., 30 minutes), allowing rediscovery to retry games that were closed due to transient failures
2. **Condition-aware reopening** — when rediscovery detects that a game in `_recently_closed` still has upcoming tip-off time, clear the entry and allow reopening
3. **Separate transient vs permanent close** — distinguish between "game has no data because it's too far out" (permanent, cache is correct) and "game had data but API stopped responding" (transient, should retry)

The 3-strike threshold itself is sound — closing unresponsive game pages prevents resource exhaustion. The issue is specifically the permanent cache that prevents recovery after the underlying condition resolves.

## Related Concepts

- [[concepts/persistent-page-chrome-scraper-architecture]] - The persistent-page architecture where `_recently_closed` prevents tab thrashing; the cache is architecturally correct but needs TTL
- [[concepts/bet365-v3-scraper-capability-ladder]] - The v3 capability ladder's error recovery scenarios (3-strike dead tab at 30s intervals) validated the close logic but didn't test the cache interaction with rediscovery
- [[concepts/game-scraper-chrome-crash-recovery]] - Chrome crash auto-recovery handles a different failure mode (dead Chrome); the cache deadlock is live Chrome with valid data blocked by in-memory state
- [[concepts/bet365-session-login-detection-gap]] - Login wall producing empty responses is one trigger for the 3-strike close; login detection would prevent the cascade by identifying the root cause before 3 strikes accumulate
- [[connections/operational-compound-failures]] - Cache deadlock + no alerting + manual restart required follows the established compound failure pattern

## Sources

- [[daily/lcash/2026-05-02.md]] - MLB scraper producing zero odds despite 14 games on bet365 AU; Network.onResponseReceived not capturing data; multiple hypotheses explored (API changes, Cloudflare, response filters); restart cleared `_recently_closed` cache and immediately produced 1,000+ picks across 5 theories; sometimes restart > deep investigation (Sessions 12:48, 15:23)
