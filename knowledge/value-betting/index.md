# VB Scanner Brain — Index

> Master index of all wiki pages. Start here.

---

## Domain Knowledge (wiki/)
- [[wiki/devig-engine]] — The 4 devig methods, aggregation, sport/market differences
- [[wiki/ev-calculation]] — EV% formula, confidence weighting, theory evaluation
- [[wiki/clv]] — Closing line value: soft vs sharp, convergence rates, leading indicator
- [[wiki/interpolation]] — Line adjustment when sharp != soft: logit vs Poisson
- [[wiki/confidence-scoring]] — Per-book data quality scores, max 5.0
- [[wiki/theories]] — Theory system: named configs, calibration, promotion
- [[wiki/calibration]] — Weight sweeps, Brier score, optimizer, backtesting
- [[wiki/market-matcher]] — Cross-book market grouping by player/prop/side
- [[wiki/performance-tracking]] — Segmented performance analysis design
- [[wiki/glossary]] — Domain terms: vig, devig, sharp, soft, CLV, Brier, etc.

## Sports
- [[sports/nba]] — NBA: sharp books, prop performance, timing, biases, highest-conviction filters
- [[sports/mlb]] — MLB: research phase, context banking done, not yet calibrated
- [[sports/nrl]] — NRL: stub, OpticOdds only
- [[sports/afl]] — AFL: stub, OpticOdds only

## Data Sources (sources/)
- [[sources/opticodds]] — OpticOdds API: 40+ books, endpoints, rate limits, book IDs
- [[sources/bet365-scraper]] — Bet365 game scraping via CDP/AdsPower
- [[sources/betstamp]] — Betstamp Pro WebSocket: Bet365 odds fallback
- [[sources/direct-scrapers]] — AU bookies: Sportsbet, Neds, TAB, etc.

## Infrastructure (infra/)
- [[infra/server]] — FastAPI server: SSE streaming, state management, multi-sport
- [[infra/tracker]] — Pick tracking: trail_entries append-only pattern
- [[infra/resolver]] — Auto-resolution: OpticOdds player results, CLV
- [[infra/database]] — Supabase schema: all tables, RLS, migrations
- [[infra/deployment]] — Mini PC + VPS setup, ports, deploy script, health checks
- [[infra/dashboard]] — Frontend: SSE, data.json, results tab, stats bar
- [[infra/sport-config]] — Per-sport registry: NBA, MLB, NRL, AFL

## Findings (time-stamped)
- [[findings/2026-04-07-clv-1000-picks]] — 1,000 pick CLV analysis: sharp count is strongest signal, AU books crush Bet365
- [[findings/2026-04-08-favourite-longshot]] — Pinnacle article: favourite-longshot bias implications for power devig
- [[findings/2026-04-09-sharp-clv-first-data]] — First sharp CLV data: +8.9% sharp vs +1.79% soft

## Patterns
- [[patterns/data-flow]] — Full pipeline cycle: scrape -> devig -> track -> resolve
- [[patterns/adding-a-sport]] — How to add a new sport
- [[patterns/adding-a-book]] — How to add a new bookmaker source
- [[patterns/theory-lifecycle]] — Create -> calibrate -> promote -> evaluate -> retire
- [[patterns/debugging-ev]] — Common EV calculation issues and how to trace them

## Meta
- [[hot]] — Current investigations, open questions, active work
- [[log]] — Append-only changelog of all wiki operations
