---
title: "Persistent-Page Chrome Scraper Architecture"
aliases: [persistent-page, persistent-tab, game-page-dict, non-blocking-setup, incremental-odds-serving]
tags: [value-betting, bet365, scraping, architecture, chrome, reliability]
sources:
  - "daily/lcash/2026-04-28.md"
created: 2026-04-28
updated: 2026-04-28
---

# Persistent-Page Chrome Scraper Architecture

On 2026-04-28, the bet365 MLB scraper was rewritten from a worker-cycling model (one shared page rotated between games) to a persistent-page-per-game architecture where each game gets its own Chrome tab that stays open for the duration of the session. The `_game_pages` dict maps game IDs to their dedicated page objects. `scrape_cycle()` returns cached odds instantly from all open pages, while `_refresh_loop()` re-captures stale pages in the background. The same pattern was applied to the NBA scraper in the same session. Critically, game page setup is non-blocking — the worker enters its poll loop immediately and serves odds incrementally as each game finishes setup, rather than waiting for all games to complete.

## Key Points

- Each game gets a dedicated Chrome tab via `_game_pages` dict — tabs persist for the session lifetime instead of being created/destroyed per scrape cycle
- `scrape_cycle()` reads cached odds instantly from all open pages; `_refresh_loop()` handles background refresh of stale pages
- Non-blocking setup: worker enters poll loop immediately, games set up in background (~2 min per game for SPA boot + market expansion), first game's odds hit the shared file within 30s
- Per-game fault tolerance: if one game page fails or hangs, all other games continue serving — eliminates the all-or-nothing crash pattern from the previous blocking setup
- MLB setup for 15-19 games takes 30+ min total but odds flow incrementally from each game as it completes
- Replaced the `_WorkerPage` cycling model where a single page navigated between games sequentially, accumulating tabs and creating EPIPE crash loops

## Details

### The Worker-Cycling Problem

The previous MLB scraper architecture used a `_WorkerPage` model where one or more Chrome pages cycled through assigned games sequentially. Each cycle, a page would navigate to a game, wait for the SPA to render, expand market sections, capture the batch API response, then navigate to the next game. This cycling model had three fundamental problems:

1. **Tab accumulation**: Each navigation could create a new page context without properly closing the old one. Over many cycles, Chrome accumulated 30-51+ stale tabs (see [[concepts/chrome-tab-leak-accumulation]]), progressively degrading performance until EPIPE crash loops occurred.

2. **All-or-nothing blocking**: The `_open_game_pages()` method blocked until ALL games were set up. If one game's SPA boot hung or timed out, the entire worker was killed — zero odds served from any game until the setup completed or the worker crashed.

3. **Sequential staleness**: With 15-19 MLB games and ~2 minutes per game for SPA boot + market expansion, a full rotation took 30+ minutes. By the time the last game was scraped, the first game's odds were 30 minutes stale.

### The Persistent-Page Solution

The rewrite assigns each game a dedicated Chrome tab that persists for the entire session:

**`_game_pages` dict**: Maps `event_id` → Playwright `Page` object. Each game's page is opened once, navigated to the game's props tab, and kept alive. The page accumulates cached SPA state (session cookies, market data, JavaScript context) that makes subsequent refreshes faster than cold navigation.

**`scrape_cycle()`**: Iterates all open pages in `_game_pages`, reading cached odds from each. Since pages are persistent and pre-warmed, this is essentially a memory read — returning whatever the last successful refresh captured. The cycle completes in milliseconds rather than minutes.

**`_refresh_loop()`**: A background async loop that periodically re-navigates each page to capture fresh odds. Stale pages (where the last successful capture exceeds a threshold) are prioritized. This decouples the "serve current data" path from the "fetch new data" path — the scraper never blocks on a refresh to serve odds.

### Non-Blocking Setup Pattern

The critical architectural change is that game page setup is non-blocking. The worker's initialization flow:

1. Discover games via sidebar/API
2. Start the poll loop immediately (even with zero games set up)
3. Spawn background tasks to open and initialize each game page
4. As each game completes setup, it's added to `_game_pages`
5. `scrape_cycle()` picks up newly opened pages on the next iteration

This means the first game's odds are available within ~30 seconds of worker start (one game's setup time), even though the full 15-game setup takes 30+ minutes. The worker is `_started = True` before all pages finish opening, so `scrape_cycle()` serves partial odds while setup continues.

### Per-Game Fault Tolerance

If one game page hangs during setup or refresh, it affects only that game — all other games continue serving odds. This eliminates the previous pattern where one hung page killed the entire worker. The fault tolerance is automatic: `scrape_cycle()` iterates whatever pages exist in `_game_pages`, and a failed page simply isn't present (or is marked stale and skipped).

### Tab Cleanup by Event ID

The rediscovery logic (which checks for new games every 30 minutes) now matches tabs by `event_id` rather than URL. URL-based matching was unreliable because bet365's SPA URLs can change format between navigations. Event ID matching is robust — each game has a unique fixture identifier that persists across the session. Tab cleanup is also sport-scoped: NBA rediscovery only closes NBA tabs (`/B18/`), MLB only closes MLB tabs (`/B16/`), preventing cross-sport tab deletion when both scrapers share Chrome.

### Chrome Lifecycle: Always Fresh on Worker Start

The persistent-page architecture pairs with the "always kill and relaunch Chrome" pattern (see [[concepts/cdp-stale-connection-poisoning]]). On worker start, Chrome is killed and relaunched with a persistent profile directory (`bet365_nba_profile` or `bet365_mlb_profile`). The persistent profile preserves login cookies so no re-authentication is needed, while the fresh Chrome process eliminates stale CDP connections and orphaned tabs from dead workers.

### Application to NBA Scraper

The same non-blocking setup pattern was applied to the NBA scraper on 2026-04-28. Previously, the NBA scraper's `_open_game_pages()` blocked until all 8 games were set up — one hung page killed the entire worker. After the fix, the NBA worker enters its poll loop immediately, with games opening in the background. This is the same pattern the MLB scraper uses, creating architectural consistency across both bet365 game scrapers.

## Related Concepts

- [[concepts/chrome-tab-leak-accumulation]] - The tab leak problem that the persistent-page architecture solves by having a fixed, managed set of tabs instead of creating new ones per cycle
- [[concepts/cdp-stale-connection-poisoning]] - The "always fresh Chrome" pattern that pairs with persistent pages: fresh process + persistent profile = clean state with preserved login
- [[concepts/mlb-parallel-scraper-workers]] - The previous architecture (N_WORKERS cycling model) that this persistent-page design replaces
- [[concepts/game-scraper-chrome-crash-recovery]] - The crash auto-recovery mechanism that still applies: if Chrome dies, the worker relaunches it and re-opens all game pages
- [[connections/browser-automation-reliability-cost]] - Persistent pages reduce one reliability dimension (tab accumulation) while the non-blocking pattern reduces another (all-or-nothing crashes)
- [[concepts/bet365-mlb-batch-api-co-format]] - The batch API response that each persistent page captures during its refresh cycle

## Sources

- [[daily/lcash/2026-04-28.md]] - MLB `_MLBGamePage` class rewrite replacing `_WorkerPage` cycling with `_game_pages` dict + `_refresh_loop`; non-blocking setup applied to both MLB and NBA; per-game fault tolerance eliminates all-or-nothing crashes; tab cleanup by event_id scoped per sport; MLB 15-19 games × 2min = 30+ min setup but odds flow incrementally; `_started = True` before all pages open (Sessions 08:16, 08:47, 09:18, 11:33, 11:36)
