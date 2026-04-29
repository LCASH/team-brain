---
title: "CDP Stale Connection Poisoning"
aliases: [cdp-poisoning, stale-cdp, playwright-deadlock, fresh-chrome-pattern, ghost-cdp-session]
tags: [value-betting, bet365, chrome, cdp, reliability, playwright, operations]
sources:
  - "daily/lcash/2026-04-28.md"
created: 2026-04-28
updated: 2026-04-28
---

# CDP Stale Connection Poisoning

When a Playwright worker process dies (crash, kill, deploy), its CDP (Chrome DevTools Protocol) connection to Chrome becomes stale — a ghost session that the Chrome process still considers active. A new worker can successfully call `connect_over_cdp` to the same Chrome instance, but cannot reliably create or manage pages because the ghost session's state conflicts with the new connection. This manifests as Playwright deadlocks, inability to open new pages, and crash loops on worker restart. The solution is to always kill Chrome and relaunch it fresh on worker start, using a persistent profile directory to preserve login cookies across restarts.

## Key Points

- When a worker dies, its CDP connection becomes a ghost session that Chrome still tracks — new workers connecting to the same Chrome inherit poisoned state
- `connect_over_cdp` succeeds (connection established) but page operations fail (can't create/manage pages due to ghost session conflicts) — deceptively appears to work
- The fix is **always kill Chrome and relaunch fresh** on worker start rather than trying to reuse an existing Chrome instance
- Persistent profile directories (`bet365_nba_profile`, `bet365_mlb_profile`) preserve login cookies across Chrome restarts — no re-authentication needed after kill+relaunch
- `_kill_stale_chrome()` must match the exact profile path string in Chrome's command line; mismatches let stale Chrome processes survive
- ~30s setup cost per game page after fresh Chrome launch is acceptable given it only happens once per worker lifecycle

## Details

### The Poisoning Mechanism

Chrome's CDP debugging protocol maintains stateful sessions for each connected client. When a Playwright worker connects via `connect_over_cdp(f"http://localhost:{port}")`, Chrome allocates a session context that tracks page ownership, event subscriptions, and protocol state. When the worker process dies abruptly (SIGKILL, crash, SSH disconnect), the TCP connection drops but Chrome's internal session state is not immediately cleaned up.

A new worker connecting to the same Chrome instance via the same CDP endpoint inherits a Chrome process that still has the ghost session's state. The new connection can complete the CDP handshake — `connect_over_cdp` returns successfully — but when the worker attempts to create new pages or interact with existing ones, the operations fail or deadlock because Chrome's internal state management conflicts between the ghost session and the new session.

This is particularly insidious because the connection step succeeds. The worker's startup logs show a successful CDP connection, suggesting everything is healthy. The failure only manifests when the worker tries to actually use the connection — creating pages, navigating, or capturing network events. By this point, the worker may have already set `_started = True` and entered its poll loop, creating a state where it reports as "running" but cannot produce data.

### The Fresh Chrome Pattern

The fix eliminates the possibility of ghost sessions by always starting from a clean Chrome process:

1. **Kill existing Chrome**: `_kill_stale_chrome()` terminates any Chrome process whose command line contains the matching profile directory path (e.g., `bet365_nba_profile` or `bet365_mlb_profile`)
2. **Launch fresh Chrome**: Start a new Chrome instance with `--remote-debugging-port` and the persistent profile directory
3. **Connect via CDP**: The new worker connects to a Chrome process with zero prior sessions — guaranteed clean state

The persistent profile directory is the key enabler: it stores Chrome's cookie jar, local storage, and session data on disk. When Chrome is killed and relaunched with the same profile directory, the bet365 login session (stored in cookies) survives the restart. The worker gets a clean CDP state without requiring re-authentication.

### Profile Path Matching

`_kill_stale_chrome()` identifies stale Chrome processes by checking if the command line contains the profile directory path. This must be an exact substring match — if the path string differs between the kill function and the actual Chrome launch command (e.g., different path separators, trailing slashes, or absolute vs relative paths), the stale process survives and the new Chrome launch may fail due to profile directory locking.

On Windows, this matching is particularly fragile: `C:\Users\Dell\bet365_game_profile` vs `C:/Users/Dell/bet365_game_profile` vs `bet365_game_profile` (relative) are all different strings. The kill function must use the same path format as the Chrome launch command.

### Why Not Reuse Chrome?

The alternative approach — attaching to an existing Chrome instance and trying to manage its state — was attempted and abandoned because:

1. **Ghost sessions are invisible**: There is no CDP command to enumerate and close stale sessions. Chrome's internal session tracking is not exposed via the protocol.
2. **Page ownership is non-transferable**: Pages created by a previous worker's session cannot be reliably adopted by a new session. Attempting to interact with orphaned pages produces protocol errors.
3. **Recovery is non-deterministic**: Sometimes reattaching works (if the ghost session happened to be cleaned up by Chrome's GC), sometimes it doesn't. This non-determinism makes the approach unreliable for production use.

The fresh Chrome pattern trades ~30 seconds of startup time (Chrome launch + initial page creation) for guaranteed reliability. For scrapers that run continuously for hours or days, this is an excellent tradeoff.

### Interaction with Tab Cleanup

The fresh Chrome pattern eliminates tab accumulation at worker start — each fresh Chrome starts with zero tabs. Combined with the persistent-page architecture (see [[concepts/persistent-page-chrome-scraper-architecture]]) where tabs are managed explicitly via `_game_pages`, the system maintains a known, bounded set of tabs throughout operation. The previous pattern of accumulating 41-51+ stale tabs from dead workers is structurally impossible with fresh Chrome on every worker start.

## Related Concepts

- [[concepts/persistent-page-chrome-scraper-architecture]] - The persistent-page architecture that pairs with fresh Chrome: clean process start + persistent profile + explicit tab management
- [[concepts/game-scraper-chrome-crash-recovery]] - The auto-recovery mechanism (5 failures → stop/start) that now uses the fresh Chrome pattern instead of trying to reattach
- [[concepts/chrome-tab-leak-accumulation]] - Tab leaks from dead workers are eliminated by fresh Chrome; the root cause (unclosed pages from cycling architecture) is also addressed by persistent pages
- [[connections/browser-automation-reliability-cost]] - CDP poisoning adds a seventh reliability dimension: connection state corruption from worker lifecycle events
- [[concepts/bet365-auto-login-session-recovery]] - CAPTCHA blocks automated re-login; the persistent profile directory preserving cookies is essential because manual login cannot be triggered programmatically when CAPTCHA appears
- [[concepts/cdp-browser-data-interception]] - CDP is the data capture mechanism; stale connections corrupt the same protocol layer used for odds interception

## Sources

- [[daily/lcash/2026-04-28.md]] - NBA scraper crash-looping from stale CDP connections after worker death; 41 tabs accumulated on Chrome 9223; Playwright `connect_over_cdp` succeeds but page operations deadlock; fix: always kill Chrome + relaunch with persistent profile; `_kill_stale_chrome()` must match exact profile path; ~30s setup cost acceptable; applied to both NBA and MLB scrapers; 12 orphaned push workers compounded the issue (Sessions 08:16, 08:47, 09:18, 11:33)
