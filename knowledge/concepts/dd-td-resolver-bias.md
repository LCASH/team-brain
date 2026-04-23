---
title: "DD/TD Resolver Encoded Stat Bug"
aliases: [double-double-resolver, triple-double-resolver, dd-td-mis-grading, opticodds-encoded-stats, dd-td-resolver-bug]
tags: [value-betting, resolver, data-quality, bug, opticodds]
sources:
  - "daily/lcash/2026-04-16.md"
  - "daily/lcash/2026-04-17.md"
  - "daily/lcash/2026-04-23.md"
created: 2026-04-16
updated: 2026-04-23
---

# DD/TD Resolver Encoded Stat Bug

The value betting scanner's Double Double (DD) and Triple Double (TD) resolver was trusting OpticOdds' `player_double_double` stat field, which is NOT a binary 0/1 flag but an encoded stat-line concatenation (e.g., `1.280707` = 28 points, 7 rebounds, 7 assists). The `> 0.5` comparison against this field produced incorrect resolution for **645 of 773 picks** (83.4% mis-grading rate). The fix computes DD/TD from individual stat primitives (`player_points`, `player_rebounds`, `player_assists`, `player_steals`, `player_blocks`), counting categories ≥ 10.

## Key Points

- OpticOdds' `player_double_double` field is an encoded stat-line concatenation (format: `1.PPRRAA` where PP=points, RR=rebounds, AA=assists), NOT a binary 0/1 indicator
- The `> 0.5` comparison against this encoded float produced incorrect win/loss grades for 645 of 773 picks — the 100% Over / 0% Under "bias" was actually a mis-grading bug
- Fix: compute DD/TD from primitives — count `(pts, reb, ast, stl, blk)` categories with value ≥ 10; DD = count ≥ 2, TD = count ≥ 3 — at `server/resolver.py:546-570`
- Full audit of all other prop types confirmed DD/TD was the ONLY resolver defect — combo props (PRA, PR, PA, RA) cross-verified against individual stat sums with zero mismatches across 49 spot-checks
- 111 picks couldn't be re-resolved due to player name matching failures — nulled out for production resolver retry after deployment
- 768 total DD/TD picks collapse to 291 unique `(player, prop, side, game)` combos — 62% duplicates from soft_book_id in the pick hash

## Details

### The Encoding Discovery (2026-04-17)

On 2026-04-17, lcash investigated the 100% Over / 0% Under win rate anomaly flagged on 2026-04-16 and discovered the root cause: OpticOdds' `player_double_double` field is not a binary flag but an encoded stat-line concatenation. The encoding pattern packs stat digits as a decimal number: the first digit is always `1`, followed by pairs of digits representing each stat category. For example, `1.280707` decodes to 28 points, 7 rebounds, 7 assists — clearly NOT a Double Double (only one category ≥ 10).

The resolver's `actual_stat > 0.5` comparison treated ANY value above 0.5 as "DD achieved." Since the encoding always produces values ≥ 1.0 when any stats are present (the leading `1.` is part of the format), virtually every pick resolved as "Over wins" regardless of whether the player actually achieved a Double Double. This explains the 100% Over win rate: it was not a market bias or sampling artifact — it was a systematic mis-grading bug where every player with any stats was counted as having achieved a DD.

Re-resolution using the correct methodology (computing DD from individual stat primitives) showed that 645 of 773 picks had been graded incorrectly — an 83.4% error rate. The previous article's hypotheses about sampling bias, market structure, and small Under samples were all wrong; the asymmetry was entirely caused by the encoding assumption.

### The Correct Resolution Method

The fix at `server/resolver.py:546-570` replaces the OpticOdds trust with local computation:

1. Fetch individual stats: `player_points`, `player_rebounds`, `player_assists`, `player_steals`, `player_blocks`
2. Count how many categories have a value ≥ 10
3. DD Over wins if count ≥ 2; TD Over wins if count ≥ 3
4. Under wins if the count is below the threshold

This approach is immune to OpticOdds' encoding choices because it uses only the primitive integer stat fields (points=28, rebounds=7, etc.), which are clean and correct. The `player_double_double` field is no longer consulted.

### Full Prop Type Audit

The DD/TD discovery prompted a full audit of every prop type in the resolver. The audit confirmed that DD/TD was the **only** defective resolver path:

- **Core NBA props** (Points, Rebounds, Assists, Threes, Steals, Blocks, Turnovers): Use clean integer stats from OpticOdds — correct
- **Combo props** (PRA, PR, PA, RA): Cross-verified by summing individual stat fields — 49 spot-checks, zero mismatches
- **MLB props** (Hits, RBIs, Strikeouts, Home Runs, Stolen Bases): Use clean integer stats — correct
- **AFL props** (Disposals, Goals): Use clean integer stats — correct
- **MLB rare events** (HR Over 9%, SB Over 9%, Triples Over 0%): Correctly graded but represent bad pick selection, not resolver bugs

### Player Name Matching Failures

111 of 773 DD/TD picks could not be re-resolved because OpticOdds' stat data uses slightly different player name formatting than the tracked picks (e.g., "De'Aaron Fox" vs "DeAaron Fox", or "P.J. Washington" vs "PJ Washington"). These picks were nulled out (`outcome = NULL`) rather than force-matched, allowing the production resolver's fuzzy matching logic to handle them automatically after the fix is deployed.

### Pick Deduplication Inflation

The pick ID hash at `server/tracker.py:88-91` includes `soft_book_id`, so the same player+prop+game generates separate pick IDs per soft book. 768 total DD/TD picks collapse to 291 unique `(player, prop, side, game)` combos — 62% duplicates. The fix belongs in the analytics layer, not the tracker. See [[concepts/pick-dedup-multi-theory-limitation]] for the design principle.

### Three Forward Rules

The DD/TD investigation codified three rules for future development:

1. **Never trust pre-computed derived stats from APIs — compute from primitives.** The encoded `player_double_double` field was the sole input to the resolver; cross-checking against individual stats would have immediately revealed the discrepancy.
2. **Extreme win rates (>90% or <10% on 20+ picks) are a bug signal, not an edge.** 100% win rate on 350+ picks should have triggered an automatic sanity alert, not gone unnoticed for weeks.
3. **Pick deduplication is needed at the analytics layer.** The 2.6x inflation obscures anomalies in the noise and makes manual audits harder.

### Packed Field as Potential Cross-Check (2026-04-23)

On 2026-04-23, a Wembanyama DD pick was graded incorrectly because OpticOdds returned **truncated component stats** (5 pts / 4 reb / 1 ast / 12 min — only Q1-Q2 data) while the packed `player_double_double` field was `1.501040001`, suggesting ~50 pts / ~10 reb from the full game. The resolver's fix to compute from primitives — correct for the encoding bug — produced a wrong result because the primitives themselves were incomplete.

This reveals a potential second use for the packed field: as a **cross-check** against component-derived resolutions. When the packed field disagrees with the component derivation (e.g., packed suggests DD achieved but components show 0 categories ≥ 10), the pick should be flagged for manual review rather than auto-graded. The packed field appears to be populated from a different data pipeline that may have more complete data in partial-response scenarios.

See [[concepts/opticodds-partial-stats-silent-misresolution]] for the full analysis of the partial stats failure mode.

## Related Concepts

- [[concepts/opticodds-partial-stats-silent-misresolution]] - Second-order consequence of the primitives fix: when components are truncated, the previously-dismissed packed field may contain more complete data
- [[concepts/opticodds-critical-dependency]] - The encoded stat field is an OpticOdds-specific data quality issue; trusting it without verification amplifies the single-provider risk
- [[concepts/pick-dedup-multi-theory-limitation]] - The pick dedup architecture that produces the 2.6x inflation; analytics-layer dedup established as the correct fix location
- [[concepts/one-sided-consensus-structural-bias]] - Another Over/Under asymmetry (951:13) from a different root cause (structural method bug vs. encoding assumption)
- [[concepts/value-betting-theory-system]] - DD/TD theories need no configuration change — the resolver fix is sufficient
- [[connections/silent-type-coercion-data-corruption]] - The broader pattern of implicit type/encoding assumptions producing plausible but wrong results

## Sources

- [[daily/lcash/2026-04-16.md]] - Initial DD/TD investigation: 100% Over / 0% Under win rate flagged; encoded floats like 1.402040003 noted; 768→291 dedup (62% inflation); resolution trusted OpticOdds entirely (Session 14:45)
- [[daily/lcash/2026-04-17.md]] - Encoding decoded: `player_double_double` is stat-line concatenation (1.PPRRAA), NOT binary; 645/773 picks mis-graded (83.4%); fix: compute from primitives (pts, reb, ast, stl, blk ≥ 10); full audit confirmed DD/TD was ONLY resolver defect; combo props zero mismatches across 49 checks; 111 unresolvable nulled for production retry; three forward rules codified (Sessions 13:15, 13:56, 14:52)
- [[daily/lcash/2026-04-23.md]] - Wembanyama DD pick mis-resolved: OpticOdds returned truncated stats (5 pts / 4 reb / 1 ast / 12 min) while packed field `1.501040001` suggested full-game DD achieved; component derivation correct in principle but fails on incomplete data; packed field identified as potential cross-check source (Session 18:23)
