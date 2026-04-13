---
title: "Fixture Name Canonicalization"
aliases: [fixture-dedup, fixture-name-normalization, game-name-splitting]
tags: [data-quality, deduplication, value-betting, normalization]
sources:
  - "daily/lcash/2026-04-13.md"
created: 2026-04-13
updated: 2026-04-13
---

# Fixture Name Canonicalization

A data quality fix for the value betting scanner where the same game appeared multiple times in the dashboard because different odds sources use incompatible naming formats. The root cause was that fixture names were set only at market creation time (`state.py:104`) and never updated during subsequent merges. The fix applies a canonical "vs" format preference during every merge operation, not just on initial creation.

## Key Points

- The same game appeared up to 3 times in the dashboard: "Miami Heat vs Atlanta Hawks", "ATL Hawks @ MIA Heat", "Atlanta at Miami"
- Root cause: `state.py:104` sets `fixture_name` only on market creation, never updates it during subsequent merges from other data sources
- Different sources use different conventions: "vs" (OpticOdds), "@" with abbreviations (Bet365 game scraper), city-only with "at" (other soft books)
- Fix applies canonical "vs" format preference at merge time — when a merge encounters a "vs" format name, it overwrites whatever was set at creation
- 100% fixture canonicalization confirmed across NBA, MLB, and AFL after deployment

## Details

### The Problem

The value betting scanner aggregates odds from multiple sources for the same sporting event. Each source identifies games differently: OpticOdds uses full team names with "vs" ("Miami Heat vs Atlanta Hawks"), the Bet365 game scraper uses abbreviations with "@" ("ATL Hawks @ MIA Heat"), and some Australian soft books use city names with "at" ("Atlanta at Miami"). When the scanner creates a market entry from the first source to report a game, it stores that source's fixture name. Subsequent sources merge their odds into the same market entry but never update the name.

The issue is that the market matching logic (which correctly identifies these as the same game) operates on internal IDs and normalized keys, while the display layer uses the stored `fixture_name` string. If two sources happen to create separate market entries before the deduplication logic merges them — a race condition during startup or after a restart — the dashboard shows duplicate entries for the same game.

### The Fix

The fix is applied at `state.py:104` in the odds aggregator, modifying the merge path (not just the creation path) to prefer canonical naming. When a merge operation encounters a fixture name containing "vs" (the most complete format, always using full team names), it overwrites the stored `fixture_name` regardless of what was set at creation. This ensures that even if a market was initially created by a source using abbreviations or city names, the display name converges to the canonical format as soon as a "vs" source reports odds for that game.

This approach avoids the complexity of a dedicated name normalization service or mapping table. The "vs" format from OpticOdds is the most human-readable and unambiguous, so treating it as canonical is a pragmatic choice. The merge-time update means the system is self-healing — after one full odds cycle, all fixtures display their canonical names regardless of which source created the initial entry.

### Verification

Post-deployment verification confirmed 100% fixture canonicalization across all three active sports (NBA, MLB, AFL). No duplicate game entries appeared in the dashboard, and the trail system correctly associated all odds updates with the canonicalized fixture name.

## Related Concepts

- [[concepts/server-side-snapshot-cache]] - Deployed in the same session; both fixes improved push worker data quality
- [[concepts/betstamp-bet365-scraper-migration]] - Different naming conventions between Betstamp and game scraper were a historical source of this problem
- [[concepts/value-betting-operational-assessment]] - Data quality was identified as a gap area in the assessment

## Sources

- [[daily/lcash/2026-04-13.md]] - Fixture name splitting discovered: same game 3x in dashboard ("vs" / "@" / "at" formats); root cause at `state.py:104` (set on creation, never updated); fix applies canonical "vs" format at merge time; 100% canonicalization verified across NBA/MLB/AFL (Session 07:45 ongoing)
