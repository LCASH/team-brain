---
title: "V3 Scanner Centralized Query-Response Architecture"
aliases: [v3-scanner, centralized-architecture, v3-redesign, query-response-model, v3-12-phase]
tags: [value-betting, architecture, redesign, modular, event-driven]
sources:
  - "daily/lcash/2026-05-05.md"
  - "daily/lcash/2026-05-06.md"
  - "daily/lcash/2026-05-07.md"
  - "daily/lcash/2026-05-08.md"
created: 2026-05-05
updated: 2026-05-08
---

# V3 Scanner Centralized Query-Response Architecture

On 2026-05-05, lcash completed a comprehensive 12-phase architectural redesign of the value betting scanner (V3), replacing the distributed push model (mini PC → VPS) with a centralized query-response architecture. The mini PC becomes a queryable odds server on port 8900 with GET endpoints, the tracker is event-driven (wakes on `asyncio.Event` for real data changes instead of 5-second polling), theories are loaded once at startup from Supabase (eliminating the 5-minute TTL refresh cycle), and scrapers are modularized into separate files for login, discovery, and scraping via a `CDPPageBase` abstraction. The system was deployed with 65 passing tests and validated live with 1,400+ odds from 3 NBA games and 7,400+ MLB raw odds across 15 games.

## Key Points

- **Push → Query**: Mini PC shifts from pushing odds to VPS to serving them on port 8900 via FastAPI GET endpoints (`/v1/odds`, `/v1/games`, `/v1/stream`); VPS becomes display-only, querying the mini PC API
- **Event-driven tracker**: Wakes on `asyncio.Event` set by DataStore when odds actually change, replacing fixed 5-second polling — more efficient and more responsive
- **Theories loaded once at startup**: Eliminates the 5-minute TTL Supabase refresh cycle that was a recurring source of startup delays and 266+ sequential GETs
- **Modular scraper architecture**: `CDPPageBase` (low-level CDP transport + tab lifecycle) and `ChromeManager` (process lifecycle + binary discovery) extracted as shared abstractions; sport scrapers inherit and override `_on_cdp_event()`
- **12-phase build sequence**: Pure functions → scraper abstraction → data layer → tracker → orchestrator → VPS cutover, with risk reduction at each phase
- **65 tests passing**: Comprehensive pytest suite with async fixtures, mocked external services (OpticOdds, Bet365), and modular component isolation
- **Parallel V2/V3 operation**: V3 on port 8900, V2 on port 8800; V3 VPS dashboard on port 8803, V2 on 8802 — full game day validation before cutover

## Details

### The Push Architecture Problem

The V2 architecture operated as a distributed push system: each sport server on the mini PC ran its own push worker that periodically serialized odds and POSTed them to the VPS relay endpoint. This created multiple operational problems documented across the knowledge base: push worker orphan accumulation (see [[concepts/push-worker-orphan-accumulation]]), per-sport process management overhead, silent push worker death with no auto-recovery, and the SSE cascade crash vulnerability where VPS SSE errors killed the backend tracker (see [[concepts/vps-sse-cascade-silent-crash]]). The unified aggregator on port 8899 (see [[concepts/unified-odds-aggregator-pipeline]]) was an intermediate fix that consolidated push workers but didn't address the fundamental push-vs-query architecture.

V3 inverts the data flow: the mini PC serves odds via HTTP endpoints, and downstream consumers (VPS, dashboards, trackers) query when they need data. This eliminates the entire push worker class of failures and simplifies the mini PC to a single process running a FastAPI server with scraper background tasks.

### Modular Scraper Architecture

V2's scrapers were monolithic — a single file handling Chrome launch, login, game discovery, page management, odds parsing, and push. V3 separates these concerns:

- **`CDPPageBase`**: Low-level CDP transport abstraction handling WebSocket connections to Chrome tabs, Network event capture (`responseReceived` + `getResponseBody`), and tab lifecycle management. Sport scrapers inherit from this.
- **`ChromeManager`**: Chrome process lifecycle — binary discovery (finds Chrome executable), process launch with debugging port and persistent profile, kill-and-relaunch pattern from [[concepts/cdp-stale-connection-poisoning]].
- **Login module**: `login_and_confirm()` with human-like delays, credential-based auto-login with CAPTCHA fallback to manual polling (5-minute timeout), `requires_login` config flag so MLB (which uses anonymous `matchbettingcontentapi/partial`) skips login entirely.
- **Discovery module**: `discover_games()` captures `contentapi` API responses via CDP to enumerate available games and extract event IDs.
- **Sport scrapers**: `NBAGameScraper` and `MLBGameScraper` inherit from `CDPPageBase`, each implementing `_on_cdp_event()` override for sport-specific response parsing. MLB overrides `setup()`/`refresh()` to cycle 26 MGs per game (I0 tab + 19 batter + 7 pitcher hash-nav URLs).

### Event-Driven DataStore

V3's `DataStore` extends the V2 `AppState` with an `asyncio.Event` (`change_event`) that is set whenever new odds data arrives. The tracker awaits this event instead of polling on a fixed interval:

- V2: Tracker polls every 5 seconds regardless of whether data has changed
- V3: Tracker sleeps until `change_event.is_set()`, processes immediately, then resets the event

This is more efficient (no wasted cycles polling unchanged data) and more responsive (reacts within milliseconds of new data instead of up to 5 seconds later). The DataStore also provides sport-aware filtering via `get_markets(sport=, book=, game=)` and `get_active_games()`.

### Theory Startup Loading

V2 refreshed theories from Supabase every 5 minutes with a TTL cache. This caused the SSE startup theory creation hang (see [[concepts/sse-startup-theory-creation-hang]]) where 266+ sequential Supabase GETs blocked SSE stream launch. V3 loads theories exactly once at startup — a single Supabase query returning all active theories. Changes to theories require a V3 restart, which is acceptable because theory configuration changes are infrequent (weekly at most) and restart is fast (~30 seconds).

### Deployment and Integration Findings

Initial deployment to the mini PC on 2026-05-05 exposed an "assembly problem" — all 12 phases were implemented and tested individually, but the wiring in `startup.py` had three critical gaps: (1) OpticOdds initialization called with wrong parameter signature (callback vs proper params), (2) Bet365 scraper initialization was a placeholder, and (3) market schema mismatch (`market_key` field expected by DataStore but not produced by scrapers). These were all fixed in a single integration session.

A `captured_at` staleness bug was discovered during live monitoring: the REST seed and Bet365 push loop were setting `captured_at` to the original parse time (10+ hours old for REST) instead of current time. Bet365 data appeared 36,327 seconds stale until fixed to use `time.time()` at push time.

### MLB Multi-URL Cycle

MLB's V3 scraper required a critical Phase 13-14 enhancement: V3 initially only loaded the I0 tab, producing 2 markets per game. The V2 architecture cycled through 26 MGs per game (19 batter + 7 pitcher hash-nav URLs in addition to I0). After implementing the multi-URL cycle in `MLBGameScraper`, coverage jumped from 2 to 1,120+ markets per game (~7,400 raw odds total across 15 games). The `SETUP_CONCURRENCY` was bumped from 3 to 5 to reduce MLB startup from ~25 to ~15 minutes.

### V3 Dashboard and VPS

A V3 VPS display server was deployed on port 8803 alongside the existing V2 dashboard on port 8802. The V3 server proxies the mini PC at `:8900` for live odds data and reads Supabase directly for picks. The dashboard HTML is an exact copy of V2's `dashboard/index.html` using `API_BASE = window.location.origin` for transparent API routing. A systemd service (`value-betting-v3`) was created for auto-restart.

### Tracker Fixture ID Dedup

During live testing, the V3 tracker initially found 20 picks but with duplicates — the same player appeared multiple times because different sportsbooks used different fixture IDs (14, 15, 16) for the same game. The fix groups by `(player, market_key, line)` without fixture_id and deduplicates to the best EV pick per `(player, market_key, line, sportsbook)` combination, producing 11 clean picks.

## Related Concepts

- [[concepts/push-worker-orphan-accumulation]] - The push worker orphan problem that V3's query-response model structurally eliminates
- [[concepts/unified-odds-aggregator-pipeline]] - The intermediate aggregator (port 8899) that V3 supersedes
- [[concepts/sse-startup-theory-creation-hang]] - The 266+ sequential Supabase GETs that V3's startup-once loading eliminates
- [[concepts/persistent-page-chrome-scraper-architecture]] - V3 inherits the persistent-page pattern via CDPPageBase
- [[concepts/cdp-stale-connection-poisoning]] - The fresh-Chrome-on-start pattern codified in ChromeManager
- [[connections/chrome-lifecycle-management-pattern]] - The unified Chrome lifecycle pattern that V3's modular architecture builds on
- [[concepts/opticodds-sse-reconnect-state-loss]] - SSE state loss discovery that led to REST reseed in V3
- [[concepts/value-betting-operational-assessment]] - The 7-weakness assessment that V3 was designed to address
- [[concepts/bet365-ws-native-scraper-migration]] - The WS-native NBA/MLB scrapers deployed on 2026-05-06 as WSNBAOrchestrator and WSMLBOrchestrator
- [[concepts/v3-dashboard-ev-computation-architecture]] - The V3 dashboard's live EV computation via mini PC `/v1/picks` endpoint

### WebSocket-Native Scraper Deployment (2026-05-06)

On 2026-05-06, the V3 architecture evolved further with the deployment of `WSNBAOrchestrator` and `WSMLBOrchestrator` — WebSocket-native scrapers that replace the CDP HTTP response interception model. Instead of navigating Chrome tabs and intercepting API responses, the WS orchestrators stream odds updates directly from bet365's WebSocket connection at sub-second latency. NBA worst-case dropped from 23s to ~8s, and both scrapers were deployed to production with 5,001 NBA + 5,249 MLB = 13,239 total markets streaming.

Key deployment issues resolved: `startup.py` was passing orchestrator objects (not Playwright Page objects) to `discovery.py`; `Target.activateTarget` was called on the wrong Chrome port; discovery tabs created with pre-loaded URLs caused navigation timeouts (fixed to create as `about:blank` first). The V3 dashboard was also built with live EV computation from the mini PC's `/v1/picks` endpoint — see [[concepts/v3-dashboard-ev-computation-architecture]].

Additionally, a 2-second flush throttle was added to the OpticOdds SSE consumer to prevent event loop blocking — OpticOdds streams 24+ events/second, each holding the asyncio lock. Buffering and flushing in batch every 2s reduced lock acquisitions 97% (239 → 8 per 10 seconds).

### CO Market Removal (2026-05-06)

A prop type mapping audit confirmed NBA was 13/13 perfectly matched between OpticOdds and Bet365. MLB had 14 matched plus 8 CO-only (combo/accumulator) markets with no OpticOdds equivalent — these can never be devigged. All 9 CO entries were removed from `MLB_MG_NAME_MAP`: Home Runs CO, Bases CO, Hits CO, RBIs CO, Runs CO, Hits Runs RBIs CO, Batting Strikeouts CO, Strikeouts CO, Earned Runs CO.

### V3 Discovery and Reliability Fixes (2026-05-07)

On 2026-05-07, three critical discovery and reliability issues were resolved:

**CDPSession pipe contention**: The MLB orchestrator's CDPSession (WS frame listener) blocked Playwright `evaluate()` calls on the shared page, causing discovery to hang indefinitely. Fix: discovery now creates a dedicated fresh page from `playwright_browser` — never shares the orchestrator's CDPSession-linked page. See [[concepts/bet365-cdpsession-pipe-contention]].

**getsplashpods home page constraint**: Discovery was navigating to sport-specific URLs (`#/AS/B18/AC/`) that never trigger getsplashpods. The API only fires from `#/HO/` (home page). Additionally, `pullpodapi` responses were being dropped by the URL capture filter (only `contentapi` was matched). After fixing both, discovery found 104 total games (12 NBA + 15 MLB). See [[concepts/bet365-getsplashpods-home-page-constraint]].

**VB_V3_Restart Windows Task**: A `VB_V3_Restart` scheduled task was created with system startup trigger + 5-minute polling if V3 is not running. This replaces the prior schtask model and was verified working: V3 restarted cleanly at 00:19 with login preserved (Chrome sessions persisted), NBA found 11 games, MLB discovery ran successfully. The EPIPE crash at 23:10:50 that motivated this task was not caught by the previous schtask configuration.

### Vanilla Chrome Anti-Bot Detection Blocker (2026-05-07)

On 2026-05-07 (Session 22:29), V4 deployment to the mini PC failed because the production environment runs **vanilla Chrome** with `--remote-debugging-port`, not AdsPower. bet365's anti-bot system now detects `navigator.webdriver=true` (which vanilla Chrome exposes when launched with debugging port) and serves partial/degraded content from the wizard endpoint. Body size diagnostic: 114KB on mini PC (vanilla Chrome, partial bot detection) vs 131KB locally (AdsPower, full content).

V3 rollback was also attempted but failed identically, confirming this is an **environmental anti-bot escalation** by bet365, not a V4 code regression. bet365 likely shipped stricter anti-bot checks within the past 24 hours that pushed vanilla Chrome below the detection threshold. See [[concepts/bet365-headless-detection]] for the full analysis.

This is the most impactful environment parity failure in the scanner's history: all V3/V4 development and testing used AdsPower (which masks CDP artifacts), while production used vanilla Chrome. The fix requires either installing AdsPower on the mini PC or adding stealth JS injection scripts (~50 lines) to mask `navigator.webdriver` and related properties.

### V4 HTTP+WS Hybrid Architecture (2026-05-07)

Session 22:29 also confirmed the V4 hybrid architecture locally via AdsPower: single Playwright page with `add_init_script` interceptor captures both WS connections, batch subscribe injection handles CONNECTING state with retry logic, and the HTTP refresh loop updates `_live_odds` in place every 30s (NBA) / 60s (MLB). NBA uses a single mega-endpoint (`betbuilderpregamecontentapi/wizard`) returning all 13 prop types in one 5.5s fetch; MLB requires walking 26 G-IDs per game (~24s/game) — a structural bet365 product asymmetry.

Session 22:57 documented remaining untested hypotheses from the WS protocol reversal: (1) time-of-day gating where WS streams may activate 30-60 minutes before tipoff, and (2) betslip-triggered subscribes where the server only allocates stream buffers for PAs added to the betslip. These are deferred to a morning MLB first-pitch validation test.

## Sources

- [[daily/lcash/2026-05-05.md]] - Complete architectural redesign defined (Session 10:56); Phases 3-7 completed: CDPPageBase, ChromeManager, login/discovery separation, OpticOdds SSE consumer, DataStore with change_event (Session 11:11); Testing strategy with 65 tests (Session 11:18); All 12 phases completed (Session 11:47); Deployment ready, 3 commits, 44 files, 8,827 lines (Session 12:02); Mini PC deployment, integration findings: OpticOdds API signature mismatch, Bet365 placeholder, market schema gap (Session 13:19); Full integration wiring (Session 13:26); Live: 1,400+ odds from 3 NBA games, 389 theories loaded (Session 13:51); MLB multi-URL cycle: 2→1,120+ markets, 7,400 raw odds across 15 games; BB wizard requires login, MLB partial does not (Session 16:54); Tracker fixture ID dedup: 20→11 clean picks (Session 22:40); V3 dashboard on VPS port 8803 (Session 23:42); captured_at staleness: 36,327s → 6s after fix (Session 23:37)
- [[daily/lcash/2026-05-07.md]] - CDPSession pipe contention: MLB discovery hung from WS listener consuming Playwright pipe; fix: dedicated fresh page for discovery. getsplashpods only fires from `#/HO/` — sport-specific URLs never trigger it; pullpodapi added to capture filter; BC field is midnight not tipoff (grace check removed). VB_V3_Restart task created with 5-min polling; verified: V3 restarted cleanly with login preserved. isTrusted click detection: sidebar CDP mouse click required. NST direct fetch confirmed dead. I99 wizard delivers 286-482 PAs/game in single fetch (zero in-game clicks architecture). WS pre-game limitation: OV_POPULAR is global firehose, 0 PA_ID overlap; hybrid HTTP+WS decided (Sessions 09:18, 09:51, 11:22, 11:54, 13:56, 14:32, 16:30, 18:40, 19:20)
- [[daily/lcash/2026-05-08.md]] - **MLB wizard-first regression fix**: 26-G-ID walk replaced by single BB wizard fetch (865 PAs/9.7s vs 76/71.8s); context-level init_script fingerprinting walk tabs fixed with page-level scoping. **Playwright locator hang**: `get_by_text()` hangs on bet365 SPA — replaced with raw JS DOM scan + `Array.from()` materialization. **Discovery fixes**: SPA requires `#/HO/` for sidebar rendering; `marketscontentapi` returns 0 fixtures on single-game days; Playwright `locator.count()` has no implicit timeout. **Parallel refresh**: `asyncio.gather()` over per-game tabs eliminates shared-state race from sequential page navigation. **asyncio Event.wait() memory leak**: `change_event.wait()` without `.clear()` in SSE producer caused 75MB/sec leak — identical to previously-fixed tracker bug. **VPS pull/proxy architecture confirmed**: v3 VPS proxies browser requests to mini PC via Tailscale; Eve transition just needs Tailscale + MINI_PC_URL update. Production: 5,313 markets, 25 +EV picks flowing (Sessions 00:36, 07:48, 09:04, 10:09, 10:44, 11:17, 12:11, 13:19, 13:56, 14:29, 15:07, 15:38, 17:54, 18:36)
