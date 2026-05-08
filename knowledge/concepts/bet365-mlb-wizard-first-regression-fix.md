---
title: "bet365 MLB Wizard-First Architecture (G-ID Walk Regression Fix)"
aliases: [mlb-wizard-first, wizard-vs-gid-walk, mlb-wizard-refactor, gid-walk-regression, bb-wizard-mlb]
tags: [value-betting, bet365, mlb, scraping, architecture, performance]
sources:
  - "daily/lcash/2026-05-08.md"
created: 2026-05-08
updated: 2026-05-08
---

# bet365 MLB Wizard-First Architecture (G-ID Walk Regression Fix)

On 2026-05-08, lcash discovered that the MLB v4 scraper's 26-G-ID sequential walk was an **architectural regression** from the v1 scraper's single BB wizard endpoint (`/I99/`). The wizard returns ALL prop types (~268KB, 838-865 PAs, 9 prop types, 20 players) in a single fetch — identical to the NBA scraper's existing approach. Switching MLB back to wizard-first yielded **11x more props in 26x fewer requests** (865 PAs in 9.7s vs 76 PAs in 71.8s), eliminating the rate-limit cascade that plagued the G-ID walk entirely. The 26-G-ID walk had been added for "completeness" (CO/combo variants), but those markets have no sharp pair and produce zero +EV picks — the scanner was paying 26x the request budget for nothing.

## Key Points

- **v1's architecture was superior**: Single BB wizard fetch (`/I99/`) returns all MLB prop types in one response — the 26-G-ID walk was a regression, not an improvement
- **11x more props, 26x fewer requests**: 865 PAs in 9.7s (wizard) vs 76 PAs in 71.8s (26 G-ID walk) — wizard eliminates rate-limit cascade entirely
- **Rate-limit cascade eliminated**: G-ID walk with `GID_PARALLELISM=2` triggered bet365 soft-blocking (only 10/26 G-IDs returned bodies); wizard needs exactly 1 request
- **CO/combo markets were worthless**: The 26 G-IDs included 8 CO/combo markets (Home Runs CO, Bases CO, etc.) with no OpticOdds sharp equivalent — they can never be devigged and produce zero +EV picks
- **Critical `_refresh_loop` bug caught**: After refactoring `add_game()` to wizard, `_refresh_loop` was still using the old 26-G-ID walk — caused 364 requests/min instead of 14; extracted `_fetch_wizard_for_game()` as shared helper
- **Old walk functions retained for instant rollback**: One-block switch in `add_game` to revert if wizard path breaks in production

## Details

### The Regression Discovery

The investigation started from a different angle: lcash was benchmarking parallelism configurations for the 26-G-ID walk (`GID_PARALLELISM=4` caused rate-limiting, dropping to 2 with 0s decoy wait achieved 76 PAs in 71.8s). The user then asked about the historical v1 approach (`bet365_mlb_game_v1.py`), which revealed that v1 used a single BB wizard endpoint returning all props in one fetch — the same endpoint NBA already uses successfully.

The 26-G-ID walk was introduced during the v2→v3→v4 evolution for "completeness" — to capture CO milestone variants (e.g., "3+ Hits" threshold format) and combo markets that the wizard might not include. However, a prop type mapping audit had already confirmed that 8 of the 26 G-IDs were CO/combo markets with no OpticOdds equivalent. These can never be paired with sharp books for devigging and therefore can never produce +EV picks. The remaining 18 G-IDs returned data that was a subset of what the wizard provides in a single response.

### Performance Comparison

| Metric | 26-G-ID Walk | BB Wizard (I99) |
|--------|-------------|-----------------|
| Requests per game | 26 navigations | 1 fetch |
| PAs per game | 76 (rate-limited) | 838-865 |
| Time per game | 71.8s | 9.7s |
| Prop types | 9 (plus 8 worthless CO) | 9 (all useful) |
| Rate-limit risk | High (triggers soft-blocking at 4+ parallel) | Zero (single request) |
| Alt lines | Partial (per-G-ID) | Full (threshold ladders included free) |

The wizard endpoint (`betbuilderpregamecontentapi/wizard`) returns the complete player prop surface in approximately 268KB — all prop types, all players, including full threshold ladder alt lines. This is architecturally identical to NBA's wizard approach documented in [[concepts/bet365-nba-bb-wizard-v3-rewrite]].

### The _refresh_loop Bug

A critical bug was caught during deployment: after refactoring `add_game()` to use the wizard, `_refresh_loop` was still calling the old 26-G-ID walk function. This meant initial game population used 1 request (wizard) but every subsequent refresh used 26 (walk) — producing 364 requests/min per refresh cycle instead of the expected 14.

The fix extracted `_fetch_wizard_for_game()` as a shared helper function used by both `add_game()` and `_refresh_loop()`, ensuring a single source of truth for the data-fetch pattern. This follows a general principle: when refactoring a data-fetch pattern, audit ALL callers, not just the initial load path.

### Context-Level Init Script Bot Detection

During the G-ID walk optimization phase (before discovering the wizard approach), lcash identified `ctx.add_init_script(INTERCEPTOR_JS)` as a bot detection vector. The context-level script injection applied the WebSocket wrapper + `window.__wsObjs`/`__lastSent` globals to ALL tabs including walk tabs, making them trivially fingerprintable via `WebSocket.toString()`. The fix scoped injection to page-level (`self._page.add_init_script`) instead of context-level, so walk tabs spawn without bot fingerprints. See [[concepts/context-level-init-script-bot-fingerprint]] for the full analysis.

### Broader Lesson: Newer Isn't Always Better

The v1→v4 evolution added complexity (26 G-IDs, parallel walk, rate-limit mitigation) to solve a problem that didn't exist. The wizard endpoint was always available and always returned more data than the walk. The architectural regression happened because each version built on the previous version's assumptions rather than re-evaluating the fundamental approach. This is a concrete example of accidental complexity: the 26-G-ID walk was solving for "what if the wizard misses some markets?" without validating whether it actually did.

## Related Concepts

- [[concepts/bet365-nba-bb-wizard-v3-rewrite]] - NBA already used wizard-first architecture; MLB wizard refactor brings parity
- [[concepts/bet365-mlb-hash-nav-mg-fetching]] - The 26 G-ID hash-nav approach that the wizard replaces; retained as fallback code
- [[concepts/bet365-mlb-batch-api-co-format]] - CO segment format that motivated the G-ID walk; confirmed as zero-value (no sharp pairs)
- [[concepts/co-milestone-one-sided-pairing-imbalance]] - CO markets can never be devigged; the G-ID walk's "completeness" was illusory
- [[concepts/mlb-parallel-scraper-workers]] - The MLB scraper evolution history; wizard-first is the latest (and simplest) architecture
- [[connections/anti-scraping-driven-architecture]] - bet365 rate-limits concurrent navigations; wizard avoids the problem entirely with 1 request

## Sources

- [[daily/lcash/2026-05-08.md]] - v1 BB wizard endpoint discovered returning 838 PAs (9 prop types, 20 players) in single fetch; 26-G-ID walk confirmed as architectural regression from v1; wizard yields 11x more props in 26x fewer requests (865 PAs/9.7s vs 76/71.8s); `_refresh_loop` still using old walk after `add_game` refactor caused 364 req/min — extracted `_fetch_wizard_for_game()` shared helper; old walk functions retained for rollback; context-level init_script identified as bot fingerprint vector (Sessions 15:07, 15:38). GID_PARALLELISM=4 triggered rate-limiting (10/26 G-IDs returned bodies); GID_PARALLELISM=2 + page-level inject = 76 PAs in 71.8s (best G-ID walk config) — still 11x worse than wizard (Session 13:56, 14:29). Full production test: 5,313 markets, 488 pulse, 25 +EV picks flowing after wizard refactor (Session 15:38)
