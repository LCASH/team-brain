# Wiki Change Log

> Append-only. Every wiki operation gets an entry here.

---

## 2026-04-09 — Structure Refinement

Reorganized brain into clear zones. Motivation: wiki/ was a flat bucket mixing domain knowledge with infrastructure; no sport-specific home; no findings layer for time-stamped research.

**Moves:**
- `wiki/` data source pages → `sources/` (opticodds, bet365-scraper, betstamp, direct-scrapers)
- `wiki/` infrastructure pages → `infra/` (server, tracker, resolver, database, deployment, dashboard, sport-config)
- `raw/` article → `raw/articles/`

**New pages:**
- `wiki/clv.md` — CLV concepts, soft vs sharp, convergence rates
- `sports/nba.md` — NBA context with all 1,000 pick findings integrated
- `sports/mlb.md` — MLB stub (research phase)
- `sports/nrl.md` — NRL stub
- `sports/afl.md` — AFL stub
- `findings/2026-04-07-clv-1000-picks.md` — 1,000 pick analysis headlines and implications
- `findings/2026-04-08-favourite-longshot.md` — Pinnacle article implications for devig method selection
- `findings/2026-04-09-sharp-clv-first-data.md` — First sharp CLV results (+8.9% vs +1.79% soft)

**Updated:** CLAUDE.md (new folder structure + routing table), index.md (reorganized), backlinks fixed.

---

## 2026-04-08 — Initial Seed

- **Created** CLAUDE.md — Wiki schema, domain terminology, folder structure, rules
- **Created** index.md — Master index of all wiki pages
- **Created** log.md — This file
- **Created** hot.md — Current hot topics and open questions
- **Created** wiki/devig-engine.md — Core devig pipeline (4 methods, aggregation)
- **Created** wiki/ev-calculation.md — EV formula, confidence weighting
- **Created** wiki/interpolation.md — Logit vs Poisson line adjustment
- **Created** wiki/confidence-scoring.md — Per-book data quality scores
- **Created** wiki/theories.md — Theory system: configs, evaluation, promotion
- **Created** wiki/calibration.md — Weight sweeps, optimizer, backtesting
- **Created** wiki/market-matcher.md — Cross-book market grouping
- **Created** wiki/opticodds.md — OpticOdds API client and book mappings
- **Created** wiki/bet365-scraper.md — Bet365 game scraping via CDP
- **Created** wiki/betstamp.md — Betstamp Pro WebSocket fallback
- **Created** wiki/direct-scrapers.md — AU bookie scrapers
- **Created** wiki/server.md — FastAPI server architecture
- **Created** wiki/tracker.md — Pick tracking and trail_entries
- **Created** wiki/resolver.md — Auto-resolution and CLV
- **Created** wiki/database.md — Supabase schema overview
- **Created** wiki/deployment.md — Mini PC deployment
- **Created** wiki/dashboard.md — Frontend dashboard
- **Created** wiki/sport-config.md — Per-sport registry
- **Created** wiki/glossary.md — Domain glossary
- **Created** patterns/data-flow.md — Full pipeline cycle
- **Created** patterns/adding-a-sport.md — How to add a new sport
- **Created** patterns/adding-a-book.md — How to add a new bookmaker
- **Created** patterns/theory-lifecycle.md — Theory lifecycle pattern
- **Created** patterns/debugging-ev.md — EV debugging guide

**Source:** Seeded from codebase exploration of `C:\Users\b8ste\Desktop\VB Software\value-betting-scanner\` + Claude memory files.

## 2026-04-08 — Core Mission Context

- **Updated** hot.md — Added core mission statement: identify +EV bets with long-term profitability confidence
- **Updated** wiki/devig-engine.md — Added "Why Each Sport and Market Is Different" section covering sport-specific sharpness, vig distribution by market type, interpolation sensitivity per stat, and implications for theories
- **Updated** wiki/theories.md — Added "Why One Theory Doesn't Fit All" section covering sport-level and market-level differences, plus the calibration frontier (key open questions for future theory iterations)

**Context:** Jay emphasized that the brain's primary value is carrying sport-specific and market-specific context for theories and devigging. Each sport is different, each market within a sport behaves differently. The brain prevents every session from rediscovering this.

## 2026-04-08 — Performance Tracking Research & Design

- **Created** wiki/performance-tracking.md — Comprehensive design doc for segmented performance analysis
- **Updated** index.md — Added Performance & Analytics section
- **Updated** hot.md — Added core principle: "track everything, filter later"

## 2026-04-08 — Integrated Scanner Repo Findings + GitHub Setup

- **Updated** CLAUDE.md — Added scanner repo docs relationship table, key doc references, deployment info
- **Updated** hot.md — Replaced generic items with findings from 1,000 pick CLV analysis: soft vs sharp CLV gap, sharp count as strongest predictor, high EV false positives, AU books outperforming Bet365, weight fallback bug, alt line Phase 1 status
- **Created** README.md — Collaborator onboarding guide
- **Created** .gitignore — Obsidian workspace files excluded
- **Pushed** to LCASH/vb-scanner-brain (private repo)

**Key research findings:**
- CLV converges ~100x faster than ROI (std dev 0.1 vs 1.0 per bet) — 50 bets for CLV signal vs 2000+ for ROI
- Brier score is diagnostic (devig calibration), not decision metric — reliability diagrams more actionable
- Industry standard: snapshot odds at first identification, line changes = new picks
- Odds decay from trail_entries is a unique competitive advantage no consumer tool surfaces
- For odds 1.5-2.0: 400 bets gives reliable CLV + hit rate, 2000+ for ROI confidence

## 2026-04-09 — Session Learnings Offload (P0-P4 fixes + operational findings)

- **Updated** hot.md — Moved 4 items to Resolved (sharp CLV wired, weight fallback fixed, API key mismatch fixed, dashboard P0-P3). Added 3 new Active items (player name matching 52% skip rate, null player_name bug, Bet365 2.0 missing picks)
- **Rewritten** wiki/resolver.md — Two CLV types, sharp CLV implementation, dead `nba_odds_history` infrastructure, resolution states, player name matching gap, multi-sport processing order, manual trigger, API key dependency
- **Updated** wiki/dashboard.md — Weight fallback bug fix, True odds column, sharp detail Over/Under, theory editor weight 0 default, corrected data flow, push command
- **Updated** wiki/deployment.md — Corrected VPS architecture (relay mode, systemd, 170.64.213.223:8802). Fixed sport ports (NRL 8801, AFL 8802). API key sync warning. Deploy script and health check endpoints
- **Updated** wiki/database.md — `sharp_clv_pct FLOAT` column, `016_sharp_clv.sql` migration, dead `nba_odds_history` note
- **Updated** wiki/tracker.md — Weight guard details (absent books = 0 not 1.0), DISABLE_TRACKER/DISABLE_RESOLVER env vars
- **Updated** wiki/theories.md — Weight key convention, `max_line_gap`/`line_gap_penalty` params, AltLine-V1 theory, weight bug cross-reference
- **Updated** wiki/performance-tracking.md — First sharp CLV data (+8.9% sharp vs +1.79% soft), trail data purpose for bet timing backtesting
- **Updated** patterns/debugging-ev.md — System health debugging: API key mismatch, resolver last_result misleading, manual resolution, VPS log commands, null player_name bug, Supabase I/O budget

**Key operational findings:**
- OpticOdds API key mismatch blocked all 4 sports' resolution for 12+ hours
- Sharp CLV confirms real edge: +8.9% sharp vs +1.79% soft
- Player name matching is biggest data loss: 52% skip rate
- Trail data enables backtesting optimal bet timing window
