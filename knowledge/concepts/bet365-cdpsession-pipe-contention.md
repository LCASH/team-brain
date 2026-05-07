---
title: "bet365 CDPSession Pipe Contention"
aliases: [cdpsession-contention, cdpsession-pipe-block, playwright-cdpsession-hang, dedicated-page-pattern]
tags: [value-betting, bet365, cdp, playwright, reliability, architecture]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# bet365 CDPSession Pipe Contention

An active CDPSession on a Playwright page blocks all `page.evaluate()` and `page.goto()` calls on that same page — even for seemingly unrelated operations. On 2026-05-07, the MLB orchestrator's CDPSession (listening for WS frames via `Network.webSocketFrameReceived`) was consuming the Playwright Node.js subprocess pipe, causing `page.evaluate("location.hash = '/'")` to hang indefinitely with no timeout. The fix is to create a **dedicated fresh page** for any operation (like discovery) that needs Playwright DOM interaction, rather than sharing the orchestrator's CDPSession-linked page.

## Key Points

- An active CDPSession (WS frame listener) on `self._page` blocks ALL Playwright `evaluate()`/`goto()` calls on that same page — the CDPSession consumes the Node.js pipe capacity
- The hang is **indefinite with no timeout** — `page.evaluate()` never returns, never errors, never times out; the only escape is killing the process
- This is distinct from the EPIPE crash documented in [[concepts/playwright-node-pipe-crash-vector]]: EPIPE is a buffer overflow that crashes Node.js; CDPSession contention is a **deadlock** where the pipe is busy but not broken
- Fix: create a dedicated fresh page from `playwright_browser` for discovery operations — the fresh page has no CDPSession, so Playwright pipe is uncontended
- Both NBA and MLB orchestrators were affected — each sport's discovery phase now gets its own temporary page that is closed after parsing
- The `about:blank` navigation pattern (navigate to blank, disable Network CDP, perform hash-nav, re-enable Network CDP) was developed as a complementary mitigation within the orchestrator's own page

## Details

### The Contention Mechanism

The bet365 V3 scrapers use a hybrid architecture: Playwright manages DOM-heavy operations (discovery, login), while raw CDP WebSocket connections handle game page lifecycle. Each sport orchestrator (`WSNBAOrchestrator`, `WSMLBOrchestrator`) maintains a `self._page` Playwright page with an active CDPSession that listens to `Network.webSocketFrameReceived` events for real-time odds streaming.

The contention occurs because Playwright communicates with Chrome through a single Node.js subprocess pipe. When the CDPSession is actively receiving WS frames (bet365 streams 7-8 updates/second), the pipe is saturated with incoming CDP events. A `page.evaluate()` call on the same page must send a command through the same pipe and wait for a response — but the pipe is busy processing incoming CDPSession events. The evaluate call queues behind the stream of incoming events and never gets a turn.

This is fundamentally different from the EPIPE crash vector: EPIPE occurs when the pipe buffer overflows (too many CDP events from tab creation), killing the Node.js subprocess entirely. CDPSession contention is a **livelock** — the pipe is functional and draining events, but outgoing commands from `evaluate()` never get priority. The Node.js process is alive, the pipe is open, but the call never completes.

### Discovery Context

The MLB discovery was stuck because `discover_games()` was called with the orchestrator's `self._page` — the same page that had an active CDPSession listening for WS frames. When discovery attempted `page.evaluate("location.hash = '/'")` to navigate back to the home page, the call hung indefinitely. The scraper appeared frozen with no error output.

The NBA orchestrator had the same vulnerability but manifested differently: after successful discovery, subsequent rediscovery cycles would hang when the CDPSession was actively streaming. The `_do_rediscover` method's hash navigation attempts were blocked by the CDPSession's pipe consumption.

### The Dedicated Page Fix

The fix passes `playwright_browser` (the browser connection object) to `discover_games()` instead of the orchestrator's page. Discovery creates its own temporary page:

1. `page = await playwright_browser.new_page()` — fresh page with no CDPSession
2. Navigate to bet365, parse the DOM for game data
3. `await page.close()` — clean up the temporary page
4. Return discovered games to the orchestrator

The temporary page uses an uncontended pipe path — no CDPSession is attached, so Playwright commands flow freely. The orchestrator's page continues streaming WS frames undisturbed throughout the discovery process.

### The about:blank Complementary Pattern

For operations that must occur on the orchestrator's page (not discovery), a complementary pattern was developed:

1. `CDPSession.send('Network.disable')` — pause the WS frame listener
2. `page.goto('about:blank')` — navigate away, clearing pending events
3. Perform the needed navigation or evaluation
4. `page.goto(original_url)` — return to the streaming page
5. `CDPSession.send('Network.enable')` — resume WS listening

This pattern is used during `add_game()` when the orchestrator needs to navigate its own page to a new game URL. The 0.5-second sleep after `Network.disable` allows the pipe to drain before the navigation command is sent.

### Cross-Sport Isolation

The NBA and MLB orchestrators use separate Chrome instances (port 9223 and 9224 respectively), each with their own Playwright browser connection. Cross-sport CDPSession contention is impossible because the pipes are physically separate. Within-sport, the orchestrator's `self._page` is shared by design — `add_game()` navigates this page sequentially to each game, capturing coupon data before moving to the next.

The user raised an important question: "do we ever have parallel `add_game()` calls on the same page?" This is an open investigation — if the orchestrator dispatches `add_game()` concurrently for multiple games, two `page.goto()` calls could collide on `self._page`, producing race conditions or stale captures.

## Related Concepts

- [[concepts/playwright-node-pipe-crash-vector]] - EPIPE is a pipe buffer overflow crash; CDPSession contention is a pipe livelock — both stem from the Playwright Node.js pipe architecture but manifest differently
- [[connections/playwright-elimination-scraper-reliability]] - The progressive elimination of Playwright from the critical path; dedicated discovery pages reduce Playwright's contention surface
- [[concepts/persistent-page-chrome-scraper-architecture]] - The persistent-page pattern where `self._page` is shared; CDPSession contention adds a constraint: shared pages with active CDPSessions cannot be used for Playwright DOM operations
- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture where CDPSession contention was discovered during MLB discovery integration
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native orchestrators whose CDPSessions create the contention; the about:blank pattern was developed as part of the WS scraper deployment

## Sources

- [[daily/lcash/2026-05-07.md]] - MLB discovery hung at `page.evaluate("location.hash = '/'")` indefinitely; root cause: CDPSession WS frame listener consuming Playwright pipe on shared page; fix: dedicated fresh page for discovery from `playwright_browser`; about:blank + Network.disable/enable pattern for same-page operations; cross-sport isolation via separate Chrome ports confirmed; open question on parallel `add_game()` calls (Sessions 09:18, 09:23)
