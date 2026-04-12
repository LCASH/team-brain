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
| [[concepts/bet365-racing-data-protocol]] | Custom pipe-delimited WS protocol with two-letter field codes (NA=, OD=, FI=), F\|/U\| snapshots/deltas | daily/lcash/2026-04-11.md | 2026-04-12 |
| [[concepts/spa-navigation-state-api-access]] | bet365 SPA requires proper navigation flow for API access; navigate-away trick busts internal cache | daily/lcash/2026-04-11.md | 2026-04-12 |
| [[concepts/cdp-browser-data-interception]] | CDP-level WS frame and HTTP response interception for pre-existing browser connections | daily/lcash/2026-04-11.md | 2026-04-12 |
| [[concepts/bet365-racing-adapter-architecture]] | Two-layer adapter: HTTP discovery scan for name mapping + WS streaming for live odds | daily/lcash/2026-04-11.md, daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/browser-mediated-websocket-streaming]] | Piggybacking on browser WS connections via JS injection + CDP capture to bypass 403 auth | daily/lcash/2026-04-11.md | 2026-04-12 |
| [[connections/anti-scraping-driven-architecture]] | How bet365's four-layer defense stack forced each architectural pivot in the adapter | daily/lcash/2026-04-11.md | 2026-04-12 |
| [[concepts/playwright-evaluate-uncancellable]] | Playwright page.evaluate() blocks asyncio event loop; not cancellable by asyncio.wait_for when browser JS is unresponsive | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/async-global-timeout-partial-results]] | Global timeout + mutable containers pattern to preserve partial work when individual async ops hang | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/opticodds-critical-dependency]] | OpticOdds as sole sharp odds provider — single point of failure for devigging and 3/4 sports | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[connections/browser-automation-reliability-cost]] | Browser-mediated architecture forced by anti-scraping introduces uncancellable JS hangs and stale session failures | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/betstamp-bet365-scraper-migration]] | Removing Betstamp adapter, consolidating Bet365 scraping under game scraper with book_id 366→365 | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/configuration-drift-manual-launch]] | Batch file missing flags and API keys that were set manually; restart via script causes silent feature regression | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[connections/scraper-consolidation-provider-dependency]] | Betstamp removal deepens OpticOdds single-provider dependency by eliminating independent EV cross-check | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/silent-worker-authentication-failure]] | Workers silently exit/idle with zero log output when API keys are missing; discovered with direct_scrapers and blackstream | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[concepts/value-betting-operational-assessment]] | Systematic 7-weakness assessment: OpticOdds SPOF, no monitoring, config drift, silent failures, browser fragility, no redundancy, bus factor | daily/lcash/2026-04-12.md | 2026-04-12 |
| [[connections/operational-compound-failures]] | Config drift + silent failures + no monitoring compound to create extended invisible degradation | daily/lcash/2026-04-12.md | 2026-04-12 |
