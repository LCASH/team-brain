---
title: "NBA Milestone Prop Collision Bug"
aliases: [nba-milestone-collision, nba-co-suffix-needed, nba-milestone-vs-ou, points-high-low-collision]
tags: [value-betting, bet365, nba, data-quality, bug, parser]
sources:
  - "daily/lcash/2026-05-22.md"
created: 2026-05-22
updated: 2026-05-22
---

# NBA Milestone Prop Collision Bug

On 2026-05-22, lcash discovered that the NBA bet365 wizard parser (`bet365_game.py`) emits both milestone props ("20+ Points" at line 19.5) and standard Over/Under as `prop_type="Points" side="Over"`, causing `market_key` collision. This is the exact same bug that was fixed for MLB on 2026-05-15 with the `_CO` suffix (see [[concepts/co-ou-parser-conflation-phantom-picks]]), but the NBA parser at lines 229-241 (milestone) and 186-198 (O/U) was never given the same treatment. Additionally, bet365 sends multiple alt lines (17.5, 24.5, 30.5, 37.5, 49.5) in the same wizard payload — all landing on the same `market_key` (which has no line component), with last-write-wins producing wrong EV when a random alt-line's odds are paired against sharp consensus at a different line.

## Key Points

- **NBA milestone props ("20+ Points") collide with standard O/U** on the same `prop_type="Points" side="Over"` — identical to the MLB CO/OU conflation fixed on May 15
- **MLB fix (`_CO` suffix) was never applied to NBA** — lines 229-241 (milestone handler) and 186-198 (O/U handler) in `bet365_game.py` both emit to the same key
- **Soft trail oscillation observed**: SGA Points pick showed trail alternating between line=23.5 and line=37.5 — the JournalTracker captured both alt-line writes to the same market_key
- **Alt-line overwrite within O/U** is a separate compounding bug: bet365 sends 5 alt lines (17.5, 24.5, 30.5, 37.5, 49.5) per player; all map to one key; last-write-wins produces random line pairing with sharps
- **Fix is the same as MLB**: append `" CO"` suffix to milestone `prop_type` values in the NBA parser — option #2 from analysis; kills milestone-vs-O/U collision without touching market_key structure

## Details

### The Collision Mechanism

The bet365 BB wizard response for NBA contains both standard Over/Under props (e.g., "Anthony Edwards Points Over 25.5 @ 1.83") and milestone threshold props (e.g., "20+ Points @ 1.44") for the same player. The NBA parser at `bet365_game.py` maps both to `prop_type="Points"` with `side="Over"`. Since `market_key = (player, prop_type, side)` has no line component, both record types share the same key in the DataStore.

When the diff-cache or DataStore receives a milestone write (Over 19.5 at 1.44) followed by a standard O/U write (Over 25.5 at 1.83) — or vice versa — one overwrites the other. The stored odds could be either variant depending on write order, and the devig pipeline pairs whichever odds are stored against the sharp consensus line (typically 25.5 for Pinnacle). If the milestone's odds (1.44 for Over 19.5 — a near-certainty) happen to be stored, they're paired against sharps at 25.5, producing phantom negative EV. If an extreme alt-line's odds are stored (49.5 at very long odds), phantom positive EV is produced.

### Why This Wasn't Caught Earlier

The MLB variant of this bug was caught because 72% of recent MLB Bet365 picks were phantoms — a dramatic signal. The NBA variant was subtler because: (1) NBA has fewer milestone props per game than MLB, (2) the alt-line overwrite within O/U is a separate but compounding issue that's harder to attribute to milestones specifically, and (3) the JournalTracker's soft trail oscillation (SGA Points alternating 23.5↔37.5) was the first clear per-pick diagnostic signal.

### Two Separate Bugs, Same Root Cause

The session identified two distinct bugs sharing the `market_key` collision root cause:

**Bug 1 — Milestone vs O/U collision**: Milestone "20+ Points" (line 19.5) and standard "Points Over 25.5" both map to `("Player", "Points", "Over")`. Fix: append `" CO"` suffix to milestone prop_types, mirroring the MLB fix.

**Bug 2 — Alt-line overwrite within O/U**: bet365 sends 5 different O/U lines per player (17.5, 24.5, 30.5, 37.5, 49.5) in the same wizard payload. All 5 map to the same `market_key`. Last-write-wins means the stored odds are from a random alt line, not necessarily the main line. Fix options: (a) key markets by line (bigger blast radius), (b) `_tag_main_lines()` post-processor (already deployed for the same-book alt-line collision — see [[concepts/bet365-same-book-alt-line-collision]]).

Bug 1 is the higher priority because milestones have structurally different odds from O/U (near-certainties at low thresholds vs standard probabilities at main lines), producing the most dramatic phantom EV. Bug 2 produces smaller distortions because all 5 alt lines are at least the same market type.

## Related Concepts

- [[concepts/co-ou-parser-conflation-phantom-picks]] - The identical bug on MLB, fixed on May 15 with `_CO` suffix across 4 parser files; NBA was defensively included in that fix for `ws_nba.py` but the game scraper parser at `bet365_game.py` was missed
- [[concepts/bet365-same-book-alt-line-collision]] - The alt-line-within-O/U overwrite bug; `_tag_main_lines()` post-processor tags median as `is_main=True`, blocking alt→main overwrites via the DataStore guard at `state.py:285-287`
- [[connections/market-key-dateless-design-recurring-bugs]] - The NBA milestone collision is a seventh manifestation of the lineless, dateless market_key design causing collisions
- [[concepts/push-loop-diff-cache-phantom-freshness]] - The diff cache where alt-line flapping (Bug 1 in the diff cache article) is the same collision at the cache layer

## Sources

- [[daily/lcash/2026-05-22.md]] - SGA Points soft trail oscillating between line=23.5 and line=37.5; traced to bet365_game.py lines 229-241 (milestone) and 186-198 (O/U) both emitting prop_type="Points" side="Over"; MLB fix (_CO suffix) never applied to NBA game scraper parser; 5 alt lines (17.5, 24.5, 30.5, 37.5, 49.5) all landing on same market_key; option #2 (CO suffix split) recommended to mirror MLB fix (Session 09:57)
