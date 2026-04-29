---
title: "Connection: Chrome Lifecycle Management as Reliability Foundation"
connects:
  - "concepts/cdp-stale-connection-poisoning"
  - "concepts/chrome-tab-leak-accumulation"
  - "concepts/persistent-page-chrome-scraper-architecture"
  - "concepts/game-scraper-chrome-crash-recovery"
sources:
  - "daily/lcash/2026-04-28.md"
created: 2026-04-28
updated: 2026-04-28
---

# Connection: Chrome Lifecycle Management as Reliability Foundation

## The Connection

Four independently discovered Chrome reliability problems — stale CDP connections from dead workers, tab accumulation from cycling architectures, EPIPE crash-loop recovery, and all-or-nothing setup blocking — were all resolved on 2026-04-28 by adopting a unified Chrome lifecycle management pattern: "always fresh Chrome + persistent profile + explicit page management." This pattern is not a single fix but a coherent reliability philosophy that addresses the root cause shared by all four problems: Chrome state corruption from unmanaged process and connection lifecycles.

## Key Insight

The non-obvious insight is that these four problems — which appeared at different times, manifested differently, and were initially debugged independently — share a single root cause: **Chrome process state drifts from the expected state when worker lifecycle events (crashes, kills, deploys, restarts) are not matched by corresponding Chrome lifecycle management.** Each problem is a different symptom of the same underlying gap:

| Problem | When Chrome State Drifts | Symptom |
|---------|------------------------|---------|
| CDP stale connections | Worker dies → ghost CDP session persists | New worker connects but can't manage pages; Playwright deadlock |
| Tab accumulation | Pages created but never closed across cycles | 30-51+ tabs → Chrome overwhelmed → EPIPE crashes |
| EPIPE crash recovery | Chrome pipe breaks → profile dir locked | Scraper serves stale cached data indefinitely |
| All-or-nothing setup | One page hangs during blocking setup | Entire worker killed, zero odds from any game |

The unified pattern resolves all four by managing Chrome state explicitly at each lifecycle boundary:

1. **Worker start**: Kill existing Chrome → launch fresh Chrome with persistent profile dir → connect via CDP. Eliminates ghost sessions and inherited tabs.
2. **During operation**: Persistent pages in an explicit `_game_pages` dict — bounded, managed set instead of create-per-cycle accumulation. Eliminates tab leaks.
3. **Per-game fault tolerance**: Non-blocking setup with `_started = True` before all pages open. One hung page affects only that game. Eliminates all-or-nothing blocking.
4. **Worker crash**: Fresh Chrome on next worker start means the crash doesn't corrupt the next session. Crash recovery is structurally clean.

The persistent profile directory is the key enabler that makes "always kill Chrome" viable — it preserves login cookies and session data across Chrome restarts, so the cost of a fresh Chrome is ~30 seconds of startup, not a full re-authentication (unless CAPTCHA triggers, which still requires manual intervention — see [[concepts/bet365-auto-login-session-recovery]]).

## Evidence

On 2026-04-28, all four problems manifested simultaneously during a single debugging session:

- **08:16**: MLB rewrite from `_WorkerPage` cycling to persistent-page architecture — addresses tab accumulation and all-or-nothing setup
- **08:47**: NBA 41 tabs accumulated, EPIPE crash, worker unable to scrape since 22:03 — confirmed tab leak from `_discover_games()` creating unclosed pages
- **09:18**: NBA crash-looping from stale CDP connections after previous worker death + 12 orphaned push workers overwhelming VPS — CDP poisoning + process orphan accumulation
- **11:33**: NBA `_open_game_pages()` blocked until all 8 games set up; one hung page killed worker — applied non-blocking setup

Each fix was applied in isolation, but the combined result is a coherent lifecycle management pattern. The "always fresh Chrome" decision was the architectural catalyst — once the team committed to killing Chrome on every worker start, the other pieces (persistent profile, persistent pages, non-blocking setup) followed naturally because the previous architecture's assumptions (reuse Chrome, attach to existing sessions) were invalidated.

## Architectural Pattern

The pattern can be stated as three rules:

1. **Never reuse a Chrome process across worker lifecycles** — always kill and relaunch with a persistent profile
2. **Never create pages implicitly** — all pages are in an explicit, managed collection (`_game_pages`) with sport-scoped cleanup by event ID
3. **Never block the worker on page setup** — serve partial odds from completed pages while remaining pages initialize in the background

These rules trade startup speed (30s Chrome launch + ~2min per game page) for guaranteed reliability. For scrapers that run for hours between restarts, the startup cost is negligible.

## Related Concepts

- [[concepts/cdp-stale-connection-poisoning]] - The ghost CDP session problem that the "always fresh Chrome" rule solves
- [[concepts/chrome-tab-leak-accumulation]] - The tab accumulation problem that persistent-page management and fresh Chrome solve
- [[concepts/persistent-page-chrome-scraper-architecture]] - The explicit page management architecture that replaces implicit page creation
- [[concepts/game-scraper-chrome-crash-recovery]] - The crash recovery mechanism that benefits from guaranteed-clean Chrome state on restart
- [[connections/browser-automation-reliability-cost]] - The broader reliability cost analysis that this pattern partially mitigates; CDP poisoning adds a seventh reliability dimension resolved by this pattern
- [[concepts/push-worker-orphan-accumulation]] - A parallel lifecycle management problem in the push layer; the same "always clean start" philosophy applies
