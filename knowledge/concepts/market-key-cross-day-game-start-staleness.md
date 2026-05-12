---
title: "Market Key Cross-Day Game Start Staleness"
aliases: [game-start-staleness, market-key-no-game-date, stale-game-start, isGameLive-false-positive, eve-cleanup-never-called]
tags: [value-betting, bug, architecture, data-quality, market-key, eve, mlb]
sources:
  - "daily/lcash/2026-05-12.md"
created: 2026-05-12
updated: 2026-05-12
---

# Market Key Cross-Day Game Start Staleness

On 2026-05-12, all 31 MLB fixtures showed `game_start = 2026-05-08` (3+ days stale) despite `captured_at` being only 4 seconds old — odds were fresh but game start timestamps were stuck on the first-ever observation date. The root cause was two compounding bugs in Eve's `server/state.py`: a never-overwrite guard on `game_start` once it was a full datetime string, combined with `cleanup_stale_markets()` existing but never being called from v3's `startup.py`. Since `market_key` is derived from `(player, prop_type, side)` and does NOT include `line` or `game_date`, the same player's prop market on different game days maps to the same key — meaning odds updated daily but `game_start` stayed pinned to the date of first observation. This caused 93% of MLB markets (9,275 of 10,000) to be filtered as "live" by the `isGameLive(m)` check, reducing eligible picks from ~95 to just 4.

## Key Points

- `market_key` derives from `(player, prop_type, side)` without `line` or `game_date` — the same player's prop across different game days shares one key, so odds refresh but `game_start` never advances
- TWO compounding bugs in `server/state.py`: Lines 285-290 never refreshed `game_start` once it was a full datetime string (`len > 10` check prevented overwrite), and `cleanup_stale_markets()` was wired in v2's `main.py` but never called from v3's `startup.py`
- 93% of MLB markets (9,275 / 10,000) were filtered as "live" by `isGameLive(m)` due to stale `game_start` dates from May 8 appearing as in-progress games
- The vig sanity gate commits (`0de77c5`, `632627a`, `a560ef9`) previously suspected in [[concepts/dashboard-vig-gate-cross-line-dropout]] were a red herring for the MLB zero-picks problem — the real filter was `isGameLive`
- After fix deployment (commit `ae61bfd`, merged to `89032bb`): all 31 MLB fixtures showed current `game_start` (2026-05-12/13), eligible picks jumped from 4 to 93-97

## Details

### The Never-Overwrite Guard

Eve's `server/state.py` maintains an in-memory state dictionary keyed by `market_key`. When new odds arrive for an existing key, the update logic refreshes price, odds, and `captured_at` — but `game_start` had a special guard at lines 285-290. The guard checked `len(existing_game_start) > 10`: if the stored value was already a full ISO datetime string (e.g., `"2026-05-08T19:10:00Z"` — length 20), it was considered "resolved" and never overwritten. The intent was to prevent a less-precise date string from downgrading a more-precise datetime, but the implementation meant that once `game_start` was set to a full datetime on the first observation, it would never be updated even when the same `market_key` appeared in a completely different game days later.

Because `market_key` does not include `game_date`, a player's "Points Over" prop on May 8 and May 12 share the same key. Odds from the May 12 game correctly overwrote the May 8 odds, but `game_start` stayed frozen at May 8. With `captured_at` showing 4 seconds ago and `game_start` showing May 8, the `isGameLive(m)` function concluded these were active games (start time in the past, market still receiving updates) and filtered them from the pre-game eligible pool.

### The Missing Cleanup Task

The second compounding bug was that `cleanup_stale_markets()` — a function that existed in `state.py` to periodically purge markets whose `game_start` was more than N hours in the past — was never invoked from v3's `startup.py`. It had been wired into v2's `main.py` as a periodic task but was lost during the v3 migration. If cleanup had been running, markets with `game_start = 2026-05-08` would have been purged within 6 hours, and the next observation would have created a fresh entry with the correct game start. The combination of never-overwrite plus never-cleanup made the staleness permanent and accumulating.

### Fix and Verification

The fix (commit `ae61bfd`) addressed both bugs: (1) replaced the never-overwrite guard with a chronological comparison (`incoming > existing` instead of skip-if-resolved), so `game_start` advances when a newer game date arrives for the same market key; (2) wired `cleanup_stale_markets()` into v3's `startup.py` as a periodic task running every 10 minutes with `max_age_hours=6`, ensuring markets from completed games are purged before the next day's games begin.

After deployment, all 31 MLB fixtures immediately showed current `game_start` dates (2026-05-12 and 2026-05-13), the `isGameLive` filter stopped incorrectly filtering pre-game markets, and eligible pick counts jumped from 4 to 93-97 — consistent with the theoretical maximum.

### Diagnostic Methodology

A key operational insight from this investigation: offline Python replication of the client-side dropout logic was dramatically more productive than fighting Playwright/AdsPower browser automation for diagnosis. By pulling Eve's raw state via API and running the same `isGameLive` and EV computation functions locally, the root cause was isolated in minutes rather than the hours typically consumed by browser-based debugging with login flows and session management.

## Related Concepts

- [[concepts/matched-market-line-null-bug]] - First manifestation of the `line`-not-in-key design; this bug is a third manifestation where `game_date` not being in the key causes cross-day staleness
- [[concepts/dashboard-vig-gate-cross-line-dropout]] - The vig gate was initially suspected as the cause of MLB zero picks, but turned out to be a red herring — the real filter was `isGameLive` acting on stale `game_start` values
- [[concepts/dashboard-client-server-ev-divergence]] - Another instance of client-side vs server-side divergence; the server had fresh odds but the client-side `isGameLive` check filtered markets using stale metadata

## Sources

- [[daily/lcash/2026-05-12.md]] - All 31 MLB fixtures had `game_start = 2026-05-08` (3+ days stale) despite fresh `captured_at`; TWO bugs in `server/state.py`: never-overwrite guard (len > 10 check) + `cleanup_stale_markets()` never called from v3 `startup.py`; 93% of markets (9,275/10,000) filtered as live by `isGameLive`; fix deployed as `ae61bfd` merged to `89032bb`; picks jumped 4 to 93-97; offline Python replication far more productive than browser automation for diagnosis (Sessions 08:49, 09:42)
