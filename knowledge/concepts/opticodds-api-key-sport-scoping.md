---
title: "OpticOdds API Key Sport-Specific Scoping"
aliases: [api-key-scoping, nba-only-key, opticodds-sport-access, sse-sports-filter]
tags: [value-betting, opticodds, infrastructure, configuration, api]
sources:
  - "daily/lcash/2026-04-24.md"
created: 2026-04-24
updated: 2026-04-24
---

# OpticOdds API Key Sport-Specific Scoping

On 2026-04-24, lcash discovered that the current OpticOdds API key only has access to **NBA basketball** — not multi-sport. REST fixtures return empty for all non-basketball sports, SSE connections fail with 400 "not enabled for your API key" for all 22 non-basketball streams, and even other basketball leagues (NBL, EuroLeague, CBA) are inaccessible. This means the entire multi-sport SSE infrastructure (22 streams, 432 auto-discovered leagues) was spinning up against a key that could only access NBA — massive wasted compute.

## Key Points

- OpticOdds API key access is **sport-specific** — current key covers NBA basketball REST and basketball SSE only; everything else returns empty or 400
- **MLB has zero sharp data**: all 275 MLB markets come exclusively from the Bet365 game scraper on mini PC (port 8803) — no EV calculation possible without sharp book reference
- **NRL and AFL servers are dead** — not running on the mini PC at all
- SSE auto-discovery creates theories for 432 leagues without checking API key permissions first — wastes 5+ min on boot for inaccessible sports
- `SSE_SPORTS` env var added to `server/main.py` to filter which sports get SSE streams — runtime control without code redeploy
- Fix for MLB: wired `fetch_mlb_stats()` from podcast pipeline as MLB resolver fallback since OpticOdds can't provide baseball fixture results

## Details

### Discovery

The discovery came during investigation of the VPS SSE startup appearing stuck. The SSE startup was actually running but spending 5+ minutes on sequential theory creation for 432 auto-discovered leagues — all of which the key can't access. When the SSE streams finally launched, all 22 non-basketball streams failed with 400 errors.

A systematic audit tested the API key against every sport: basketball returned data (NBA only), while baseball, soccer, tennis, hockey, football, esports, and all other sports returned either empty responses or explicit 400 "not enabled" errors. Even other basketball leagues (NBL Australia, EuroLeague, China CBA) that were part of the Pinnacle and Crypto Edge pipeline expansion returned nothing.

### Impact Assessment

The current data coverage reality:

| Sport | Status | Data Source | EV Possible? |
|-------|--------|-------------|-------------|
| NBA | Working | OpticOdds (sharps + softs) + Bet365 + TAB | Yes |
| MLB | Bet365-only | Bet365 game scraper (port 8803) | No (no sharps) |
| NRL | Dead | Mini PC server not running | No |
| AFL | Dead | Mini PC server not running | No |
| Soccer/Tennis/Hockey | No access | API key doesn't cover | No |

This fundamentally changes the operational picture: the scanner is effectively NBA-only despite infrastructure and code supporting multi-sport operation. The Pinnacle prediction-market pipeline, Crypto Edge strategy, and SSE streaming expansion are all NBA-only until the API key is upgraded.

### MLB Resolution Fallback

MLB Crypto Edge picks were being tracked (from Bet365 soft book data) but couldn't be resolved because OpticOdds returns zero baseball fixture results. The existing `fetch_mlb_stats()` function from the podcast pipeline (`ev_scanner/podcast.py`) was wired as an MLB resolver fallback, using the MLB Stats API for box score data instead of OpticOdds.

A sport parameter was also added to the resolve endpoint (previously hardcoded to a single `SPORT_KEY`), enabling per-sport resolution.

### SSE_SPORTS Environment Variable

To stop wasting compute on inaccessible sports, an `SSE_SPORTS` environment variable was added to `server/main.py`. This controls which sports get SSE streams activated. It was deliberately set to all sports (not just basketball) so that when the API key is upgraded, streams auto-activate without a code change — failed connections silently retry with no harm. Auto-discovery still runs for all leagues, but only filtered sports get streams started.

### SSE Startup and Auto-Resolver Conflict

When both the SSE startup and auto-resolver run simultaneously after a VPS restart, they can flood the OpticOdds API, causing SSE streams to get stuck. The auto-resolver was given a 5-minute startup delay to stagger the load. VPS restarts also clear all market data (rebuilds from push quickly) but SSE streams take 5-10 minutes to come online.

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - This discovery adds a fourth dependency risk dimension: not just availability, bias, and completeness, but also API key scope limiting sport access
- [[concepts/sse-startup-theory-creation-hang]] - The SSE startup hang is exacerbated by auto-discovery creating theories for 432 leagues that the key can't access
- [[concepts/opticodds-sse-streaming-scaling]] - The SSE streaming architecture designed for 491+ leagues is NBA-only until key upgrade
- [[concepts/pinnacle-prediction-market-pipeline]] - Pinnacle pipeline's multi-sport expansion is blocked by API key scope
- [[concepts/crypto-edge-non-pinnacle-strategy]] - Crypto Edge's MLB goldmine (1,354 markets) cannot be evaluated without sharp data
- [[concepts/podcast-pick-extraction-pipeline]] - `fetch_mlb_stats()` from the podcast pipeline reused as MLB resolver fallback

## Sources

- [[daily/lcash/2026-04-24.md]] - API key audit: only NBA basketball returns data; all other sports empty/400; MLB 275 markets from Bet365 only, zero sharps; NRL/AFL servers dead; 22 non-basketball SSE streams all fail; 432 leagues auto-discovered but inaccessible (Sessions 14:40, 15:47, 16:35). `SSE_SPORTS` env var added for runtime filtering; auto-discovery still runs for all leagues (Session 15:47). MLB Crypto Edge resolver fallback via `fetch_mlb_stats()` from podcast pipeline; sport parameter added to resolve endpoint; Supabase URL length limit with 658 pick IDs; SSE + auto-resolver simultaneous flood issue with 5-min delay (Session 16:37)
