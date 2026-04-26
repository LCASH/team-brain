---
title: "MatchedMarket Line Null Bug"
aliases: [line-null-bug, matched-market-to-dict, top-level-line-missing, trail-pipeline-broken-input]
tags: [value-betting, bug, data-quality, tracker, trail-data, architecture]
sources:
  - "daily/lcash/2026-04-26.md"
created: 2026-04-26
updated: 2026-04-26
---

# MatchedMarket Line Null Bug

A critical data model bug where ALL 3,101 NBA markets had `line=None` at the top level of `MatchedMarket.to_dict()`. The `line` field only existed per-book inside `BookOdds`, never on `MatchedMarket` itself. This meant the tracker couldn't create picks for ANY market because `_generate_pick_id()` requires a line value. The dashboard appeared functional because client-side EV computation doesn't need a top-level line, masking the fact that pick tracking, trail recording, and all downstream persistence were completely broken.

## Key Points

- ALL 3,101 NBA markets had `line=None` at the top level — `MatchedMarket.to_dict()` never included a `line` field derived from per-book data
- The tracker couldn't create picks because `_generate_pick_id()` requires `line` to hash the pick UUID — no picks in Supabase means no trail entries
- The dashboard showed picks fine because client-side `computeEVForTheory()` reads odds from per-book entries, not the top-level `line` — same data, different consumers, different failure modes
- Fix: added a top-level `line` field to `to_dict()` derived from the first main-line book entry, rather than restructuring the entire `MatchedMarket` dataclass
- ~43% of historical picks had zero trail entries (created before the fix), but old results/ROI/CLV are valid since the pick record itself was populated correctly — only trail depth is missing
- Confirmed working immediately after fix: 20/20 picks for both NBA and MLB generated trail entries

## Details

### The Data Model Gap

The `MatchedMarket` dataclass aggregates odds from multiple bookmakers for the same market. Each bookmaker's odds are stored in a `BookOdds` object that includes the line value (e.g., 25.5 for "Points Over 25.5"). However, `MatchedMarket` never had a top-level `line` attribute — it was purely an aggregation container that let consumers drill into per-book data.

When `to_dict()` serialized the market for the tracker, the resulting dictionary had odds per book but no `line` at the root level. The tracker's `_generate_pick_id()` function hashes `(player, prop, side, line, game_date, soft_book)` to create a deterministic UUID. With `line=None`, the hash was either invalid or produced a single collision UUID for all markets — in either case, no valid picks were persisted to Supabase.

### Why the Dashboard Masked the Bug

The dashboard's EV computation path (`computeEVForTheory()`) iterates over per-book odds entries within each market, reading the line from the book-level data. It never needs a top-level `line` field. This meant the dashboard displayed real-time +EV picks correctly — users could see opportunities, the numbers were accurate — but zero picks were being recorded in Supabase for tracking, trail capture, or historical analysis.

This is a particularly dangerous failure mode: the user-visible output (dashboard picks) appeared healthy while the backend pipeline (pick persistence, trail recording) was completely broken. The divergence was only discovered when trail chart buttons showed empty data for all picks.

### Discovery Chain

The bug was uncovered through a chain of trail chart debugging on 2026-04-26:

1. Trail chart buttons weren't rendering for picks → `pick_id` lookup via `pickIdByKey` only matched cached picks
2. Charts rendering empty despite picks existing → timezone mismatch: browser AEST vs Supabase UTC game dates
3. One specific pick (NAW Blocks Under 0.5) had no Supabase pick at all → investigation revealed ALL markets had `line=None`
4. Root cause confirmed: `MatchedMarket.to_dict()` never included `line`

### The Fix

The fix adds a top-level `line` field to `MatchedMarket.to_dict()` by reading the line from the first main-line book entry in the market's book data. This is a pragmatic fix — different books can theoretically have different lines for the same market, but the first main-line entry is a reasonable default that unblocks the entire pipeline.

Known limitations of the fix:
- The line is computed at serialization time, not persisted on the dataclass
- Different books may disagree on the line value (the fix picks the first one)
- The `market_key` doesn't include line, so two markets at different lines share one key
- Binary props (Blocks, Steals, Double Double) that always have line 0.5 should ideally have a hardcoded fallback

### Impact on Historical Data

Historical picks that were created before the fix via alternative code paths (some picks were created through non-standard flows that provided a line) have valid results, ROI, and CLV — the pick record was correctly populated. What's missing is trail depth for ~40-50% of older picks that had `line=None` at the time Phase B trail collection ran. No data rebuild is needed; the issue is purely forward-looking trail coverage.

### Additional Trail Chart Fixes

The trail chart debugging session also revealed two UI issues:

1. **SSE auto-refresh destroying charts**: The SSE auto-refresh (every 3s) called `render()` which rebuilt the entire table, destroying dynamically inserted chart rows. Fixed by tracking open charts and restoring them after render.
2. **Timezone mismatch**: Browser (AEST) showed April 26 while Supabase stored picks as April 25 (US game dates). Fixed by loading a 3-day window (yesterday + today + tomorrow) in the pick cache.

## Related Concepts

- [[concepts/pick-id-float-int-hashing-bug]] - Another bug where `_generate_pick_id()` received incorrect input (float vs int line), silently breaking trail collection; this bug is the more severe variant where the line was entirely null
- [[connections/silent-type-coercion-data-corruption]] - The broader pattern of plausible wrong output with zero error signal; the dashboard appearing healthy while backend persistence was broken is the most extreme instance
- [[concepts/trail-preseeding-coverage-bug]] - Another silent trail coverage failure from a different root cause (pre-seeding prevented baseline writes); both produce the same symptom: picks exist but trails don't
- [[concepts/dashboard-client-server-ev-divergence]] - The architectural pattern where client-side and server-side consume the same data differently; here the divergence was between "can compute EV" (dashboard, doesn't need top-level line) and "can persist pick" (tracker, needs line for pick_id hash)
- [[concepts/trail-change-detection-architecture]] - Trail change detection was architecturally correct; the entry point (pick creation) was silently failing due to null lines — a "correct pipeline, broken input" pattern

## Sources

- [[daily/lcash/2026-04-26.md]] - ALL 3,101 NBA markets had `line=None` at top level; `line` only existed per-book in `BookOdds`, never on `MatchedMarket`; tracker couldn't create picks (pick_id requires line); dashboard showed picks fine (client-side EV doesn't need top-level line); fix: derive line from first main-line book entry in `to_dict()`; ~43% of historical picks had zero trails; 20/20 picks confirmed generating trails after fix; SSE auto-refresh destroying chart rows fixed; timezone mismatch (AEST browser vs UTC game dates) fixed with 3-day cache window (Sessions 08:20, 11:03)
