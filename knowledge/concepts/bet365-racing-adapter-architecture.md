---
title: "bet365 Racing Adapter Architecture"
aliases: [bet365-adapter, bet365-local, superwin-bet365]
tags: [architecture, adapter, bet365, racing, superwin]
sources:
  - "daily/lcash/2026-04-11.md"
  - "daily/lcash/2026-04-12.md"
  - "daily/lcash/2026-04-13.md"
  - "daily/lcash/2026-04-14.md"
  - "daily/lcash/2026-04-15.md"
  - "daily/lcash/2026-04-16.md"
  - "daily/lcash/2026-04-17.md"
created: 2026-04-11
updated: 2026-04-17
---

# bet365 Racing Adapter Architecture

A local adapter (`bet365_local.py`) that extracts live Australian and New Zealand horse racing data from bet365.com.au via CDP-attached browser automation. The production architecture uses a two-layer approach: one-time HTTP discovery scan for runner name/ID mapping, followed by persistent WebSocket streaming for real-time odds updates.

## Key Points

- Two-layer architecture: HTTP `racecoupon` endpoint provides runner names, jockeys, weights, form, and IDs; WebSocket stream provides live odds updates keyed by those IDs
- Discovery phase uses T6 splash endpoint (no auth needed) to find all racing meetings, then navigates to each meeting and clicks race tabs to trigger HTTP responses captured via CDP
- The adapter evolved through four iterations: two-phase enumerate+fetch → single-pass tab-click → navigate-away per race → WS streaming — each pivot driven by a specific bet365 behavioral discovery
- Final HTTP-only metrics: 14 meetings, 12 loaded, 67 races, 661 runners, 100% odds coverage in ~4 minutes
- Output format matches SuperWin's `Race.to_dict()` interface with `bookie_ids`, `bookie_venues`, and `odds["bet365"]` containing win + place odds

## Details

### Architecture Evolution

The adapter went through four distinct architectural iterations in a single day, each driven by a discovery about bet365's anti-scraping behavior:

**Iteration 1 — Two-Phase Enumerate + Fetch:** Phase 1 clicked all race tabs within a meeting to discover non-sequential F values (race IDs like 192644720, 192644727). Phase 2 used navigate-away pattern to fetch each race individually. Result: 19/28 races in 95s from 3 meetings, but slow (~2.5s per race navigation).

**Iteration 2 — Navigate-Away per Race:** Applied the navigate-away trick (hash to soccer `#/AS/B1/` between each venue) to force fresh HTTP requests. Achieved 14/14 venues with 0 failures in 38 seconds, but only fetched 1 race per meeting (next-to-jump).

**Iteration 3 — Single-Pass Tab-Click:** Discovered that clicking race tabs within a meeting triggers fresh HTTP requests without needing navigate-away between individual races — only between meetings. Navigate to meeting once, click through all race tabs, capture each response via CDP. Result: 67 races from 12 meetings, 661 runners, 100% odds, ~4 minutes. Navigate-away still needed between meetings to prevent SPA caching.

**Iteration 4 — WebSocket Streaming (target architecture):** User directed pivot away from polling/scraping toward live streaming. The browser's WebSocket connection at `wss://premws-pt1.365lpodds.com/zap/` pushes ~7-8 odds updates per second. Independent Python WebSocket connections get 403'd, so the adapter piggybacks on the browser's existing connection by injecting subscription messages via `page.evaluate()` and capturing responses via CDP `Network.webSocketFrameReceived`. HTTP discovery scan still needed once for runner name ↔ participant ID mapping.

### Discovery Phase

The T6 discovery endpoint (`nexttojumpcontentapi/splash T6`) returns all current racing meetings (~30K chars) without requiring authentication or navigation state. Meetings include venue names, race times, and PD identifiers. Racing classification codes in discovery responses: `CL=2030` (horse racing), `CL=2031` (greyhounds), `CL=2032` (harness). Promotional entries with `#P12#` in their PD field should be filtered out.

**Discovery endpoint migration (2026-04-13):** The original `/contentdata/racecouponcontentapi/T6Splash` endpoint is dead. The replacement is `/nexttojumpcontentapi/splash` (no `/contentdata/` prefix), which only fires on cold page loads. Reusing an existing tab produces a lighter delta-only response at `/contentdata/nexttojumpcontentapi/splash` containing only navigation data, not the full meeting list. The solution is to open a fresh tab via `ctx.new_page()` for each discovery scan and close it after parsing — the cold-load URL is per-page-session, not per-browser-session. Direct `page.evaluate(fetch(...))` still returns empty due to SPA cache validation, so the adapter intercepts the SPA's own request via CDP `Network.responseReceived` + `Network.getResponseBody`.

### End-to-End Pipeline (Current)

As of 2026-04-13, the full adapter pipeline uses WebSocket constructor injection (see [[concepts/websocket-constructor-injection]]) for live streaming:

1. **Discovery:** Open fresh tab → navigate to racing → intercept full splash response via CDP → close tab
2. **Auth:** On main tab (with injected constructor wrapper already in place), cycle through 5 hash navigations to force a subscription frame. Capture `sync_term` from the `,A_{1452-char-token}` pattern in WS frames
3. **Runner map:** Tab-click capture technique: click each race tab within each meeting, intercept `racecoupon` HTTP responses via CDP, parse fixture/participant IDs and runner names
4. **Stream:** Send subscription messages on the captured WS, receive and parse odds updates via `addEventListener` + Python polling

Page reload kills the WebSocket, so auth extraction (which needs the WS alive for frame sniffing) must happen after the constructor injection but before any operation that would reload the page. First successful end-to-end run: 4 meetings, 294 participants across 25 fixtures, live price moves confirmed (e.g., `Scone #3 Yacht Girl 3.40 → 3.20 DOWN`).

### Venue Scanning Reliability

The venue scanning phase (HTTP discovery) is subject to reliability issues when the browser's JavaScript context degrades after scanning many venues. During testing on 2026-04-12, the Toowoomba venue consistently caused `page.evaluate()` to hang indefinitely — likely due to SPA state degradation after navigating through 10+ venues. This hang is uncancellable at the individual call level (see [[concepts/playwright-evaluate-uncancellable]]).

The adopted mitigation is a global 4-minute timeout on the entire `build_runner_map()` phase, with mutable containers (`participant_map`, `fixture_participants`) passed as parameters so partial results survive cancellation (see [[concepts/async-global-timeout-partial-results]]). This means the adapter proceeds to streaming with whatever venues were successfully scanned before the hang.

Additionally, stale browser WebSocket connections from repeated process kills cause auth extraction failures. The `x-net-sync-term` and session tokens may reference expired connections, producing silent failures. A fresh browser session (clean AdsPower profile start) is required for reliable full runs.

### Discovery Timing Dependency

The splash HTTP endpoint has a server-side population schedule — it returns 0 meetings before approximately 09:00 AEST. However, WebSocket OV topics already carry live race data by ~07:50 AEST. This creates a time-of-day blind spot where the adapter cannot discover races that are already streaming. Previous testing (Sunday 16:30) masked this because the splash was already populated. A WS-based discovery path (parsing race info from OV topics) would eliminate this dependency. See [[concepts/bet365-splash-timing-dependency]] for full analysis.

### WebSocket Cluster Selection

The adapter must specifically target `premws-pt1.365lpodds.com` connections when hijacking the browser's WebSocket. bet365 operates multiple WS clusters (`premws`, `pshudws`) carrying different data. Hijacking a `pshudws` connection produces 1% coverage (4/556 participants) despite valid subscriptions. The `premws` connections can transition to CLOSED state mid-session, requiring cluster-aware selection and recovery logic. See [[concepts/bet365-websocket-cluster-topology]].

### Supervisor Retry Logic

WS discovery failures (0 frames captured) initially caused the adapter's `main()` to return implicitly, which the supervisor treated as a clean exit. Fixed to return `False` on discovery failure so the supervisor retries the run instead of accepting 0 results as success.

### Dell Server Deployment

The adapter was ported to a Dell server on 2026-04-15, revealing several deployment-critical discoveries:

**Headless detection:** bet365 detects `--headless=new` Chrome and serves degraded/inert SPA content — the page loads, JS runs, and WS constructor wrappers inject, but zero WS traffic arrives. The existing NBA/MLB game scrapers already run in headed mode intentionally. The Dell server has an active desktop session, so headed Chrome renders into a real window with genuine fingerprints. Profile wiping via `shutil.rmtree` is fine — session warming is not required; headed mode alone is sufficient. See [[concepts/bet365-headless-detection]] for full analysis.

**Runner map alternative:** The CSS selector approach for race tab clicking (`.rcr-7b`) fails on fresh Chrome profiles — obfuscated class names may differ between versions. The preferred alternative is using the `racecoupon` HTTP endpoint via `page.evaluate("fetch(...)")` to inherit session cookies and sync_term, reusing the existing `_parse_racecoupon_response` parser (~30 lines).

**Windows issues:** Zombie Chrome processes hold CDP port and profile directory hostage — new connections silently attach to zombies instead of spawning fresh. Must kill entire process tree + re-wipe profile. Python stdout buffering on Windows loses output on crash (fix: `python -u` or `PYTHONUNBUFFERED=1`). Unicode characters crash due to cp1252 default encoding (fix: `sys.stdout.reconfigure(encoding='utf-8')`).

### Current Limitations

- **Horse racing only** — greyhound (`B4`) and harness (`B3`) meetings require separate discovery queries not yet implemented
- **Cloudflare blocking on VPS** — datacenter IPs and headless browser fingerprints are detected; requires AdsPower with residential proxy for deployment
- **Browser dependency** — adapter requires a live browser session (AdsPower or local Chromium), cannot operate as a standalone HTTP client
- **Race tab detection** — 2/14 meetings failed tab detection (likely fully completed meetings with no active races)
- **Past races** — races that have already jumped return runner data but no odds; this is expected behavior, not a bug
- **Venue scanning hangs** — certain venues (consistently Toowoomba) cause uncancellable `page.evaluate()` hangs after 10+ venues scanned; mitigated by global timeout with partial results
- **Splash timing dependency** — HTTP discovery returns 0 meetings before ~09:00 AEST; WS-based discovery not yet implemented
- **WS cluster selection** — premws connections can go CLOSED mid-session; adapter must detect and rehijack to correct cluster
- **Runner map degradation** — coverage degrades after ~5 meetings (outstanding investigation)
- **Subscription chunk-dropping** — only ~45 runners respond regardless of chunk count (outstanding investigation)
- **Headless mode blocked** — bet365 detects `--headless=new` and serves empty data; headed Chrome on a desktop session required (see [[concepts/bet365-headless-detection]])

### Multi-Fixture Production Deployment (2026-04-16)

On 2026-04-16, the adapter was deployed as `bet365_stream.py` to both Dell server and VPS for production multi-fixture streaming:

**Local Mac validation:** 502 participants, 24 fixtures, 13 meetings, 198/502 named (39%). AdsPower timeout adds ~9s before Chrome-via-CDP fallback.

**Dell production:** 484 participants, 25 fixtures, 12 meetings, 221/484 named (44%). Multi-fixture iteration (13 meetings × 5-8 races × 3s each) takes 2-3 minutes to build full runner map. Dell CPU at 66-94% (avg ~78%), adding ~15-20% over ~60% baseline from NBA/MLB workers. 8.3GB RAM free — CPU is the constraint, not memory.

**VPS ingest pipeline:** Dell streams → HTTP POST to VPS `/api/v1/ingest/bet365` (INGEST_TOKEN authenticated) → merged alongside Betfair → TAKEOVER SSE. Push interval set to 15s. 23 races pushed, 23 matched on VPS catalogue, bookies=2 showing bet365 merged alongside Betfair. TAKEOVER frontend needs zero changes since it reads `runner.odds["bet365"]` generically from SSE.

**Critical runner map fix:** `build_runner_map` was patched to iterate all fixtures per meeting (not just first) — critical for full race coverage. A secondary `(fixture_id, barrier_number)` lookup was added when direct PA ID match fails — see [[concepts/bet365-coupon-pm-id-mismatch]]. This doubled race coverage from 23→46 matched, 16→39 with live odds.

**Process persistence:** SSH disconnect kills the bet365_stream process tree. A Windows `schtasks` entry (`Bet365Racing`, `/SC ONSTART`) was set up for persistence, with batch file SCP'd from Mac because PowerShell here-string didn't survive SSH escaping.

**Remaining issues:** Greyhound matching broken (0/7 matched — trap/box vs barrier numbering mismatch with Betfair). bet365 only sends odds for races close to jump time (~60 min window). If Dell gets CPU-overloaded, levers are: reduce drain interval (0.5s), increase push interval (15s→30s), or drop workers.

### Stream Staleness Watchdog and Day-Change Handling (2026-04-17)

On 2026-04-17, the stream survived overnight but went stale — it never re-discovered the new day's racing card because the supervisor only restarts on crash, not on "no data." The assumption that "no crash = healthy" is wrong for long-running WS streams when the upstream data source simply goes silent at the end of a day's racing and new fixtures are never subscribed.

A **staleness watchdog** was added: 5 consecutive health check windows (~75 seconds total) of 0 odds updates raises a `STALE_STREAM` exception, which the supervisor catches and triggers a full restart with fresh discovery. This transforms the day-change problem from an indefinite silent stall into an automatic recovery within ~75 seconds of the stream going dry.

The `schtasks` entry (`Bet365Racing`, ONSTART trigger) was registered on the Dell server so the stream survives SSH disconnects and reboots. The batch file was SCP'd from Mac because PowerShell here-strings don't survive SSH escaping well. An operations document (`docs/BET365_RACING_OPERATIONS.md`) was created for teammate reference covering architecture, commands, credentials, monitoring, and troubleshooting.

### Deployment Architecture

The adapter runs locally against an AdsPower browser instance or headed Chrome on a desktop session. VPS deployment is blocked by Cloudflare — AdsPower with a residential proxy is needed. The `pstk` cookie and `cf_clearance` cookie are the key authentication tokens. The `x-net-sync-term` header rotates every ~55 seconds and must be refreshed from the page's JavaScript context. The Dell → VPS ingest pipeline uses HTTP POST with token authentication for production streaming.

## Related Concepts

- [[concepts/bet365-racing-data-protocol]] - The wire protocol consumed by this adapter
- [[concepts/spa-navigation-state-api-access]] - The SPA constraints that shaped the adapter's navigation strategy
- [[concepts/cdp-browser-data-interception]] - The data capture technique at the adapter's core
- [[concepts/browser-mediated-websocket-streaming]] - The target streaming architecture for real-time odds
- [[concepts/websocket-constructor-injection]] - The WS capture technique used in the current pipeline
- [[concepts/playwright-evaluate-uncancellable]] - The uncancellable evaluate issue affecting venue scanning reliability
- [[concepts/async-global-timeout-partial-results]] - The timeout pattern adopted for resilient venue scanning
- [[connections/browser-automation-reliability-cost]] - The broader reliability costs of the browser-mediated approach
- [[concepts/bet365-splash-timing-dependency]] - The splash endpoint timing gap affecting early-morning discovery
- [[concepts/bet365-websocket-cluster-topology]] - WS cluster selection required for correct data capture
- [[concepts/bet365-headless-detection]] - Headless Chrome detection that blocks data flow; headed mode required
- [[concepts/bet365-ws-topic-authorization]] - WS topic authorization limits streaming to registered render topics; racing works, NBA props don't
- [[concepts/bet365-coupon-pm-id-mismatch]] - Coupon PA IDs ≠ PM subscription IDs; barrier number as fallback join key for runner matching

## Sources

- [[daily/lcash/2026-04-11.md]] - Full adapter development across sessions 12:39–16:06: four architecture iterations, discovery of /contentdata/ prefix (Session 13:35), navigate-away trick (Session 14:45), single-pass tab-click (Session 15:53), pivot to WS streaming (Session 16:06)
- [[daily/lcash/2026-04-12.md]] - Venue scanning reliability: Toowoomba hang discovery, global timeout + mutable containers solution, stale browser session issues (Session 15:37)
- [[daily/lcash/2026-04-13.md]] - Discovery endpoint migration (old T6Splash dead, new cold-load-only endpoint), full end-to-end pipeline with constructor injection: discovery → auth → runner map → stream, first live price moves confirmed (Session 15:00 onward)
- [[daily/lcash/2026-04-14.md]] - Splash returns 0 meetings before ~09:00 AEST (timing dependency); WS cluster selection: premws vs pshudws, 1% coverage from wrong cluster; supervisor retry on discovery failure; runner map degradation and chunk-dropping still outstanding (Sessions 07:56, 10:00)
- [[daily/lcash/2026-04-15.md]] - Dell server port: headless Chrome detection (zero WS traffic in headless mode), headed mode required, racecoupon HTTP preferred over CSS click runner map, Windows zombie Chrome/stdout buffering/cp1252 issues (Session 14:55)
- [[daily/lcash/2026-04-16.md]] - Multi-fixture production deployment: Mac 502 participants/13 meetings, Dell 484/12 meetings; VPS ingest pipeline (23 races matched, bookies=2); build_runner_map patched for all fixtures per meeting; coupon-PM ID mismatch fixed with barrier-number fallback (23→46 matched); Dell CPU 66-94%; schtasks persistence; greyhound matching still broken (Sessions 12:26, 14:10, 15:16, 15:46)
- [[daily/lcash/2026-04-17.md]] - Stream survived overnight but went stale (no day-change rediscovery); staleness watchdog added: 5 consecutive windows of 0 updates → STALE_STREAM → supervisor restart; schtasks entry registered; operations doc created; horses/harness 80-100% match, greyhounds 0/7 still broken (Session 16:44)
