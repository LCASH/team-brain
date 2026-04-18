---
title: "Trail Pre-Seeding Coverage Bug"
aliases: [trail-preseeding, tracked-ids-preseeding, phase-b-baseline-skip, mini-pc-trail-gap]
tags: [value-betting, bug, trail-data, data-quality, tracker]
sources:
  - "daily/lcash/2026-04-18.md"
created: 2026-04-18
updated: 2026-04-18
---

# Trail Pre-Seeding Coverage Bug

The value betting scanner's trail coverage was only 5.9% across all picks because of a cache interaction between the mini PC and VPS. The mini PC inserts picks directly into Supabase (without writing trails), and the VPS tracker loads these picks on startup into `_tracked_ids` with pre-seeded state values. When Phase B trail collection runs, `_should_append_soft` compares current odds against the pre-seeded cached values — if they match (which they often do on the first cycle), the function returns `False` and no baseline trail is ever written. The fix: don't pre-seed `_tracked_state` from Supabase, letting the first Phase B cycle write baseline trails for all tracked picks.

## Key Points

- Mini PC inserts picks into Supabase directly (Phase A) but doesn't write trail entries — picks exist but have no odds history
- VPS loads these picks on startup into `_tracked_ids` and pre-seeds `_tracked_state` with cached values from the Supabase row
- Phase B's `_should_append_soft` checks if current odds differ from cached state — pre-seeded values often match, so the function skips the write
- Result: 5.9% overall trail coverage; Bet365 2.0 had only 24/475 (5%) trail coverage
- Fix: don't pre-seed `_tracked_state` from Supabase — first Phase B cycle writes baseline trail entries for all tracked picks
- Second fix deployed in the same session: event-driven tracker cycle reduced from 30s → 5s for faster baseline writes

## Details

### The Architecture Gap

The value betting scanner operates across two environments: a mini PC (running scrapers + local tracker) and a VPS (running relay tracker + dashboard). Both write to the same Supabase database. The mini PC's tracker evaluates odds, creates picks (Phase A), and writes trail entries (Phase B) for the picks it creates. The VPS relay tracker also runs Phase B for picks that arrive via the push pipeline.

The bug occurs when the mini PC creates a pick and inserts it into Supabase without writing any trail entries (this happens when the Phase B cycle hasn't run yet, or when the pick is created between Phase B cycles). The VPS relay tracker loads all tracked picks from Supabase on startup, including these trail-less picks. To avoid re-evaluating picks that were already tracked, the VPS pre-seeds `_tracked_state` with the pick's current values from the database.

The pre-seeded state creates a false baseline: when Phase B runs on the VPS and calls `_should_append_soft`, it compares the current market odds against the pre-seeded cached values. If the odds haven't changed since the pick was created (common in the first few minutes), the function returns `False` ("no change, don't append") and no trail entry is written. On subsequent cycles, the cached state still matches the pre-seeded values, so trails continue to be skipped — indefinitely.

### Discovery

The bug was discovered on 2026-04-18 during the sharp CLV analytics build (see [[concepts/sharp-clv-theory-ranking]]). CLV computation requires trail data, and the coverage numbers were unexpectedly low: only 5.9% of all picks had any trail entries. Bet365 2.0 (the mini PC's primary scraper) had particularly poor coverage at 24/475 picks (5%), because nearly all its picks were inserted by the mini PC and never received VPS-side trail writes.

The root cause was confirmed by tracing the flow: mini PC INSERT → Supabase row exists → VPS startup loads into `_tracked_ids` with pre-seeded state → Phase B `_should_append_soft` sees matching values → skip → no trail ever written.

### The Fix

The fix removes the pre-seeding step: `_tracked_state` is not populated from Supabase data on startup. Instead, the first Phase B cycle encounters each tracked pick with no cached state, writes a baseline trail entry (because there's nothing to compare against — any value is "new"), and then subsequent cycles operate normally using the baseline as the comparison point.

A secondary fix reduced the event-driven tracker cycle from 30 seconds to 5 seconds, ensuring that baseline trails are written quickly after pick creation rather than waiting up to 30 seconds.

### Pattern: Silent Coverage Loss

This bug follows the established pattern of silent data loss in the scanner's architecture. Like the trail capture SOFT_IDS gap (see [[concepts/trail-capture-soft-ids-gap]]) and the pick ID float/int hashing bug (see [[concepts/pick-id-float-int-hashing-bug]]), the failure produces zero errors and zero warnings — trails simply don't appear. The absence of trails is a valid state ("pick hasn't been tracked long enough for trail data"), making it impossible to distinguish "bug: trails never written" from "expected: trails not yet written" without aggregate coverage analysis.

The 5.9% coverage figure was the diagnostic signal — at steady state with a healthy trail system, coverage should be 80%+ for recently created picks. The extreme gap between expected and actual coverage pointed to a systemic issue rather than normal operational variance.

## Related Concepts

- [[concepts/tracker-optimistic-id-poisoning]] - A sibling tracker ID management bug discovered in the same daily log: `_tracked_ids.add()` before confirmed insert causes cascading NOT NULL errors when game-line inserts fail
- [[concepts/trail-capture-soft-ids-gap]] - Another silent trail coverage failure: SOFT_IDS excluded prediction market book IDs, causing 0% trail coverage for Pinnacle picks
- [[concepts/pick-id-float-int-hashing-bug]] - Another silent trail failure: float/int type coercion in pick ID hash caused Phase B to miss all moneyline trails
- [[concepts/trail-data-temporal-resolution]] - Trail data quality depends on trails being written at all; this bug prevented even baseline entries
- [[concepts/sharp-clv-theory-ranking]] - The CLV analytics build that exposed this bug through low coverage numbers
- [[connections/silent-type-coercion-data-corruption]] - Part of the broader pattern of plausible-wrong-output failures with zero error signals

## Sources

- [[daily/lcash/2026-04-18.md]] - Trail coverage only 5.9%; root cause: mini PC inserts picks without trails → VPS pre-seeds `_tracked_state` → `_should_append_soft` never fires; Bet365 2.0 at 24/475 (5%); fix: don't pre-seed from Supabase; event-driven tracker 30s→5s; sharp CLV built on this discovery (Sessions 17:04, 17:35, 21:07)
