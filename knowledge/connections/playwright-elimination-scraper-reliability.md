---
title: "Connection: Progressive Playwright Elimination Improves Scraper Reliability"
connects:
  - "concepts/playwright-node-pipe-crash-vector"
  - "concepts/persistent-page-chrome-scraper-architecture"
  - "concepts/cdp-stale-connection-poisoning"
  - "concepts/chrome-tab-leak-accumulation"
  - "concepts/game-scraper-chrome-crash-recovery"
sources:
  - "daily/lcash/2026-04-29.md"
  - "daily/lcash/2026-04-28.md"
created: 2026-04-29
updated: 2026-04-29
---

# Connection: Progressive Playwright Elimination Improves Scraper Reliability

## The Connection

The bet365 game scraper's reliability improved monotonically as Playwright was progressively eliminated from the critical path. Each architectural evolution removed one layer of Playwright involvement, eliminating a corresponding class of failure. The progression from "Playwright manages everything" to "Playwright only used for DOM-heavy discovery, raw CDP for everything else" represents a general principle: high-level browser automation frameworks add convenience but introduce failure modes that low-level CDP connections don't have.

## Key Insight

The non-obvious insight is that **Playwright's reliability cost is not in its abstraction quality but in its process architecture.** Playwright communicates with Chrome through a Node.js subprocess pipe — an additional process and an additional IPC channel that neither raw CDP (direct TCP WebSocket to Chrome) nor Chrome itself (native process) require. Every failure mode unique to Playwright traces back to this intermediary:

| Failure Mode | Root Cause | Playwright Layer | Raw CDP Equivalent |
|---|---|---|---|
| EPIPE crash | Node.js pipe overflow from CDP tab events | Node.js subprocess pipe | N/A (no pipe) |
| Tab leak amplification | Playwright page objects not cleaned up in `close()` | Page lifecycle management | Explicit `json/close/{id}` |
| Stale page contexts | Playwright's internal page registry out of sync | Session state tracking | Stateless per-request |
| ValueError in asyncio | Pipe error propagates through background callbacks | Event loop integration | Direct WebSocket messages |
| Disconnect/reconnect fragility | Playwright's connect_over_cdp session management | CDP connection lifecycle | Single WebSocket per page |

Raw CDP has its own complexity (manual JSON message construction, no CSS selector helpers, no auto-waiting), but its failure modes are all **network-level** (connection timeout, Chrome crash) rather than **framework-level** (pipe overflow, session state corruption). Network-level failures are visible, detectable, and recoverable; framework-level failures are often invisible and unrecoverable.

## The Progression

The scraper architecture evolved through four phases, each removing Playwright from one more operation:

**Phase 1 (pre-2026-04-28): Playwright manages everything.**
Playwright creates pages, navigates, intercepts responses, manages tab lifecycle. EPIPE crashes every 1-10 minutes from pipe overflow. Tab leaks accumulate to 51+. Auto-recovery restarts Playwright, which re-creates the same failure conditions.

**Phase 2 (2026-04-28): Persistent pages replace cycling.**
`_game_pages` dict manages tab identity, Playwright still creates and controls pages. Tab leaks reduced (explicit management), but EPIPE crashes persist because Playwright's pipe is still active during page creation.

**Phase 3 (2026-04-28): Fresh Chrome + persistent profile.**
Chrome is killed and relaunched on each worker start, eliminating stale CDP connections from dead workers. Playwright connects to a known-clean Chrome state. Crash recovery improves, but EPIPE still occurs during normal operation.

**Phase 4 (2026-04-29): Raw CDP for game pages, Playwright only for discovery.**
Playwright disconnects after `_discover_games()`, raw CDP WebSocket manages all game page lifecycle. EPIPE eliminated — the pipe is only active during the brief discovery phase when no tabs are being created. Tab count matches expected (`5/4→6/6`), 2,060 odds streaming, zero crashes on first startup.

Each phase's improvement was not additive but multiplicative: removing Playwright from one operation eliminated an entire class of failures, making the remaining Playwright-dependent operations more reliable (fewer competing pipe traffic sources).

## Evidence

The before/after metrics from 2026-04-29 demonstrate the compound effect:

- **Phase 1**: `tabs=21/4` (massive leak), 5-10 restart cycles per startup attempt
- **Phase 4**: `tabs=5/4→6/6` (perfect match), single-cycle startup, 2,060 odds streaming, zero crashes

The crash loop severity declined correspondingly: 14 game scraper restarts/day (Phase 1, measured 2026-04-19), reduced to zero crashes over the monitoring window in Phase 4.

MLB remains at Phase 2-3 (Playwright-managed pages, pending raw CDP migration). Its vulnerability is higher: 3 Playwright pages per game × 15 games = 45 potential pages, far exceeding the ~3-page pipe overflow threshold. The Phase 4 migration for MLB will consolidate to 1 CDP tab per game using hash navigation for sub-tab switching.

## The General Principle

For browser automation tasks where reliability matters more than development speed: **use the lowest-level tool that provides the needed functionality.** Playwright's CSS selectors and auto-waiting are valuable for DOM interaction (discovery, form filling, element clicking). Raw CDP is sufficient and more reliable for page navigation, response interception, and tab management. The hybrid approach — Playwright for complex DOM work, raw CDP for everything else — captures the benefits of both without the reliability cost of using Playwright where it isn't needed.

## Related Concepts

- [[concepts/playwright-node-pipe-crash-vector]] - The root cause analysis that drove Phase 4: Node.js pipe overflow from CDP tab creation
- [[concepts/persistent-page-chrome-scraper-architecture]] - Phase 2-3: explicit tab management that reduced (but didn't eliminate) Playwright failures
- [[concepts/cdp-stale-connection-poisoning]] - Phase 3: fresh Chrome pattern that eliminated stale connection corruption
- [[concepts/chrome-tab-leak-accumulation]] - Phase 1-2: tab leaks from Playwright page objects not cleaned up
- [[concepts/game-scraper-chrome-crash-recovery]] - The auto-recovery mechanism that benefits from each phase's stability improvement
- [[connections/chrome-lifecycle-management-pattern]] - The unified lifecycle pattern that Phase 4 completes: fresh Chrome + persistent profile + explicit pages + raw CDP
- [[connections/browser-automation-reliability-cost]] - The broader reliability cost analysis; each phase progressively reduced the cost

```

