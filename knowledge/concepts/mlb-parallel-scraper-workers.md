---
title: "MLB Parallel Scraper Workers"
aliases: [parallel-scraper, mlb-parallel-workers, parallel-chrome, n-workers]
tags: [value-betting, mlb, scraping, architecture, performance]
sources:
  - "daily/lcash/2026-04-21.md"
  - "daily/lcash/2026-04-22.md"
created: 2026-04-21
updated: 2026-04-22
---

# MLB Parallel Scraper Workers

The bet365 MLB game scraper was redesigned from a sequential single-page model to a parallel multi-worker architecture to reduce per-game refresh time. Sequential scraping required ~9-12 minutes per full rotation across all games — unacceptable for a system where odds staleness directly impacts EV calculation accuracy. The parallel architecture uses `N_WORKERS = 3` Chrome browser pages scraping concurrently, with round-robin game distribution and a 30-minute rediscovery loop, reducing effective per-game update time to ~1.5-3 minutes.

## Key Points

- Sequential MLB scraping took ~9-12 minutes per full rotation — each game requires navigating to the game page, expanding markets, and capturing the batch API response
- Parallel architecture uses 3 Chrome workers (browser pages) scraping concurrently via round-robin game distribution
- `N_WORKERS = 3` balances speed vs Chrome memory/detection risk — Dell mini PC has 7.2 GB free RAM, comfortably handles 3 workers
- Rediscovery loop runs every 30 minutes to detect new games and redistribute across workers dynamically
- This contrasts with the NBA scraper, which uses the BB wizard endpoint (no DOM rendering needed) and refreshes all games instantly via a single API call

## Details

### The Sequential Bottleneck

The MLB scraper's navigation flow requires visiting each game individually: click the game in the sidebar → wait for the game page to render → click the Batter/Pitcher Props tab → expand market sections → capture the `batchmatchbettingcontentapi` response via CDP interception → navigate back to the game list → repeat for the next game. Each game takes approximately 30-60 seconds including navigation, rendering, and response capture. With 8-15 MLB games per day, a full rotation takes 9-12 minutes.

This is fundamentally different from the NBA scraper's architecture. The NBA scraper uses bet365's BB wizard endpoint, which returns all player prop data in a single HTTP response without requiring DOM rendering or page-level navigation. The MLB scraper cannot use the BB wizard endpoint because bet365 moved MLB props to the batch API format that requires page-level interaction (see [[concepts/bet365-mlb-batch-api-co-format]]).

### Parallel Worker Design

The parallel architecture spawns multiple browser pages (tabs) within a single Chrome instance. Each worker page independently navigates to its assigned games and captures data. Games are distributed via round-robin: if there are 9 games and 3 workers, worker 1 handles games 1/4/7, worker 2 handles 2/5/8, and worker 3 handles 3/6/9. This ensures even load distribution regardless of game count.

The choice of `N_WORKERS = 3` was calibrated against the Dell mini PC's resources. Each Chrome page consumes approximately 200-400 MB of RAM for a bet365 game page. With 7.2 GB free RAM, 3 workers consume ~600-1200 MB — well within capacity. More workers would increase detection risk (multiple rapid navigations from the same Chrome session may trigger bet365's behavioral anti-bot systems) without proportional speed gains due to Chrome's internal resource contention.

### Rediscovery Loop

A separate 30-minute loop checks for newly posted games. MLB game availability changes throughout the day — bet365 publishes props a few hours before first pitch, so games appearing in the afternoon weren't available during morning startup. The rediscovery loop calls the game list endpoint, compares against currently tracked games, and redistributes the full game set across workers. This is the same rediscovery pattern used by the NBA scraper but adapted for the parallel worker model.

### Market Expansion Gap

During initial deployment, the mini PC showed significantly lower odds capture than local testing: 208-216 odds per game vs 700+ locally. This is likely a Chrome profile/cache maturity issue — the mini PC's Chrome profile may need more cached SPA assets and session state to match the local environment's performance. Batter Props market expansion (clicking to reveal individual market odds) worked more reliably on a mature Chrome profile with cached bet365 SPA state. The gap requires further investigation during tomorrow's pre-game slate.

### Overnight Production Validation (2026-04-22)

On 2026-04-22, overnight results confirmed the parallel architecture is production-stable: **6,669 odds across 12 prop types from 13-14 of 15 games**, with workers producing 500-850+ odds per game. The Dodgers@SF game hit the high-water mark at 851 odds, 16 markets expanded, 168KB of data. No crashes, no memory issues, workers cycled correctly through the rotation.

The worker count scales dynamically with `min(N_WORKERS, len(game_list))`, capped at `N_WORKERS = 3`. The Dell mini PC handled 3 Chrome tabs plus all other servers comfortably with 7.2 GB RAM free.

However, the market expansion gap persists on the mini PC: 0-7 markets expanded vs 15-17 locally. The production Dodgers@SF result (16 markets, 851 odds) is an outlier — most games on the mini PC expand significantly fewer markets. Chrome profile/SPA cache build-up may help over time, but the gap remains under investigation.

## Related Concepts

- [[concepts/bet365-mlb-batch-api-co-format]] - The batch API format that the parallel workers scrape; each worker captures the full batch response per game
- [[concepts/bet365-mlb-lazy-subscribe-migration]] - The broader MLB scraper evolution history that led to the current architecture
- [[concepts/game-scraper-chrome-crash-recovery]] - Chrome crash auto-recovery applies to each parallel worker; a crashed worker can be restarted independently
- [[connections/browser-automation-reliability-cost]] - More Chrome workers means more crash-recovery overhead; 3 workers × 14 restarts/day baseline = significant operational complexity
- [[concepts/bet365-headless-detection]] - All workers must run in headed mode; cannot use headless Chrome for parallel workers

## Sources

- [[daily/lcash/2026-04-21.md]] - Sequential MLB scraping ~9-12 min per rotation too slow; parallel worker architecture with N_WORKERS=3, round-robin distribution, 30-min rediscovery; Dell has 7.2 GB free RAM; NBA scraper doesn't need this because BB wizard endpoint returns all data in single call (Session 17:12). Market expansion gap: 208-216 odds on mini PC vs 700+ locally, likely Chrome profile maturity issue (Session 17:12). First deployment: 2,468 odds from 3 games on first check (Session 12:36)
- [[daily/lcash/2026-04-22.md]] - Overnight validation confirmed: 6,669 odds, 12 prop types, 13-14/15 games; workers 500-850+ odds/game; Dodgers@SF peak at 851 odds/16 markets/168KB; no crashes, no memory issues; dynamic scaling `min(N_WORKERS, len(game_list))`; market expansion gap persists (0-7 vs 15-17 local) (Session 08:48)
