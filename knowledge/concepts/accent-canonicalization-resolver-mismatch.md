---
title: "Accent Canonicalization Mismatch Between Resolver and Podcast"
aliases: [accent-canon-mismatch, nfd-normalize-mismatch, accented-player-silent-null, unicode-normalization-resolver]
tags: [value-betting, resolver, bug, data-quality, mlb, unicode]
sources:
  - "daily/lcash/2026-05-29.md"
created: 2026-05-29
updated: 2026-05-29
---

# Accent Canonicalization Mismatch Between Resolver and Podcast

The value betting scanner's pick resolver and podcast.py module used different Unicode normalization strategies: `_normalize` (resolver) NFD-decomposes and strips accents, but `_normalize_name` (podcast.py) does not. Any player with accented characters in their name (Acuña, Giménez, Ramírez, Dubón) silently stayed `result=null` forever — the resolver looked up "Acuna" but podcast.py stored "Acuña", so the name match never fired. This affected 571 legitimate picks for star MLB players, discovered during Phase 2 of a multi-phase data correction on 2026-05-29.

## Key Points

- **`_normalize` (resolver) NFD-strips accents**; `_normalize_name` (podcast.py) does not — silent mismatch with zero error signal
- **571 picks for star players silently stuck as null**: Ramírez (34 picks), Giménez (44 picks), Acuña, Dubón — all high-volume players
- **Discovered during Phase 2 dry-run** — would have incorrectly voided 571 legitimate picks without the sanity check
- **Fixing data without fixing code = regression next cycle**: overnight M8 audit jumped from resolved back to 6.36% disagreement, stale from 33→141
- **Code fix shipped as commit `e72d26e`**: patched `_normalize_name` to NFD-decompose matching resolver behavior; validated with 10 test names
- **Post-deploy: stale dropped 141→51 immediately**, confirming the code fix works in production

## Details

### The Normalization Gap

Python's `unicodedata.normalize("NFD", s)` decomposes accented characters into base letter + combining mark (e.g., "ñ" → "n" + combining tilde), which can then be stripped to produce ASCII-only text. The resolver's `_normalize` function applied this transformation, so all name lookups used accent-free keys. However, `_normalize_name` in podcast.py — which processes MLB Stats API responses — did NOT apply NFD decomposition, preserving the original accented names.

When the resolver attempted to match a pick's player name against the stats database, it searched for "Acuna" but the database contained "Acuña". No match was found, so the pick remained unresolved with `result=null`. This is a silent failure — no error is logged, no exception is raised, the pick simply appears as "pending" forever.

### Multi-Phase Discovery Context

This bug was discovered during Phase 2 of a multi-phase data correction for the [[concepts/resolver-adjacent-day-merge-bug]]:

1. **Phase 1** (May 28): Mass re-resolution of ~47K MLB picks to fix the dates_to_fetch ordering bug. This had its own bug — v1 omitted `game_start` from the SELECT, causing `et_from()` to fall back to `game_date` (UTC), making ~385 night-game picks worse.

2. **Phase 2** (May 29): Dry-run to clean up remaining M8 audit failures. The dry-run categorized 741 picks: 170 legitimate voids (DNPs, Ohtani pitching-day batting props) and 571 that appeared to need voiding but were actually accent-canon misses — star players whose picks should have graded normally.

3. **Phase 2 execution**: 170 voids + 571 accent-canon grades applied, bringing M8 from 25.5% → <1%.

4. **Overnight regression**: M8 jumped back to 6.36%, stale from 33→141 because the code bug wasn't fixed — only the historical data was corrected. New picks for accented players continued to fail.

5. **Code fix** (commit `e72d26e`): Patched `_normalize_name` to NFD-decompose. Stale dropped 141→51 immediately.

### Multi-Phase Scope Cascading

After the code fix, M8 was still at 6.36% — a THIRD issue emerged. Phase 1's early buggy run had corrupted some picks (e.g., Carroll `game_date=5-22`) that then fell outside Phase 2's correction window because Phase 2 filtered on `updated_at`. The corrupted picks' `updated_at` had been moved past the cutoff by the buggy Phase 1 run.

The lesson: when correcting historical data in multiple phases, scope by `game_date` (immutable) rather than `updated_at` (mutable). Earlier buggy passes can shift `updated_at`, causing subsequent correction passes to miss the very records they need to fix.

### The Anti-Pattern: Data Fix Without Code Fix

The initial approach — fix the 571 historical picks but not the underlying `_normalize_name` code — guaranteed regression on the next resolver cycle. Every new pick for an accented player would silently fail. The corrected workflow is: **always ship the code fix first**, then clean up historical data. This ensures no new corruption accumulates while the backfill runs.

## Related Concepts

- [[concepts/resolver-adjacent-day-merge-bug]] - The parent bug whose multi-phase correction exposed the accent-canon mismatch
- [[connections/resolver-multi-layer-grading-contamination]] - Multiple resolver bugs compounding at different pipeline stages
- [[connections/silent-type-coercion-data-corruption]] - Accent-canon is another "plausible wrong output" pattern: picks silently stay null with zero error signal
- [[concepts/data-integrity-audit-pipeline-validation]] - Unicode NFD for diacritics was one of 8 fixes in the May 2 audit; this is a different normalization gap in a different module

## Sources

- [[daily/lcash/2026-05-29.md]] - Phase 2 dry-run caught 571 accent-canon misses (Ramírez 34x, Giménez 44x); `_normalize_name` vs `_normalize` NFD gap; code fix commit e72d26e; overnight regression M8 6.36%, stale 33→141 from unfixed code; data-without-code = regression; Phase 1 corruption cascading through updated_at filtering; game_date scoping needed (Sessions 10:48, 17:22)
