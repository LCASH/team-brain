---
title: "bet365 Points Alt-Line Main-Tag Accumulation Bug"
aliases: [main-tag-accumulation, tag-main-lines-oscillation, is-main-demotion-guard, points-alt-line-bug, sticky-main-failure]
tags: [value-betting, bet365, nba, data-quality, bug, architecture]
sources:
  - "daily/lcash/2026-05-27.md"
created: 2026-05-27
updated: 2026-05-27
---

# bet365 Points Alt-Line Main-Tag Accumulation Bug

On 2026-05-27, lcash diagnosed two interacting bugs causing every bet365 NBA Points alt-line to accumulate `is_main=True` after 5-10 wizard refresh cycles. Bug A: `_tag_main_lines()` tags the median-index line as main per refresh, but the line set shifts between refreshes (e.g., Hartenstein spans 2.5-12.5 across 5-9 alt lines), so different lines become median each cycle. Bug B: `state.py:393` guard prevents `is_main=True -> is_main=False` demotion, so once any line was ever the median, it stays main forever. After 5-10 cycles every alt accumulates `is_main=True`, making "main" selection effectively random via `_pick_main` tiebreak by `captured_at` (most recently refreshed alt = "main").

## Key Points

- **Two interacting bugs, not one**: (A) `_tag_main_lines()` tags median index per-refresh, but the line set shifts between refreshes so different lines become median each cycle; (B) `state.py:393` guard prevents `is_main=True→is_main=False` demotion
- **After 5-10 cycles every alt has `is_main=True`** — the guard ratchets up only, never down; once a line was ever tagged main, it stays main permanently
- **`_pick_main` tiebreak by `captured_at`** means "main" = "most recently refreshed alt" — no relationship to actual centre line
- **Points is worse than other props** because bet365 publishes a wider alt-line spread (e.g., Hartenstein 2.5-12.5 across 5-9 lines), amplifying the random-main effect
- **Both (A) and (B) must be fixed together** — (A) alone leaves historical mis-flagged alts in the store; (B) alone doesn't stabilize which line gets tagged
- **No prop_type duplication** confirmed — `EV_NAME_MAP` correctly maps one entry for Points; the issue is purely in the main-line tagging mechanism
- **VPS proxy strips `alts` on serialization** — cosmetic gap only; engine on Eve still sees alts

## Details

### Bug A: Median Index Oscillation

The `_tag_main_lines()` post-processor groups all records by `(player, prop_type, side)`, sorts by line value, and tags the median-index line as `is_main=True`. This was designed to identify the "centre" line — the main line that sharp books also price. However, bet365's wizard doesn't return a fixed set of alt lines on every refresh. The available lines shift based on game state, time to tip-off, and internal pricing cycles. A refresh at time T might return lines [17.5, 24.5, 30.5] (median = 24.5), while T+30s returns [19.5, 24.5, 30.5, 37.5] (median = 27.5 interpolated, or index-based = 24.5 or 30.5).

Each refresh independently computes the median from its current line set, which means different lines get tagged as main on different cycles. This produces oscillating main-line assignment that never stabilizes.

### Bug B: is_main Demotion Guard

The DataStore at `state.py:393` contains a guard that prevents `is_main` from being demoted from `True` to `False`. The intent was to protect against alt-line writes accidentally demoting a legitimately main-line record. However, combined with Bug A's oscillating tagging, this guard creates a ratchet: every line that was EVER tagged as median (on any refresh cycle) retains `is_main=True` permanently.

After 5-10 refresh cycles, the oscillation has visited most or all alt lines as the median at least once. At that point, every alt line in the group has `is_main=True`. The `_pick_main` function, which should select the one true main line, falls through to a tiebreak by `captured_at` — selecting whichever line was most recently refreshed. This is effectively random selection, unrelated to the actual centre/consensus line.

### Why Points Is Most Affected

Points markets have the widest alt-line spread of any NBA prop type. A player like Hartenstein might have lines spanning 2.5 to 12.5 — a 10-point range across 5-9 alt lines. Other props (Rebounds 3.5-7.5, Assists 1.5-5.5) have narrower ranges and fewer alts, so the median oscillation is less dramatic. The wider the alt-line spread, the more cycles it takes for the oscillation to visit all lines, but also the more wrong the eventually-random "main" selection becomes.

### Required Fix

Both bugs must be fixed simultaneously:

**Fix A (stabilize tagging):** Implement a sticky-main approach where the main line is determined once (e.g., closest to the sharp consensus) and remembered across refreshes, rather than re-computed from the median of each refresh's variable line set. ~20 LOC in `ws_nba.py:_tag_main_lines()`.

**Fix B (allow demotion):** Either remove the `is_main` demotion guard in `state.py` so `_tag_main_lines` can clear `is_main=False` on all non-main lines in each group, or have `_tag_main_lines` explicitly propagate `is_main=False` through upsert for all non-chosen lines.

Fix A without Fix B leaves historical mis-flagged alts in the store with `is_main=True`. Fix B without Fix A allows demotion but doesn't stabilize which line gets tagged, so the rapid oscillation continues (just without accumulation).

## Related Concepts

- [[concepts/nba-milestone-prop-collision-bug]] - The prior diagnosis (May 22) identified two bugs (milestone vs O/U collision + alt-line overwrite) but did not capture the state accumulation mechanism; this article expands the diagnosis
- [[concepts/bet365-same-book-alt-line-collision]] - The `_tag_main_lines()` post-processor was deployed for the same-book alt-line collision; the accumulation bug is a second-order failure of the same mechanism
- [[concepts/push-loop-diff-cache-phantom-freshness]] - Diff cache Bug 1 (alt-line flapping) is the cache-layer manifestation of the same underlying problem
- [[connections/market-key-dateless-design-recurring-bugs]] - The lineless market_key design enables alt-line collisions; the main-tag accumulation is the mechanism by which the `is_main` guard (intended to prevent them) fails

## Sources

- [[daily/lcash/2026-05-27.md]] - Deep investigation confirmed bet365 emits 5-9 alt lines per (player, Points, side); every alt has is_main=True in state store after 5-10 cycles; Bug A: _tag_main_lines() median oscillation from shifting line sets; Bug B: state.py:393 guard prevents is_main demotion, creating ratchet; _pick_main tiebreak by captured_at = random; Points worst because widest alt spread (Hartenstein 2.5-12.5); both fixes needed together; no EV_NAME_MAP duplication confirmed (Session 10:55)

```
