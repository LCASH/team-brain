---
title: "Push Loop Diff Cache and Phantom Freshness"
aliases: [diff-cache, phantom-freshness, change-event-suppression, push-loop-dedup, diff-key-flapping]
tags: [value-betting, architecture, performance, data-quality, pipeline]
sources:
  - "daily/lcash/2026-05-13.md"
created: 2026-05-13
updated: 2026-05-13
---

# Push Loop Diff Cache and Phantom Freshness

The v3 value betting scanner's push loop fired `store.change_event` every 5 seconds regardless of whether any odds had actually changed, causing the event-driven tracker to wake and grind through full no-op evaluation cycles on unchanged data. On 2026-05-13, a diff cache was deployed that stores the last-seen odds per market and only fires the change event when actual data changes are detected. Three bugs were discovered in the diff cache key design during live production testing, each causing phantom churn from key collisions.

## Key Points

- Push loop fired `store.change_event` every 5s unconditionally — the event-driven tracker woke every cycle regardless of whether data changed, defeating the efficiency gain of event-driven design
- Diff cache stores last-seen odds per `(fixture_id, market_key, line, is_main)` key; only fires change_event when actual changes are detected
- **Bug 1 — Missing `line` in key**: `make_market_key()` deliberately drops `line` for cross-line EV matching, but this caused alt lines (Over 25.5 vs Over 26.5) to flap-overwrite each other in the diff cache
- **Bug 2 — Missing `is_main` in key**: MLB wizard emits both O/U records (`is_main=True`) and milestone records (`is_main=False`) at the same `(player, prop, side, line)` with different odds — collide without this dimension
- **Bug 3 — MLB sub-market collisions**: MLB wizard packs sub-stats (Hits/Singles/Doubles/Triples) into one EV section; 3 different odds (1.714, 4.75, 20.0) map to the same logical key before parser fix
- First-wins dedupe deployed as pragmatic fix for Bug 3 with WARNING log for upstream visibility; upstream parser fix followed same day

## Details

### The Phantom Freshness Problem

The v3 scanner uses an `asyncio.Event` (`store.change_event`) to wake the tracker when new odds data arrives — a design documented in [[concepts/v3-scanner-centralized-architecture]] as an efficiency improvement over v2's fixed 5-second polling. However, the push loop was setting this event on every cycle without checking whether the pushed data differed from the previous push. This meant the event-driven tracker woke every 5 seconds — identical behavior to the polling model it replaced — but with the added overhead of the event/await machinery.

The phantom freshness also interacted with the `captured_at` overwrite bug documented in [[concepts/per-soft-book-temporal-lineage]]: the push loop stamped fresh timestamps on every cycle, so the staleness gate never triggered. Together, these two bugs meant the tracker was (1) waking unnecessarily often and (2) evaluating markets with phantom-fresh timestamps — burning CPU without producing better picks.

### The Diff Cache Mechanism

The diff cache is a dictionary keyed on `(fixture_id, market_key, line, is_main)` that stores the last-seen odds value for each market. On each push cycle, the loop compares the incoming odds against the cached value:

- **If different**: Update the cache, include the market in the push payload, and flag that `change_event` should be set
- **If identical**: Skip the market — don't include in the payload, don't fire the event

The cache is populated incrementally as markets arrive. The first push cycle after startup always fires (no cached values exist). Subsequent cycles only fire when at least one market has genuinely changed odds.

### Bug 1: Diff Key Must Include `line`

The internal `make_market_key()` utility deliberately drops the `line` value from the market key because the EV engine needs to group the same logical market across books that price at slightly different lines (e.g., Points Over 25.5 at Bet365 vs Points Over 26.5 at Sportsbet). This is architecturally correct for EV matching but wrong for diff caching.

When the diff cache used `make_market_key()` as its key, alt-line variants of the same market (Over 19.5 and Over 25.5 for the same player's Points prop) mapped to the same cache entry. Each push cycle alternately wrote one variant's odds to the cache, saw the other variant as "changed," and fired `change_event` — an infinite flapping cycle. The fix adds `line` explicitly to the diff key: `(fixture_id, market_key, line)`.

This is the same root cause as the `matched-market-line-null-bug` (line not in key breaks pick creation) and `dashboard-vig-gate-cross-line-dropout` (line not in key breaks vig gate) documented in [[connections/market-key-dateless-design-recurring-bugs]] — but manifesting in a new context (diff caching rather than pick creation or EV computation).

### Bug 2: Diff Key Must Include `is_main`

The MLB BB wizard returns two record types for the same `(player, prop, side, line)`: O/U records (`is_main=True`) with standard Over/Under odds, and milestone records (`is_main=False`) with threshold-style odds (e.g., "1+ Hits" at line 0.5). These have different odds values for the same logical key. Without `is_main` in the diff key, the two record types alternately overwrote each other in the cache, producing phantom churn on every cycle.

### Bug 3: MLB Sub-Market Collisions

The MLB wizard packs multiple sub-stats under a single EV section header. A section called "Player Hits" contains separate PA records for Hits, Singles, Doubles, and Triples — each with different odds but the same `(player, prop_type="Hits", side, line)` before the parser disambiguates. This caused 3 different odds values (e.g., 1.714 for Hits, 4.75 for Singles, 20.0 for Triples) to collide under one diff key, with each push cycle writing a different value.

The pragmatic fix was first-wins dedupe in the push loop: the first value seen for a given key is cached, and subsequent colliders are logged as WARNINGs. This was deployed alongside the upstream parser fix that extracts the actual stat from the wizard `S2` field — see [[concepts/mlb-wizard-sub-market-collision-s2-field]].

### Live Verification Caught All Three Bugs

All three bugs were invisible in unit tests but obvious under production load. Bug 1 manifested as persistent `change_event` firing despite no real odds movement. Bug 2 manifested as MLB markets appearing to change on every cycle. Bug 3 manifested as 93 collision keys producing 222 duplicate entries, which the sub-market parser fix reduced to 11 keys and 30 duplicates (residual milestone collisions — a separate concern).

## Related Concepts

- [[concepts/per-soft-book-temporal-lineage]] - The parent architectural change that the diff cache is part of (Phase 1 of 4-phase temporal honesty overhaul)
- [[concepts/asyncio-event-spin-loop-memory-leak]] - A prior `change_event` bug: Event.wait() without .clear() created an infinite spin loop; phantom freshness is a different failure mode (event set too often, not event never cleared)
- [[concepts/mlb-wizard-sub-market-collision-s2-field]] - The upstream parser fix that resolves Bug 3 by disambiguating Hits/Singles/Doubles/Triples via the S2 field
- [[connections/market-key-dateless-design-recurring-bugs]] - Bug 1 (missing line in diff key) is the fourth manifestation of the lineless/dateless market_key design causing collisions
- [[concepts/v3-scanner-centralized-architecture]] - The event-driven DataStore architecture whose change_event the diff cache gates

## Sources

- [[daily/lcash/2026-05-13.md]] - Diff cache deployed with 3 bugs found in live verification: (1) alt-line flapping from missing `line` in key, (2) milestone vs O/U collision from missing `is_main`, (3) MLB sub-market collisions from parser flattening; first-wins dedupe as pragmatic fix; verified captured_at ages now 10-15s (was 0s); all 3 bugs invisible in unit tests, obvious under production load (Sessions 09:32, 10:02)
