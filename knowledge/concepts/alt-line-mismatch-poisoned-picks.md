---
title: "Alt-Line Mismatch Poisoned Picks"
aliases: [poisoned-picks, alt-line-bug, high-ev-contamination, line-mismatch]
tags: [value-betting, data-quality, bug, tracker, interpolation]
sources:
  - "daily/lcash/2026-04-13.md"
created: 2026-04-13
updated: 2026-04-13
---

# Alt-Line Mismatch Poisoned Picks

A recurring data quality bug in the value betting scanner where Australian soft books (PointsBet AU, Sportsbet, Bet365 2.0, Ladbrokes AU) offer alternate lines far from the main line, and the tracker matches these against sharps at the main line. The interpolation between the mismatched lines produces massively inflated EV values (up to 153.7%), creating "poisoned picks" that contaminate the dashboard and backtest data.

## Key Points

- AU soft books offer alt lines (e.g., LeBron Rebounds Over 11.5) when the main line is much lower (e.g., ~8.5) — these are legitimate alt-market offerings, not data errors
- The tracker's `_get_max_line_gap` logic matches these alt-line soft book odds against sharps at the main line, then interpolates — producing phony EV values of 50-200%
- Morning cleanup on 2026-04-13 deleted 1,611 picks with `triggered_ev > 50%` (including 393 at 50-100%), but 10 new poisoned picks appeared within hours — symptom-only treatment
- Root cause requires a fix in `server/tracker.py` line-gap logic: either tighten `_get_max_line_gap`, reject pairs where `line_gap > (line × 0.3)`, or skip interpolation entirely for count props on gaps > 1
- An interpolation fix was deployed and verified by the evening session — 0 new poisoned picks, last pick at 1.72% EV in the trusted 0-15% band

## Details

### The Mechanism

The value betting scanner tracks odds across multiple soft books and compares them against sharp book odds (via OpticOdds) to identify positive expected value. When the tracker encounters a soft book line, it looks for a matching sharp line to calculate EV. If an exact match isn't available, it interpolates between the nearest sharp lines.

The problem arises with alternate lines. Australian soft books frequently offer player prop markets at non-standard lines — for example, "LeBron James Rebounds Over 11.5" when the consensus main line is 8.5. The tracker's line-gap tolerance allows it to match this 11.5 soft line against the nearest sharp line (8.5), producing an interpolated "true probability" that is wildly wrong. Since the soft book is offering decent odds on an extreme line (far over the consensus), the interpolated comparison shows enormous EV — sometimes over 150%.

These are not genuine value opportunities. They are artifacts of comparing odds at incompatible lines. A bettor taking "Over 11.5 rebounds" at the posted odds is not getting 153% EV — they're getting roughly fair odds for a line that's 3 points above the main.

### Recurrence Pattern

The bug was initially treated by bulk-deleting picks with `triggered_ev > 50%` on the morning of 2026-04-13 (1,611 picks removed in a first pass, then 393 more at 50-100%). However, 10 new poisoned picks appeared within hours — the same root cause generating new contamination as AU soft books published new alt lines for the day's games. This confirmed that deletion was only treating the symptom. The root cause required modifying the tracker's interpolation logic.

### The Fix

An interpolation fix was deployed to `server/tracker.py` during the day. The fix tightens the line-gap acceptance criteria so that interpolation is not attempted when the gap between the soft book line and the nearest sharp line exceeds a threshold. For count-based props (rebounds, assists, points), where line values represent discrete counts, a gap of more than 1-2 points is strong evidence of an alt-line mismatch rather than a minor line difference.

Verification in the evening session (22:50) confirmed: zero new poisoned picks since the fix, the most recent pick (Derik Queen Points Over, 1.72% EV) was in the trusted 0-15% band, and the historical count of `triggered_ev > 15%` picks had not grown. The 2,002 historical 15-50% EV picks were deliberately retained as a baseline to measure whether the phenomenon declines over time under the new fix.

### Proposed Approaches

Three approaches were discussed for the tracker fix:
1. **Tighten `_get_max_line_gap`** — reduce the maximum allowed gap between soft and sharp lines globally
2. **Proportional rejection** — reject pairs where `line_gap > (line × 0.3)`, scaling the tolerance with the line value
3. **Skip interpolation for count props** — disable interpolation entirely for rebounds, assists, and similar discrete-count props when the gap exceeds 1

## Related Concepts

- [[concepts/trail-data-temporal-resolution]] - Trail data cleanup performed in the same session as poisoned pick deletion
- [[concepts/opticodds-critical-dependency]] - Sharp odds from OpticOdds are the reference against which interpolation is calculated
- [[concepts/value-betting-operational-assessment]] - The operational assessment did not identify this specific bug, but it falls under the "data quality" gap area
- [[concepts/betstamp-bet365-scraper-migration]] - AU soft books from the game scraper are a primary source of alt-line data

## Sources

- [[daily/lcash/2026-04-13.md]] - Morning: 1,611+393 picks deleted with triggered_ev > 50%; 10 new poisoned picks appeared within hours; root cause identified as alt-line/main-line mismatch in `server/tracker.py` line-gap logic (e.g., LeBron Rebounds Over 11.5 vs main 8.5 producing 153.7% EV); interpolation fix deployed; evening verification: 0 new poisoned picks, last pick at 1.72% EV (Sessions 08:50, 16:31, 22:50)
