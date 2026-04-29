---
title: "Playwright Node.js Pipe Crash Vector"
aliases: [playwright-epipe, node-pipe-overflow, playwright-cdp-conflict, raw-cdp-websocket, hybrid-discovery-architecture]
tags: [value-betting, bet365, playwright, cdp, chrome, reliability, architecture]
sources:
  - "daily/lcash/2026-04-29.md"
created: 2026-04-29
updated: 2026-04-29
---

# Playwright Node.js Pipe Crash Vector

The root cause of chronic EPIPE crashes in the bet365 game scrapers was identified on 2026-04-29: Playwright's internal Node.js subprocess pipe overflows when new Chrome tabs are created via CDP HTTP endpoints while Playwright is still connected to the same Chrome instance. The pipe traffic from Playwright's event monitoring plus CDP HTTP tab lifecycle events exceeds the Node.js subprocess pipe buffer, producing `ValueError: I/O operation on closed pipe` errors that propagate through asyncio background callbacks — uncatchable by normal `try/except` or `warnings.filterwarnings`. The solution is a hybrid architecture: Playwright for DOM-heavy discovery operations, raw CDP WebSocket (`websockets` library, Python → Chrome over TCP) for all game page management.

## Key Points

- Playwright communicates with Chrome via a Node.js subprocess pipe; CDP HTTP tab creation generates additional pipe traffic that overflows the buffer once ~3+ pages exist simultaneously
- The `ValueError: I/O operation on closed pipe` propagates through asyncio event loop background callbacks — `try/except`, `warnings.filterwarnings`, and `loop.set_exception_handler()` can suppress but not prevent the underlying pipe death
- Raw CDP WebSocket (`websockets` library) connects Python directly to Chrome via TCP, completely bypassing the Node.js subprocess pipe — eliminates the crash vector entirely
- Hybrid architecture: Playwright connects for `_discover_games()` (needs DOM interaction for sidebar/game list parsing), disconnects before game pages open, raw CDP handles all game page lifecycle
- Before/after: Playwright approach leaked to `tabs=21/4` with 5-10 restart cycles; raw CDP achieved `tabs=5/4→6/6` (perfect match), 2,060 odds streaming, zero crashes on first startup
- MLB migration deferred to bake NBA overnight; MLB is even more vulnerable with 3 Playwright pages/game (I0, I2, I5 tabs) × 15 games = 45 potential pages

## Details

### The Pipe Overflow Mechanism

Playwright Python automates Chrome by spawning a Node.js subprocess that manages the CDP (Chrome DevTools Protocol) connection. All communication between Python and Chrome flows through this subprocess's stdin/stdout pipes. When Playwright monitors Chrome events (page loads, network activity, DOM changes), it generates continuous pipe traffic. Simultaneously, when new tabs are created via CDP HTTP endpoints (`http://localhost:9223/json/new`), Chrome sends lifecycle events about the new pages through the same pipe.

The conflict occurs when both traffic streams exceed the pipe's buffer capacity. Node.js pipes have finite buffers (typically 64KB on most systems), and when the buffer fills faster than Node.js can drain it, the pipe breaks. The broken pipe manifests as an EPIPE error in the Node.js process, which then surfaces in Python as `ValueError: I/O operation on closed pipe`.

This error does NOT propagate through normal Python exception handling. It fires in asyncio background callbacks — internal event loop machinery that processes Playwright's asynchronous responses. Python's `try/except` blocks in user code never see it because the error originates in the event loop's callback dispatcher, not in a user-awaitable coroutine. Even `loop.set_exception_handler()` — a custom asyncio exception handler — can only log and suppress the error after the pipe is already dead, not prevent the crash.

### The Raw CDP WebSocket Solution

Raw CDP WebSocket connections bypass the Node.js subprocess entirely. Python opens a direct TCP WebSocket to Chrome's debugging endpoint (e.g., `ws://localhost:9223/devtools/page/{id}`), communicates CDP commands and receives events over this connection, and manages all tab lifecycle operations via the CDP HTTP API (`/json/new`, `/json/close/{id}`). No Node.js process is involved — the crash vector is structurally eliminated.

The key CDP operations for game page management:
1. **Tab creation**: HTTP GET to `http://localhost:9223/json/new` returns the new page's WebSocket URL
2. **Navigation**: Send `Page.navigate` command over the page's WebSocket
3. **Response interception**: Enable `Network.enable` + listen for `Network.responseReceived` events to capture API responses
4. **Response body extraction**: `Network.getResponseBody` to read captured API response content
5. **Tab closure**: HTTP GET to `http://localhost:9223/json/close/{id}`

These operations provide everything needed for odds scraping without Playwright's high-level abstractions.

### The Hybrid Architecture

Playwright is still needed for one operation: `_discover_games()`. Game discovery requires parsing the bet365 sidebar DOM, identifying game links, and extracting event IDs — operations that benefit from Playwright's CSS selector and DOM traversal APIs. Raw CDP can perform DOM queries via `Runtime.evaluate`, but the code complexity is significantly higher.

The hybrid architecture manages this with a connect/disconnect cycle:

1. **Discovery phase**: `_reconnect_playwright()` connects Playwright to the existing Chrome instance
2. Playwright navigates to the games list, parses the sidebar DOM, extracts event IDs
3. **Pre-game-setup**: `_disconnect_playwright()` disconnects Playwright from Chrome
4. **Game page management**: Raw CDP opens per-game tabs, navigates, intercepts API responses
5. **Rediscovery** (every 30 min): reconnect Playwright → discover new games → disconnect → open new CDP tabs

The critical constraint is that Playwright must be disconnected BEFORE any CDP game tabs are created. If Playwright is still connected when tabs open, the pipe overflow occurs. The `_disconnect_playwright` / `_reconnect_playwright` pattern ensures Playwright's pipe is only active during the brief discovery phase (~5-10 seconds) when no tabs are being created.

### MLB Vulnerability

The MLB scraper is more vulnerable than NBA because it uses 3 Playwright pages per game (I0 for main props, I2 for batter props, I5 for pitcher props). With 15 MLB games, this creates up to 45 Playwright-managed pages — far exceeding the ~3-page threshold where pipe overflow begins. The raw CDP migration for MLB was designed but deployment was deferred to let the NBA changes bake overnight first.

MLB's migration plan consolidates the 3 pages per game into 1 CDP WebSocket tab using hash navigation (`window.location.hash`) to cycle between I0/I2/I5 views — the same hash-nav approach documented in [[concepts/spa-navigation-state-api-access]]. This reduces MLB's page count from 45 to 15 (one per game), all managed via raw CDP.

### Custom Exception Handler as Interim Fix

Before the full raw CDP migration, a custom asyncio exception handler was deployed as a stopgap:

```python
loop.set_exception_handler(lambda loop, ctx: None)  # suppress pipe errors
```

This extended the crash interval from ~1 minute to ~4 minutes by preventing the `ValueError` from killing the event loop. However, it only delays the inevitable — once the Node.js pipe is dead, Playwright can no longer communicate with Chrome, and subsequent operations fail silently. The raw CDP migration is the root cause fix; the exception handler was a pragmatic interim while the migration was being built.

### Silent Post-Startup Server Death

After the raw CDP migration achieved clean startup (6 tabs, 2,060 odds), the server died silently ~42 minutes later with no error in logs. The game setup via raw CDP was confirmed stable — the crash happened post-setup, not during. The cause is under investigation; candidates include a lingering Playwright process from the discovery reconnect cycle or an OS-level watchdog interaction.

## Related Concepts

- [[concepts/persistent-page-chrome-scraper-architecture]] - The persistent-page architecture that pairs with raw CDP: each game gets a dedicated tab managed via CDP WebSocket instead of Playwright
- [[concepts/cdp-stale-connection-poisoning]] - A different CDP-level failure mode: ghost sessions from dead workers. Raw CDP migration solves pipe crashes but not connection state poisoning
- [[concepts/game-scraper-chrome-crash-recovery]] - The auto-recovery mechanism (5 failures → stop/start) that now benefits from raw CDP: recovery starts a clean Chrome + raw CDP tabs instead of relaunching Playwright
- [[concepts/chrome-tab-leak-accumulation]] - The `_setup_task` leak was amplified by Playwright's pipe overflow — each leaked tab added pipe traffic that accelerated the crash
- [[connections/browser-automation-reliability-cost]] - Raw CDP migration eliminates the sixth reliability dimension (Playwright pipe crashes) while the others (JS hangs, stale sessions, warmup, crash loops, session expiry) remain
- [[connections/chrome-lifecycle-management-pattern]] - The unified lifecycle pattern (fresh Chrome + persistent profile + explicit pages) now includes "raw CDP for page management" as a fourth rule
- [[concepts/cdp-browser-data-interception]] - CDP response interception (`Network.responseReceived` + `Network.getResponseBody`) is the same technique used here, now without the Playwright intermediary

## Sources

- [[daily/lcash/2026-04-29.md]] - Root cause identified: Playwright Node.js subprocess pipe overflow from CDP tab creation; raw CDP WebSocket via `websockets` library eliminates crash vector; hybrid architecture: Playwright for discovery, raw CDP for game pages; before/after: tabs=21/4 with crashes → tabs=5/4→6/6 with zero crashes and 2,060 odds (Sessions 11:32, 13:13, 13:30). Custom asyncio exception handler as interim: extended crash interval 1min→4min; MLB 45 pages most vulnerable; server silent death ~42min post-startup under investigation (Sessions 13:13, 13:30). `Page.navigate` fires `Network.responseReceived` but `Page.reload` alone doesn't (needs `Page.enable`); tab count matching confirmed as health indicator (Session 11:32)
