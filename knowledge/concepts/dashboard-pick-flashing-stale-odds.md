---
title: "Dashboard Pick Flashing and Stale Odds Display"
aliases: [pick-flashing, stale-odds-display, captured-at-override, reconcile-sport-grace, market-key-format-mismatch]
tags: [value-betting, dashboard, bug, sse, data-quality, architecture]
sources:
  - "daily/lcash/2026-04-22.md"
created: 2026-04-22
updated: 2026-04-22
---

# Dashboard Pick Flashing and Stale Odds Display

Multiple independent bugs stacked to produce a single visible symptom: dashboard picks "flashing" in and out while displaying stale odds as fresh. Five distinct causes were identified and fixed: (1) SSE snapshot clearing on reconnect, (2) `reconcile_sport()` aggressively removing markets, (3) stored Supabase picks carrying frozen `book_odds`, (4) market key format inconsistency (spaces vs underscores in player names), and (5) **the most damaging bug** — `captured_at` being overwritten with `time.time()` at VPS ingest (`state.py:2115`), making every market appear 5 seconds old regardless of actual age.

## Key Points

- The `captured_at: time.time()` override at VPS ingest (state.py line 2115) was the most damaging bug — it made every market look 5s old, so the 5-min staleness filter (`MAX_SOFT_ODDS_AGE_S`) never triggered, hiding the fact that sharp data was **111 minutes stale**
- SSE reconnection cleared `markets = {}` (full wipe) instead of merging — each reconnect destroyed client state and replaced it with a potentially smaller VPS snapshot
- `reconcile_sport()` aggressively removed markets not in the current push every 5 seconds — if push cycles had varying market sets, downstream clients saw instability
- Stored Supabase picks carried frozen `book_odds` from insertion time — Harrison Barnes Threes showing 2.45 when live bet365 was 1.833
- Market key format mismatch: stored picks generate keys with underscores (`harrison_barnes_threes_under`), live API uses spaces (`harrison barnes_threes_under`) — caused dedup failures allowing stale duplicates to leak through

## Details

### The `captured_at` Override — Root Cause of Stale-But-Fresh-Looking Data

The most architecturally damaging bug was a single line in `state.py:2115` that overwrote `captured_at` with `time.time()` every time the VPS ingested a push payload. This was identified in Session 11:06 when lcash traced why "live" odds on the dashboard were clearly wrong compared to actual bet365 prices.

The override meant that every market's freshness timestamp was reset to "now" on every push cycle (~5 seconds). The dashboard's staleness filter (`MAX_SOFT_ODDS_AGE_S = 300`, i.e., 5 minutes) compared the current time against `captured_at` — which was always ~5 seconds old. The filter never triggered, even when the underlying data hadn't been updated in over an hour.

Investigation revealed that OpticOdds sharp data was **111 minutes stale** at the time of diagnosis — but the dashboard displayed it as fresh because each push cycle re-stamped the `captured_at`. This means every EV computation displayed on the dashboard was computed against sharp odds that were nearly 2 hours old — the "edges" shown were phantoms from stale sharp data.

The fix removed the `time.time()` override, preserving the original scraper-side timestamps through the VPS ingest layer. This is the same problem identified in [[concepts/odds-staleness-pipeline-diagnosis]] (where `captured_at` was documented as "re-stamped with `now()` at each pipeline layer"), but the VPS ingest override was still active despite earlier awareness of the issue.

**Additional gap discovered:** the dashboard's staleness filter only checks **soft book** age, not **sharp book** age. Picks computed from 2-hour-old sharp data still display with confident EV% because the soft book odds are fresh. A sharp staleness check is needed.

### SSE Snapshot Clearing

The SSE event handler used `markets = {}` (clear-and-replace) when processing snapshot events. On every SSE reconnection (which can happen from network interrupts, tab sleeps, or server pushes), the client's entire market state was wiped and rebuilt from the new snapshot. If the new snapshot was smaller than the prior state (due to timing or `reconcile_sport` pruning), picks that were visible before the reconnect disappeared.

The fix changed the handler from clear-and-replace to merge-based approach. Stale markets are now filtered naturally by the existing `MAX_SOFT_ODDS_AGE_S` check — markets that haven't been refreshed eventually expire, rather than being instantly wiped.

### reconcile_sport() Aggressive Removal

The VPS `reconcile_sport()` function runs every 5 seconds and removes any markets not present in the current push payload. If the mini PC's push cycles have varying market sets (e.g., a scraper temporarily misses a game between rotation cycles), markets are removed from VPS state and then re-added on the next push — creating instability for any SSE client that reconnects between these cycles.

The fix added a **60-second grace period** before removing markets. Markets not seen in the current push are marked as "last seen" but not deleted until 60 seconds have elapsed. This accommodates single-cycle scraper gaps without killing picks on the dashboard.

### Frozen Stored Pick Odds

Stored Supabase picks carry the `book_odds` value from insertion time — the odds when the pick was first detected. These are not refreshed from live data before rendering. When the dashboard renders both live-computed picks and stored picks for the same sport, users see stale odds from the stored pick mixed with current odds from live computation.

The fix for SSE sports (NBA/MLB): show only `computeEVPicks()` output from live SSE data, never merge stored Supabase picks. For virtual sports (NRL/AFL/Pinnacle) that have no SSE data, stored picks are the only option and are displayed as-is.

Additionally, `loadStoredEVPicks()` was triggering `render()` every 30 seconds even for SSE sports — causing unnecessary DOM rebuilds that contributed to visual flashing. This was stopped for non-virtual sports.

### Market Key Format Inconsistency

Stored picks in Supabase generate market keys with underscores in player names (`harrison_barnes_threes_under`), while the live API uses spaces (`harrison barnes_threes_under`). The dedup filter that should prevent showing both stored and live picks for the same market failed because the keys didn't match — both versions appeared on the dashboard simultaneously.

The fix normalized market keys in the dedup filter to handle both formats. This is another instance of the format inconsistency pattern seen elsewhere in the scanner (e.g., `prop_type` spaces vs underscores in [[concepts/game-line-display-normalization]]).

### 15-Minute Game-Start Buffer

Picks were disappearing from the dashboard "before tip-off" because OpticOdds reports the **scheduled** start time, but actual NBA tip-off is 10-15 minutes later (pre-game ceremonies and introductions). The dashboard's `isGameLive()` function was filtering out picks at the scheduled time while they were still actionable.

A 15-minute buffer was added to the dashboard's `isGameLive()` to match the server-side fix (which had already been deployed in [[concepts/pinnacle-prediction-market-pipeline]]). This prevents premature pick filtering.

## Related Concepts

- [[concepts/odds-staleness-pipeline-diagnosis]] - The `captured_at` re-stamping problem was first documented there but the VPS ingest override at state.py:2115 was still active; sharp staleness check gap also identified there but not yet implemented
- [[concepts/dashboard-client-server-ev-divergence]] - A parallel dashboard rendering issue; the market key format mismatch is a new variant of the client/server data format inconsistency pattern
- [[concepts/sse-display-tracking-market-separation]] - The SSE architecture whose reconnection behavior causes the snapshot clearing problem
- [[concepts/vps-sse-cascade-silent-crash]] - The SSE cascade crash that triggered the VPS restart leading to this debugging session
- [[connections/silent-type-coercion-data-corruption]] - The `captured_at` override is another "plausible wrong output" — markets look fresh because the staleness check passes, but the underlying data is hours old

## Sources

- [[daily/lcash/2026-04-22.md]] - Dashboard picks flashing: SSE snapshot clearing on reconnect, reconcile_sport aggressive removal, stored picks frozen book_odds (Harrison Barnes 2.45 vs live 1.833), market key format mismatch (spaces vs underscores) (Sessions 09:42, 10:31). **The `captured_at` override** at state.py:2115 was the most damaging bug: every market appeared 5s old, 5-min staleness filter never triggered, sharp data 111 minutes stale; dashboard only checks soft book age not sharp; removed the override (Session 11:06). SSE merge instead of clear; reconcile_sport 60s grace period; 15-min isGameLive buffer; stopped loadStoredEVPicks re-render for SSE sports (Sessions 10:31, 11:06)
