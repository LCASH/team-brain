---
title: "Venue Auto-Learn Race Name Pollution"
aliases: [venue-pollution, auto-learn-pollution, race-name-venue-bug, venue-alias-cleanup, tab-venue-abbreviations]
tags: [superwin, racing, data-integrity, venue-linking, bug, cleanup]
sources:
  - "daily/lcash/2026-05-30.md"
created: 2026-05-30
updated: 2026-05-30
---

# Venue Auto-Learn Race Name Pollution

SuperWin's `auto_learn` venue linking feature created polluted canonical venue entries by ingesting race names instead of meeting names — storing entries like "Syngenta Maiden Plate" and "@Thegardensgrnsw Maiden" as venue names. The cleanup removed 33 polluted aliases and 25 polluted canonical entries. Real venues were already present in the database; the polluted aliases simply pointed to incorrect canonicals. A parallel issue involved 65 unmapped TAB venue abbreviations, 16 of which were ambiguous due to multi-discipline venues sharing codes.

## Key Points

- `auto_learn` used race names instead of meeting names when creating venue entries, producing canonical venues like "Syngenta Maiden Plate" and "@Thegardensgrnsw Maiden"
- 33 polluted aliases and 25 polluted canonical entries deleted — the real venues already existed in the DB, aliases just pointed to wrong canonicals
- Thread 1 fix: regex filtering on Sprint/Maiden/Plate/Handicap race-name patterns prevents new pollution at ingest time
- 65 unmapped TAB abbreviations discovered: 49 unambiguous (auto-mappable), 16 ambiguous because multi-discipline venues share codes (e.g., BEN = Bendigo thoroughbred AND Bendigo greyhound)
- TAB sends uppercase abbreviations that become the canonical_id if TAB's adapter ingests data first, before other bookies provide the full venue name
- Race catalogue not cleaning resulted races aggressively enough — 2-day-old stale data persists

## Details

### The Auto-Learn Pollution Mechanism

SuperWin's venue linking system includes an `auto_learn` mode designed to automatically create venue aliases when an unknown venue string appears. The intended flow is: a bookie sends a meeting name (e.g., "Flemington"), the system checks if it exists in the canonical venue table, and if not, creates a new canonical entry and alias. The bug was that the adapter was passing race names rather than meeting names to the auto-learn function. Race names like "Syngenta Maiden Plate", "TAB Highway Class 3", and "@Thegardensgrnsw Maiden" were stored as canonical venue names.

This didn't immediately break functionality because races still resolved to a venue — just the wrong one. Multiple races at different actual venues could end up mapped to a single polluted canonical like "Maiden Plate". The real venues (Flemington, Randwick, etc.) already existed in the database with correct data from other bookies. The pollution created a parallel set of incorrect entries that some aliases pointed to.

### Two-Thread Fix

Thread 1 addressed the source: a regex filter at ingest time now screens incoming venue strings for patterns characteristic of race names rather than venue names. Strings containing "Sprint", "Maiden", "Plate", "Handicap", "Class", and similar racing-specific terms are rejected from auto-learn. This prevents future pollution without disabling auto-learn entirely, which remains valuable for genuinely new venues.

Thread 2 was the database cleanup. The 33 polluted aliases were deleted, and their races re-resolved to the correct existing canonicals. The 25 polluted canonical entries (which had no legitimate races once the aliases were corrected) were then removed. Because the real venues were already in the database, no data was lost — the aliases simply needed to point to the right targets.

### TAB Abbreviation Mapping

A related discovery surfaced 65 unmapped TAB venue abbreviations. TAB's API sends venue codes as uppercase abbreviations (e.g., "FLEM" for Flemington, "BEN" for Bendigo). When TAB ingests data before other bookies, these abbreviations become the canonical_id in the venue table. Of the 65 unmapped codes, 49 were unambiguous — each code maps to exactly one venue regardless of discipline. The remaining 16 were ambiguous because Australian racing venues frequently host multiple disciplines: BEN could be Bendigo thoroughbred racing or Bendigo greyhound racing, requiring discipline context to resolve correctly.

### Stale Catalogue Data

The investigation also revealed that the race catalogue was not cleaning resulted (completed) races aggressively enough. Races that had resulted 2 days prior were still present in the catalogue, creating unnecessary load on venue resolution and odds processing. The catalogue's persistence model ("once added, never removed until day rollover") needs tighter cleanup windows for resulted races to prevent stale data accumulation.

## Related Concepts

- [[concepts/superwin-venue-linking-integrity-bug]] - The original venue linking integrity issue that the auto-learn feature was designed to address; this pollution is a secondary failure mode of the same system
- [[concepts/fixture-name-canonicalization]] - The broader canonicalization framework that venue linking is part of; race-name pollution is a failure in the canonicalization input pipeline
- [[concepts/data-integrity-audit-pipeline-validation]] - The audit methodology used to identify the 33+25 polluted entries; applicable pattern for future data quality sweeps
- [[concepts/tab-cold-start-akamai-discovery-thrashing]] - TAB adapter issues that affect venue data ingest timing; if TAB ingests first with abbreviations, those become canonical_ids

## Sources

- [[daily/lcash/2026-05-30.md]] - auto_learn using race names instead of meeting names; 33 polluted aliases + 25 polluted canonicals deleted; regex filtering Sprint/Maiden/Plate prevents new pollution; 65 unmapped TAB abbreviations (49 unambiguous, 16 ambiguous multi-discipline); TAB uppercase abbreviations becoming canonical_id; race catalogue stale data persisting 2 days
