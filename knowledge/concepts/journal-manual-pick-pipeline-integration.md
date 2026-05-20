---
title: "Journal Manual Pick Pipeline Integration"
aliases: [manual-topdown-picks, journal-supabase-cutover, manual-pick-first-class, topdown-journal-refactor]
tags: [value-betting, architecture, journal, dashboard, supabase, pipeline]
sources:
  - "daily/lcash/2026-05-20.md"
created: 2026-05-20
updated: 2026-05-20
---

# Journal Manual Pick Pipeline Integration

On 2026-05-20, lcash shipped a multi-phase refactor making manual "top-down" journal picks first-class rows in the existing `nba_tracked_picks` table, replacing a parallel localStorage-based journal system with Supabase-backed server endpoints. Manual picks are tagged with `triggered_by='manual_topdown'` and flow through the standard production resolver for grading, CLV, and analytics — eliminating the need for a separate auto-resolve loop, ET/UTC date juggling, and manual W/L buttons. The key architectural principle: when a background resolver already populates result/CLV columns on the same table, the client journal doesn't need its own resolve/CLV-fetch loops — just read the row.

## Key Points

- Manual picks are rows in `nba_tracked_picks` with `triggered_by='manual_topdown'` — not a separate table or localStorage; production resolver handles grading/CLV automatically
- **`origin` parameter in `_generate_pick_id`** prevents hash collision with theory-fired rows on the same market — theory path unchanged (`origin=""`), manual picks get distinct IDs
- **Phase 2 trail guard**: `_load_cache` Supabase query filters `triggered_by != 'manual_topdown'` so manual picks never leak into the theory tracker pipeline or accumulate trail entries
- **Hybrid CLV at display time**: `COALESCE(sharp_clv_pct_true, optic_clv_pct, synthetic_clv_pct, clv_pct)` — manual picks naturally fall through to whatever CLV the resolver populates
- **`crypto.subtle` is undefined on plain HTTP** — broke SHA-256 pick ID computation on VPS (port 8803); replaced with synchronous identity-key matching (`sport|player|prop|side|date|book_id`)
- Imported 66 of Jay's localStorage picks (64 unique after dedup); resolver graded 44/64 (69%); concordance 21/23 (91%) — the 2 disagreements led to discovery of the adjacent-day merge bug
- **Phase 5.6**: 5-min loop on VPS PATCHes manual picks' `closing_odds` from live `_closing_snapshots` dict after games end; line-drift guard skips cross-line patches

## Details

### Architecture: Why Not a Separate Table

The original approach (from a friend's PR) maintained a parallel journal system: localStorage for pick storage, `autoResolveLoop` for grading via NBA Stats API, `fetchProdCLVForPick` for CLV backfill, and ET/UTC date conversion for game-date matching. This duplicated what the production `server/resolver.py` already does — grade picks, compute CLV, handle timezone boundaries — but with its own bugs (ET date dance, void-retry logic, stale localStorage).

Making manual picks first-class rows in `nba_tracked_picks` leverages all existing infrastructure: the hourly resolver cycle grades them automatically, CLV columns are populated by the standard trail/closing-odds machinery, and the Supabase API provides cross-device access without localStorage drift. The `triggered_by='manual_topdown'` marker is the single discriminator that enables downstream components to handle manual picks differently where needed.

### Six-Phase Implementation

| Phase | Change | Status |
|-------|--------|--------|
| 1 | `origin` parameter in `_generate_pick_id` — append to hash input with `if origin:` guard | Shipped |
| 2 | Tracker cache guard — filter `triggered_by != 'manual_topdown'` at `_load_cache` Supabase query | Shipped |
| 3 | `POST /api/v1/journal/take` endpoint on VPS — UPSERT with server-side game_date in UTC | Shipped |
| 4 | `GET /api/v1/journal/picks` list endpoint | Shipped |
| 5 | `topdown.html` rewrite — removed localStorage, W/L buttons, autoResolveLoop, fetchProdCLVForPick, syncProdCLVs, ET date juggling (~370 lines changed) | Shipped |
| 5.6 | Live closing-odds patcher — 5-min loop PATCHes `closing_odds` from `_closing_snapshots` after games end | Shipped |
| 6 | Analytics/calibration filter — exclude `triggered_by='manual_topdown'` from theory ROI and calibration | Pending |

Phase 5.5 (sharp_snapshot at Take time) was shipped and reverted in the same day — it produced misleading `clv_pct=0` via the resolver's entry_snapshot fallback. The locked principle: "Journal entries are frozen at Take time. No trails, no derived data afterwards." Closing odds are the close half of the CLV equation — filling them post-game is correct, not a violation.

### The crypto.subtle Secure Context Constraint

The initial implementation used SHA-256 (`crypto.subtle.digest`) in the browser to compute `computeManualPickId` for matching picks against Supabase rows. This works on localhost (a secure context) but fails silently on plain HTTP connections to the VPS (port 8803). The Web Crypto API is only available in secure contexts (HTTPS or localhost) — plain HTTP on a VPS doesn't qualify. The fix replaced client-side hashing with identity-key matching: the client builds a string like `nba|Julian Champagnie|Assists|Over|2026-05-16|365` and the server handles canonical SHA-256 internally.

### CLV Architecture for Manual Picks

Manual picks follow a different CLV data path than theory picks:

| CLV Source | Theory Picks | Manual Picks |
|------------|-------------|--------------|
| `sharp_clv_pct_true` | From trail-anchored bundle | NULL (no trails) |
| `optic_clv_pct` | From OpticOdds historical backfill | Populated when fixture matches |
| `synthetic_clv_pct` | From anchored closing bundle | NULL (no trails) |
| `clv_pct` | From Phase 5.6 closing snapshot | Populated when closing odds captured |

The display waterfall (`COALESCE(sharp_clv_pct_true, optic_clv_pct, synthetic_clv_pct, clv_pct)`) naturally falls through to whichever source has data. For 19 of 49 imported picks, `theory_anchored` CLV was available — copied from matching theory rows that had the same market with better closing data. The remaining 29 picks are permanently un-CLV-able because bet365 has no external historical API for player props and the 24-hour capture window has passed.

### Closing-Odds Architecture (Phase 5.6)

A 5-minute background loop on the VPS PATCHes manual picks' `closing_odds` from the live `_closing_snapshots` dict after games end. Two guards prevent bad data:

1. **Timestamp format mismatch**: Supabase returns `+00:00` while the live API returns `Z` — the lookup tries both forms
2. **Line-drift guard**: If `closing_line != opening_line`, the CLV comparison would be cross-line (apples to oranges) — the patch is skipped, leaving the pick at `opening_fallback`

### Three-Tier Closing Source Priority

A priority system was established for closing data enrichment:

1. **`theory_anchored`** — copy closing data from a matching theory-fired row (same market, different origin)
2. **`live_closing_snapshot`** — Phase 5.6 captures bet365's closing price from the live feed
3. **`opening_fallback`** — the take-time odds, used when no closing data exists

## Related Concepts

- [[concepts/resolver-adjacent-day-merge-bug]] - Jay's imported picks provided the ground truth that exposed the MLB resolver date-iteration bug; concordance checking is a powerful validation tool
- [[concepts/pick-dedup-multi-theory-limitation]] - The `origin` parameter in `_generate_pick_id` extends the existing pick ID architecture to disambiguate manual vs theory origins
- [[concepts/dashboard-client-server-ev-divergence]] - The `crypto.subtle` secure context failure is a 13th manifestation of client-server divergence — browser API unavailability on plain HTTP
- [[concepts/trail-anchored-bundle-read-layer-fix]] - Manual picks have no trails, so the anchored bundle never fires; CLV must come from external sources (OpticOdds, closing snapshots)
- [[concepts/sharp-clv-theory-ranking]] - Manual picks' CLV uses the same waterfall but with different coverage; `optic_clv_pct` is the most likely source for manual picks

## Sources

- [[daily/lcash/2026-05-20.md]] - Multi-phase journal refactor: Phase 1 hash marker, Phase 2 tracker guard, Phase 3 POST endpoint, Phase 5 full topdown.html rewrite (370 lines), Phase 5.5 reverted (speculative CLV), Phase 5.6 closing-odds patcher; crypto.subtle undefined on HTTP; 66 imported picks, 44 graded, 21/23 concordance; theory_anchored CLV for 19 picks; bet365 has no external historical API for player props; locked principle: "frozen at Take time"; identity-key matching replaces SHA-256; three-tier closing source priority (Sessions 09:36, 10:09, 10:43, 11:38, 12:08, 14:05, 15:20, 15:52)
