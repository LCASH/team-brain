---
title: "OpticOdds Partial Stats Silent Mis-Resolution"
aliases: [partial-stats, truncated-stats, incomplete-api-stats, wembanyama-resolution-bug, minutes-played-check]
tags: [value-betting, opticodds, resolver, data-quality, bug]
sources:
  - "daily/lcash/2026-04-23.md"
created: 2026-04-23
updated: 2026-04-23
---

# OpticOdds Partial Stats Silent Mis-Resolution

OpticOdds can return truncated/partial player stat lines — only a portion of a game's stats present — with no completeness flag or quality indicator. The resolver grades picks based on these incomplete stats, producing silently wrong resolutions. Discovered via a Wembanyama Double Double pick graded as Loss (Under wins) when the packed `player_double_double` field suggested he achieved a DD. The component stats showed only 5 pts / 4 reb / 1 ast / 12 minutes — clearly truncated Q1-Q2 data with Q3/Q4 all zeros.

## Key Points

- OpticOdds returned truncated stats for Wembanyama in April 22 Spurs vs Blazers: 5 pts / 4 reb / 1 ast / 12 min — partial game data with no incompleteness flag
- The packed `player_double_double` field was `1.501040001` (encoding ~50 pts, 10 reb, 4 ast) suggesting a DD was achieved, but the resolver ignores this field entirely
- The resolver's `_derive_binary_compound()` computes DD/TD from component stats only — which was the CORRECT fix for the encoding bug (see [[concepts/dd-td-resolver-bias]]) but fails when components themselves are truncated
- No minutes-played sanity check exists — a player with 12 minutes in a game that went regulation should raise a data quality flag before grading
- This is a different failure mode than the DD/TD encoding bug: that bug had WRONG interpretation of a field; this bug has CORRECT interpretation of WRONG data

## Details

### The Failure Mechanism

The value betting resolver fetches player stats from OpticOdds' `/fixtures/results` API to grade picks. For binary compound props like Double Double, the resolver was previously fixed (see [[concepts/dd-td-resolver-bias]]) to compute from individual stat primitives (`player_points`, `player_rebounds`, `player_assists`, `player_steals`, `player_blocks`) rather than trusting the packed `player_double_double` field. This fix was correct: the packed field uses an encoded stat-line concatenation that was being misinterpreted as a binary flag.

However, the fix created a new vulnerability: if the individual stat components themselves are incomplete, the derivation produces a wrong result from the wrong direction. In the Wembanyama case, OpticOdds returned stats covering only ~12 minutes of play (likely Q1-Q2 only) with all later quarters showing zeros. The resolver computed: 5 pts + 4 reb + 1 ast = 0 categories ≥ 10 → no Double Double → Under wins. But the packed field `1.501040001` — which appears to encode the full game stats (~50 points, ~10 rebounds) — suggested he DID achieve a DD.

The packed field, previously identified as unreliable due to its encoding format, may actually contain more complete data than the component fields in cases of partial API responses. This creates an ironic inversion: the fix for one data quality issue (encoding misinterpretation) exposed vulnerability to another (data completeness).

### No Completeness Signal

The most dangerous aspect of this bug is that OpticOdds provides no indication that the returned stats are partial. The API returns HTTP 200 with valid-looking JSON containing real numbers (5 points is a plausible stat, just not the full game). The resolver has no way to distinguish "the player scored 5 points in 40 minutes" (legitimate low performance) from "the player scored 5 points in 12 minutes of a game where they ultimately scored 50" (truncated data).

This follows the scanner's established "plausible wrong output" failure pattern documented in [[connections/silent-type-coercion-data-corruption]]: the output passes all validation checks, looks reasonable at a glance, and only reveals itself as wrong through external cross-verification.

### The Packed Field as Cross-Check

The `player_double_double` packed field — previously dismissed as unreliable due to encoding confusion — could serve as a cross-check against component-derived resolutions. If the packed field encodes `1.501040001` (suggesting ~50 pts, ~10 reb, ~4 ast from the full game) while the components show 5 pts / 4 reb / 1 ast, the disagreement would flag a data completeness issue. The packed field appears to be populated from a different data pipeline than the per-quarter component stats, which may explain why it contains full-game data when components are truncated.

However, using the packed field as a primary source is not recommended — the DD/TD encoding bug (see [[concepts/dd-td-resolver-bias]]) proved that the packed field's format is non-obvious and was historically misinterpreted. The safer approach is to use it as a **cross-check only**: when the packed field disagrees with the component derivation, flag the pick for manual review rather than automatically trusting either source.

### Potential Detection Mechanisms

Three detection mechanisms could catch partial stats before they produce wrong resolutions:

1. **Minutes-played sanity check**: Compare `player_minutes` against expected game minutes. A player with 12 minutes in a regulation NBA game that lasted 48+ minutes should trigger a data quality flag. The threshold would vary by sport (48 min NBA, 60 min NRL/AFL, 9 innings MLB).

2. **Component-vs-packed cross-validation**: If `_derive_binary_compound()` produces a different result than parsing the packed `player_double_double` field, defer resolution and retry on the next cycle (hoping for complete data).

3. **Historical stat comparison**: If a star player's stats are dramatically below their season average (e.g., Wembanyama averaging 25+ ppg but showing 5 pts), flag as potentially truncated. This is noisier (players do have bad games) but provides a statistical safety net.

### Relationship to Date-Priority Hypothesis

The initial hypothesis was a date-priority bug — that the resolver fetched Wembanyama's stats from the wrong game date (April 21 instead of April 22). Investigation ruled this out: Wembanyama didn't play on April 21, so there was no alternative date to confuse with. The partial stats are genuinely from the April 22 game, just incomplete.

## Related Concepts

- [[concepts/dd-td-resolver-bias]] - The encoding bug that drove the fix to compute from components; this bug is a second-order consequence of that fix: components can also be wrong (truncated)
- [[concepts/opticodds-critical-dependency]] - OpticOdds as the sole stats provider; partial data without quality flags adds a third dependency risk dimension (availability, bias, completeness)
- [[connections/silent-type-coercion-data-corruption]] - Another instance of the "plausible wrong output" pattern: truncated stats look valid, pass all checks, silently produce wrong resolutions
- [[concepts/afltables-player-stats-fallback]] - Sport-specific fallback scrapers were built for NRL/AFL stat gaps; a similar cross-verification could catch partial data for NBA
- [[concepts/value-betting-operational-assessment]] - No monitoring catches silently wrong resolutions; the pick was only discovered through manual investigation

## Sources

- [[daily/lcash/2026-04-23.md]] - Wembanyama DD pick graded as Loss/Under when packed field suggested DD achieved; OpticOdds returned 5 pts / 4 reb / 1 ast / 12 min (clearly truncated Q1-Q2); packed field `1.501040001` encodes full-game stats; `_derive_binary_compound()` ignores packed field by design; no minutes-played sanity check; initial date-priority hypothesis ruled out (Wembanyama didn't play April 21) (Session 18:23)
