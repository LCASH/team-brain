---
title: "MLB Team Alias Fixture Resolution"
aliases: [athletics-rename, team-alias-dict, mlb-team-rename, fixture-canon-alias]
tags: [value-betting, resolver, data-quality, mlb, fixture-matching]
sources:
  - "daily/lcash/2026-06-01.md"
created: 2026-06-01
updated: 2026-06-01
---

# MLB Team Alias Fixture Resolution

On 2026-06-01, lcash diagnosed that only "Oakland Athletics vs Yankees" failed fixture resolution out of 14 MLB games. Root cause: the 2025 MLB team rename from "Oakland Athletics" to just "Athletics." The MLB Stats API uses the new name while bookies may use either form. Fixed with a `_TEAM_ALIASES` dict in `resolver.py` that maps alternate names to canonical forms, plus a `_canonicalize_fixture` helper that normalizes fixture names before matching. The approach is symmetric — both old and new names are in the accepted set — future-proofing against bookie vs API name drift.

## Key Points

- **2025 MLB rename**: "Oakland Athletics" → "Athletics" broke fixture matching between resolver and MLB Stats API
- **Only 1 of 14 games affected** — the failure was surgical, not systemic, making it harder to detect
- **`_TEAM_ALIASES` dict + `_canonicalize_fixture` helper** added to `resolver.py` — symmetric mapping accepts both forms
- **Bookie naming lags behind official API** — bookies may continue using "Oakland Athletics" while the API uses "Athletics" for months or years
- **Same pattern applies to other renames**: team relocations, name changes, and abbreviation differences between data sources

## Details

The MLB Stats API updated its canonical team name for the 2025 season from "Oakland Athletics" to "Athletics" (reflecting the team's pending relocation). The value betting scanner's resolver uses fixture names to match picks against game results from the MLB Stats API. When the pick's `fixture_name` contained "Oakland Athletics" (from a bookie still using the old name) and the API returned "Athletics," the string match failed and the pick remained unresolved.

The fix introduces a `_TEAM_ALIASES` dictionary that maps known alternate names to their canonical form. The `_canonicalize_fixture` helper applies these mappings to fixture names before comparison. The approach stores both forms (old and new) in the accepted set, so matches succeed regardless of which name either source uses. This is more robust than a one-directional rename because bookies, scrapers, and APIs may adopt new names at different speeds.

## Related Concepts

- [[concepts/fixture-name-canonicalization]] - The broader fixture canonicalization framework that team aliases extend
- [[concepts/resolver-adjacent-day-merge-bug]] - Another resolver matching failure from a different cause (date ordering); both are cases where structurally valid data fails to match due to a naming/formatting difference
- [[concepts/accent-canonicalization-resolver-mismatch]] - A parallel canonicalization mismatch between resolver normalization paths; team aliases and accent normalization serve the same purpose at different granularity levels

## Sources

- [[daily/lcash/2026-06-01.md]] - Athletics fixture resolution failure: only 1/14 games affected; 2025 MLB rename Oakland Athletics → Athletics; `_TEAM_ALIASES` + `_canonicalize_fixture` symmetric approach; committed as one of 4 focused commits; healthcheck skill updated with lesson (Session 11:20)
