---
title: "AFLTables Player Stats Fallback Scraper"
aliases: [afltables-fallback, afl-resolver-fallback, afltables-scraper, afl-stats-scraper]
tags: [value-betting, resolver, afl, scraping, fallback]
sources:
  - "daily/lcash/2026-04-19.md"
created: 2026-04-19
updated: 2026-04-19
---

# AFLTables Player Stats Fallback Scraper

OpticOdds returns 0 player results for AFL (and NRL), leaving AFL player prop picks (Disposals, Goals) unresolvable through the standard resolution path. A fallback scraper was built using AFLTables.com as the data source — clean HTML tables with full player stats per game, no authentication needed, following the same pattern as the existing NRL.com fallback for tries.

## Key Points

- OpticOdds returns only fixture scores for AFL, NOT player stats — `player_disposals` and `player_goals` picks had no resolution path before this fallback
- AFLTables provides clean HTML with ~86 players per game; column mapping: `cells[3]` = Disposals (DI), `cells[4]` = Goals (GL)
- Critical parsing trap: AFLTables pages have TWO table sections — game stats (~23 cells per row) and player details (~5 cells with career data). Parsing both overwrites correct stats with zeros
- Fix: filter rows by `len(cells) >= 20` to select only game stats rows
- `\xa0` (non-breaking space) in HTML table cells converts to empty string, causing `int()` to return 0 — needs explicit handling in the value parser
- Player name format on AFLTables is `"Surname, First"` — needs mapping to match tracked pick names
- Trail coverage verified at 100% after deployment: 82/82 picks, 1,055 trail entries, 0 missing

## Details

### Data Source Evaluation

Three AFL data sources were evaluated before selecting AFLTables:

1. **Squiggle API** — provides game scores only, no individual player stats. Useful for moneyline resolution but not player props.
2. **Footywire** — has player stats but uses JavaScript-loaded content that's harder to scrape reliably. Would require browser automation (Playwright/Selenium), adding complexity and fragility.
3. **AFLTables** — provides full player stats in clean server-rendered HTML tables. No JavaScript loading, no authentication, stable URL patterns. The clear winner for reliability and simplicity.

AFLTables was selected because it follows the same pattern as the existing NRL.com fallback: simple HTTP GET → parse HTML → extract stats. This keeps the fallback scraper codebase consistent and avoids introducing browser automation dependencies in the resolver.

### The Two-Table Parsing Trap

AFLTables game pages contain two visually distinct table sections for each team. The first section contains actual game statistics with ~23 columns per row: kicks, marks, handballs, disposals, goals, behinds, hit-outs, tackles, rebounds, inside-50s, clearances, clangers, frees for/against, brownlow votes, contested/uncontested possessions, centre clearances, and more.

The second section contains player biographical/career details with only ~5 cells per row: age information (e.g., "30y 206d"), career games played, and other reference data. Both sections appear in the same HTML `<table>` element, differentiated only by the number of cells per row.

When the parser iterated all rows indiscriminately, the second section's rows would overwrite the stats dictionary with values from the wrong columns. Specifically, `cells[3]` in a 5-cell row contains a string like `"←"` (an arrow indicating data continues from above), which fails to parse as an integer and silently returns 0 via the value parser. This overwrote the correct Disposals count with 0 for any player whose stats row appeared before a details row.

The fix filters rows by cell count: `len(cells) >= 20` selects only game stats rows, reliably excluding the biographical section.

### Non-Breaking Space Handling

AFLTables HTML uses `&nbsp;` (rendered as `\xa0` in Python) in some table cells, particularly for empty or placeholder values. Python's `str.strip()` does not strip `\xa0` by default, and attempting `int("")` (after naive stripping) raises a `ValueError`. The value parser function `_val()` explicitly handles this: strip both regular whitespace and `\xa0`, convert empty results to 0, then parse as integer. Without this handling, certain games would silently produce 0 stats for all players in affected columns.

### Column Mapping

The AFLTables game stats table follows a fixed column order. The two columns relevant to value betting resolution are:

| Index | Code | Stat |
|-------|------|------|
| 3 | DI | Disposals |
| 4 | GL | Goals |

Other columns in the same table include: KI (Kicks, index 0), MK (Marks, 1), HB (Handballs, 2), BH (Behinds, 5), HO (Hit-Outs, 6), TK (Tackles, 7), RB (Rebounds, 8), IF (Inside 50s, 9), CL (Clearances, 10), CG (Clangers, 11), FF (Frees For, 12), FA (Frees Against, 13), BR (Brownlow Votes, 14), CP (Contested Possessions, 15), UP (Uncontested Possessions, 16), CM (Centre Clearances, 17), MI (Marks Inside 50, 18). These additional columns are available for future prop type expansion.

### Resolver Integration

The fallback follows the same pattern as `_fetch_nrl_try_stats` for NRL:

1. Resolver calls OpticOdds `/fixtures/results` for AFL — gets fixture scores but 0 player stats
2. When player stats are needed for a prop like `player_disposals`, the resolver invokes the AFLTables fallback
3. The fallback fetches the game page, parses the HTML table, extracts the relevant stat for the specific player
4. Returns the stat value to the resolver, which grades the pick (Over/Under vs. actual)

Both fallbacks are now in place: NRL → NRL.com (tries), AFL → AFLTables (disposals + goals). The shared architectural pattern makes it straightforward to add fallbacks for other sports if OpticOdds lacks player-level data.

## Related Concepts

- [[concepts/resolver-sequential-sport-bottleneck]] - A slow fallback scraper amplifies the sequential resolver bottleneck; if AFL had many stale dates, this fallback would cause the same blocking pattern as NRL
- [[concepts/opticodds-critical-dependency]] - OpticOdds returns 0 player results for AFL and NRL, forcing sport-specific fallback scrapers
- [[concepts/afl-circular-devig-trap]] - The AFL devig quality problems (circular sharps, one-sided consensus) are separate from the resolver — even correctly resolved AFL picks may have been triggered by phantom EV
- [[connections/resolver-fallback-data-source-chain]] - The broader pattern of OpticOdds player stat gaps driving sport-specific fallback architectures

## Sources

- [[daily/lcash/2026-04-19.md]] - OpticOdds confirmed 0 player results for AFL; AFLTables selected over Squiggle (scores only) and Footywire (JS-loaded); column mapping DI=3, GL=4; two-table parsing trap with 23-cell vs 5-cell rows; `\xa0` handling; player name format "Surname, First"; trail coverage 82/82 verified; follows NRL.com fallback pattern (Sessions 11:42, 12:29, 12:59)
