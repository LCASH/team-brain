---
title: "TAB.com.au Scraper and Threshold Market Integration"
aliases: [tab-scraper, tab-908, tab-threshold-markets, tab-competition-endpoint, tab-name-resolution]
tags: [value-betting, scraping, soft-book, tab, architecture, interpolation]
sources:
  - "daily/lcash/2026-04-24.md"
created: 2026-04-24
updated: 2026-04-24
---

# TAB.com.au Scraper and Threshold Market Integration

TAB.com.au (book_id 908) was integrated as a new soft book in the value betting scanner on 2026-04-24. TAB's public REST API delivers all NBA match data — including player prop markets — in a single 1.6MB competition-level request, requiring no authentication beyond browser-like headers and Akamai cookies (handled by `curl_cffi`). TAB offers two prop formats: standard Over/Under lines and **threshold markets** (e.g., "20+ Points", "10+ Rebounds") that are posted hours before tipoff, providing early coverage unavailable from other soft books. The threshold markets required Poisson interpolation for count props (logit produced 300%+ phantom EVs) and a self-contained name resolution system using TAB's own data.

## Key Points

- Single competition endpoint (`/sports/Basketball/competitions/NBA?jurisdiction=NSW`) returns ALL matches with ALL markets inline — 1.6MB, no pagination, no individual match fetches needed
- TAB posts **threshold markets** (20+ Points, 10+ Rebounds) 10+ hours before tipoff, but O/U props only ~2-3 hours before game time — threshold markets provide an early coverage window
- Player name abbreviation problem: TAB O/U props use abbreviated names ("A Edwards", "Jad McDanls", "D DiVincenz") — resolved using TAB's own threshold market full names from the same API response (15/15 exact matches)
- Threshold lines (e.g., Over 19.5) are coarse and don't match sharp book lines (e.g., 26.5) — `max_line_gap=4` was added to all 7 NBA theories to enable interpolation
- Logit interpolation produced 300%+ phantom EVs on discrete count props — switched to `interpolate_for_prop()` which routes count props through Poisson and Points/combos through calibrated logit
- `curl_cffi` required because Akamai bot protection blocks plain `httpx`; runs in a thread via `direct_scraper_worker` since `curl_cffi` is synchronous
- Initial results: 206 TAB odds flowing on mini PC, 32 picks at +8.3% avg EV after Poisson fix; 11 TAB picks tracked on VPS with EV ranging +2.6% to +68.7%

## Details

### API Architecture

TAB's REST API follows a clean hierarchy: `/sports/{Sport}/competitions/{Comp}/matches/{Match}`. However, the competition-level endpoint is sufficient for all data needs — it returns match data inline for all NBA games without requiring individual match fetches. The response is approximately 1.6MB for a full NBA slate and includes two distinct prop market formats:

**Over/Under markets** use `betOptionSpectrumId` values (837/838/839/1789/1791/1787/1788) with 2 propositions per player per market. These are the standard Over/Under props familiar from other soft books. All 103 O/U pairs in testing came back complete (both over and under for every line).

**Threshold markets** use different spectrum IDs (3515, 3520, etc.) and list all qualifying players in a single market with a single proposition per player (e.g., "Anthony Edwards 20+ Points @ 1.44"). These are converted to the scanner's standard format by mapping "20+ Points" → Over 19.5, enabling EV evaluation against sharp book lines.

TAB only posts player props close to tipoff — in testing, only 1 of 8 NBA matches had full props (the nearest game had 326 markets vs 47-86 for games further out). Threshold markets appear earlier (10+ hours before) while O/U markets appear later (~2-3 hours before).

### Name Resolution

TAB abbreviates player names inconsistently in O/U props: "A Edwards" for Anthony Edwards, "Jad McDanls" for Jaden McDaniels, "D DiVincenz" for Donte DiVincenzo, "T Hardawy" for Tim Hardaway Jr. The scanner's existing fuzzy matcher cannot handle first-initial-only format or the degree of truncation.

The solution is self-contained: TAB's own threshold markets provide full player names (e.g., "Anthony Edwards (MIN)") in the same API response. The scraper builds an abbreviated→full name mapping from threshold market data, then applies it to O/U abbreviated names during parsing. This avoids external lookups and achieved 15/15 exact matches in testing.

### Interpolation for Threshold Lines

Threshold markets inherently produce coarse lines that differ from sharp book consensus lines. TAB's "20+ Points" (Over 19.5) compared against Pinnacle's line at 26.5 creates a 7-point gap. Without `max_line_gap` configured, the tracker only evaluates exact line matches — which never occur between threshold and standard lines.

Adding `max_line_gap=4` to all 7 NBA theories enabled interpolation across the gap. However, the initial implementation produced 300%+ phantom EVs because logit interpolation breaks on discrete count props with large line gaps (the same failure mode documented in [[concepts/alt-line-mismatch-poisoned-picks]]). Switching to `interpolate_for_prop()` — which routes Threes/Blocks/Steals/Rebounds/Assists through Poisson and Points/combos through calibrated logit — produced realistic results: 32 picks at +8.3% average EV.

Steals, Blocks, and Threes are the highest-value threshold props because the line gaps from sharp books are small (typically 1 point) and Poisson handles cleanly. Points and combo props have larger gaps and are more prone to interpolation noise.

### Deployment Pipeline

TAB was integrated across multiple pipeline components:

1. **Scraper**: `tab_scraper.py` polls every 60s via `direct_scraper_worker.py` (thread-based, same pattern as other scrapers)
2. **Mini PC**: `curl_cffi` installed, scraper deployed, 206 markets confirmed flowing
3. **VPS models**: 908 added to `SOFT_BOOK_IDS` in `models.py` so the tracker evaluates TAB as a soft book
4. **Dashboard**: 908 added to `SOFT_IDS` array in `dashboard.html` (separate from `models.py` — both need updating for a new book)
5. **Theories**: `max_line_gap=4` added to all 7 NBA theories; `max_hours_before_start=24` set to capture early threshold props

A key deployment lesson: the dashboard's `SOFT_IDS` filter array is separate from the backend's `SOFT_BOOK_IDS`. Having `BOOK_NAMES` with an entry for 908 does not make the book appear in the dropdown — the `SOFT_IDS` array gates visibility.

### Pick Creation vs Trail Timing

TAB threshold markets exposed a timing gap: these props are posted 10+ hours before tipoff, but the default `max_hours_before_start=3` prevented the tracker from evaluating them. The fix separated pick creation timing (24h before game) from trail recording (3h before game). See [[concepts/pick-trail-time-window-separation]] for the full architectural change.

### Debugging "Zero Picks" for a New Soft Book

The integration exposed a systematic debugging order for "0 picks from new soft book":

1. **Data presence in state** — are TAB markets visible in the VPS market snapshot?
2. **Theory `soft_books` config** — does at least one theory include 908 in its soft books?
3. **Time window filters** — is `max_hours_before_start` allowing evaluation of markets this far from game time?
4. **`max_line_gap`** — is interpolation enabled for the line differences between this book and sharps?

The time filter (step 3) was the non-obvious culprit — TAB data was present, theories included 908, but the 3h window silently discarded everything.

## Related Concepts

- [[concepts/alt-line-mismatch-poisoned-picks]] - Poisson interpolation for count props was developed for the alt-line mismatch bug and reused here for TAB threshold markets
- [[concepts/pick-trail-time-window-separation]] - The architectural change to separate pick creation (24h) from trail recording (3h) driven by TAB's early threshold props
- [[concepts/value-betting-theory-system]] - TAB required theory changes (`max_line_gap=4`, `max_hours_before_start=24`) via Supabase — no code changes needed
- [[concepts/trail-capture-soft-ids-gap]] - Same pattern of hardcoded book ID sets needing manual updates when adding a new book
- [[concepts/opticodds-critical-dependency]] - TAB is an independent soft book data source — its odds come from the TAB scraper, not OpticOdds
- [[concepts/bet365-headless-detection]] - TAB requires `curl_cffi` for Akamai, similar to bet365 requiring headed Chrome for Cloudflare — different anti-bot, same constraint pattern

## Sources

- [[daily/lcash/2026-04-24.md]] - TAB API hierarchy mapped: competition endpoint returns all matches with all markets; two prop formats: O/U (betOptionSpectrumId 837/838) and threshold (3515/3520); 1.6MB response, 7 prop stat types; name abbreviation ("A Edwards") resolved via threshold market full names (15/15 match); props only available close to tipoff (Session 10:56). TAB assigned book_id 908, `curl_cffi` needed for Akamai; deployed to mini PC with 206 markets flowing; 12 local +EV found (Session 11:29). Dashboard `SOFT_IDS` array separate from `models.py` `SOFT_BOOK_IDS`; TAB returns 0 when games started/finished (Session 12:12). Threshold markets extracted as fallback; logit produced 300%+ phantom EVs → Poisson fix; 32 picks at +8.3% avg EV; Steals/Blocks/Threes highest-value threshold props (Session 12:49). `max_line_gap=4` added to all 7 theories; theory cache 5-min TTL; TAB may be too sharp for frequent +EV (Session 13:22). 11 TAB picks tracked with +2.6% to +68.7% EV; `max_hours_before_start` was silently filtering threshold markets (Session 14:09)
