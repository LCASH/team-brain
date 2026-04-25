---
title: "OpticOdds API Key Sport-Specific Scoping"
aliases: [api-key-scoping, nba-only-key, opticodds-sport-access, sse-sports-filter, baseball-unlocked]
tags: [value-betting, opticodds, infrastructure, configuration, api]
sources:
  - "daily/lcash/2026-04-24.md"
  - "daily/lcash/2026-04-25.md"
created: 2026-04-24
updated: 2026-04-25
---

# OpticOdds API Key Sport-Specific Scoping

On 2026-04-24, lcash discovered that the current OpticOdds API key only had access to **NBA basketball** — not multi-sport. On 2026-04-25, after switching to a new API key, **baseball access was unlocked** alongside expanded basketball coverage (111 leagues, not just NBA). The new key covers basketball (111 leagues including Australia WNBL1, Japan B1, France LNB Pro B) and baseball (15 leagues including MLB, KBO, NPB, College Baseball, MiLB AAA, CPBL). Soccer, tennis, hockey, football, and esports remain inaccessible. OpticOdds baseball `market_stats` uses the same format as basketball — all 17 prop mappings confirmed working (hits, bases, strikeouts, HRs, earned runs, etc.).

## Key Points

- OpticOdds API key access is **sport-specific** and **can change without notice** — sports that were blocked can become enabled (baseball went from blocked to fully working on a new key)
- **New key (2026-04-25)**: basketball (111 leagues) + baseball (15 leagues) — a major upgrade from NBA-only; soccer/tennis/hockey/esports still inaccessible
- OpticOdds baseball `market_stats` uses the same format as basketball — resolver code works as-is for all 17 MLB prop types (hits, bases, strikeouts, HRs, earned runs, etc.)
- **NRL and AFL servers are still dead** — not running on the mini PC at all
- SSE auto-discovery creates theories for 432 leagues without checking API key permissions first — wastes 5+ min on boot for inaccessible sports
- `SSE_SPORTS` env var added to `server/main.py` to filter which sports get SSE streams — runtime control without code redeploy
- The 22 SSE streams that appeared "alive" were actually in retry loops getting rejected — tasks staying alive ≠ receiving data

## Details

### Discovery

The discovery came during investigation of the VPS SSE startup appearing stuck. The SSE startup was actually running but spending 5+ minutes on sequential theory creation for 432 auto-discovered leagues — all of which the key can't access. When the SSE streams finally launched, all 22 non-basketball streams failed with 400 errors.

A systematic audit tested the API key against every sport: basketball returned data (NBA only), while baseball, soccer, tennis, hockey, football, esports, and all other sports returned either empty responses or explicit 400 "not enabled" errors. Even other basketball leagues (NBL Australia, EuroLeague, China CBA) that were part of the Pinnacle and Crypto Edge pipeline expansion returned nothing.

### Impact Assessment (Updated 2026-04-25)

The data coverage after the new API key:

| Sport | Status | Data Source | EV Possible? |
|-------|--------|-------------|-------------|
| NBA | Working | OpticOdds (sharps + softs) + Bet365 + TAB | Yes |
| Baseball (MLB + 14 leagues) | **Newly Working** | OpticOdds (sharps + softs) + Bet365 game scraper | **Yes** |
| Basketball (111 leagues) | **Newly Working** | OpticOdds (sharps + softs) | **Yes** |
| NRL | Dead | Mini PC server not running | No |
| AFL | Dead | Mini PC server not running | No |
| Soccer/Tennis/Hockey | No access | API key doesn't cover | No |

The operational picture improved significantly on 2026-04-25: the scanner expanded from NBA-only to basketball (111 leagues) + baseball (15 leagues). The Pinnacle prediction-market pipeline and Crypto Edge strategy can now evaluate MLB markets with sharp data — previously MLB had 275 markets from Bet365 with zero sharps. However, NRL/AFL remain dead and soccer/tennis/hockey are still inaccessible.

### Key Discovery: Access Changes Without Notice

OpticOdds API access can change without notice. The initial test of the new key appeared identical to the old one (basketball + football only). Only thorough per-sport testing — which the user insisted on — revealed that baseball had been unlocked. The 22 SSE streams that appeared "alive" during prior diagnostics were actually in continuous retry loops getting 400-rejected — tasks staying alive does not mean they are receiving data.

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
- [[daily/lcash/2026-04-25.md]] - New API key tested: initially appeared identical to old key, but thorough per-sport testing revealed baseball unlocked; 111 basketball leagues with active fixtures (WNBL1, Japan B1, France LNB Pro B, etc.); 15 baseball leagues (MLB, KBO, NPB, College Baseball, MiLB AAA, CPBL); OpticOdds baseball market_stats uses same format as basketball — all 17 prop mappings confirmed; 22 "alive" SSE streams were retry loops getting rejected; reconciliation disabled in relay mode for pick flashing fix; sport param added to /api/v1/resolve; auto-resolver found 4 stale MLB dates (Apr 19-22); chunk size 50 for resolver (Session 07:28)
