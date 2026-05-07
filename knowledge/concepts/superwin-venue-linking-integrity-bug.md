---
title: "SuperWin Venue Linking Data Integrity Bug"
aliases: [venue-linking-bug, venue-alias-missing, case-sensitivity-venue-bug, venue-auto-repair]
tags: [superwin, racing, data-integrity, bug, supabase]
sources:
  - "daily/lcash/2026-05-05.md"
created: 2026-05-05
updated: 2026-05-05
---

# SuperWin Venue Linking Data Integrity Bug

A deep investigation on 2026-05-05 revealed systemic data integrity issues in the SuperWin racing scanner's venue linking infrastructure: 190 venues were marked as `resolved=true` in `unmatched_venues` but had no corresponding `venue_aliases` entries — the linking code marked venues resolved without actually creating the alias records. The bug affected 73 venues across a Feb 28 – Mar 22, 2026 batch operation window, with a 38% overall failure rate and 95% failure rate for Betfair specifically. An auto-repair strategy using cross-bookie canonical mapping fixed 70 of 73 venues (95.9% success rate). A latent case-sensitivity bug was also found: `upsert_venue_alias` uses `.upper()` but `resolve_unmatched_venue` uses `.eq()` (case-sensitive match), meaning aliases were created correctly but unmatched rows were never marked resolved.

## Key Points

- **190 resolved venues with no aliases**: `unmatched_venues.resolved=true` but zero `venue_aliases` entries — the linking code marked resolved without creating the alias
- **38% failure rate overall, 95% for Betfair**: Betfair Capalaba (27,656 occurrences) and Sapphire Coast (26,231) were the top victims
- **Feb 28 – Mar 22 batch window**: All broken records trace to an interim deployment period that never made it into git history — a migration-era artifact
- **Current code is structurally sound**: Both DB writes (resolve flag + alias creation) are in the same try/except block since Mar 25 deployment — the bug is historical, not active
- **Auto-repair**: Cross-bookie canonical venue mapping (TAB has correct mapping → use it for Betfair) fixed 70/73 venues (95.9%); 3 remain (NZ venue, Carrick, Rosehill need manual canonical venue creation)
- **Case-sensitivity bug**: `.upper()` on write vs `.eq()` on read — aliases created correctly but `unmatched_venues` rows never marked resolved; fix: `.eq()` → `.ilike()` (Postgres case-insensitive match) in `supabase.py:434`; deployed as commit `6609e07`
- **`resolved` flag is cosmetic only** — it never gates the actual venue resolution pipeline; historical pick journal (12.3% ROI, 1,000 picks) is intact

## Details

### Discovery Chain

The investigation started from a simple operational issue: 3 unmatched venues (Moe, Mandurah/Gosford mismatch) were blocking edge picks. The user escalated with "you need to investigate much deeper," which uncovered the full scope: 190 venues marked resolved but with broken linking, tracing to a batch operation that ran between Feb 28 and Mar 22, 2026.

The batch operation appears to have been a migration script that updated `unmatched_venues.resolved = true` for all venues it processed but either failed to create `venue_aliases` entries (the actual linking records) or used a different code path that skipped alias creation. Since this deployment predates the current git history (the current code was deployed Mar 25), the exact bug cannot be reconstructed from source control.

### The Case-Sensitivity Asymmetry

A latent bug was discovered in the current codebase: the `upsert_venue_alias` function normalizes venue names to uppercase via `.upper()` before writing to `venue_aliases`, but `resolve_unmatched_venue` uses `.eq("raw_name", raw_name)` — a case-sensitive Postgres match — to look up the unmatched venue row and mark it resolved. If the raw_name was stored with mixed case (e.g., "Capalaba"), the `.eq()` comparison against the uppercase version would fail, leaving the unmatched row unremarked despite the alias being created successfully.

The fix is a one-line change: `.eq("raw_name", raw_name)` → `.ilike("raw_name", raw_name)` at `supabase.py:434`. `.ilike()` is Postgres's case-insensitive pattern matching, which handles the normalization mismatch transparently. This was deployed as commit `6609e07`.

### Impact Assessment

The `resolved` flag in `unmatched_venues` is purely cosmetic — it controls what appears in the admin UI's "unresolved venues" list. The actual venue resolution pipeline reads from `venue_aliases` and `canonical_venues`, never from `unmatched_venues.resolved`. This means:

- **Historical pick journal is intact**: The 12.3% ROI across 1,000 picks is accurate because pick resolution uses `venue_aliases`, not the `resolved` flag
- **Admin UI was misleading**: The admin UI showed fewer unresolved venues than actually existed (because broken-but-resolved venues were hidden)
- **Edge picks from Feb-Mar may be missing**: Races at affected venues during the broken window may not have generated edge picks if the venue couldn't be matched — this is potential historical data loss, not data corruption

### Auto-Repair Strategy

The auto-repair leveraged cross-bookie canonical mapping: if TAB has venue "Capalaba" correctly linked to canonical venue "Capalaba" in `venue_aliases`, and Betfair has "Capalaba" as an unmatched venue with no alias, the repair copies TAB's canonical_venue_id to create a Betfair alias. This cross-bookie approach works because venues have consistent canonical names across bookies — the raw_name formats differ but the canonical venue is the same.

The auto-repair successfully fixed 70 of 73 broken venues (95.9%). The 3 remaining require manual canonical venue creation: one NZ venue with no Australian equivalent, Carrick (regional venue not in the canonical table), and Rosehill (expected to be in the table but wasn't found — possibly a name variant issue).

### Bet365 Racing Pipeline Status

During the same investigation, lcash confirmed that the bet365 racing pipeline (`bet365_stream.py`) was not running on the Dell mini PC — the VPS ingest endpoint was functional (tested with synthetic data) but the Dell-side scraper had never been started or had crashed. All 4 other bookies were confirmed healthy: TAB (176 races), TabTouch (178 races), Betfair (244 races), bet365 (0 races — pending Dell fix).

## Related Concepts

- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal whose Feb-Mar data may be missing picks from broken venue linking; the 12.3% ROI figure is from correctly-linked venues only
- [[concepts/data-integrity-audit-pipeline-validation]] - A parallel data integrity investigation in the value betting scanner; both discovered that paired DB operations can have asymmetric failures
- [[connections/silent-type-coercion-data-corruption]] - The case-sensitivity asymmetry is another instance of plausible wrong output: aliases created successfully but unmatched rows not resolved, inflating the admin UI's "work remaining" count
- [[concepts/bet365-racing-adapter-architecture]] - The bet365 racing pipeline that was confirmed not running on Dell during this investigation

## Sources

- [[daily/lcash/2026-05-05.md]] - Initial 3 unmatched venues escalated to 190 broken; 73 venues with missing aliases from Feb 28–Mar 22 batch operation; 38% failure rate overall, 95% for Betfair; Betfair Capalaba 27,656 occurrences; auto-repair 70/73 (95.9%); current code structurally sound (both writes in same try/except since Mar 25) (Session 13:58). Case-sensitivity: `.upper()` write vs `.eq()` read; fix `.eq()` → `.ilike()` at supabase.py:434; deployed as `6609e07`; `resolved` flag is cosmetic only; historical pick journal intact; bet365 racing not running on Dell (Session 14:33)
