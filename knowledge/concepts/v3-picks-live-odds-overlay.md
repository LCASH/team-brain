---
title: "V3 Picks Live Odds Overlay"
aliases: [live-odds-overlay, picks-overlay, cached-vs-live-odds, overlay-live-odds, stale-picks-display]
tags: [value-betting, dashboard, architecture, performance, v3]
sources:
  - "daily/lcash/2026-05-21.md"
created: 2026-05-21
updated: 2026-05-21
---

# V3 Picks Live Odds Overlay

The V3 picks/theories dashboard view showed Bet365 odds lagging by minutes compared to the `/topdown` view because the two endpoints read from different data sources. `/v1/picks` runs the full `engine.process_all()` over 3,000+ markets, cached for 60 seconds with thread-pool offload; `/topdown` reads the live in-memory DataStore directly. The fix uses an **overlay approach**: on each `/v1/picks` cache read, `_overlay_live_odds()` re-stamps `book_odds` from the live store and recomputes `ev_pct` from `true_prob × fresh_odds - 1`. Theory pass/fail decisions honor the cached computation (preventing mid-window pick flicker), while displayed odds and EV% always reflect the latest available data.

## Key Points

- **Root cause**: `/v1/picks` (60s cache, full engine computation) vs `/topdown` (live store read) — two different read paths for the same underlying data
- **Overlay approach**: Re-stamp `book_odds` from live store on every cache read + recompute `ev_pct` — fresh odds + fresh EV without re-running the full engine
- **Theory pass/fail stays cached**: A pick that passed theory evaluation at cache time continues to display until the next full computation — prevents picks appearing and disappearing mid-window
- **Vanished markets silently dropped**: If a market exists in the cached picks but is no longer in the live store, the pick is dropped rather than badged — simpler and arguably correct (can't take a bet that no longer exists)
- **Shallow-copy required**: Must copy pick objects before re-stamping or the underlying cache gets corrupted by mutation
- **Tracker is already fast** (1s throttle, event-driven via `change_event.wait()`) — the bottleneck was the display read path, not the data processing path

## Details

### The Architectural Mismatch

The V3 architecture (see [[concepts/v3-scanner-centralized-architecture]]) separates data processing (event-driven tracker, sub-second) from display serving (HTTP endpoints, cached). The tracker's DataStore updates in real-time as odds change. The `/v1/picks` endpoint, however, runs `engine.process_all()` — a full computation across all markets and theories — and caches the result for 60 seconds. During that 60-second window, displayed odds are frozen while the DataStore continues receiving live updates.

The `/topdown` journal view reads the DataStore directly (no engine computation needed — it just reads stored picks and their current odds). This created a visible discrepancy: a user looking at the same Bet365 prop on both views would see different odds, with `/topdown` always showing the fresher value.

### The Overlay Mechanism

Rather than reducing the cache TTL (which would increase CPU load) or eliminating caching entirely (which would make every request take 17+ seconds cold), the overlay re-stamps a subset of fields on cached results:

1. Read picks from the 60s cache
2. **Shallow-copy** each pick object (preventing cache mutation)
3. For each pick, look up `(market_key, soft_book_id)` in the live DataStore
4. If found: replace `book_odds` with the live value, recompute `ev_pct = true_prob × fresh_odds - 1`
5. If not found: drop the pick from the response (market has vanished)
6. Return the overlay-stamped picks

The `true_prob` used for EV recomputation comes from the cached engine result (which used the theory's sharp books and devig method). Only the soft-book odds side is refreshed. This means displayed EV% always agrees with displayed odds — preventing the confusing state where odds show 2.10 but EV% was computed against 1.95.

### Why Not Full Recomputation

Six options were evaluated before choosing the overlay:

| Option | Approach | Risk | Status |
|--------|----------|------|--------|
| 1 | Reduce cache TTL to 5s | CPU spike on every request | Rejected |
| 2 | **Overlay live odds on cached results** | Cache key mismatch (market_key drift) | **Chosen** |
| 3 | Read from tracker Supabase rows | 5-min staleness from tracker write cycle | Rejected |
| 4 | First-class in-memory picks projection | Major refactor | Deferred (Option 6) |
| 5 | SSE push of pick changes | Complex real-time sync | Rejected |
| 6 | Promote picks to DataStore-level projection | Best long-term architecture | Parked |

Option 2 was selected as lowest-risk immediate fix. Option 6 (a first-class in-memory picks projection alongside the `_catalogue`) is the long-term architectural direction but requires significant refactoring.

### Monitoring

The overlay logs `Overlay [mlb]: N re-stamped, K dropped` on each request. A high drop rate indicates market key mismatch between the cached engine output and the live DataStore — meaning the two data representations have drifted in their key formats. This should be monitored as a canary for data model inconsistencies.

## Related Concepts

- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture where the DataStore is the source of truth and `/v1/picks` is a cached computation layer
- [[concepts/v3-dashboard-ev-computation-architecture]] - The V3 dashboard's EV computation pipeline; the overlay addresses the cached→live gap in this pipeline
- [[concepts/dashboard-client-server-ev-divergence]] - A related class of display issues; the overlay prevents one specific divergence (cached vs live odds) while other divergences (theory exclusion, vig gate, etc.) require different fixes
- [[concepts/vps-proxy-byte-cache-optimization]] - The VPS proxy byte cache is a different caching layer (VPS→browser) that the overlay operates upstream of (mini PC engine→VPS)

## Sources

- [[daily/lcash/2026-05-21.md]] - User reported Bet365 odds lagging by minutes on picks/theories vs /topdown; traced to 60s-cached engine.process_all() vs live store read; overlay approach chosen: re-stamp book_odds + recompute ev_pct on cache read; theory pass/fail stays cached; vanished markets dropped; shallow-copy required; deployed as commit b6f5d11 (Session 15:08)
