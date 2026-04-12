---
title: "Playwright Evaluate Is Uncancellable"
aliases: [playwright-evaluate-hang, page-evaluate-blocking, asyncio-wait-for-playwright]
tags: [playwright, asyncio, browser-automation, gotcha, python]
sources:
  - "daily/lcash/2026-04-12.md"
created: 2026-04-12
updated: 2026-04-12
---

# Playwright Evaluate Is Uncancellable

Playwright Python's `page.evaluate()` blocks the asyncio event loop when the browser's JavaScript context becomes unresponsive. Wrapping it in `asyncio.wait_for()` does not cancel the call — the coroutine continues to block even after the timeout fires. CDP-level `Runtime.evaluate` via `cdp.send()` exhibits the same behavior.

## Key Points

- `page.evaluate()` in Playwright Python is not cancellable by `asyncio.wait_for` — the timeout exception fires but the underlying call continues blocking
- CDP `Runtime.evaluate` via `cdp.send()` hangs identically — it is not a viable workaround for the same problem
- The root cause is that the browser's JS context itself is unresponsive (stale page state, SPA degradation), not a Playwright bug per se
- This was discovered when the Toowoomba venue consistently caused hangs during bet365 adapter venue scanning after 10+ venues
- The only reliable mitigation is a global timeout around the entire operation, not per-call timeouts

## Details

### Discovery

During bet365 racing adapter development, lcash found that scanning certain venues (consistently Toowoomba) caused `page.evaluate()` to hang indefinitely. The adapter calls `page.evaluate()` to extract data from the SPA and to inject WebSocket subscription messages. When the browser's JavaScript context becomes unresponsive — likely due to SPA state degradation after navigating through 10+ venues — the evaluate call never returns.

The natural approach in asyncio Python is to wrap the call in `asyncio.wait_for(page.evaluate(...), timeout=30)`. This does raise `asyncio.TimeoutError` after the specified duration, but the underlying Playwright RPC call is not actually cancelled. The coroutine remains blocked in Playwright's internal event loop integration, meaning resources are not freed and subsequent evaluate calls on the same page may also hang. This behavior differs from typical asyncio coroutines that respect cancellation.

### Why CDP Doesn't Help

The next attempted workaround was to bypass Playwright's high-level API and use CDP directly via `cdp.send('Runtime.evaluate', {'expression': '...'})`. CDP's `Runtime.evaluate` accepts a `timeout` parameter. However, when the browser context is truly unresponsive, the CDP call hangs in the same way — the browser is not processing any protocol messages, so the timeout parameter in the request is never evaluated by the browser.

### The Fundamental Issue

The problem is architectural: both Playwright's `page.evaluate()` and CDP's `Runtime.evaluate` send a message to the browser and wait for a response. When the browser's JS execution context is blocked or stale, no response comes. The Python-side timeout can raise an exception, but it cannot force the browser to respond or release the connection. This makes per-call timeouts unreliable for any operation that depends on browser-side JS execution.

### Practical Impact

In the bet365 adapter, this means that a single unresponsive venue can block the entire venue scanning phase indefinitely. The solution adopted was a global timeout on the entire `build_runner_map()` phase (4 minutes), with mutable containers passed as parameters so that venues scanned before the hang are preserved. See [[concepts/async-global-timeout-partial-results]] for the pattern.

## Related Concepts

- [[concepts/async-global-timeout-partial-results]] - The pattern adopted to work around this limitation
- [[concepts/bet365-racing-adapter-architecture]] - The adapter where this was discovered during venue scanning
- [[concepts/cdp-browser-data-interception]] - CDP-level access that also fails to work around this issue
- [[concepts/browser-mediated-websocket-streaming]] - The browser-mediated architecture that makes JS evaluation unavoidable

## Sources

- [[daily/lcash/2026-04-12.md]] - Discovery during Toowoomba venue hang: `asyncio.wait_for` ineffective on `page.evaluate()`, CDP `Runtime.evaluate` hangs identically, global timeout adopted as solution (Session 15:37)
