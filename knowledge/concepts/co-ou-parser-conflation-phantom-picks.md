---
title: "CO/OU Parser Conflation Phantom Picks"
aliases: [co-ou-conflation, milestone-ou-conflation, phantom-co-picks, co-suffix-fix, co-quarantine]
tags: [value-betting, bet365, mlb, data-quality, bug, parser, cleanup]
sources:
  - "daily/lcash/2026-05-15.md"
created: 2026-05-15
updated: 2026-05-15
---

# CO/OU Parser Conflation Phantom Picks

On 2026-05-15, lcash discovered that MLB bet365 parsers were conflating CO (milestone/Column) markets with Over/Under (O/U) markets because milestone props lacked a distinguishing suffix. Milestones like "1+ HR" at line 0.5 entered the DataStore under the same `prop_type` as "HR Over/Under" — and when the devig pipeline paired milestone odds against O/U sharp lines, it produced phantom +EV signals averaging +20.84% triggered_ev with only 9% actual win rate. **72% of the last 24 hours of MLB Bet365 picks (349/483) were phantoms.** The fix appends a `_CO` suffix to all milestone prop types across four parser files, preventing milestone→O/U sharp pairing. A quarantine script tagged 3,908 definite phantom-CO historical rows using the existing `pick_filter_reason` column.

## Key Points

- CO milestone markets (1+ HR at line 0.5, 3+ strikeouts at line 2.5) entered the DataStore with the same `prop_type` as O/U markets — no suffix distinguished them
- The devig + interpolation pipeline then applied sharp O/U closing lines to milestone odds, producing phantom +EV at massive scale: **72% of recent MLB Bet365 picks were phantoms**
- **Smoking gun diagnostic**: `line ∈ {0.5, 1.5, 2.5, 3.5}` + `opening_odds ≥ 5` + prop in conflation set = definite phantom. 7.9% win rate on this bucket confirmed these were milestone bets (rare events) incorrectly tracked as +EV
- Fix: `_CO` suffix applied to all four parser files (`ws_mlb.py`, `ws_nba.py`, `ws_nrl.py`, `ws_afl.py`) — NRL/AFL confirmed not affected (single-side binary markets) but fixed defensively
- Historical cleanup: 3,908 "definite" rows tagged via `pick_filter_reason = 'phantom_co_milestone'` using existing migration-033 column — fully reversible via `--undo` flag
- 1,619 "likely" rows (opening_odds 3-5, 25.8% win rate) held back as too ambiguous for mass-tagging without spot-checking
- Also added 4 missing pitcher prop EV name mappings (Hits Allowed, Earned Runs, Outs, Pitcher Walks) based on May 6 G-ID discovery doc

## Details

### The Conflation Mechanism

The bet365 BB wizard response contains both O/U markets ("Player Home Runs Over 0.5 @ 1.83") and CO milestone markets ("1+ Home Runs @ 1.83") for the same player. These are structurally different bet types: the O/U market has two sides (Over and Under) that can be devigged against each other, while the milestone is a one-sided threshold bet with no natural pair. However, both mapped to `prop_type = "Home Runs"` in the parser output.

When the DataStore received both record types under the same key, the devig pipeline couldn't distinguish them. The critical failure occurs during sharp pairing: sharp books (Pinnacle, DraftKings) offer standard O/U markets. The tracker found the milestone's odds (e.g., Over 0.5 at 1.20 for "1+ Home Runs" — a near-certainty) and paired them against the sharp's O/U line at a completely different point (e.g., Over 0.5 at 1.83 for the standard market). The interpolation engine then computed phantom EV from this structurally invalid comparison.

The phantom signature is distinctive: milestone lines cluster at round half-integers (0.5, 1.5, 2.5, 3.5) representing "1+", "2+", "3+", "4+" thresholds, and their opening odds are typically ≥5 for higher thresholds (e.g., "3+ Home Runs" is a rare event with long odds). The 7.9% win rate on the "definite" bucket confirmed these were milestone bets — rare events that hit at their natural probability, not the inflated implied probability the phantom EV suggested.

### Scale of Damage

The conflation was massive: 72% of recent MLB Bet365 picks were phantoms. The average phantom `triggered_ev` was +20.84%, inflating all Bet365 MLB theory ROI analytics. This distortion affected every downstream consumer: the dashboard displayed phantom edges, the resolver graded milestone bets as if they were standard O/U picks, and the CLV calculations compared milestone outcomes against O/U baselines.

The damage was separated into two confidence buckets:

| Bucket | Criteria | Rows | Win Rate | Confidence |
|--------|----------|------|----------|------------|
| **Definite** | line ∈ {0.5,1.5,2.5,3.5}, opening_odds ≥ 5 | 3,908 | 7.9% | High — clearly milestone bets |
| **Likely** | line ∈ {0.5,1.5,2.5,3.5}, opening_odds 3-5 | 1,619 | 25.8% | Ambiguous — could be legitimate short-line O/U |

Only the definite bucket was quarantined. The "likely" bucket's 25.8% win rate is plausible for both milestones at moderate thresholds and legitimate short-line O/U props — mass-tagging without individual spot-checking could destroy valid data.

### The CO Suffix Fix

The fix appends `_CO` to the `prop_type` for all milestone markets in four parser files:

- `ws_mlb.py` — MLB bet365 parser (primary target)
- `ws_nba.py` — NBA bet365 parser (had the same conflation)
- `ws_nrl.py` — NRL bet365 parser (confirmed not affected but fixed defensively)
- `ws_afl.py` — AFL bet365 parser (confirmed not affected but fixed defensively)

After the fix, milestone markets map to `prop_type = "Home Runs_CO"` while O/U markets remain `prop_type = "Home Runs"`. Since no sharp book offers markets under the `_CO` suffix, the devig pipeline naturally orphans milestone records — they have no sharp pair and produce zero picks. This is the correct behavior: CO milestones have no sharp counterpart for devigging (see [[concepts/co-milestone-one-sided-pairing-imbalance]]).

### Quarantine via pick_filter_reason

Historical cleanup uses the `pick_filter_reason` column from migration 033 — a pre-existing infrastructure designed for exactly this purpose. Tagged rows are automatically excluded from `/api/v1/results` ROI calculations and the dashboard by existing filter logic in `analytics.py` and `main.py`. The quarantine is fully reversible: running the cleanup script with `--undo` clears the filter reason from all tagged rows.

Three rows out of 3,908 required manual PATCH because new picks flowed in during the tagging window — a timing edge case in batch cleanup scripts operating against a live database.

### Relationship to _tag_main_lines

The `_tag_main_lines()` fix (see [[concepts/bet365-same-book-alt-line-collision]]) deployed in the same session addresses a related but distinct problem: alt O/U lines overwriting the main line within the same book. `_tag_main_lines` wouldn't catch the CO/OU conflation because milestone records passed through the parser on the same `prop_type` key as legitimate O/U records — the tagging distinguished alt vs main within O/U, not O/U vs CO.

## Related Concepts

- [[concepts/co-milestone-one-sided-pairing-imbalance]] - CO milestones are structurally one-sided with no sharp pair; the conflation bug paired them against O/U sharps that don't represent the same market
- [[concepts/bet365-same-book-alt-line-collision]] - A parallel parser-level bug discovered in the same session; alt O/U lines colliding under the same market_key
- [[concepts/mlb-wizard-sub-market-collision-s2-field]] - A related MLB wizard parser bug where sub-stats (Hits/Singles/Doubles/Triples) collided under one EV section header
- [[concepts/push-loop-diff-cache-phantom-freshness]] - Bug 2 (missing `is_main`) was a diff-cache-level variant of the O/U vs milestone collision
- [[connections/market-key-dateless-design-recurring-bugs]] - The lineless market_key design enables conflation because milestone (line 0.5) and O/U (line 1.5+) share a key
- [[connections/silent-type-coercion-data-corruption]] - Phantom +20.84% EV with 9% win rate is another "plausible wrong output" — the EV values looked real, the pipeline reported no errors

## Sources

- [[daily/lcash/2026-05-15.md]] - User reported dashboard discrepancies on MLB markets; traced to CO milestone conflation with O/U; 72% (349/483) of recent MLB Bet365 picks were phantoms; definite bucket (3,908 rows) quarantined via pick_filter_reason; 4 missing pitcher EV name mappings added (Hits Allowed, Earned Runs, Outs, Walks); NRL/AFL parsers confirmed immune (single-side binary markets); committed and deployed to mini PC and VPS (Sessions 10:30, 12:22, 14:58)
