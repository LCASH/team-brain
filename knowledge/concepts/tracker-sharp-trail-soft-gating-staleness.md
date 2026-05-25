---
title: "Tracker Sharp Trail Soft-Gating Staleness"
aliases: [sharp-trail-soft-coupling, anchor-staleness, sharp-trail-gating-bug, tracker-soft-book-loop-coupling, decoupled-sharp-trail]
tags: [value-betting, tracker, trail-data, bug, architecture, clv, data-quality]
sources:
  - "daily/lcash/2026-05-25.md"
created: 2026-05-25
updated: 2026-05-25
---

# Tracker Sharp Trail Soft-Gating Staleness

The value betting tracker's sharp trail writes were gated inside a per-soft-book loop (`server/tracker.py:1747-1754`), meaning sharp trails only wrote when a soft book's odds were fresh enough to trigger evaluation. When bet365 MLB stalled for 5+ minutes between wizard refresh cycles, sharp trail writes from OpticOdds — which was streaming fresh data — were skipped entirely because the outer soft-book loop never executed for stale soft books. This produced a **28-minute median sharp anchor gap** (p90 = 82 minutes) before game start, meaning CLV closing-line computations were based on sharp snapshots from nearly half an hour before tip-off. The fix (commit `212d3dd`) decouples sharp trail writes to fire once per pick per tracker cycle, independent of soft book freshness.

## Key Points

- `server/tracker.py:1747-1754` gated sharp trail writes inside the per-soft-book loop — when bet365 stalled 5+ min, OO sharp data was fresh but never written because the soft-book gate never opened
- **Median sharp anchor: 28 minutes pre-game** (p90 = 82 min, only 1 of 15 sampled within 5 min of tip) — NOT "a few minutes" as previously assumed; this is meaningful market-drift territory
- MLB particularly affected: bet365 MLB pushes less frequently than NBA, and AU direct-scraper books (Neds, Ladbrokes, PointsBet, Sportsbet) cover NBA heavily but MLB barely (only book 908)
- Root cause hypothesis: tracker's `_is_game_live(buffer_minutes=15)` stops trail writes ~15 min before tip, compounding with the soft-gate coupling to create a dead zone
- Fix: sharp trail now fires **once per pick per cycle** independent of soft book freshness — +66/-62 lines, mostly comment restructuring (commit `212d3dd`)
- **Option A (decouple sharp trail) chosen over Option B (forced T-0 snapshot)** — eliminates structural coupling rather than papering over it

## Details

### The Coupling Mechanism

The tracker's Phase B trail collection iterates over tracked picks, and for each pick iterates over soft books to check for odds changes. Sharp trail writes were placed inside this inner soft-book loop — architecturally, the code said "for each soft book that has fresh odds, also write a sharp snapshot." This meant sharp trail frequency was bounded by the *least fresh* soft book, not by sharp data availability.

For NBA, this coupling was mostly invisible: AU direct-scraper books (Neds 901, Ladbrokes 908/909, PointsBet 910, Sportsbet 961) cover NBA heavily, providing frequent fresh soft data that kept the soft-book gate open. For MLB, only book 908 (TAB) covers the sport from AU direct scrapers — the other AU books have minimal MLB coverage. When bet365 MLB's wizard cycle stalled (which happens regularly for 5-10 minutes between refreshes), no soft book had fresh data, and the soft-book gate stayed closed, blocking sharp trail writes despite OO streaming continuous sharp updates.

### Quantifying the Anchor Gap

A staleness analysis across 15 randomly sampled resolved picks revealed the sharp anchor gap was far worse than assumed:

| Metric | Value |
|--------|-------|
| Median anchor gap | 28 minutes before game_start |
| P90 anchor gap | 82 minutes before game_start |
| Picks within 5 min of tip | 1 of 15 (6.7%) |
| Picks within 15 min of tip | ~4 of 15 (~27%) |

This means CLV computations — which use the last sharp trail entry as the "closing" sharp reference — were comparing pick odds against sharp prices from nearly half an hour before tip-off. In fast-moving pre-game markets (where sharp action arrives in the final 30-60 minutes), this gap is large enough to systematically mis-estimate CLV.

### The _is_game_live Compounding Factor

The tracker's `_is_game_live(buffer_minutes=15)` function flips a game from "pre-game" to "live" approximately 15 minutes before the scheduled game_start time. Once flipped, Phase B trail writes stop for that game. Combined with the soft-book coupling:

1. Sharp trails stop at `game_start - 28 min` (median, due to soft-book gate)
2. Trail writes stop entirely at `game_start - 15 min` (due to `_is_game_live` buffer)
3. The resolver's closing-line gate uses `captured_at <= game_start`

The 28-minute gap from the soft-book coupling was a bigger contributor to anchor staleness than the 15-minute live buffer — the coupling was the dominant bottleneck.

### The Fix

The fix extracts sharp trail writes from the soft-book loop and runs them once per pick per tracker cycle:

**Before:**
```python
for book_id in soft_books:
    if soft_is_fresh(book_id):
        write_soft_trail(pick, book_id)
        write_sharp_trail(pick)  # gated by soft freshness
```

**After:**
```python
write_sharp_trail(pick)  # independent, once per pick per cycle
for book_id in soft_books:
    if soft_is_fresh(book_id):
        write_soft_trail(pick, book_id)
```

This is architecturally clean: sharp data availability from OO is independent of soft book data availability from bet365. The two data streams have different cadences, different sources, and different freshness profiles — coupling them was a structural error from the original tracker design.

### MLB vs NBA Cycle-Rate Asymmetry

Investigation into why MLB trackers fire less often than NBA revealed a market-structure explanation, not a bug: AU direct-scraper books cover NBA heavily but MLB barely. Specifically, book IDs 901, 908, 909, 910, 961 all produce NBA odds but only 908 (TAB) produces MLB odds. Bet365 MLB actually pushes MORE than NBA (9 vs 1 in a 16-min window) — but the "diff-key collision" warnings on MLB pushes are a parser sub-market collapse issue (wizard/coupon/WS dedup), not a push failure.

### CLV Impact Assessment

The Peters Hits U0.5 sign-flip discovered during Bug A+B verification was recontextualized: with a 7.7-minute pre-game anchor + fast-moving market (soft trail 2.1→1.901), the stale sharp anchor alone could explain the sign mismatch without needing Bug B (alt-line race) as the cause. Tighter anchors may eliminate some apparent CLV anomalies that were previously attributed to other bugs.

## Related Concepts

- [[concepts/trail-anchored-bundle-read-layer-fix]] - The anchored bundle enforces soft-anchored sharp alignment at READ time; this fix ensures sharp data is WRITTEN frequently enough for the anchored bundle to have fresh data to work with
- [[concepts/clv-under-pick-side-encoding-contamination]] - Bug A (side encoding) and Bug B (alt-line race) were fixed in earlier sessions; sharp trail staleness is an independent CLV accuracy issue that compounds with both
- [[concepts/trail-change-detection-architecture]] - The change-only recording model means sharp trails only write when OO data changes; the soft-gating bug prevented even those change-triggered writes from executing
- [[concepts/per-soft-book-temporal-lineage]] - Per-book temporal lineage separated `captured_at` for different soft books; this fix extends the temporal honesty principle to sharp trails
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV accuracy depends directly on sharp trail freshness; 28-min-stale anchors reduce CLV precision for all theories

## Sources

- [[daily/lcash/2026-05-25.md]] - Stage 4 root cause: `server/tracker.py:1747-1754` gates sharp trail inside soft-book loop; median anchor 28 min (p90=82 min); fix deployed commit `212d3dd` (+66/-62 lines); MLB/NBA cycle-rate difference is market structure not bug; AU direct-scraper books cover NBA (5 books) but MLB barely (only 908); bet365 MLB pushes 9 vs NBA 1 in 16-min window; Peters sign-flip recontextualized as anchor staleness not Bug B (Sessions 13:06, 13:37, 15:59)
