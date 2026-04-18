---
title: "Tracker Optimistic ID Poisoning"
aliases: [staged-ids, optimistic-tracking, premature-id-commit, tracked-ids-poisoning]
tags: [value-betting, bug, tracker, architecture, anti-pattern]
sources:
  - "daily/lcash/2026-04-18.md"
created: 2026-04-18
updated: 2026-04-18
---

# Tracker Optimistic ID Poisoning

The value betting scanner's tracker added pick IDs to `_tracked_ids` before the Supabase INSERT was confirmed. When the INSERT failed — e.g., a `null value in column "player_name"` error from game-line markets with no associated player — the ID remained permanently poisoned in the tracked set. Phase B trail collection then attempted to write trails for picks that didn't exist in the database, generating cascading NOT NULL errors. The fix: staged IDs pattern where IDs are only committed to `_tracked_ids` after Supabase confirms the insert.

## Key Points

- `_tracked_ids.add(pick_id)` executed BEFORE Supabase insert — failed inserts permanently poisoned the tracking set
- Phase B generated trail entries for non-existent picks → NOT NULL constraint errors cascaded because the trail INSERT referenced a `pick_id` with no parent row
- Root cause trigger: game-line markets (moneyline, totals) have empty `player_name`, hitting the Supabase `NOT NULL` constraint on the picks table
- Fix: staged IDs — only add to `_tracked_ids` after Supabase confirms the INSERT succeeded; failed inserts are retryable on the next cycle
- Complementary fix: PATCH (`.update().eq()`) instead of POST/upsert for batch trail updates — avoids hitting NOT NULL constraints on partial column inserts

## Details

### The Mechanism

The tracker's pick creation flow had a subtle ordering bug:

1. Tracker evaluates a market and decides it's +EV → creates a pick object
2. `_tracked_ids.add(pick_id)` — marks the ID as "already tracked" to prevent re-evaluation
3. Supabase INSERT → **fails** (e.g., `player_name` is NULL for a game-total market)
4. The pick does not exist in the database, but `pick_id` is now in `_tracked_ids`
5. On the next tracker cycle, Phase A skips this market ("already tracked")
6. Phase B iterates `_tracked_ids`, finds the poisoned ID, attempts to write a trail entry referencing the non-existent pick → foreign key or NOT NULL error

The poisoning is permanent for the lifetime of the process. Since `_tracked_ids` is an in-memory set that is never pruned against the database, the poisoned ID persists across every subsequent tracker cycle. Each cycle generates another trail write attempt, another failure, and another error log line — a cascading failure from a single failed insert.

### Discovery Context

The bug was discovered on 2026-04-18 during NHL dashboard expansion (Session 22:20). Adding NHL game-line markets (moneyline, totals, puck line) introduced picks with empty `player_name` fields — game-level markets have no associated player. The Supabase picks table has a NOT NULL constraint on `player_name`, so these inserts failed. The cascading trail errors were the visible symptom that led to the root cause diagnosis.

NHL was the first sport to trigger this at scale because the NHL expansion was primarily game-line markets (see [[concepts/pinnacle-prediction-market-pipeline]]), unlike NBA/MLB where player props dominated. The 381 NHL markets with sharp data produced only 3 picks that passed the +EV threshold, and all 3 were false positives from line mismatches — but the INSERT failures from game-total markets (which have no player) generated the visible error cascade.

### The Staged IDs Fix

The fix reorders the pick creation flow:

1. Tracker evaluates a market and decides it's +EV → creates a pick object
2. Supabase INSERT → succeeds or fails
3. **Only if INSERT succeeds**: `_tracked_ids.add(pick_id)`
4. If INSERT fails: the pick is not tracked, and will be re-evaluated on the next cycle

This ensures `_tracked_ids` is a faithful reflection of what actually exists in the database. Failed inserts are automatically retried on the next tracker cycle (since the ID isn't in the tracked set, the market will be re-evaluated), which provides natural retry behavior without explicit retry logic.

### Complementary: PATCH Over POST/Upsert

A related discovery in the same session: Supabase's upsert with `on_conflict: "id"` still attempts an INSERT first, which hits NOT NULL constraints on columns not provided in the partial update. For batch trail updates and backfill operations, using PATCH (`.update().eq("id", pick_id)`) instead of POST/upsert avoids this — PATCH only touches existing rows and doesn't require all NOT NULL columns. This pattern was adopted for the sharp CLV backfill (see [[concepts/sharp-clv-theory-ranking]]) and is recommended for all operations that update existing picks without providing the full column set.

### Anti-Pattern: Optimistic State Commitment

This bug is an instance of a general anti-pattern: committing state changes to an in-memory data structure before the corresponding persistent operation succeeds. The "optimistic" commitment assumes the database write will succeed, and when it doesn't, the in-memory state diverges from the persistent state with no reconciliation mechanism.

The pattern is particularly dangerous when the in-memory state is used as a filter (as `_tracked_ids` is — it prevents re-evaluation of already-tracked picks). A filter based on diverged state silently suppresses correct behavior: the market should be re-evaluated, but the poisoned ID prevents it.

## Related Concepts

- [[concepts/trail-preseeding-coverage-bug]] - A sibling tracker ID management bug: pre-seeding `_tracked_state` from Supabase prevents baseline trail writes. Both bugs affect the tracker's ID/state management and produce silent trail coverage loss
- [[concepts/silent-worker-authentication-failure]] - Same failure signature: zero useful output, zero errors in the expected code path, cascading failures in a dependent phase
- [[connections/silent-type-coercion-data-corruption]] - Part of the broader pattern of plausible-wrong-output failures; the poisoned ID produces "already tracked" (a valid state) when the pick doesn't exist
- [[concepts/game-line-display-normalization]] - Game-line markets with empty `player_name` were the trigger for the NOT NULL failures
- [[concepts/sharp-clv-theory-ranking]] - The PATCH-over-upsert pattern adopted during the same session for the CLV backfill

## Sources

- [[daily/lcash/2026-04-18.md]] - `_tracked_ids.add(pick_id)` before Supabase insert caused cascading NOT NULL errors; game-line markets (no player_name) triggered the failure; staged IDs fix: commit only after confirmed insert; PATCH over POST/upsert for partial updates; NHL 381 markets, 3 false positive picks from line mismatches (Session 22:20)
