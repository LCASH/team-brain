---
title: "bet365 Same-Book Alt-Line Collision"
aliases: [alt-line-collision, tag-main-lines, same-book-multi-line, is-main-tagging, bet365-alt-line-overwrite]
tags: [value-betting, bet365, scraping, data-quality, bug, architecture]
sources:
  - "daily/lcash/2026-05-15.md"
created: 2026-05-15
updated: 2026-05-15
---

# bet365 Same-Book Alt-Line Collision

On 2026-05-15, lcash discovered that bet365 emits 3 Over/Under lines per player per prop type (low/main/high alt lines) under the same market group in the BB wizard response. Since `market_key = (player, prop_type, side)` drops the line, all three alt lines map to the same DataStore key. The last-write-wins race between these variants causes random alt-line odds to be stored as "the" odds for that market, producing fake +EV picks (e.g., +130% EV) when a high alt-line's long odds are paired against sharp consensus at the main line. The fix is a `_tag_main_lines()` post-processor that groups by `(player, prop_type, side)`, sorts by line, tags the median as `is_main=True`, and tags the rest as `is_main=False`. The existing DataStore guard at `state.py:285-287` then correctly blocks alt→main overwrites.

## Key Points

- bet365 wizard emits **3 O/U lines per player** (e.g., Points Over 19.5, Over 25.5, Over 31.5) under the same market group — "Points High" and "Points Low" are alt lines, not separate market types
- `market_key = (player, prop_type, side)` intentionally drops line for cross-book aggregation — but same-book multi-line creates a **last-write-wins collision** within a single book
- `state.py:285-287` had the correct `is_main` guard to prevent alt→main overwrites, but it was **a silent no-op** because the parser never set `is_main=False` — defensive guard without a data source
- `_tag_main_lines()` hooked into all 3 parser entry points: `_parse_i19_coupon`, `_parse_nba_body`, `_parse_nba_body_with_mg`
- The same alt-line collision exists in **OpticOdds soft books** (PointsBet AU confirmed showing 2-5x fake "moves" from alt-line flips) — a cross-cutting concern across all parsers
- Distinct from the cross-book alt-line mismatch in [[concepts/alt-line-mismatch-poisoned-picks]] which is about interpolation across different books' lines; this is about same-book multi-line overwriting within a single scraper

## Details

### The Collision Mechanism

The bet365 BB wizard endpoint (`betbuilderpregamecontentapi/wizard`) returns player props grouped by market type. For a player like Anthony Edwards, the "Player Points" section contains not one but three Over/Under line variants:

- **Low alt**: Points Over 19.5 @ 1.06 (near-certainty)
- **Main line**: Points Over 25.5 @ 1.83 (consensus line)
- **High alt**: Points Over 31.5 @ 4.50 (longshot)

All three map to `market_key = ("Anthony Edwards", "Points", "Over")` because `market_key` deliberately excludes `line`. The DataStore processes these sequentially during a wizard parse. If the high alt (Over 31.5 @ 4.50) is the last to write, the stored odds become 4.50 — the longshot price. When the devig engine then compares this against Pinnacle's main line at 25.5 (true probability ~50%), the EV calculation sees "soft book offers 4.50 (implied 22%) vs true probability 50% → +130% EV." This is entirely phantom — the 4.50 odds are for a structurally different bet (Over 31.5) than what the sharp reference prices (Over 25.5).

### Why the Guard Was Silent

The DataStore at `state.py:285-287` already contained a guard: if an incoming market has `is_main=False`, it cannot overwrite a market that has `is_main=True`. This is architecturally correct — alt lines should never replace the main line in the canonical store. However, the bet365 parser never set `is_main` on any record — all markets defaulted to `is_main=True` (or the field was absent). The guard never fired because no incoming market ever presented itself as non-main.

This is a general anti-pattern: **defensive guards that rely on upstream data which is never provided are functionally dead code.** The guard passed all code review (correct logic) and all testing (never triggered) while providing zero protection in production.

### The `_tag_main_lines()` Post-Processor

The fix introduces a post-processing step after the parser extracts all PA records from the wizard response:

1. Group all records by `(player, prop_type, side)`
2. Within each group, sort by `line` value
3. Tag the median line as `is_main=True`
4. Tag all other lines as `is_main=False`

The median was chosen over the minimum or maximum because it corresponds to the consensus main line — the line that sharp books also price. The low and high alts are typically equidistant from the main line. After tagging, the DataStore's existing guard correctly prevents alt lines from overwriting the main line.

The tagger is hooked into all three NBA parser entry points to ensure coverage regardless of which response format the wizard uses on a given day.

### Cross-Cutting Concern

The same collision pattern exists in two other parsers:

- **MLB bet365 parser** (`ws_mlb_v4.py::_parse_mlb_wizard_to_pa_map`): MLB wizard also emits multiple lines per player prop. The port of `_tag_main_lines` requires capturing a live MLB wizard body first to verify the multi-line shape.
- **OpticOdds parser** (`v3/opticodds.py`): AU soft books like PointsBet AU also emit alt lines for the same player prop. SSE events arrive one at a time (not in batch), so the tagging requires per-book state tracking rather than batch post-processing.

The PointsBet AU collision was confirmed during trail investigation: sharp trail entries showed 2-5x fake "moves" that were actually alt-line flips within the same book, not genuine market movement.

## Related Concepts

- [[concepts/alt-line-mismatch-poisoned-picks]] - Cross-book alt-line mismatch (tracker interpolates between mismatched lines from different books); this article covers same-book multi-line collision (one book's alt lines overwrite each other)
- [[connections/market-key-dateless-design-recurring-bugs]] - The `market_key` dropping `line` is the architectural root cause; this is the fifth documented manifestation of the dateless/lineless key design
- [[concepts/push-loop-diff-cache-phantom-freshness]] - Diff cache Bug 1 (alt-line flapping) is the same collision at the cache layer; `_tag_main_lines` prevents it at the parser layer
- [[concepts/co-ou-parser-conflation-phantom-picks]] - A parallel parser-level data quality bug discovered in the same session; CO milestones conflated with O/U markets

## Sources

- [[daily/lcash/2026-05-15.md]] - User reported "Points High" and "Points Low" creating bad data; traced to 3 alt O/U lines per player under same market group; `_tag_main_lines()` post-processor tags median as `is_main=True`; hooked into all 3 parser entry points; `state.py:285-287` guard was silent because parser never set `is_main=False`; PointsBet AU alt-line flips confirmed in trails; committed as `bcfe2e7` with writeup at `brain/findings/2026-05-14-bet365-nba-alt-line-collision.md` (Sessions 09:57, 10:04)
