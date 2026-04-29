---
title: "bet365 MLB Batch API and CO Segment Format"
aliases: [batch-api, batchmatchbettingcontentapi, co-segment-format, co-columns, milestone-format]
tags: [bet365, mlb, scraping, reverse-engineering, data-format]
sources:
  - "daily/lcash/2026-04-21.md"
  - "daily/lcash/2026-04-29.md"
created: 2026-04-21
updated: 2026-04-29
---

# bet365 MLB Batch API and CO Segment Format

In mid-April 2026, bet365 migrated MLB player props from individual `matchbettingcontentapi` responses to a `batchmatchbettingcontentapi` endpoint that delivers all prop markets in a single payload using a segment-based format. The new format uses MG (Market Group), MA (Market Area), CO (Column), and PA (Participant) segments to pack 8 milestone threshold columns per player — a much denser data delivery than the previous Over/Under toggle format. This is the fourth major API format change for the MLB scraper.

## Key Points

- bet365 changed MLB props from `matchbettingcontentapi` (individual responses per market) to `batchmatchbettingcontentapi` (single batch payload with all markets)
- New CO (Column) segment format: `MG → MA (players with names) → MA (no NA, odds grid) → CO NA=1 → PA odds → CO NA=2 → PA odds → ... → CO NA=8`
- PA IDs are consistent between the player list MA and the odds grid — `PA ID=1056417056` in the player list matches the same ID in the CO odds sections
- Each CO segment represents a milestone threshold (1-8), mapping to line N-0.5 with side="Over"
- Odds are in fractional format (e.g., `2/9`) requiring conversion to decimal
- The fix was minimal: ~8 lines added at `bet365_mlb_game.py:216-224` to set `current_section = "milestone_{N}"` so the existing milestone PA handler picks it up automatically
- Parser confirmed working locally: 333 odds from a single game

## Details

### The Data Structure

The batch API response follows a hierarchical segment structure. At the top level, `MG` (Market Group) segments define market types like "Total Hits, Runs and RBIs", "Total Bases", or "Strikeouts". Each MG contains two `MA` (Market Area) segments:

1. **Player list MA** — contains PA entries with player names (`NA=`), last-5 game stats, and participant IDs. This MA has an `NA=` attribute identifying the market label.

2. **Odds grid MA** — has no `NA=` attribute (distinguishing it from the player list). Contains `CO` (Column) segments numbered 1-8, each representing a different milestone threshold. Within each CO, PA entries carry the odds (`OD=` in fractional format) for that specific threshold.

The CO segment structure is fundamentally different from the previous Over/Under format. Instead of offering separate Over and Under toggles per player per market, bet365 now offers a grid of milestone thresholds (1+, 2+, 3+, ... 8+) where each column represents a different line. This is denser — a single batch response contains the equivalent of what previously required multiple separate API calls and DOM interactions.

### Parser Implementation

The fix was deliberately minimal. Rather than building a new parser from scratch, an ~8-line CO segment handler was added to the existing parser at `bet365_mlb_game.py:216-224`. When the parser encounters a CO segment with `NA=N`, it sets `current_section = "milestone_{N}"`. This feeds into the existing milestone PA handler, which already knows how to extract odds from PA entries within a milestone section. The threshold N maps to `line = N - 0.5` with `side = "Over"` — the existing conversion logic.

This approach leverages the fact that the new format's PA entries use the same field codes (`OD=`, `NA=`, `FI=`) as the old format. The structural difference is in the container hierarchy (CO segments instead of separate responses), not in the individual data fields.

### Batter vs Pitcher Props

The CO format applies to both batter and pitcher prop markets, but they load differently:

- **Pitcher props** tabs return data without market expansion — some markets are "default open" and deliver 19-20 odds per game immediately on tab click
- **Batter props** return an initial menu structure (~10KB with MG names) but require additional market expansion clicks to trigger the actual odds data

This asymmetry means the scraper handles pitcher props with a simpler flow (click tab → capture response) while batter props require the more complex click-expand-capture sequence.

### Market Name Mapping

The batch response uses descriptive market names that must be mapped to the scanner's internal prop type identifiers:

| bet365 MG Name | Scanner Prop Type |
|----------------|-------------------|
| Total Hits, Runs and RBIs | `player_hits_runs_rbis` |
| Total Bases | `player_total_bases` |
| Strikeouts | `player_strikeouts` |
| Hits | `player_hits` |
| Home Runs | `player_home_runs` |
| RBIs | `player_rbis` |

Some MG groups (particularly pitcher-specific props) may use different structures. The parser handles the common format and logs unrecognized MG groups for future mapping.

### RBIs Name Mismatch (2026-04-29)

On 2026-04-29, lcash discovered that bet365 renamed the "Runs Batted In" market group to "RBIs" in their API responses. The production scraper's market name mapping had the old name, causing it to silently drop approximately 109 RBI records per game. This is a recurring data format drift pattern — upstream API changes that produce zero errors but silently lose data (see [[connections/silent-type-coercion-data-corruption]]). The fix was a simple map patch adding the new name.

Additionally, two formats per stat were confirmed to exist: CO milestones (threshold-style, e.g., "3+ RBIs") and standard O/U (over/under line). The games-list surface only has O/U format, while per-game tabs have both — many edges live in the CO milestone alt lines that are only available via per-game fetching.

## Related Concepts

- [[concepts/bet365-mlb-lazy-subscribe-migration]] - The prior API migration history (v1 BB wizard → v2 lazy-subscribe → v3 hybrid → v4 batch API)
- [[concepts/bet365-racing-data-protocol]] - The racing adapter uses similar pipe-delimited field codes (NA=, OD=, FI=) in a different structural format
- [[concepts/spa-navigation-state-api-access]] - The batch API fires from specific navigation states; hash navigation alone doesn't trigger it
- [[connections/anti-scraping-driven-architecture]] - The batch API is yet another format change in bet365's evolving defense stack
- [[concepts/bet365-mlb-hash-nav-mg-fetching]] - Hash-nav with G-ids provides deterministic URL-driven access to all 25 MGs, replacing click-expand; discovered alongside the RBIs name mismatch

## Sources

- [[daily/lcash/2026-04-21.md]] - Implementation plan: old `matchbettingcontentapi` → new `batchmatchbettingcontentapi` with MG/MA/CO/PA segment hierarchy; debug dump analysis showing CO NA=1→8 structure; PA ID consistency between player list and odds grid; fractional odds format (Session 09:13). CO segment handler added as ~8 lines at `bet365_mlb_game.py:216-224`; threshold N maps to line N-0.5; 333 odds from single game confirmed locally; pitcher props auto-load without expansion, batter props need expansion clicks (Session 09:27). Parser confirmed working with 333 odds from a single game locally (Session 10:41)
- [[daily/lcash/2026-04-29.md]] - RBIs name mismatch: bet365 renamed "Runs Batted In" → "RBIs" silently dropping ~109 records/game; two formats per stat (CO milestones vs O/U) confirmed; games-list only has O/U, per-game tabs have both (Session 18:02)
