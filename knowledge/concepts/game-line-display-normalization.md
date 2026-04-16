---
title: "Game-Line Display Normalization"
aliases: [team-name-display, moneyline-labels, game-line-dashboard, side-label-translation]
tags: [value-betting, dashboard, ui, data-quality, game-lines]
sources:
  - "daily/lcash/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# Game-Line Display Normalization

When the value betting scanner expanded from player props to game-line markets (moneyline, spread, totals), the dashboard displayed raw "Over"/"Under" side labels — meaningless for team-selection markets where the bettor needs to know which team to bet on. The fix extracts home/away team names from `fixture_name` and displays them instead. Three distinct bugs surfaced during implementation: side label translation, a `prop_type` format mismatch, and empty `player_name` fields hitting Supabase NOT NULL constraints.

## Key Points

- Moneyline and spread picks showed "Over"/"Under" instead of team names — useless for a bettor deciding which team to back
- Team names are extracted from `fixture_name` (split on "vs" or "@") and mapped: Over→home team, Under→away team, with color coding (green=home, red=away, yellow=Draw)
- `prop_type` stored as "Run Line" (space) in the database but code checked for "run_line" (underscore) — format mismatch caused team-name display logic to miss all spread picks
- Supabase upsert with partial fields on a new pick ID triggers INSERT, hitting NOT NULL on `player_name` — game-total markets legitimately have no player, so the tracker was inserting empty strings
- Totals markets retain Over/Under labels (where they make semantic sense); only team-selection markets (moneyline, spread) get team name translation

## Details

### The Display Gap

The value betting scanner's dashboard was designed for player props: each pick naturally has a `player_name` (e.g., "LeBron James") and a `side` (Over/Under) that together communicate the bet clearly — "LeBron James Points Over 25.5". When game-line markets were added via the Pinnacle prediction-market pipeline (see [[concepts/pinnacle-prediction-market-pipeline]]) and the SSE display/tracking separation (see [[concepts/sse-display-tracking-market-separation]]), picks appeared as "Over" or "Under" with no indication of which team was involved.

For moneyline picks, "Over" means the home team wins and "Under" means the away team wins — but this encoding is an internal convention, not something a bettor should need to decode. For spread (Run Line) picks, the confusion is worse: a negative line value (-1.5) paired with "Under" is doubly confusing because "Under -1.5" could be misread as a totals bet. The fix translates these internal side labels into team names at display time, using the `fixture_name` field as the source of team identity.

### Three Implementation Bugs

**1. Side label translation.** The core fix maps Over→home team name and Under→away team name for moneyline and spread markets. Home and away are extracted by splitting `fixture_name` on " vs " (the canonical format — see [[concepts/fixture-name-canonicalization]]). A color-coding scheme provides additional visual clarity: green for home (Over), red for away (Under), yellow for Draw. Totals markets (e.g., "Total Runs Over 8.5") retain the Over/Under labels because they are semantically correct for totals.

**2. prop_type format mismatch.** The tracker stores prop types with spaces and title case — "Run Line", "Moneyline" — matching OpticOdds' format. The dashboard's team-name display logic checked for snake_case variants — "run_line", "moneyline". This mismatch caused the display logic to silently skip all spread picks, falling back to the default Over/Under labels. The fix normalizes the comparison. This is an instance of a recurring pattern in the scanner: data format inconsistencies between the tracker (which stores OpticOdds' format) and the dashboard (which uses its own conventions).

**3. Empty player_name on game-total markets.** Game-level totals (e.g., "Total Runs Over 8.5") have no associated player — the `player_name` field is empty. When the tracker attempted to upsert a new pick with an empty `player_name`, Supabase's NOT NULL constraint rejected the INSERT. The fix adds a guard in the tracker to substitute the `fixture_name` when `player_name` is empty for game-level markets. On the dashboard side, the display falls back to `fixture_name` when `player_name` is blank.

### Pattern: Player-Prop Assumptions in Game-Line Contexts

The three bugs share a root cause: the scanner's data model and display layer were designed around player props, where every pick has a player, Over/Under is semantically meaningful, and prop types follow a consistent format. Game-line markets break all three assumptions: no player, Over/Under needs translation to team names, and prop types may use different formatting. As game-line coverage expands (NHL game lines planned for the Pinnacle pipeline — see [[concepts/pinnacle-prediction-market-pipeline]]), any code path that assumes player-prop structure will need similar adaptation.

## Related Concepts

- [[concepts/fixture-name-canonicalization]] - The "vs" format fixture name that provides the team name extraction source
- [[concepts/pinnacle-prediction-market-pipeline]] - The pipeline whose game-line expansion exposed these display gaps
- [[concepts/sse-display-tracking-market-separation]] - The display/tracking split that brought game-line markets to the dashboard
- [[concepts/dashboard-client-server-ev-divergence]] - A parallel dashboard rendering issue (EV computation mismatch vs display label mismatch)

## Sources

- [[daily/lcash/2026-04-16.md]] - Moneyline/spread picks showing "Over"/"Under" instead of team names; team name extraction from fixture_name; prop_type format mismatch ("Run Line" vs "run_line"); empty player_name hitting NOT NULL on game-total markets; color coding green=home/red=away/yellow=Draw; totals retain Over/Under (Session 23:44)
