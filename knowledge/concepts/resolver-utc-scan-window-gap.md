---
title: "Resolver UTC Scan Window Gap"
aliases: [resolver-today-gap, utc-date-boundary-miss, oo-boundary-exclusive, resolver-date-scan-window]
tags: [value-betting, resolver, bug, timezone, operations]
sources:
  - "daily/lcash/2026-05-21.md"
created: 2026-05-21
updated: 2026-05-21
---

# Resolver UTC Scan Window Gap

The value betting resolver loop only scanned `yesterday UTC` for unresolved picks, never `today UTC`. Games played in the late evening US Eastern Time (e.g., 8:13 PM ET = 2026-05-20T00:13Z) land on "today" in UTC but "yesterday evening" in ET. The resolver scanning only yesterday's UTC date missed these picks entirely, leaving them unresolved for ~24 hours until they became "yesterday" in UTC. A secondary bug compounded this: OpticOdds' `start_date_after` fixture lookup filter is boundary-exclusive — a game with `start_date=2026-05-20T00:00:00Z` is NOT returned by `start_date_after=2026-05-20T00:00:00Z`. The fix expands the resolver loop to iterate `{today, yesterday} ∪ get_unresolved_dates()` and widens the OO fixture lower bound by 12 hours.

## Key Points

- Resolver loop scanned only `yesterday UTC` — picks with `game_date = today UTC` (from late-evening ET games) sat unresolved for ~24 hours
- A game at 8:13 PM ET on May 19 has `game_date = 2026-05-20` in UTC — the resolver scanning May 19 never finds it; scanning May 20 only happens tomorrow
- OpticOdds `start_date_after` is **boundary-exclusive**: `start_date_after=2026-05-20T00:00:00Z` does NOT return fixtures with `start_date=2026-05-20T00:00:00Z` — must pad by ≥1 second (12 hours chosen for safety)
- Fix: resolver now iterates `{today, yesterday} ∪ get_unresolved_dates()` per cycle, with the 14-day staleness gate still applying
- User correctly identified the gap despite system showing `result IS NULL` — "they have all played" pushed investigation to the pipeline rather than the data

## Details

### The UTC Date Boundary Problem

The value betting scanner stores `game_date` in UTC. NBA/MLB games played in US evening time zones (ET, CT, PT) frequently straddle the UTC date boundary. A game tipping off at 8:00 PM ET on May 19 starts at 2026-05-20T00:00Z — the next calendar date in UTC. The resolver's per-cycle scan previously iterated only `yesterday UTC` (computed as `datetime.now(timezone.utc).date() - timedelta(days=1)`), meaning picks from tonight's games in ET would not be scanned until tomorrow's resolver cycle.

For the Knicks-Cavs game at 00:13Z, the pick had `game_date = 2026-05-20` but the resolver running on May 20 only scanned May 19. The pick was invisible to the resolver until May 21 when May 20 became "yesterday." This created a systematic ~24-hour grading delay for all late-evening ET games.

### The OO Boundary-Exclusive Bug

When the resolver does find the correct date to scan, it queries OpticOdds' `/fixtures/results` endpoint with `start_date_after` to fetch game scores. This filter is boundary-exclusive: a fixture with `start_date=2026-05-20T00:00:00Z` is NOT returned when the query uses `start_date_after=2026-05-20T00:00:00Z`. The fix widens the lower bound by 12 hours (using `start_date_after=2026-05-19T12:00:00Z` for May 20 games), which comfortably captures all games on the target date regardless of their exact start time.

### The Discovery Pattern

The user flagged 16 manual picks stuck as "pending" despite games having finished. The initial diagnosis attributed them to "tonight's games" based on UTC confusion — the system showed `result IS NULL` which could mean either "game not played" or "resolver hasn't scanned yet." The user pushed back: "they have all played." This correction directed investigation to the resolver pipeline rather than game scheduling, ultimately revealing both the scan window gap and the OO boundary bug.

This follows a recurring lesson in the scanner: **don't trust system state over user domain knowledge.** The user knew the games were complete from watching them; the system's `NULL` result was a pipeline gap, not a data truth.

### Relationship to Other Resolver Date Bugs

This is distinct from the adjacent-day merge bug documented in [[concepts/resolver-adjacent-day-merge-bug]], which involved wrong stats from the previous day's game being applied to today's picks via a first-wins dict merge. The scan window gap is about picks never being scanned at all, not about wrong data being applied. Both bugs relate to UTC/ET date boundaries but operate at different pipeline stages: the scan window gap is at the "which dates to process" stage, while the adjacent-day merge is at the "which stats to use for a given date" stage.

## Related Concepts

- [[concepts/resolver-adjacent-day-merge-bug]] - A different UTC date boundary bug: wrong stats applied from adjacent days via first-wins merge. This bug is about picks never reaching the resolver at all
- [[concepts/sharp-consensus-clv-manual-picks]] - The CLV display gap discovered in the same session; manual picks that were finally resolved needed a new CLV fallback
- [[connections/first-wins-merge-iteration-anti-pattern]] - The broader pattern of date-related resolver bugs; the scan window gap is a "date omission" variant rather than the "date ordering" variant

## Sources

- [[daily/lcash/2026-05-21.md]] - 16 manual picks stuck pending; resolver loop only scanned yesterday UTC, never today; games at 00:13Z on "today" missed entirely; OO `start_date_after` boundary-exclusive at exact timestamp; fix: iterate {today, yesterday} ∪ get_unresolved_dates(); user's domain knowledge ("they have all played") directed investigation correctly (Sessions 07:57, 08:36)
