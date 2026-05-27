---
title: "Sportsbet UTC Timezone Canonical ID Bug"
aliases: [sportsbet-timezone-bug, meeting-date-utc-aest, canonical-id-timezone-mismatch, sportsbet-merger-failure]
tags: [superwin, racing, bug, timezone, data-quality, architecture]
sources:
  - "daily/lcash/2026-05-26.md"
created: 2026-05-26
updated: 2026-05-26
---

# Sportsbet UTC Timezone Canonical ID Bug

The Sportsbet racing adapter was using UTC date for `meeting_date` while all other bookies (TAB, TabTouch, Betfair, Betr) use AEST date. Since `canonical_id` includes `meeting_date`, Sportsbet races could **never merge** with Betfair or any other bookie — making the entire bookie useless for value scanning. Only 1 of 188 Sportsbet races had a Betfair pairing versus 116/117 for TAB/TabTouch/betr. The fix: explicitly convert to `AEST = timezone(timedelta(hours=10))` using Brisbane time (no DST).

## Key Points

- **Sportsbet adapter used UTC for `meeting_date`** while all other bookies use AEST — `canonical_id` includes date, so Sportsbet races NEVER merged with Betfair
- **1/188 Sportsbet races had Betfair pairing** vs 116/117 for TAB/TabTouch/betr — a 0.5% merge rate vs 99%+ for working bookies
- The single race that merged was a coincidence where the UTC and AEST dates happened to align (early-morning race)
- **Fix: `AEST = timezone(timedelta(hours=10))`** — Brisbane timezone has no DST, so the offset is constant year-round
- Discovered while debugging why the new `sb-normal` edge produced 0 opportunities despite data flowing correctly
- The edge itself, criteria, and scanner pipeline all worked — the broken merger meant Sportsbet could never produce a Betfair-referenced EV calculation

## Details

### The Canonical ID Collision Mechanism

The SuperWin racing scanner uses a `canonical_id` to merge odds from different bookies for the same race. The canonical ID includes `meeting_date` as a component — when two bookies report the same venue, race number, and date, their data merges into a single race entry for cross-bookie EV comparison.

The Sportsbet adapter computed `meeting_date` from server timestamps in UTC. All other adapters (TAB, TabTouch, Betfair, Betr, BoostBet) use AEST (UTC+10) because Australian racing operates on local time. A race that runs at 6 PM AEST on May 26 has:
- AEST date: 2026-05-26
- UTC date: 2026-05-26 (same — only because 6 PM AEST = 8 AM UTC, still same calendar day)

But a race that runs at 8 AM AEST on May 27 has:
- AEST date: 2026-05-27
- UTC date: 2026-05-26 (previous day — 8 AM AEST = 10 PM UTC May 26)

When the UTC date falls on the previous calendar day, the Sportsbet canonical_id includes `2026-05-26` while Betfair's includes `2026-05-27`. The IDs never match. The race from the two bookies never merge. The EV calculation never fires.

### Why It Went Undetected

The bug was invisible because Sportsbet data appeared to flow correctly through every layer:
- Discovery found races ✓
- Odds were parsed and stored ✓  
- The scanner evaluated edges ✓
- The `sb-normal` edge row was correctly configured ✓

The failure only manifested as "0 opportunities" — which is indistinguishable from "the market is efficient" (a valid state). Only comparing the merge rates across bookies (Sportsbet 0.5% vs TAB/TabTouch/betr 99%+) revealed the systematic failure.

### The Fix

The fix explicitly converts to AEST using Brisbane timezone (which has no daylight saving time):

```python
from datetime import timezone, timedelta
AEST = timezone(timedelta(hours=10))
meeting_date = server_timestamp.astimezone(AEST).date()
```

Brisbane is used rather than `"Australia/Sydney"` because Sydney observes DST (UTC+11 in summer, UTC+10 in winter), which would introduce seasonal date-boundary shifts. Brisbane (Queensland) stays at UTC+10 year-round, matching the constant offset that all other racing adapters use.

### Broader Timezone Pattern

This bug belongs to the same family as three other timezone-related resolver bugs in the value betting scanner: the adjacent-day merge bug (see [[concepts/resolver-adjacent-day-merge-bug]]), the UTC scan window gap (see [[concepts/resolver-utc-scan-window-gap]]), and the JournalTracker UTC midnight rollover (see [[concepts/journal-tracker-manual-pick-trail-writing]]). All share the root cause: Australian racing and US sports operate in local time, but Python defaults to UTC, and the mismatch at calendar-day boundaries causes merges, lookups, or scans to fail silently.

## Related Concepts

- [[concepts/resolver-adjacent-day-merge-bug]] - Same timezone boundary pattern in the sports resolver: UTC date assignment caused wrong-game stats from adjacent days
- [[concepts/resolver-utc-scan-window-gap]] - Resolver only scanned yesterday UTC, missing same-day ET games — same class of UTC/local boundary miss
- [[concepts/fixture-name-canonicalization]] - Canonical IDs also depend on venue name normalization; the timezone bug is a date-component analog
- [[connections/silent-type-coercion-data-corruption]] - 0 opportunities from timezone mismatch is another "plausible wrong output" — the system reports no edge, which looks like market efficiency

## Sources

- [[daily/lcash/2026-05-26.md]] - Sportsbet adapter using UTC for meeting_date; 1/188 Betfair pairing vs 116/117 for other bookies; fix: AEST = timezone(timedelta(hours=10)) (Brisbane, no DST); discovered while debugging sb-normal edge producing 0 opportunities; criteria field is `bookies` not `allowed_bookies` — skill doc corrected (Session 09:21)
