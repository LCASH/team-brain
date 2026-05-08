---
title: "Context-Level Init Script Bot Fingerprint"
aliases: [init-script-fingerprint, context-vs-page-injection, websocket-tostring-fingerprint, add-init-script-scope]
tags: [value-betting, bet365, anti-scraping, browser-automation, cdp, bot-detection]
sources:
  - "daily/lcash/2026-05-08.md"
created: 2026-05-08
updated: 2026-05-08
---

# Context-Level Init Script Bot Fingerprint

On 2026-05-08, lcash identified `ctx.add_init_script(INTERCEPTOR_JS)` as the smoking gun for bet365 bot detection during the MLB G-ID walk. The context-level script injection applied the WebSocket constructor wrapper (`window.__wsObjs`, `window.__lastSent` globals) to **ALL tabs** in the browser context — including walk tabs created for navigating individual market groups. This made every tab trivially fingerprintable: `window.WebSocket.toString()` no longer returns `[native code]` after the constructor reassignment, and the presence of `__wsObjs`/`__lastSent` globals is a bot signal. The fix scopes injection to page-level (`self._page.add_init_script`) so only the orchestrator's main page carries the interceptor; walk tabs spawn clean.

## Key Points

- `ctx.add_init_script()` (context-level) applies the script to **every new page** created in that browser context — including walk tabs, discovery tabs, and any temporary pages
- `self._page.add_init_script()` (page-level) applies only to the specific page — walk tabs created via `browser.new_page()` are clean
- `window.WebSocket.toString()` returns the wrapper function's source code after constructor reassignment, not `[native code]` — a trivial anti-bot fingerprint
- `window.__wsObjs` and `window.__lastSent` are non-standard globals that no legitimate page would have — their mere presence signals automation
- Benchmarking confirmed: **page-level inject + no decoy = best config** (76 PAs in 71.8s with 2-tab parallelism); context-level inject with same parallelism triggered rate-limiting
- This is distinct from the `WebSocket.prototype.send` wrapping detected in [[concepts/bet365-istrusted-synthetic-click-detection]] — this is about constructor replacement on non-target pages, not prototype modification

## Details

### The Scope Difference

Playwright's `add_init_script` can be called at two levels:

**Context-level** (`browser_context.add_init_script(js)`): The script is registered on the browser context and automatically injected into every new page created within that context. This includes pages created by `context.new_page()`, `browser.new_page()` (if using the default context), and any popups or iframes.

**Page-level** (`page.add_init_script(js)`): The script is registered only on the specific page object. Other pages in the same context are unaffected.

The bet365 scraper's interceptor JS wraps the WebSocket constructor to capture WS instances for subscription injection and auth token capture. This is necessary on the orchestrator's main page (which maintains the persistent WS connection to bet365's streaming infrastructure). It is harmful on walk tabs (which navigate to individual market groups to capture HTTP responses) because those tabs don't need WS access and the fingerprint marks them as automated.

### The Fingerprint Mechanism

Two fingerprint signals are created by the interceptor:

1. **`WebSocket.toString()` output change**: After `window.WebSocket = function(...) { ... }`, calling `WebSocket.toString()` returns the wrapper function's source code instead of `function WebSocket() { [native code] }`. bet365's anti-bot JS can detect this with a single `typeof WebSocket.toString().indexOf('[native code]')` check.

2. **Non-standard global variables**: `window.__wsObjs` (array of captured WS instances) and `window.__lastSent` (buffer of last 200 outgoing WS frames) are custom globals that no legitimate page would contain. Their presence in any tab's `window` object is sufficient to identify automation.

When context-level injection was used, walk tabs that navigated to bet365's market group pages carried both signals. bet365's page-level anti-bot checks detected the wrapper and responded by soft-blocking — returning empty response bodies for 16 of 26 G-ID navigations. With page-level injection, walk tabs were clean and 10/26 G-IDs returned data (the remaining failures were IP-level rate limiting, not fingerprint detection).

### The Benchmarking Results

Five configurations were tested to isolate the fingerprint effect:

| Config | Parallelism | Injection Scope | Decoy | PAs | Time |
|--------|------------|-----------------|-------|-----|------|
| 1 | 4 tabs | Context | Yes | Rate-limited | — |
| 2 | 4 tabs | Page | No | Rate-limited | — |
| 3 | 2 tabs | Context | No | ~40 PAs | ~70s |
| 4 | 2 tabs | Page | Yes | ~70 PAs | ~75s |
| **5** | **2 tabs** | **Page** | **No** | **76 PAs** | **71.8s** |

Config 5 (page-level, no decoy, 2-tab parallelism) was the best balance — the decoy wait added latency without benefit, and context-level injection reduced PAs even at the same parallelism level. This confirmed the fingerprint was a real detection vector, not just noise from rate limiting.

Note: This entire G-ID walk approach was subsequently replaced by the wizard-first architecture (see [[concepts/bet365-mlb-wizard-first-regression-fix]]), which uses a single request and avoids walk tabs entirely.

## Related Concepts

- [[concepts/bet365-istrusted-synthetic-click-detection]] - A different anti-bot detection vector (isTrusted on DOM events vs WebSocket.toString()); the `add_init_script` interceptor was confirmed NOT triggering bot detection when scoped to page-level in Session 20:23 of 2026-05-07
- [[concepts/websocket-constructor-injection]] - The constructor wrapping technique that the init_script implements; page-level scoping preserves its functionality on the target page while preventing fingerprint leakage to other tabs
- [[connections/anti-scraping-driven-architecture]] - A ninth detection dimension: context-level script pollution as a fingerprint vector, operating at the browser-context level rather than page, network, or protocol level
- [[concepts/bet365-headless-detection]] - Another browser fingerprint detection layer; context-level pollution and navigator.webdriver detection are complementary anti-bot signals

## Sources

- [[daily/lcash/2026-05-08.md]] - `ctx.add_init_script(INTERCEPTOR_JS)` identified as bot detection smoking gun — applies WS wrapper to ALL tabs including walk tabs; `WebSocket.toString()` no longer returns `[native code]` after reassignment; 5 configs benchmarked: page-level inject + no decoy = 76 PAs in 71.8s (best); context-level at same parallelism triggered more aggressive blocking; page-level scoping fix deployed (Session 14:29)
