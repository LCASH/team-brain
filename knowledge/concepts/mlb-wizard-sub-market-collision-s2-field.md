---
title: "MLB Wizard Sub-Market Collision and S2 Field Disambiguation"
aliases: [mlb-sub-market-collision, s2-field-disambiguation, wizard-ev-section-flattening, hits-singles-doubles-triples-collision]
tags: [value-betting, bet365, mlb, scraping, data-quality, parser, bug]
sources:
  - "daily/lcash/2026-05-13.md"
created: 2026-05-13
updated: 2026-05-13
---

# MLB Wizard Sub-Market Collision and S2 Field Disambiguation

The bet365 MLB BB wizard packs multiple sub-stats (Hits, Singles, Doubles, Triples, Batter Walks) into a single EV section called "Player Hits." The `S2` field in each PA record carries the actual stat name (e.g., "Over 0.5 Singles"), but the parser was using the EV-section header as `prop_type`, causing all sub-stats to collapse under `prop_type="Hits"`. This produced 229 apparent "data anomalies" on the coverage dashboard and 93 collision keys with 222 duplicate entries. After extracting the actual stat from S2, collisions dropped 88% (93→11 keys, 222→30 dupes) and new prop types began flowing: Singles, Doubles, Triples, and Batter Walks.

## Key Points

- MLB wizard EV section "Player Hits" contains PA records for 4 sub-stats: Hits, Singles, Doubles, Triples — all mapped to `prop_type="Hits"` by the parser
- The `S2` field is the disambiguator: `S2="Over 0.5 Singles"` vs `S2="Over 0.5 Hits"` — the EV section header is misleading
- **229 "data anomalies" on coverage page were sub-stat collisions** — Triples odds (26.0) appearing as Hits @ 26.0; only 2 genuine outliers after fix
- Parser fix: extract actual stat from `S2` field via regex (strip "Over/Under {line}" prefix), use as canonical `prop_type`
- OpticOdds already exposes Singles (288 markets), Doubles (288), Triples (145) as separate prop_types — the parser just needed to match
- 11 residual collisions from milestone records (`is_main=False`) — a separate concern from the main prop_type fix
- Collision WARNING throttled to once/60s/sport to maintain visibility without log spam

## Details

### The EV Section Flattening Bug

The MLB BB wizard endpoint (`betbuilderpregamecontentapi/wizard`) structures its response hierarchically. At the top level, EV sections group markets by category — "Player Hits," "Player Bases," "Player Strikeouts," etc. Within each EV section, PA records contain individual player lines with odds. The parser extracted the EV section name as the `prop_type` for every PA record in that section.

This works correctly for most EV sections where one section = one stat type. But "Player Hits" is an exception: it contains PA records for Hits, Singles, Doubles, and Triples — four distinct statistical categories. The parser assigned `prop_type="Hits"` to all four, making them indistinguishable downstream.

The collision manifests when the diff cache or any downstream consumer processes multiple sub-stats with the same `(player, prop_type="Hits", side, line)` key. Three different odds values appear for the same logical key — for example, a player's Hits at 1.714, Singles at 4.75, and Triples at 26.0 — producing phantom churn in the push loop (see [[concepts/push-loop-diff-cache-phantom-freshness]], Bug 3).

### The S2 Field

Each PA record in the wizard response contains an `S2` field with the full proposition description: `"Over 0.5 Singles"`, `"Over 1.5 Hits"`, `"Under 2.5 Doubles"`. This field carries the actual stat name that the EV section header hides. The parser fix extracts the stat name from S2 using regex to strip the "Over/Under {line}" prefix, then uses this as the canonical `prop_type`.

For the "Player Hits" section, this transforms:
- `S2="Over 1.5 Hits"` → `prop_type="Hits"` (unchanged)
- `S2="Over 0.5 Singles"` → `prop_type="Singles"` (newly disambiguated)
- `S2="Over 0.5 Doubles"` → `prop_type="Doubles"` (newly disambiguated)
- `S2="Over 0.5 Triples"` → `prop_type="Triples"` (newly disambiguated)

### Coverage Impact

The fix immediately unlocked new prop types that were previously invisible to the scanner:

| New Prop Type | OpticOdds Markets | Status |
|---------------|-------------------|--------|
| Singles | 288 | Now flowing from Bet365 |
| Doubles | 288 | Now flowing from Bet365 |
| Triples | 145 | Now flowing from Bet365 |
| Batter Walks | ~100 | Now flowing from Bet365 |

OpticOdds already exposed these as separate prop types with sharp book coverage, so the devigging pipeline can evaluate them immediately. The scanner was leaving edge opportunities on the table by collapsing them all under "Hits."

### Diagnostic: One-Shot Debug Dump

The root cause was identified using a one-shot debug dump pattern: deploy a temporary data dump to `/tmp/vb_debug/`, wait for a collision to occur, inspect the raw wizard body to see the actual S2 field values, then remove the debug code. This was more productive than trying to reproduce the collision in isolation because the collision only manifests under production conditions with real wizard data containing multiple sub-stats.

### Residual Milestone Collisions

After the S2 fix, 11 collision keys and 30 duplicate entries remained. These are from milestone records (`is_main=False`) — threshold-style props like "1+ Hits" that collide with the same stat's O/U record at line 0.5. This is a separate concern from the sub-stat flattening and is handled by the `is_main` dimension in the diff cache key (see [[concepts/push-loop-diff-cache-phantom-freshness]], Bug 2).

### Theory Configuration Gap

Separately, 7 of 16 target books produced zero picks due to theory configuration gaps, not code bugs. Five MLB books (907, 909, 911, 980-982) were not listed in any MLB theory's `soft_books` array. This is a Supabase configuration change, not a code fix — the scraper data is flowing but the theories don't know to evaluate it.

## Related Concepts

- [[concepts/push-loop-diff-cache-phantom-freshness]] - The diff cache where sub-market collisions (Bug 3) were first detected; first-wins dedupe was the interim fix
- [[concepts/bet365-mlb-wizard-first-regression-fix]] - The MLB wizard endpoint whose S2 field carries the disambiguation data; the wizard format's `S1=PlayerName`, `S2=20+ Points` structure documented there
- [[concepts/bet365-mlb-batch-api-co-format]] - The batch API's CO segment format which is a different data representation of the same MLB props; CO milestones and S2-disambiguated wizard records need alignment
- [[concepts/co-milestone-one-sided-pairing-imbalance]] - CO milestones are structurally one-sided Overs; the milestone collisions remaining after the S2 fix are the same class of data
- [[connections/silent-type-coercion-data-corruption]] - Sub-market collisions are another "plausible wrong output" pattern: Triples odds appearing as Hits @ 26.0 doesn't crash anything, just produces wrong EV calculations

## Sources

- [[daily/lcash/2026-05-13.md]] - MLB wizard S2 field carries actual stat (Hits/Singles/Doubles/Triples) but parser used EV-section header; 229 "data anomalies" → 2 genuine outliers after fix; collisions dropped 88% (93→11 keys, 222→30 dupes); OpticOdds already has Singles 288, Doubles 288, Triples 145 markets; collision WARNING throttled 1/60s/sport; one-shot debug dump to /tmp/vb_debug/ identified root cause; 7 books with zero picks traced to theory soft_books config not code (Sessions 12:07, 13:25)
