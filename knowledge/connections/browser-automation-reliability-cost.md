---
title: "Connection: Browser Automation Reliability Cost"
connects:
  - "concepts/playwright-evaluate-uncancellable"
  - "concepts/browser-mediated-websocket-streaming"
  - "concepts/bet365-racing-adapter-architecture"
  - "concepts/async-global-timeout-partial-results"
sources:
  - "daily/lcash/2026-04-12.md"
  - "daily/lcash/2026-04-11.md"
  - "daily/lcash/2026-04-13.md"
  - "daily/lcash/2026-04-19.md"
created: 2026-04-12
updated: 2026-04-19
---

# Connection: Browser Automation Reliability Cost

## The Connection

The browser-mediated architecture forced by bet365's anti-scraping defenses introduces a second-order reliability cost: the adapter depends on browser JavaScript execution for critical operations, and browser JS contexts can become unresponsive in ways that are invisible to and unrecoverable from the Python orchestration layer. The same defenses that made browser automation necessary also make it fragile.

## Key Insight

The anti-scraping defense stack (documented in [[connections/anti-scraping-driven-architecture]]) eliminated every architecture that doesn't route through a real browser. But running through a browser introduces a new failure class that doesn't exist in direct HTTP/WS architectures: **unresponsive JavaScript contexts**. When `page.evaluate()` sends JavaScript to the browser and the browser's JS engine is stalled — due to SPA state degradation, memory pressure, or page lifecycle issues — the Python-side coroutine blocks indefinitely. Critically, this block is not cancellable by standard asyncio mechanisms (see [[concepts/playwright-evaluate-uncancellable]]).

This creates an ironic inversion: the adapter was forced into browser automation to bypass anti-scraping, but the browser itself becomes the least reliable component. Direct HTTP clients don't have this failure mode — they timeout cleanly because the Python process owns the socket. Browser automation adds an intermediary (the browser process) that can fail in ways the orchestrator cannot detect or recover from at the individual operation level.

The practical consequence is that the adapter must be designed for **graceful degradation**, not **reliable completion**. The global timeout + mutable containers pattern (see [[concepts/async-global-timeout-partial-results]]) accepts that some venues will fail and proceeds with partial data. This is a fundamental shift from the HTTP-based iterations (which achieved 100% venue coverage) to the streaming architecture (which targets best-effort coverage with real-time data).

## Evidence

On 2026-04-12, the Toowoomba venue consistently caused `page.evaluate()` to hang during the venue scanning phase, after 10+ venues had been successfully scanned. Three increasingly aggressive timeout strategies failed:

1. `asyncio.wait_for(page.evaluate(...))` — timeout fires, but evaluate continues blocking
2. CDP `Runtime.evaluate` with native timeout — hangs identically because the browser isn't processing protocol messages  
3. Global 4-minute timeout on `build_runner_map()` — **succeeds** at the cost of abandoning the hung venue and any venues after it

Additionally, stale browser WebSocket connections from repeated process kills caused auth extraction failures — the browser's WS connection state diverges from what the adapter expects after unclean shutdowns. A fresh browser session is required for reliable runs, adding operational overhead.

These failures are a direct consequence of the architectural choice documented on 2026-04-11: bet365's 403 rejection of independent WS connections forced the adapter to pipe everything through the browser. The browser's JS context became load-bearing infrastructure — and infrastructure that the orchestrator cannot restart or recover without killing the entire browser session.

### Warmup Latency After Restart (2026-04-13)

A further reliability cost was observed on 2026-04-13: browser-mediated scrapers in the value betting scanner (Bet365 2.0, PointsBet AU) took **hours** to warm up after a restart. Following a full system restart the previous evening, NBA soft book coverage was only 3/8 by midnight but recovered to 5/8 by the next morning check. The warmup delay is not a bug but an inherent property of browser-mediated scraping: the browser must establish sessions, pass Cloudflare challenges, navigate through SPA initialization flows, and accumulate market subscriptions before data begins flowing. This adds a third failure dimension beyond JS hangs and stale sessions: **slow recovery time** means that even when problems are fixed promptly, the system operates in a degraded state for an extended period afterward. Operators should not panic if soft book counts are low immediately post-restart — the expected pattern is gradual recovery over hours, not immediate full coverage.

### Crash-Loop Quantification (2026-04-19)

The game scraper's Chrome crash-recovery investigation on 2026-04-19 quantified the reliability cost: **14 game scraper restarts** and approximately **50 direct scraper restarts** in a single day. This is not occasional flakiness — it is a systemic pattern where Chrome dies frequently due to EPIPE broken pipes from bet365 page timeouts, and Windows file locks (on both the Chrome profile directory and the subprocess JSON data file) compound the recovery difficulty. Each crash-restart cycle produces a window of stale data, and orphaned Chrome processes (15 found in one investigation) accumulate over extended operation. See [[concepts/game-scraper-chrome-crash-recovery]] for the auto-recovery and unique-profile-per-session fixes deployed.

The crash-loop evidence confirms the broader thesis: browser-mediated architectures don't just have occasional failure modes — they have **continuous reliability overhead** that requires active mitigation (auto-recovery, crash detection, orphan cleanup) to maintain acceptable uptime.

## Related Concepts

- [[concepts/playwright-evaluate-uncancellable]] - The specific uncancellable failure mode
- [[concepts/async-global-timeout-partial-results]] - The graceful degradation pattern adopted
- [[concepts/browser-mediated-websocket-streaming]] - The architecture that makes JS execution unavoidable
- [[concepts/bet365-racing-adapter-architecture]] - The adapter where these reliability issues manifest
- [[connections/anti-scraping-driven-architecture]] - The defenses that forced the browser-mediated architecture in the first place
- [[concepts/cdp-browser-data-interception]] - CDP-level access that also fails to work around JS context hangs
- [[concepts/game-scraper-chrome-crash-recovery]] - Crash-loop quantification: 14 restarts/day for game scraper, ~50 for direct scraper
