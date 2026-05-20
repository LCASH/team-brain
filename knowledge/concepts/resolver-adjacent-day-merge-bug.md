---
title: "Resolver Adjacent-Day Stat Merge Bug"
aliases: [adjacent-day-merge, dates-to-fetch-ordering, first-wins-merge-bug, resolver-date-iteration, mlb-wrong-actual-stat]
tags: [value-betting, resolver, bug, data-quality, mlb, methodology]
sources:
  - "daily/lcash/2026-05-20.md"
created: 2026-05-20
updated: 2026-05-20
---

# Resolver Adjacent-Day Stat Merge Bug

The value betting scanner's pick resolver had a critical date-iteration bug where `dates_to_fetch = [day-1, target, day+1]` with a first-occurrence-wins dict merge caused **~16% of MLB batting picks to have wrong `actual_stat` values and ~12% to have flipped W/L results**. The root cause: when looking up a player's game stats, the resolver iterated day-before first, and any player who played on consecutive days got yesterday's stats stamped on today's picks. Discovered on 2026-05-20 via cross-referencing imported journal picks against MLB Stats API ground truth. The initial fix (reorder to `[target, day-1, day+1]`) was incomplete; the real fix required per-pick ET-date derivation using `ZoneInfo("America/New_York")`.

## Key Points

- `dates_to_fetch = [day-1, target, day+1]` iterated day-before first with a "first-wins" dict merge — players who played consecutive days got yesterday's stats stamped on today's picks
- **16.4% of 809 MLB batting picks had wrong `actual_stat`**, 12.2% (99 picks) had flipped W/L result — silently corrupting ROI/Brier calibration metrics
- The initial fix (reorder to `[target, day-1, day+1]`) was **incomplete** — only worked for ~58% of picks because bulk date assignment at file level still misassigned picks near midnight UTC
- The real fix: **per-pick ET-date derivation** via `ZoneInfo("America/New_York")` converting each pick's `game_start` to Eastern Time before determining which date's stats to fetch
- Bug was invisible to all internal consistency monitoring (M1-M7) — only caught via external ground-truth comparison (M8) against MLB Stats API, triggered by Jay's imported localStorage picks
- Mass re-resolution: MLB 98.9% resolved (33,640/34,002), NBA 96.1% (25,658/26,699); M8 audit passed with **0.00% disagreement** on 500-pick sample

## Details

### The First-Wins Merge Mechanism

The resolver's `_fetch_mlb_batting_stats()` function fetches player stats from the MLB Stats API across a 3-day window to handle timezone boundary games. The implementation used a dict merge pattern where the first stats found for each player won:

```python
dates_to_fetch = [day - timedelta(1), target_date, target_date + timedelta(1)]
for date in dates_to_fetch:
    stats = fetch_from_mlb_api(date)
    for player, stat_line in stats.items():
        if player not in result_dict:  # first-wins
            result_dict[player] = stat_line
```

Because `day-1` was iterated first, any player who played on both days had their day-before stats locked in before the target-date stats were even checked. For example, Salvador Perez had H=2 on May 17 and H=0 on May 18 — the resolver returned 2 (wrong) for May 18 picks because the May 17 stats were seen first.

### Why the Initial Fix Was Incomplete

The first fix (commit `0e0afd0`) simply reordered `dates_to_fetch` to `[target, day-1, day+1]` so the target date's stats would win. This worked when the target date was correctly determined, but the target date itself was derived from a file-level or bulk date assignment that didn't account for the UTC-to-Eastern-Time boundary. MLB games that start at 11:30 PM ET on May 17 have a `game_start` after midnight UTC (May 18 UTC), so a UTC-based date assignment stamps them as May 18 picks — but their stats are filed under May 17 in the MLB Stats API (which uses Eastern Time).

The real fix derives the target date per-pick by converting `game_start` to Eastern Time:

```python
from zoneinfo import ZoneInfo
et_date = pick.game_start.astimezone(ZoneInfo("America/New_York")).date()
```

This ensures each pick's stat lookup uses the correct game date regardless of UTC boundary effects. The per-pick approach eliminated the entire class of date-assignment bugs that the bulk approach was susceptible to.

### Discovery via External Ground Truth

The bug was invisible to all seven internal monitoring queries (M1-M7) because those queries checked internal consistency — pick IDs match, trails exist, CLV values are populated. None compared the resolver's `actual_stat` against an independent external source. Jay's imported localStorage picks provided the external ground truth: his manually recorded W/L outcomes disagreed with the resolver's grades on specific picks, and web searches against MLB Stats API confirmed Jay was right.

This led to the creation of M8 — a weekly ground-truth cross-check that samples resolved MLB picks and validates `actual_stat` against the MLB Stats API directly. The M8 audit on the re-resolved data passed with 0.00% disagreement across a 500-pick, 35-day sample (2026-04-15 to 2026-05-20), with 48 expected unknowns (doubleheaders/no box-score row).

### Re-Resolution Scope and Results

The entire Apr 13 → May 15 bug window was re-resolved:

| Sport | Total Picks | Resolved | Rate | Wrong actual_stat | Flipped W/L |
|-------|------------|----------|------|-------------------|-------------|
| MLB batting | 809 cleared | 809 | 100% | 133 (16.4%) | 99 (12.2%) |
| MLB total | 34,002 | 33,640 | 98.9% | — | — |
| NBA | 26,699 | 25,658 | 96.1% | Unknown | Unknown |

The ~3% unresolved rate is the expected floor: pitchers who didn't start, players who didn't play, voided lines, and fuzzy-match misses. The `bypass_stale_gate` kwarg was added to `resolve_picks()` for explicit backfills past the 14-day staleness gate.

### Calibration Data Contamination

Any Brier score, ROI sweep, or calibration run executed against MLB data before this fix used 16%-wrong results. The `calibrate_weights.py` and `promote_theories.py` scripts were placed under a hard stop until M8 runs cleanly for a week. Historical calibration results should be discarded and re-run against the corrected data.

### The Anti-Pattern: First-Wins Merge from Multi-Source Iteration

"First-occurrence-wins merge across multi-source iteration" is a dangerous anti-pattern because iteration order silently determines correctness. The resolver's `dates_to_fetch` is one instance; the codebase should be grepped for similar patterns where a dict is populated from multiple sources with the first value winning. At least one more was identified at `resolver.py:1391-1394`.

## Related Concepts

- [[connections/silent-type-coercion-data-corruption]] - Adjacent-day merge is another "plausible wrong output" pattern: the resolver returns valid-looking stats, passes all internal checks, and only fails external ground-truth comparison
- [[concepts/dd-td-resolver-bias]] - A different resolver grading bug (encoded stat misinterpretation); both were caught via external comparison, not internal monitoring
- [[concepts/tracker-pipeline-7-phase-audit]] - M8 ground-truth audit was added to the audit suite after this bug; Phases 1-7 all passed despite the resolver producing wrong results — internal consistency ≠ correctness
- [[concepts/opticodds-partial-stats-silent-misresolution]] - A third class of resolver error: correct code, incomplete upstream data. This bug is: wrong code, complete data.
- [[concepts/journal-manual-pick-pipeline-integration]] - Jay's imported journal picks provided the ground truth that exposed this bug

## Sources

- [[daily/lcash/2026-05-20.md]] - Salvador Perez H=2 (May 17) stamped on May 18 picks (should be H=0); Realmuto H=1 (May 17) stamped on May 18 (should be H=0); 133/809 (16.4%) wrong actual_stat, 99/809 (12.2%) flipped W/L; initial fix (reorder dates_to_fetch) incomplete — per-pick ET-date derivation is real fix; mass re-resolve MLB 98.9%, NBA 96.1%; M8 audit 0.00% disagreement on 500-pick sample; bypass_stale_gate kwarg added; calibration data contaminated — hard stop on calibrate_weights.py (Sessions 12:38, 13:34, 19:27, 20:03)
