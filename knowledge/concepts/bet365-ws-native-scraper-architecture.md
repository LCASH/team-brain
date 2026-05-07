---
title: "bet365 WebSocket-Native Scraper Architecture"
aliases: [ws-native-scraper, ws-nba-orchestrator, ws-mlb-orchestrator, ws-scraper-replacement, wizard-ws-hybrid]
tags: [value-betting, bet365, websocket, architecture, scraping, performance]
sources:
  - "daily/lcash/2026-05-06.md"
  - "daily/lcash/2026-05-07.md"
created: 2026-05-06
updated: 2026-05-07
---

# bet365 WebSocket-Native Scraper Architecture

On 2026-05-06, lcash built and deployed WebSocket-native scrapers (`WSNBAOrchestrator`, `WSMLBOrchestrator`) that replace the HTTP polling CDP scrapers for both NBA and MLB. The new architecture uses the BB wizard endpoint (I99) for NBA initial prop snapshots and 26 MG hash-nav URLs for MLB, combined with WS frame listeners for real-time delta updates. NBA worst-case latency drops from ~23s to ~8s, MLB from ~38s to ~8s, with both converging to the push+poll floor. The system was deployed live with 5,001 NBA markets and 5,249 MLB markets streaming through a single Playwright page per sport.

## Key Points

- **NBA**: Single I99 wizard fetch returns all player props (~1049 PAs/game); WS listener receives delta updates in `L{mg}-{pa}_30_0\x01U|OD=;HA=;` format
- **MLB**: 26 MG hash-nav URLs per game (I0 + 19 batter + 7 pitcher); wizard format uses `S1=PlayerName`, `S2=20+ Points`, `HA=19.5` (not `NA=` like other endpoints)
- **Latency improvement**: NBA ~23s→~8s, MLB ~38s→~8s — eliminates the sequential CDP poll cycle bottleneck
- **Single page per sport**: One Playwright page manages discovery + WS listening; game pages managed via raw CDP tab creation
- **Same `BaseOrchestrator` interface**: `all_odds`, `add_game()`, `remove_game()`, `start()`, `stop()` — startup.py change is 3 lines
- **Deployed live**: 13,239 total markets (5,001 NBA + 5,249 MLB + OpticOdds), 17 picks in ticker at deployment confirmation
- **Case sensitivity bug found and fixed**: `SHARP_BOOKS` used titlecase ("Pinnacle") while OpticOdds delivers lowercase ("pinnacle") — `_find_sharp_books()` returned empty for all markets

## Details

### NBA Wizard Format (I99)

The NBA scraper uses bet365's BB wizard endpoint (tab I99), which returns all player prop categories in a single HTTP response. The wizard format differs from the standard coupon format:

| Field | Wizard (I99) | Standard Coupon |
|-------|-------------|-----------------|
| Player name | `S1=Austin Reaves` | `NA=Austin Reaves` |
| Prop description | `S2=20+ Points` | Embedded in `MA` structure |
| Line value | `HA=19.5` | `HA=19.5` |
| Odds | `OD=1/6` | `OD=1/6` |
| PA identifier | `IT=BB{fi}-{id}` | `ID={pa_id}` |

Prop type extraction: `re.sub(r'^\d+\+\s*', '', s2)` converts "20+ Points" to "Points". Side is always "Over" in wizard format — only one side per PA record.

The wizard requires an authenticated session (login needed). This contrasts with MLB's `matchbettingcontentapi/partial` which serves anonymous users — explaining why MLB works without login but NBA doesn't.

### MLB Multi-URL Cycle

MLB uses 26 Market Group navigations per game because bet365 doesn't have a single-fetch wizard equivalent for MLB:

- 1 I0 tab (Bet Builder / main view)
- 19 batter prop hash-nav URLs
- 7 pitcher prop hash-nav URLs

Each navigation triggers an HTTP response captured via CDP response interception. The full cycle takes ~37s per game (not the 4-minute estimate from earlier analysis). With parallel refreshes across all games simultaneously, the effective cycle time drops to ~3-4 minutes for the entire slate instead of the sequential ~24 minutes.

### WS Delta Updates

After the initial HTTP snapshot, both scrapers listen for WebSocket delta updates. The WS frame format is:

```
\x15L{mg_id}-{pa_id}_30_0\x01U|OD=20/21;HA=+29.5;|
```

Key fields in deltas:
- `OD=` — fractional odds (e.g., `20/21`)
- `HA=` — O/U line value (e.g., `+29.5`)
- `SU=1` — market suspended; `SU=0` — active

The `\x01` byte between `_30_0` and `U` was a critical parsing bug — the old regex matched 0 frames until corrected. With the fix, 703+ updates flow per 120-second window.

### Discovery Architecture

Game discovery merges two endpoints for completeness:
- `getsplashpods` — reflects what's currently live/featured
- `gethomepageadditionalpods` — contains all upcoming events

Using only `getsplashpods` missed the 76ers/Knicks game (410 PAs) because the Lakers/Thunder game was live and dominated the splash. Merging both endpoints ensures upcoming games aren't hidden when something else is on.

### Deployment Debugging

Several issues were resolved during production deployment:

1. **`startup.py` passed orchestrator objects instead of `orchestrator.page`** to `discovery.py` — discovery calls `.context`, `.url` which are Playwright Page attributes, not orchestrator attributes
2. **`Target.activateTarget` on wrong Chrome port** — NBA Chrome on 9222, MLB on 9223; cross-port calls get "Target not found"
3. **Discovery tabs created with pre-loaded URLs** via `/json/new?https://...` then `Page.navigate` called again — caused 15s timeouts; fix: create tabs as `about:blank`, then navigate
4. **OpticOdds event loop blocking** — streaming 24+ events/second, each holding asyncio lock; fixed with 2-second flush throttle reducing lock acquisitions 97% (239→8 per 10s)
5. **Module-level env var reads** — `_SB_URL`/`_SB_KEY` read at import time before `load_dotenv()` — always empty; moved to function-scope reads

### Performance Characteristics

| Metric | Old CDP Polling | New WS-Native |
|--------|----------------|---------------|
| NBA worst-case latency | ~23s (15s poll + 8s push) | ~8s (WS delta + push) |
| MLB worst-case latency | ~38s (24min cycle / games) | ~8s (parallel refresh + WS) |
| Markets per request | Varies by game | All games simultaneously via WS |
| Chrome tabs | 1 per game (persistent) | 1 per game (raw CDP) |
| Playwright involvement | Full lifecycle | Discovery only |

## Related Concepts

- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture that the WS scrapers are deployed into; WS replaces CDP polling in the modular scraper layer
- [[concepts/mlb-parallel-scraper-workers]] - The evolution from parallel workers → persistent pages → raw CDP → WS-native; this is the latest architectural step
- [[concepts/bet365-mlb-hash-nav-mg-fetching]] - The 26 MG hash-nav URLs that MLB uses for its HTTP snapshot phase
- [[concepts/bet365-nba-bb-wizard-v3-rewrite]] - The NBA BB wizard v3 that the WS-native scraper extends with WS delta listening
- [[concepts/playwright-node-pipe-crash-vector]] - Playwright pipe crashes that motivated the raw CDP migration; WS-native continues using raw CDP for game pages
- [[concepts/bet365-xcft-token-hmac-forgery]] - The token forgery that could eventually enable fully standalone WS clients without browser dependency
- [[concepts/opticodds-sse-reconnect-state-loss]] - SSE staleness mismatch discovered during V3 deployment; REST reseed added alongside WS scraper
- [[concepts/bet365-ws-pre-game-prop-streaming-limitation]] - WS `OV_POPULAR_30_0` is a global firehose, not per-game feeds; pre-game props require HTTP polling supplement
- [[concepts/bet365-cdpsession-pipe-contention]] - CDPSession on orchestrator page blocks Playwright operations; discovery must use dedicated pages
- [[concepts/bet365-ws-subscription-injection-viability]] - WS injection probe confirmed interceptor-on-SPA-WS works; disjoint PA_ID spaces explain why per-G-ID navigation captures live trading IDs while I99 wizard captures static catalog IDs

## Sources

- [[daily/lcash/2026-05-06.md]] - WSNBAOrchestrator and WSMLBOrchestrator built and deployed; NBA wizard I99 format (S1/S2/HA); MLB 26 MG URLs per game; WS frame format with \x01 byte fix (703+ updates/120s); discovery merges getsplashpods + gethomepageadditionalpods; deployment bugs: orchestrator.page vs orchestrator, Target.activateTarget wrong port, about:blank tab creation, OpticOdds event loop blocking (2s flush throttle), module-level env reads (Sessions 17:39, 18:38, 19:20, 02:59). Case sensitivity bug: SHARP_BOOKS titlecase vs OpticOdds lowercase — fixed with .lower() normalization; 13,239 markets live (5,001 NBA + 5,249 MLB) (Session 01:07). MLB discovery navigation: window.location.href required for SPA hash URLs, not CDP Page.navigate; parallel refresh reduced 24min→3-4min (Session 11:20)
- [[daily/lcash/2026-05-07.md]] - **WS pre-game coverage gap confirmed**: `OV_POPULAR_30_0` is a cross-sport global firehose, NOT per-game feeds; 0 PA_ID overlap across 275+ frames on NBA/MLB/NRL; pre-game lines are static (zero WS deltas hours before tipoff); May 6 "703 updates/120s" was in-play trading, not generalizable; hybrid architecture decided: add `_refresh_loop` (10-15s HTTP wizard refresh) as primary, WS as passive supplement near tipoff; sequential `monitor.goto()` cancels previous game's subscriptions; CDPSession on orchestrator page blocks Playwright discovery — fix: dedicated fresh page for discovery (Sessions 09:18, 18:40, 19:20). **Disjoint PA_ID spaces**: HTTP wizard returns static catalog IDs (1224xxx) while per-G-ID page.goto and WS both operate in live trading space (1238-1240xxx) — explains MLB G-ID walk's WS overlap advantage over NBA I99 wizard; per-G-ID navigation fires both HTTP partial AND activates SPA WS subscription simultaneously (Session 19:51)
