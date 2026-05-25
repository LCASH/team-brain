---
title: "Resolver Merged-Dict Fallback Cross-Game Contamination"
aliases: [merged-dict-fallback, cross-game-contamination, resolver-fallback-leniency, fixture-gate-select-bug, oo-fallback-utc-bucketing]
tags: [value-betting, resolver, bug, data-quality, architecture]
sources:
  - "daily/lcash/2026-05-21.md"
created: 2026-05-21
updated: 2026-05-21
---

# Resolver Merged-Dict Fallback Cross-Game Contamination

The value betting resolver had a **two-bug stack** that caused stats from wrong games to be applied when the same matchup occurred on consecutive days (e.g., SD@LAD, LAA@OAK back-to-back). Bug 1: the fixture-completion gate (commit `54d925f`) was architecturally correct but **unreachable** because the pick SELECT clause didn't include `fixture_name` — so `pick.get("fixture_name")` always returned `None` and the gate was silently bypassed. Bug 2: when the per-date MLB Stats API lookup failed to find data (because the game hadn't finished yet), the resolver fell through to a merged flat dict from OpticOdds that contained yesterday's same-team stats — converting "no data yet" into "wrong data."

## Key Points

- **Bug 1 (fixture gate unreachable)**: `fixture_name` omitted from SELECT clause → `pick.get("fixture_name")` always returns `None` → gate never fires → wrong-game stats pass through unchecked
- **Bug 2 (OO fallback contamination)**: When MLB Stats API has no data for a player on a date, the resolver fell through to OpticOdds' `opt_stats_by_date` — a UTC-bucketed dict that can contain yesterday's same-team stats (late-night games in ET land in "today" UTC)
- **Example**: Kiner-Falefa TB=3 from May 19 applied to May 20 pick because May 20 game hadn't finished → per-date lookup returned nothing → OO fallback returned May 19 stats
- **Fix (3 layers)**: (1) `fixture_name` added to SELECT clause (commit `f7ae928`), (2) merged-dict fallback killed for all sports (commit `d8da8a9`), (3) OO fallback killed for MLB (commit `15ae6bf`)
- **Key principle**: leniency in resolvers is dangerous — converting "no data yet" into "wrong data" is worse than skipping and retrying next cycle

## Details

### The Fixture Gate SELECT Bug

The fixture-completion gate was designed to prevent grading picks before their game finished. The code checked whether the pick's `fixture_name` appeared in OpticOdds' list of completed fixtures. If not, the pick was skipped with `skip_fixture_not_complete`. This is architecturally correct — it prevents grading against incomplete or wrong-game data.

However, the Supabase SELECT query that loaded picks for resolution didn't include `fixture_name` in its column list. In Python, `pick.get("fixture_name")` on a dict without the key returns `None`. The gate compared `None` against the completed fixtures list, found no match (correctly — `None` is never in any list), and the pick fell through to the stat-fetching logic below. The gate existed, was correct, and was unreachable.

A SELECT clause silently omitting a column makes downstream `.get()` return `None` — the guard logic looks perfect but never executes. This is a Python-specific variant of the "dead code" pattern: the code isn't syntactically dead (no `if False:` guard), but it's semantically dead because its input is always `None`.

### The OO Fallback UTC Bucketing Problem

The OpticOdds fallback existed as leniency: "if the per-date MLB Stats API lookup doesn't have this player, try the OO stats dict." The problem is that OO's `opt_stats_by_date` dict is bucketed by UTC date, not ET date. A game starting at 11:30 PM ET on May 19 has a `start_date` of May 20 in UTC. If the resolver queries May 20 stats from OO, it gets the May 19 game's results (because they completed in the May 20 UTC window).

For same-matchup back-to-back games (SD@LAD May 19 and May 20), the OO May 20 bucket contains May 19's stats for the same players. The resolver finds "Kiner-Falefa TB=3" in the OO fallback, grades the May 20 pick as if it's from a completed game, and produces a wrong result. The per-date MLB Stats API lookup correctly returned nothing (May 20 game hadn't finished), but the fallback bypassed this correct "not ready" signal.

### Why Merged-Dict Fallback Is Dangerous

The merged-dict fallback was designed for leniency: "don't let a minor date mismatch prevent resolution." But in resolvers, leniency converts "no data" (skip, retry next cycle) into "wrong data" (grade, record permanently). This is fundamentally different from leniency in scrapers (where missing data means fewer picks, not wrong picks) or display layers (where stale data is better than no data).

The principle: **absence of stats data should be the gating signal, not the trigger for fallback.** If the MLB Stats API has nothing for player X on date Y, the correct response is "skip and retry next cycle" — not "search other data sources that may contain wrong-date data."

### The Belt-and-Suspenders Fix

Three independent layers ensure this class of bug cannot recur:

1. **Layer 1 (fixture gate)**: `fixture_name` added to SELECT clause (commit `f7ae928`) — the gate now actually executes, checking whether the game has completed before allowing stat resolution
2. **Layer 2 (merged fallback killed)**: The merged flat dict that combined stats across dates was removed entirely (commit `d8da8a9`) — per-date lookups are the only path
3. **Layer 2.5 (OO fallback killed for MLB)**: The OpticOdds fallback for MLB was removed (commit `15ae6bf`) — absence of MLB Stats API data now means "not published yet, retry" rather than falling through to UTC-bucketed OO data

Any single layer would have prevented the May 21 incident. Together they provide defense in depth.

### Scope Beyond MLB

The merged-dict fallback pattern existed for all sports, not just MLB. NBA avoided triggering it only because 48+ hour gaps between same-matchup games kept UTC buckets separate. NBA back-to-back games (same opponent two nights in a row) could eventually trigger the same contamination. The fix applies to all sports.

## Related Concepts

- [[concepts/resolver-adjacent-day-merge-bug]] - The prior resolver date bug: `dates_to_fetch` ordering stamped wrong-day stats. This bug is a different mechanism (fallback path, not iteration order) but the same symptom (wrong-game stats applied)
- [[connections/first-wins-merge-iteration-anti-pattern]] - The broader pattern of dict merges silently determining correctness; the OO fallback is a new variant where the fallback source contains wrong-date data
- [[concepts/resolver-utc-scan-window-gap]] - Discovered in the same day; the scan window gap prevented picks from being resolved, while this bug caused picks to be resolved *incorrectly*
- [[connections/silent-type-coercion-data-corruption]] - Wrong-game stats are another "plausible wrong output" — structurally valid stats from a real game, just not the right game

## Sources

- [[daily/lcash/2026-05-21.md]] - Traced Kiner-Falefa TB=3 from May 19 applied to May 20; fixture gate unreachable because SELECT omitted fixture_name; OO fallback contains yesterday's UTC-bucketed stats for same-team players; 3-layer fix: SELECT fix (f7ae928), merged-dict kill (d8da8a9), OO fallback kill for MLB (15ae6bf); Layer 1 showed 45/91 fixture-name mismatches on May 20 picks (Sessions 09:55, 14:47)
