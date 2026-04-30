---
title: "bet365 v3 Scraper Capability Test Ladder"
aliases: [capability-ladder, v3-test-ladder, scraper-validation, 13-capability-test, diversion-tab-shield]
tags: [bet365, scraping, testing, methodology, validation, value-betting]
sources:
  - "daily/lcash/2026-04-30.md"
created: 2026-04-30
updated: 2026-04-30
---

# bet365 v3 Scraper Capability Test Ladder

A systematic 13-capability validation methodology for the bet365 scraper rewrite (v3), testing each architectural layer in isolation before progressing to integration. The ladder produced 11/12 full passes and 1 conditional pass across capabilities ranging from single-game launch through full orchestrator stability, concurrent coordination, error recovery, and production parity. The critical finding was that **concurrency=3 is the sweet spot** — full parallel scraping (15 concurrent navigations) triggered bet365's anti-scraping throttling, cutting odds counts from 12,401 to 6,145 (50% data loss), while a bounded semaphore restored full data quality at 11,018 odds. A **diversion tab + partial-result shield** improved stability from -50% cliff-drop to -3.3% gradual drift.

## Key Points

- 13 capabilities tested sequentially: single-game launch → multi-game detection → odds parsing → tab management → rate limiting → data persistence → orchestrator stability → concurrent coordination → graceful shutdown → refresh cycle → error recovery → parity test
- **11/12 passed, 1 conditional** — parity test had 27% dupe rate from alt-line CO milestone expansion and stale 2-game snapshot
- Concurrency=3 fix was the pivotal discovery: full parallel (15 games via `asyncio.gather`) → 50% odds loss; bounded semaphore (sem=3) → 11,018 odds with zero drift over 704 seconds
- **Diversion tab** simulates natural browsing by cycling to non-sport pages; **partial-result shield** rejects degraded responses (e.g., 67% of prior odds count) and retains cached data
- Error recovery validated 3 scenarios: (A) kill mid-setup → clean teardown, 0 orphans; (B) dead tab → 3-strike at 30s intervals → auto-close; (C) orphan injection → cleanup sweep catches and removes
- 3-strike close scoped to **zero-data scrapers only** — scrapers with prior odds experiencing temporary blips (bet365 suspensions) should not be killed; skip games >6h from tip-off

## Details

### The Capability Ladder

The ladder follows a bottom-up validation approach: each capability builds on the previous, so a failure at capability N means capabilities N+1 through 13 cannot be trusted. This prevents the common integration testing failure where a working end-to-end demo masks underlying instability.

| # | Capability | Result | Key Finding |
|---|-----------|--------|-------------|
| 1 | Single-game scraper launch | **PASS** | Core scrape loop starts, navigates, captures API response |
| 2 | Multi-game slate detection | **PASS** | Games-list parsing discovers full daily slate |
| 3 | Odds parsing accuracy | **PASS** | All market types (CO milestones, O/U, named options) parsed correctly |
| 4 | Browser tab management | **PASS** | Tabs open/close cleanly with no leaks |
| 5 | Rate limiting / throttle | **PASS** | Respects bet365's concurrent navigation limits |
| 6 | Data persistence | **PASS** | Odds written to shared JSON file correctly |
| 7 | Full orchestrator stability | **PASS** | 15 games, 11,018 odds, 0% drift, 0 tab leaks (704s run) |
| 8 | Concurrent scraper coordination | **PASS** | Bounded semaphore (sem=3) prevents throttling |
| 9 | Graceful shutdown | **PASS** | SIGINT/SIGTERM → clean tab closure, 0 orphans |
| 10 | Refresh cycle accuracy | **PASS** | Odds refresh on schedule, no stale data served |
| 11 | Error recovery (A/B/C) | **PASS** | All 3 fault injection scenarios passed |
| 12 | Parity test | **CONDITIONAL** | 27% dupe rate + stale snapshot; per-game yield extrapolates correctly |

### Diversion Tab + Partial-Result Shield

Two anti-detection measures were validated during run 3:

**Diversion tab**: A background tab that periodically navigates to non-sport pages (e.g., bet365 homepage or soccer) to simulate natural multi-page browsing patterns. Combined with cross-sport activity from other running servers (NBA, NRL, AFL), this provides behavioral camouflage that reduces bet365's bot-detection scoring. Stability improved from -50% cliff-drop (run 1, no diversion) to -3.3% gradual drift (run 3, diversion + shield). The odds count stabilized at 5,652 for 300+ seconds — a plateau indicating effective mitigation.

However, the diversion tab was later **disabled on the mini PC** because it triggered Playwright EPIPE crashes from rapid concurrent pipe activity on Node v24/Windows (see [[concepts/playwright-node-pipe-crash-vector]]). The other sport servers provide sufficient cross-sport activity naturally, making the dedicated diversion tab unnecessary in the multi-server production environment.

**Partial-result shield**: When a game page returns significantly fewer odds than its previous capture, the shield rejects the response and retains cached data. During testing, DET@ATL returned 605 records versus a prior 904 (67%, below the 70% floor), and the shield correctly kept the prior data. This prevents bet365's occasional degraded responses — from CDN cache inconsistencies, temporary throttling, or SPA state issues — from overwriting good cached data.

### Error Recovery Scenarios (Capability 11)

Three fault-injection scenarios validated the scraper's resilience:

**Scenario A — Kill mid-setup**: Terminate the scraper process while game pages are being initialized. Result: clean teardown with 0 orphaned Chrome tabs. The `_game_pages` dict ensures all pages are accounted for even during abrupt termination.

**Scenario B — Tab death (3-strike detection)**: When a game page becomes unresponsive (e.g., "Sorry, page closed" from suspended or distant future games), the scraper detects failure on three consecutive checks at 30-second intervals, then auto-closes the dead tab. This was refined post-testing: 3-strike close should only apply to scrapers that **never had data** — scrapers with prior odds experiencing temporary blips (bet365 game suspensions, CDN issues) are more likely in a transient state and should be given longer recovery windows.

**Scenario C — Orphan cleanup**: Two orphan tabs (pages not tracked by any scraper) were injected and the cleanup sweep found and closed both within seconds. This prevents tab accumulation from edge cases where scraper tracking and Chrome page state diverge.

### Parity Test — Conditional Pass

The parity test compared v3 output against a known production baseline. Two issues prevented full pass:

1. **Stale snapshot**: Only 2 of 15 games in the comparison snapshot (captured from a stale April 2 data file). A fresh 15-game concurrent capture is needed.
2. **27% duplicate rate**: The same `(player, prop, side, line)` tuple appears multiple times when alt-line CO milestone data is captured across subtab refreshes. This is a dedup logic fix (deduplicate on `(player, prop, side, line, fixture)` before persisting), not a data quality problem.

Per-game yield (811-875 odds/game) extrapolates to ~12,645 total, consistent with the 11,018 observed during the stability run. All 9 player prop market types represented, all 8 required fields populated in every record. The core scraping is solid; only the dedup and fresh-snapshot follow-ups remain.

### Skip Games >6 Hours Away

Games more than 6 hours from tip-off often have no player prop data on bet365 (lines aren't posted yet). Scraping them wastes refresh cycles on pages that return zero odds. The fix defers these games to the next rediscovery cycle rather than occupying scraper slots with empty pages, and pairs with the 3-strike scoping: zero-data scrapers for distant games are closed quickly while scrapers for games with data are protected.

## Related Concepts

- [[concepts/mlb-parallel-scraper-workers]] - The MLB scraper architecture validated by this ladder; concurrent navigation rate-limiting (sem=3) discovered during Cap 8
- [[connections/anti-scraping-driven-architecture]] - The defense stack that the diversion tab + shield counter; concurrency throttling is a distinct defensive behavior
- [[concepts/persistent-page-chrome-scraper-architecture]] - The persistent-page architecture underlying tab management and error recovery capabilities
- [[concepts/playwright-node-pipe-crash-vector]] - Diversion tab caused EPIPE crashes on Windows/Node v24; disabled in multi-server production
- [[concepts/chrome-tab-leak-accumulation]] - Tab leak problem that Caps 4, 9, and 11-C validate as solved
- [[concepts/bet365-nba-bb-wizard-v3-rewrite]] - NBA v3 built using the same patterns validated here; ~720 lines mirroring the MLB v3 structure

## Sources

- [[daily/lcash/2026-04-30.md]] - Full 12-capability test results: 11/12 passed, 1 conditional; Cap 11 error recovery A/B/C all passed (3-strike dead tab at 30s intervals, orphan cleanup sweep, kill mid-setup clean teardown); Cap 12 parity test conditional (27% dupe rate from alt-line expansion, stale 2-game snapshot); concurrency=3 validated at 11,018 odds / 0% drift / 0 tab leaks in 704s run (Session 07:59). Run 3 with diversion tab + shield: -3.3% drift vs -50% cliff-drop; partial-result shield caught DET@ATL 605 vs 904 records (67%, below 70% floor); 3-strike close scoped to zero-data scrapers only; skip games >6h away (Session 08:46)
