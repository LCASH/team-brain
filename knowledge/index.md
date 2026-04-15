# Knowledge Base Index

| Article | Summary | Compiled From | Updated |
|---------|---------|---------------|---------|
| [[concepts/team-knowledge-base-architecture]] | Multi-developer shared KB with per-developer daily logs and automated compilation | daily/lcash/2026-04-10.md | 2026-04-12 |
| [[concepts/claude-code-hook-reliability]] | SessionEnd unreliable (users walk away); Stop hook fires reliably after every response | daily/lcash/2026-04-10.md | 2026-04-10 |
| [[concepts/stop-hook-periodic-capture]] | Stop hook + 30-min timer check as primary capture mechanism (<50ms overhead) | daily/lcash/2026-04-10.md | 2026-04-10 |
| [[concepts/setup-kb-skill]] | /setup-kb skill for one-command team onboarding (clone, install, configure hooks) | daily/lcash/2026-04-10.md, daily/carts00/2026-04-10.md | 2026-04-12 |
| [[concepts/local-compilation-strategy]] | Local compilation over CI to save costs ($0.45-0.65/log), nightly fallback after 6 PM | daily/lcash/2026-04-10.md | 2026-04-10 |
| [[connections/hook-reliability-and-capture-architecture]] | How SessionEnd unreliability drove the Stop-hook-based polling architecture | daily/lcash/2026-04-10.md | 2026-04-10 |
| [[concepts/claude-code-skills-directory]] | Skills must be in project-level `.claude/skills/`, not user home `~/.claude/skills/` | daily/carts00/2026-04-10.md | 2026-04-12 |
| [[concepts/parlay-ev-calculation]] | Method for calculating true EV on boosted parlays by multiplying leg true odds | daily/carts00/2026-04-10.md | 2026-04-12 |
| [[concepts/cumulative-vs-filtered-display-pattern]] | UX pattern: summary cards always cumulative, detail views respect active filter | daily/carts00/2026-04-10.md | 2026-04-12 |
| [[connections/onboarding-friction-real-world-validation]] | First real team onboarding (carts00) validated setup-kb need and revealed platform gaps | daily/carts00/2026-04-10.md | 2026-04-12 |
| [[concepts/project-context-tagging]] | Session headers tagged with `[project-name]` via cwd extraction for multi-project disambiguation | daily/lcash/2026-04-10.md | 2026-04-12 |
| [[concepts/bet365-racing-data-protocol]] | Custom pipe-delimited WS protocol with two-letter field codes (NA=, OD=, FI=), F\|/U\| snapshots/deltas, binary framing | daily/lcash/2026-04-11.md, daily/lcash/2026-04-13.md, daily/lcash/2026-04-14.md | 2026-04-15 |
| [[concepts/spa-navigation-state-api-access]] | bet365 SPA requires proper navigation flow for API access; navigate-away trick busts internal cache | daily/lcash/2026-04-11.md | 2026-04-12 |
| [[concepts/cdp-browser-data-interception]] | CDP-level WS frame and HTTP response interception for pre-existing browser connections | daily/lcash/2026-04-11.md | 2026-04-12 |
| [[concepts/bet365-racing-adapter-architecture]] | Two-layer adapter: HTTP discovery + WS streaming via constructor injection for live odds | daily/lcash/2026-04-11.md, daily/lcash/2026-04-12.md, daily/lcash/2026-04-13.md, daily/lcash/2026-04-14.md, daily/lcash/2026-04-15.md | 2026-04-15 |
| [[concepts/browser-mediated-websocket-streaming]] | Piggybacking on browser WS connections via JS injection + CDP capture to bypass 403 auth | daily/lcash/2026-04-11.md | 2026-04-12 |
| [[connections/anti-scraping-driven-architecture]] | How bet365's six-layer defense stack forced each architectural pivot including headless detection and constructor injection | daily/lcash/2026-04-11.md, daily/lcash/2026-04-13.md, daily/lcash/2026-04-14.md, daily/lcash/2026-04-15.md | 2026-04-15 |
| [[concepts/playwright-evaluate-uncancellable]] | Playwright page.evaluate() blocks asyncio event loop; not cancellable by asyncio.wait_for when browser JS is unresponsive | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/async-global-timeout-partial-results]] | Global timeout + mutable containers pattern to preserve partial work when individual async ops hang | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/opticodds-critical-dependency]] | OpticOdds as sole sharp odds provider — single point of failure for devigging and 3/4 sports | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[connections/browser-automation-reliability-cost]] | Browser-mediated architecture introduces JS hangs, stale sessions, and hours-long warmup latency after restart | daily/lcash/2026-04-12.md, daily/lcash/2026-04-13.md | 2026-04-15 |
| [[concepts/betstamp-bet365-scraper-migration]] | Removing Betstamp adapter, consolidating Bet365 scraping under game scraper with book_id 366→365 | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/configuration-drift-manual-launch]] | Batch file missing flags and API keys that were set manually; restart via script causes silent feature regression | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[connections/scraper-consolidation-provider-dependency]] | Betstamp removal deepens OpticOdds single-provider dependency by eliminating independent EV cross-check | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/silent-worker-authentication-failure]] | Workers silently exit/idle with zero log output when API keys are missing; discovered with direct_scrapers and blackstream | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/value-betting-operational-assessment]] | Systematic 7-weakness assessment: OpticOdds SPOF, no monitoring, config drift, silent failures, browser fragility, no redundancy, bus factor | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[connections/operational-compound-failures]] | Config drift + silent failures + no monitoring compound to create extended invisible degradation | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/alt-line-mismatch-poisoned-picks]] | Alt-line/main-line mismatch in tracker interpolation produces 50-200% phantom EV; fix verified with 0 new poisoned picks | daily/lcash/2026-04-13.md | 2026-04-15 |
| [[concepts/server-side-snapshot-cache]] | Background task pre-serializes odds response every 2s; reduced push cycle 55s→1.9s (29x faster) | daily/lcash/2026-04-13.md | 2026-04-15 |
| [[concepts/trail-data-temporal-resolution]] | Pre-fix trails are sparse (55s intervals) not corrupt; aggregate backtesting unaffected, sub-minute analysis degraded | daily/lcash/2026-04-13.md | 2026-04-15 |
| [[concepts/fixture-name-canonicalization]] | Same game appearing 3x in dashboard from different naming formats; fixed by preferring "vs" format at merge time | daily/lcash/2026-04-13.md | 2026-04-15 |
| [[concepts/websocket-constructor-injection]] | Pre-page-load WebSocket constructor wrapping via CDP to capture SPA's closure-hidden WS instances | daily/lcash/2026-04-13.md | 2026-04-15 |
| [[connections/push-latency-trail-quality-cascade]] | How serialization bottleneck → 55s push cycle → stale sharps → sparse trail capture cascaded into data quality issues | daily/lcash/2026-04-13.md | 2026-04-15 |
| [[concepts/value-betting-theory-system]] | Theories as Supabase rows with configurable sharp weights, devig method, EV threshold, prop/soft-book filters; no code changes needed | daily/lcash/2026-04-13.md, daily/lcash/2026-04-14.md, daily/lcash/2026-04-15.md | 2026-04-15 |
| [[concepts/worker-status-observability]] | Replaced hardcoded "streaming" with actual states (idle_no_fixtures/streaming/stale/error) for accurate health checks | daily/lcash/2026-04-13.md | 2026-04-15 |
| [[concepts/self-evolving-operational-skill]] | /checkup skill pattern: operational runbook that self-updates its known-fix database and baselines after each run | daily/lcash/2026-04-13.md | 2026-04-15 |
| [[concepts/bet365-splash-timing-dependency]] | Splash HTTP endpoint returns 0 meetings before ~09:00 AEST; WS OV topics carry data hours earlier | daily/lcash/2026-04-14.md | 2026-04-15 |
| [[concepts/bet365-websocket-cluster-topology]] | premws vs pshudws WS clusters carry different data; wrong-cluster hijack produces 1% coverage | daily/lcash/2026-04-14.md | 2026-04-15 |
| [[concepts/bet365-mlb-lazy-subscribe-migration]] | MLB props moved from BB wizard to lazy-subscribe model; v2 silently broke click/scroll triggers; v3 hybrid fix | daily/lcash/2026-04-14.md | 2026-04-15 |
| [[concepts/afl-circular-devig-trap]] | AFL "sharps" are correlated retail shops; devig is self-referential; -34.2% ROI despite +1.16% CLV | daily/lcash/2026-04-14.md | 2026-04-15 |
| [[concepts/one-sided-consensus-structural-bias]] | `one_sided_consensus` devig skips all Unders; 951:13 Over/Under imbalance from structural bug + alphabetical theory hijack | daily/lcash/2026-04-14.md | 2026-04-15 |
| [[concepts/pick-dedup-multi-theory-limitation]] | Deterministic pick UUID + alphabetical `triggered_by` limits A/B testing; theory_evs column + offline replay workaround | daily/lcash/2026-04-14.md | 2026-04-15 |
| [[connections/circular-devig-provider-dependency]] | OpticOdds dependency + no AFL market makers = circular devig producing systematically wrong EV signals | daily/lcash/2026-04-14.md | 2026-04-15 |
| [[concepts/bet365-ws-topic-authorization]] | Session-bound P-ENDP topic authorization: WS streaming works for racing (per-participant render) but not NBA props (bulk BB wizard fetch) | daily/lcash/2026-04-15.md | 2026-04-15 |
| [[concepts/bet365-headless-detection]] | bet365 detects headless Chrome and serves empty SPA; headed mode required for data flow | daily/lcash/2026-04-15.md | 2026-04-15 |
| [[concepts/odds-staleness-pipeline-diagnosis]] | Six causes of odds drift identified; `source_captured_at` end-to-end plumbing pattern for measuring scraper-to-dashboard latency | daily/lcash/2026-04-15.md | 2026-04-15 |
| [[concepts/dashboard-client-server-ev-divergence]] | Dashboard computes EV against all soft books ignoring theory restrictions; `loadTheories()` bug fix deployed | daily/lcash/2026-04-15.md | 2026-04-15 |
| [[connections/ws-viability-sport-rendering-divergence]] | Racing WS works (per-participant render registration) but NBA prop WS doesn't (bulk BB wizard fetch); dual-architecture needed | daily/lcash/2026-04-15.md | 2026-04-15 |
