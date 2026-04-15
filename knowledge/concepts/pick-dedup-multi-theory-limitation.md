---
title: "Pick Dedup Multi-Theory Limitation"
aliases: [pick-dedup, theory-attribution, triggered-by-limitation, theory-evs, offline-replay]
tags: [value-betting, architecture, a-b-testing, tracker, deduplication]
sources:
  - "daily/lcash/2026-04-14.md"
created: 2026-04-14
updated: 2026-04-14
---

# Pick Dedup Multi-Theory Limitation

The value betting scanner deduplicates picks by a deterministic UUID based on `(player, prop, side, line, game_date, soft_book)`. The `triggered_by` field records only the first theory (alphabetically) that passes for a given pick, meaning overlapping theories cannot produce independent pick rows. This architectural limitation blocks naive multi-variant A/B testing and was worked around by a belt-and-suspenders approach: a `theory_evs` JSONB column to persist per-theory EV at trigger time, plus offline replay against trail data.

## Key Points

- Pick IDs are deterministic UUIDs from `(player, prop, side, line, game_date, soft_book)` — same market always hashes to the same UUID regardless of which theory evaluates it
- `triggered_by` records only the first alphabetical theory that fires for a given pick ID — all other theories' evaluations are silently lost
- Deploying 5 overlapping theories that evaluate the same markets produces exactly the same pick rows as deploying 1, just with different `triggered_by` attribution
- **Option A (theory_evs column):** `ALTER TABLE nba_tracked_picks ADD COLUMN theory_evs JSONB` stores each theory's computed EV at trigger time, preserving multi-theory data without schema redesign
- **Option B (offline replay):** Deploy one liberal "net cast" theory that over-captures, then replay 5 variant hypotheses offline against trail data — no schema changes, no deploys, no rollback risk
- The adopted approach is belt-and-suspenders: both A and B together

## Details

### The Dedup Architecture

The tracker evaluates every market against every active theory. When a theory's criteria are met (EV exceeds threshold, sharp count sufficient, prop type not excluded), the tracker creates a pick. The pick ID is derived from the market identity — not the theory — so two theories evaluating the same market produce the same pick ID. The tracker checks whether this pick ID already exists; if so, it skips the insert. If not, it inserts the pick with `triggered_by` set to the current theory's name.

Because theories are evaluated in alphabetical order, the first alphabetically always wins the `triggered_by` field. In AFL's case, `AFL Disposals` (broken, uses `one_sided_consensus`) sorted before `AFL Disposals 5-Book` (correct, uses `multiplicative`), causing the broken theory to claim attribution for shared picks. See [[concepts/one-sided-consensus-structural-bias]] for the specific impact.

### Why Naive A/B Testing Fails

The user proposed "casting the net" — deploying multiple AFL theories forward to collect parallel data for backtest comparison. But this approach collides with the dedup architecture: if all 5 theories evaluate the same market and produce the same pick ID, only one pick row is created, tagged with whichever theory name sorts first. There is no mechanism to record that 4 other theories also would have triggered the same pick at potentially different EV values.

This makes it impossible to compare theory performance retrospectively using `triggered_by` alone — the field doesn't represent "the theory that found this pick" so much as "the theory whose name sorts first."

### Option A: theory_evs Column

Adding a `theory_evs JSONB` column to `nba_tracked_picks` stores a dictionary of `{theory_name: computed_ev}` for every theory that evaluated the pick at trigger time. This preserves the multi-theory information that `triggered_by` loses. The column is populated during the tracker's evaluation loop, before the dedup check, so all theories' EV values are recorded even though only one pick row exists.

This requires a schema migration (`ALTER TABLE`) and a code change in `server/tracker.py` (~line 889) to build and persist the `theory_evs` dict.

### Option B: Offline Replay

The alternative avoids production changes entirely. A single liberal "net cast" theory is deployed with min_ev=1 (very permissive) to capture the broadest possible universe of picks. Five variant hypotheses are defined as configuration objects, and an offline replay script (`scripts/afl_replay_variants.py`) applies each variant's devig method, weight scheme, and filters to the trail data captured by the net-cast theory. This produces per-variant performance metrics without any schema changes, deployments, or rollback risk.

The five planned variants are:
1. **baseline_prod** — current `AFL Disposals 5-Book` weights
2. **under_only** — same weights but only Under picks
3. **power_devig** — power method instead of multiplicative
4. **sportsbet_in** — Sportsbet (900) weighted 1.0 as a sharp, others reduced
5. **no_entain** — remove Bet Right (901) and Ladbrokes (903) (both Entain-owned, potentially correlated)

The offline approach is equivalent to live multi-variant testing because trail data captures the full sharp + soft odds timeline at the moment of trigger. Any devig method or weight combination can be applied retroactively.

### The Belt-and-Suspenders Decision

Both options were adopted together: Option A provides real-time multi-theory data that can be queried directly from Supabase, while Option B provides flexible offline analysis without depending on the schema migration being complete. The approaches are complementary — Option A answers "what did each theory compute at trigger time?" while Option B answers "what would have happened under a completely different configuration?"

## Related Concepts

- [[concepts/value-betting-theory-system]] - The theory system whose limitations this article describes
- [[concepts/one-sided-consensus-structural-bias]] - The specific theory bug that the attribution hijack compounded
- [[concepts/afl-circular-devig-trap]] - The broader AFL devig problem that motivates testing alternative configurations
- [[concepts/trail-data-temporal-resolution]] - Trail data quality is a prerequisite for offline replay to work

## Sources

- [[daily/lcash/2026-04-14.md]] - Pick dedup architecture limits A/B testing; `triggered_by` records first alphabetical theory only; Option A (theory_evs JSONB column) + Option B (offline replay with 5 variants) adopted as belt-and-suspenders; net cast theory config: min_ev=1, multiplicative/poisson, books 900/901/903/908/911 (Sessions 13:49, 14:31, 16:02)
