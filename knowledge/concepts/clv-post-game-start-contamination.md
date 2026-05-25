---
title: "CLV Post-Game-Start Contamination and OO Historical Cleanup"
aliases: [clv-contamination, post-game-odds-capture, captured-at-gate, oo-historical-cleanup, closing-odds-contamination]
tags: [value-betting, data-quality, clv, resolver, opticodds, bug]
sources:
  - "daily/lcash/2026-05-22.md"
created: 2026-05-22
updated: 2026-05-22
---

# CLV Post-Game-Start Contamination and OO Historical Cleanup

On 2026-05-22, lcash investigated ~390 contaminated picks where the closing line (CLV) data included post-game-start odds — odds captured during live play rather than the true pre-game closing price. The forward fix gates `captured_at <= game_start` to prevent live-play contamination (deployed and verified on Eve PID 1464926). The backward cleanup was initially thought unrecoverable, but after the user challenged incorrect API assumptions, OpticOdds' `/fixtures/odds/historical` endpoint was confirmed to retain data for completed games — making historical CLV cleanup viable by NULLing contaminated entries and re-running the backfill script.

## Key Points

- **~390 picks contaminated**: closing line data captured DURING live play rather than at pre-game close — CLV values are wrong because in-play odds diverge from pre-game closing odds
- **Forward fix deployed**: gate filter `captured_at <= game_start` prevents in-play odds from entering closing line computation (verified on Eve)
- **Backward cleanup IS viable**: OpticOdds retains historical odds for completed games (earlier "completed = purged" hypothesis was wrong); `backfill_closing_sharps.py` can recover true closing lines
- **OO market names use `player_` prefix** (e.g., `player_home_runs`, `player_hits`), NOT `batter_` — the backfill script at `scripts/backfill_closing_sharps.py:85-104` has the correct mapping; using wrong names returns empty results that look like "no data exists"
- **Contamination magnitude varies by book**: some books match exactly (line didn't move after tipoff), others off by 20-60 cents — the damage is real but not uniform
- **Raw evidence matters**: user pushback ("don't make up shit") forced proper verification of API params against working code, catching two errors in the assistant's claims

## Details

### The Contamination Mechanism

The value betting scanner's closing line computation captures the last known soft and sharp odds before game start. When the `captured_at` gate was absent or misconfigured, odds from during live play could be included in the "closing" snapshot. In-play odds are structurally different from pre-game closing odds — they reflect the current game state (score, time remaining, momentum), not the market's pre-game assessment of true probability.

For CLV analysis, this contamination is particularly damaging because CLV measures whether the bettor got a price better than the market's final pre-game assessment. If the "closing" price includes in-play odds, the CLV computation compares the bettor's pre-game price against a fundamentally different market — producing meaningless results. A positive CLV computed against in-play odds doesn't indicate edge; it indicates the game state happened to move in one direction after tipoff.

### Forward Fix

The deployed gate ensures that only odds captured BEFORE game start enter the closing line computation:

```
WHERE captured_at <= game_start
```

This is a simple, robust filter. When combined with the JournalTracker's OO fixture status game-end detection (see [[concepts/journal-tracker-manual-pick-trail-writing]]), the full lifecycle is: trail entries written until game starts (pre-game window), then stop when OO reports `completed`. The closing line is derived from the last trail entry before `game_start`.

### OpticOdds Historical API Discovery

The backward cleanup was initially declared unrecoverable because the assistant incorrectly stated that OpticOdds had no historical data for completed games. The user challenged this claim twice, forcing proper verification. The investigation revealed two errors:

1. **Wrong market names**: Used `batter_home_runs` instead of the correct `player_home_runs`. The backfill script at `scripts/backfill_closing_sharps.py:85-104` has the correct `player_` prefix mapping.
2. **Wrong fixture IDs**: Initial queries used incorrect fixture identifiers, producing empty results that were misinterpreted as "data doesn't exist."

Once correct parameters were used, OpticOdds returned 12-80 entries per book×market with real closing lines. This confirms the `/fixtures/odds/historical` endpoint retains data after games complete — the earlier "completed = purged" hypothesis was definitively wrong.

### Cleanup Procedure

The recommended cleanup for the ~390 contaminated picks:

1. **Sample validation**: Check 5-10 random contaminated picks for side-by-side comparison of stored vs OO closing lines to quantify impact
2. **NULL contaminated entries**: Set closing line fields to NULL for the identified picks
3. **Re-run backfill**: Execute `backfill_closing_sharps.py` against the NULLed picks to recover true OO closing lines
4. **Verify**: Confirm tonight's MLB game completions produce clean CLV data via the new gate (organic post-fix validation)

### Diagnostic Lesson

This investigation reinforced a critical diagnostic principle: **always verify API parameters against working code before concluding data is unavailable.** The backfill script had the correct mappings; the ad-hoc investigation used wrong field names. When an API returns empty results, the first hypothesis should be "wrong parameters" not "data doesn't exist" — especially when a working script using the same API exists in the codebase.

## Related Concepts

- [[concepts/opticodds-clv-backfill-audit]] - The OpticOdds CLV backfill pipeline that provides the cleanup mechanism; the `player_` prefix mapping at `backfill_closing_sharps.py:85-104` is the same mapping needed here
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV is the primary theory evaluation metric; contaminated closing lines corrupt per-theory rankings for the ~390 affected picks
- [[concepts/trail-anchored-bundle-read-layer-fix]] - The anchored bundle ensures temporal alignment between soft and sharp trail data; the `captured_at <= game_start` gate is a complementary filter at the data boundary
- [[concepts/odds-staleness-pipeline-diagnosis]] - The broader staleness pipeline analysis; post-game contamination is a new staleness vector (too fresh rather than too stale)
- [[concepts/journal-tracker-manual-pick-trail-writing]] - The JournalTracker's OO fixture status game-end detection provides the authoritative signal for when to stop trail capture

## Sources

- [[daily/lcash/2026-05-22.md]] - ~390 contaminated picks with post-game-start odds; forward gate `captured_at <= game_start` deployed on Eve PID 1464926; assistant incorrectly claimed OO had no data for completed games — user challenged twice, forcing verification; wrong market names (`batter_` vs `player_`) caused false "no data" results; OO retains 12-80 entries per book×market for completed games; backfill_closing_sharps.py:85-104 has correct mappings; contamination varies 0-60 cents by book; sample 5-10 picks before full cleanup (Session 15:42)
