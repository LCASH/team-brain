---
title: "CDPSession Playwright Pipe Contention"
aliases: [cdpsession-contention, cdpsession-evaluate-hang, playwright-pipe-blocking, dedicated-page-pattern]
tags: [value-betting, bet365, playwright, cdp, chrome, reliability, architecture]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# CDPSession Playwright Pipe Contention

When a Playwright CDPSession (WebSocket frame listener via `Network.enable`) is active on a page, all Playwright high-level operations on that same page — `page.evaluate()`, `page.goto()`, hash navigation — hang indefinitely with no timeout. The CDPSession's continuous WS frame traffic saturates the Node.js subprocess pipe, blocking Playwright's internal command/response cycle. This was discovered on 2026-05-07 when MLB discovery hung at `page.evaluate("location.hash = '/'")` because the MLB orchestrator's CDPSession was consuming the pipe on `self._page`.

## Key Points

- An active CDPSession (e.g., `Network.webSocketFrameReceived` listener) on a Playwright page blocks ALL `evaluate()` and `goto()` calls on that same page — they hang forever with no timeout or error
- The mechanism is pipe saturation: CDPSession's continuous WS frame events consume the Node.js subprocess pipe buffer, preventing Playwright's command/response round-trips from completing
- Fix: create a **dedicated fresh page** for any operation that needs Playwright pipe access (discovery, navigation) — never share a page with an active CDPSession
- The contention was invisible during normal WS streaming (CDPSession worked fine for its intended purpose); it only manifested when a Playwright operation was attempted on the same page
- CDPSession `Network.disable` before navigation + `Network.enable` after eliminates the WS flood during hash-nav, reducing 18-25 second delays to near-instant
- V3 discovery now passes `playwright_browser` (not orchestrator page) and creates its own temporary page, closing it after parsing

## Details

### The Failure Mechanism

The V3 bet365 scraper architecture uses a hybrid approach: Playwright for DOM-heavy discovery operations and raw CDP WebSocket for game page management (see [[concepts/playwright-node-pipe-crash-vector]]). Each sport orchestrator (`WSNBAOrchestrator`, `WSMLBOrchestrator`) maintains a `self._page` — a Playwright page object with an active CDPSession that listens for WebSocket frames via `Network.webSocketFrameReceived`.

When discovery needs to run (finding new games via `getsplashpods`), the original code passed `self._page` to the discovery function. Discovery called `page.evaluate("location.hash = '/'")` to navigate the SPA — but this call hung indefinitely. The CDPSession on `self._page` was receiving a continuous stream of WS frame events from bet365's active connections. These events consumed the Node.js subprocess pipe bandwidth, preventing Playwright's `evaluate()` command from completing its send/receive cycle through the same pipe.

This is a distinct failure mode from the EPIPE crash documented in [[concepts/playwright-node-pipe-crash-vector]]. EPIPE occurs when the pipe buffer overflows and the pipe breaks entirely. Contention occurs when the pipe is saturated but not broken — commands are queued but never complete, producing an indefinite hang rather than a crash. The hang has no timeout because Playwright's internal await has no configurable timeout for pipe-level communication.

### The CDPSession Pause Technique

A secondary optimization was also discovered: disabling the CDPSession's network monitoring during hash navigation eliminates the WS flood that causes 18-25 second delays. The sequence:

1. `cdp_session.send('Network.disable')` — pauses WS frame capture
2. Wait 0.5s for pipe to drain
3. Perform hash navigation via `page.evaluate()` or `page.goto()`
4. `cdp_session.send('Network.enable')` — resume WS frame capture

This technique is useful when the orchestrator's page must perform navigation (e.g., `add_game()` navigating to a game URL) while keeping the CDPSession alive for subsequent WS listening. Without the pause, even simple navigations can take 18-25 seconds as WS frame events flood the pipe during the navigation.

### The Dedicated Page Pattern

The permanent fix for discovery is architectural: never share a page between CDPSession listeners and Playwright operations. Discovery now receives `playwright_browser` (the browser object) instead of the orchestrator's page, creates its own temporary page via `browser.new_page()`, performs all discovery work on that clean page, and closes it when done. The orchestrator's `self._page` with its CDPSession is never touched during discovery.

This pattern extends the hybrid architecture principle: Playwright pages used for interactive work (discovery, login) must be isolated from pages used for CDP streaming (WS frame capture, response interception). Mixing these concerns on a single page creates pipe contention that is both invisible during normal operation and unrecoverable when it occurs.

### Interaction with Fresh Chrome Pattern

The dedicated page pattern complements the "always fresh Chrome" lifecycle pattern documented in [[connections/chrome-lifecycle-management-pattern]]. Fresh Chrome eliminates stale CDP sessions from dead workers; dedicated pages eliminate pipe contention between live operations. Together, they provide two layers of CDP connection hygiene: process-level (fresh Chrome) and page-level (dedicated pages per concern).

### SPA Warmup Requirement

A related discovery: after `page.goto(homepage)`, bet365's SPA needs approximately 4 seconds to redirect to `#/HO/` and initialize its internal router before hash navigation works. Without this warmup delay, hash navigation commands are silently ignored — the SPA hasn't registered its route handlers yet. The 4-second sleep after `domcontentloaded` is a pragmatic fix; a more robust approach would poll for a DOM element that indicates SPA initialization is complete.

## Related Concepts

- [[concepts/playwright-node-pipe-crash-vector]] - The EPIPE crash from pipe overflow is the catastrophic version; contention is the non-fatal but blocking version of the same underlying pipe bandwidth limitation
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native orchestrators whose CDPSession listeners cause the contention; discovery must be isolated from their pages
- [[connections/chrome-lifecycle-management-pattern]] - The unified Chrome lifecycle pattern that dedicated pages extend with page-level isolation
- [[concepts/persistent-page-chrome-scraper-architecture]] - The persistent-page architecture that `self._page` implements; dedicated discovery pages are the complement for non-persistent operations
- [[concepts/bet365-getsplashpods-discovery-routing]] - The discovery routing that runs on the dedicated page; getsplashpods only fires from `#/HO/`
- [[concepts/playwright-evaluate-uncancellable]] - A related Playwright blocking issue: `evaluate()` blocks when browser JS is unresponsive; CDPSession contention blocks when the pipe is saturated — different mechanism, same symptom (indefinite hang)

## Sources

- [[daily/lcash/2026-05-07.md]] - MLB discovery hung at `page.evaluate("location.hash = '/'")` — root cause: CDPSession WS frame listener on `self._page` blocking Playwright pipe; fix: dedicated fresh page from `playwright_browser` for discovery; CDPSession `Network.disable`/`Network.enable` pause eliminates 18-25s WS flood during navigation; SPA needs 4s warmup after domcontentloaded before hash-nav works (Sessions 09:18, 09:23, 11:54)
