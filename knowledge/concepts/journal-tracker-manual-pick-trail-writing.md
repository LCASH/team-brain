---
title: "JournalTracker Manual Pick Trail Writing"
aliases: [journal-tracker, manual-pick-trails, journal-phase-b, oo-fixture-status-game-end, game-end-detection]
tags: [value-betting, architecture, tracker, trail-data, journal, operations]
sources:
  - "daily/lcash/2026-05-22.md"
created: 2026-05-22
updated: 2026-05-22
---

# JournalTracker Manual Pick Trail Writing

On 2026-05-22, lcash deployed the JournalTracker (JT) — a per-sport event-driven process that writes soft + sharp trail entries for manual "top-down" journal picks. Prior to this, manual picks (see [[concepts/journal-manual-pick-pipeline-integration]]) had zero trail data because they bypassed the Phase B tracker pipeline. The JT spawns from `v3/startup.py` as separate NBA/MLB event loops, monitors the DataStore for odds changes, and writes trail entries using the same change-detection threshold as the production tracker. A verified test pick (SGA Points Over 37.5) generated 67 trail entries in 9 minutes (6 soft, 61 sharp), each sharp snapshot including all 21 books.

## Key Points

- **JournalTracker fills the Phase B gap** for manual picks: `triggered_by='manual_topdown'` picks previously had zero trails because the production tracker's `_load_cache` query filters them out
- **OO fixture status replaces time-based game-end**: `completed`/`cancelled` from OpticOdds fixture API is correct by construction; fallback time rule widened (NBA 5h, MLB 6h) only fires when OO unreachable — biased toward extra trail rows over early cutoff (commit `e35894b`)
- **UTC midnight rollover bug**: JT cache query `game_date >= today` (UTC) excluded late-night ET picks when UTC rolled to next day; fix includes yesterday in the cache window
- **Trail density validated**: 67 entries in 9 min (6 soft, 61 sharp) on SGA test pick — sharp snapshots include all 21 books including bet365, confirming end-to-end data flow
- **Soft trail silence is expected**: 5 of 12 in-window picks had zero soft trail entries because bet365 odds didn't change — the diff-cache correctly suppresses no-op writes

## Details

### The Phase B Gap for Manual Picks

The production tracker's Phase B trail collection loads tracked picks from Supabase on startup, then writes trail entries as odds change. However, the `_load_cache` query explicitly filters `triggered_by != 'manual_topdown'` to prevent manual picks from leaking into the theory tracker pipeline or accumulating trail entries through the production path (see [[concepts/journal-manual-pick-pipeline-integration]], Phase 2 trail guard).

This filtering was architecturally correct — manual picks should not affect theory evaluation or trigger dedup against production picks. But it created a complete trail gap: manual picks existed in Supabase with frozen detection-time odds and no odds evolution data, making CLV computation impossible and the trail chart feature empty for all journal entries.

The JournalTracker solves this by running as a separate process with its own Supabase query (`triggered_by = 'manual_topdown'`) and its own event loop. It shares the same DataStore (reads the same live odds from bet365 + OpticOdds) but writes to trail tables independently. This separation ensures production and manual pick trail writing cannot interfere with each other.

### Game-End Detection via OO Fixture Status

The initial JournalTracker used a time-based game-end heuristic: `game_start + 3.5h` for NBA, `game_start + 4.5h` for MLB. The user challenged this approach — overtime, rain delays, and doubleheaders all invalidate time estimates. The fix replaces the heuristic with OpticOdds fixture status polling.

The OO fixture lifecycle: `unplayed → live → completed` (also `delayed`/`cancelled`). The resolver already queries `_fetch_completed_fixture_names` from the same endpoint — the JournalTracker is a different consumer of the same data. One OO API call per sport per 60 seconds (cached) provides authoritative game completion status.

Fallback time rules (NBA 5h, MLB 6h) only fire when OO is unreachable, and are deliberately wide — biased toward writing extra trail rows (wasted I/O) over cutting off trail capture prematurely (lost data). This follows the principle that excess data can be filtered at query time but missing data is unrecoverable.

### UTC Midnight Rollover

A timezone boundary bug was discovered during overnight testing: the JT cache query used `game_date >= today` in UTC. When UTC rolled from May 21 to May 22 at midnight, picks with `game_date = 2026-05-21` were excluded from the cache — even though ET games from that date were still in progress (a game starting at 8 PM ET on May 21 has `game_start` at 00:00Z May 22, but `game_date` stored as May 21).

The fix includes yesterday in the cache window: `game_date >= yesterday`. This ensures late-night ET games persist past the UTC midnight boundary. The same class of UTC/ET boundary issue affected the resolver (see [[concepts/resolver-utc-scan-window-gap]]) and the stats fetcher (see [[concepts/resolver-adjacent-day-merge-bug]]).

### Dashboard Refresh Cadence

In the same session, the user reported the theories dashboard (`/nba`, `/mlb` on port 8803) felt stale. Investigation revealed `loadTheories()` only ran once at page boot and never refreshed. The fix established polling cadences: theories 10min, tracked picks 5s, taken bets 10s, results/calibration 30s, plus `visibilitychange` instant reload on tab focus.

The user initially requested 1-second polling but was pushed back due to Supabase I/O budget concerns (the same budget that caused 522 errors previously). The compromise was informed by the observation that the topdown dashboard's "instant" feel is actually 20s polling + SSE for odds + optimistic UI updates — perceived responsiveness is driven by UI patterns, not raw poll frequency.

## Related Concepts

- [[concepts/journal-manual-pick-pipeline-integration]] - The manual pick system (Phase 1-5) that JournalTracker (Phase B) completes; the `triggered_by='manual_topdown'` filter guard was the architectural decision that created the trail gap
- [[concepts/trail-change-detection-architecture]] - JT uses the same change-only recording model (0.001 threshold for soft, hash-based for sharp); the 6 soft / 61 sharp ratio is consistent with the documented 7x sharp density
- [[concepts/sharp-consensus-clv-manual-picks]] - The CLV fallback for manual picks using closing_sharps JSONB; with JT trails, manual picks may eventually get `sharp_clv_pct_true` from anchored bundles instead of consensus fallback
- [[concepts/resolver-utc-scan-window-gap]] - Same class of UTC/ET boundary bug: resolver only scanned yesterday UTC, JT excluded yesterday from cache query
- [[concepts/trail-anchored-bundle-read-layer-fix]] - The anchored bundle read-layer fix that JT trails enable; manual picks can now get temporally-aligned soft/sharp closing data

## Sources

- [[daily/lcash/2026-05-22.md]] - JournalTracker deployed with per-sport event loops from startup.py; SGA Points O37.5 test: 67 trails in 9min (6 soft, 61 sharp, all 21 books); OO fixture status replaces time-based game-end (commit e35894b); UTC midnight rollover fix includes yesterday in cache; 5/12 picks with zero soft trails = expected (bet365 didn't move); dashboard refresh: theories 10min, tracked 5s, taken 10s, visibilitychange reload; topdown's "instant" is actually 20s poll + SSE + optimistic UI (Sessions 08:55, 09:31, 09:57)
