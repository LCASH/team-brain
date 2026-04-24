---
title: "bet365 Shared Chrome Single-Session Enforcement"
aliases: [shared-chrome, single-session-per-account, chrome-port-9223, bet365-session-conflict]
tags: [bet365, scraping, operations, chrome, architecture, value-betting]
sources:
  - "daily/lcash/2026-04-24.md"
created: 2026-04-24
updated: 2026-04-24
---

# bet365 Shared Chrome Single-Session Enforcement

bet365 enforces a single active session per account — logging in on a second Chrome instance silently invalidates the first. On 2026-04-24, this caused persistent login failures: the NBA Chrome (port 9223) kept losing its session because the MLB Chrome (port 9224) was already logged in. The fix was consolidating both scrapers onto a single shared Chrome instance on port 9223, with the MLB scraper updated to attach to the same Chrome rather than maintaining its own instance.

## Key Points

- bet365 enforces **single-session-per-account**: two Chrome profiles logged into the same account = second one silently rejects the first
- Previously: NBA Chrome on port 9223, MLB Chrome on port 9224 — both logged in separately, creating constant session conflicts
- Fix: **shared Chrome on port 9223** — MLB scraper updated to attach to 9223 instead of running its own Chrome; port 9224 no longer used
- The auto-login script (see [[concepts/bet365-auto-login-session-recovery]]) now only targets port 9223 — one login serves both scrapers
- `_kill_stale_chrome` in MLB scraper won't kill the shared Chrome because `self._chrome_proc = None` when attaching to an existing instance
- This discovery refines the earlier finding that bet365 limits one session per cookie set (see [[concepts/bet365-size-gate-stale-odds]]) — it is per-account, not per-cookie

## Details

### The Session Conflict

The value betting scanner ran two separate Chrome instances for bet365 scraping: NBA on port 9223 and MLB on port 9224. Each instance was launched with `--remote-debugging-port` and logged into bet365 independently. When both instances were logged in simultaneously with the same bet365 account, bet365's session management would silently invalidate one of them — typically the one logged in first.

This produced a confusing overnight failure pattern: both Chrome sessions expired overnight (as documented in [[concepts/bet365-auto-login-session-recovery]]), and when the auto-login script attempted to restore them, it would succeed on one port but the login on the second port would silently kill the first port's session. The operator would see the second port logged in but the first port in a "not logged in" state, with no error message from bet365.

The root cause was discovered on 2026-04-24 when lcash noticed that the NBA Chrome login kept failing despite the auto-login script working correctly — the MLB Chrome was already logged in and holding the session. The user's correction — "never assume the system is good; check the NBA Chrome says logged in" — drove the investigation that uncovered the single-session enforcement.

### The Shared Chrome Architecture

The fix eliminates the session conflict entirely by running both scrapers against a single Chrome instance:

- **Port 9223**: Shared Chrome, logged into bet365 once, serves both NBA and MLB scrapers
- **Port 9224**: Killed and no longer used
- **MLB scraper**: Updated to attach to port 9223 instead of launching/managing its own Chrome
- **Auto-login**: Only targets port 9223 — one successful login authenticates both scrapers

The MLB scraper's `_kill_stale_chrome` method was modified to be safe with shared Chrome: when the scraper attaches to an existing Chrome instance rather than launching one, `self._chrome_proc = None`, so the stale-chrome cleanup logic skips the kill step. This prevents the MLB scraper from accidentally terminating the shared Chrome that the NBA scraper is also using.

### Operational Impact

The shared Chrome architecture reduces operational complexity:
- **One login instead of two** — halves the authentication maintenance burden
- **No session conflicts** — eliminates the class of "works on one port, dies on the other" failures
- **Simpler monitoring** — one Chrome health check instead of two
- **Lower resource usage** — one Chrome process consuming ~400MB instead of two

### Relationship to Cookie Injection Failure

On 2026-04-23, lcash discovered that injecting the same cookies into both Chrome instances (port 9223 and 9224) resulted in only the NBA Chrome accepting the session (see [[concepts/bet365-size-gate-stale-odds]]). The 2026-04-24 finding explains why: bet365 enforces single-session-per-account at the server level, not just per-cookie-set. Even with valid cookies, only one active session is permitted. The shared Chrome architecture makes this a non-issue by having only one session.

## Related Concepts

- [[concepts/bet365-auto-login-session-recovery]] - The auto-login script now targets only port 9223; session conflicts were the cause of login failures that motivated the shared Chrome architecture
- [[concepts/bet365-size-gate-stale-odds]] - Earlier discovery that cookie injection between two Chrome instances failed; the single-session-per-account enforcement is the root cause
- [[concepts/bet365-headless-detection]] - Shared Chrome must still run in headed mode; the consolidation doesn't change the headless detection constraint
- [[concepts/mlb-parallel-scraper-workers]] - The MLB parallel workers (N=3 Chrome pages) now operate within the shared Chrome instance, not a separate one
- [[connections/browser-automation-reliability-cost]] - Shared Chrome reduces one reliability dimension (session conflicts) but introduces a new single-point-of-failure: if the shared Chrome crashes, both scrapers are affected

## Sources

- [[daily/lcash/2026-04-24.md]] - bet365 blocks simultaneous logins from same account on two browsers; NBA Chrome login failing because MLB Chrome already logged in; consolidated to shared Chrome on port 9223; MLB scraper updated to attach to 9223; port 9224 killed; `_kill_stale_chrome` safe with `self._chrome_proc = None`; user corrected: "never assume the system is good — check every component" (Session 09:10)
