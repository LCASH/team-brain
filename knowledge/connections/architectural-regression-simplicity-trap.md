---
title: "Connection: Architectural Regression and the Simplicity Trap"
connects:
  - "concepts/bet365-mlb-wizard-first-regression-fix"
  - "concepts/bet365-mlb-hash-nav-mg-fetching"
  - "concepts/bet365-mlb-lazy-subscribe-migration"
  - "concepts/mlb-parallel-scraper-workers"
sources:
  - "daily/lcash/2026-05-08.md"
created: 2026-05-08
updated: 2026-05-08
---

# Connection: Architectural Regression and the Simplicity Trap

## The Connection

The MLB scraper's evolution from v1 (single wizard fetch, 838 PAs) through v2-v4 (26-G-ID walk, 76 PAs) and back to wizard-first (865 PAs) reveals a general anti-pattern: iterative "improvements" added complexity to solve problems that didn't exist, producing a system that was 11x worse than its original design. Each version was built on the previous version's assumptions rather than re-evaluating the fundamental approach.

## Key Insight

The non-obvious insight is that **architectural regression can be introduced by well-intentioned "completeness" additions.** The 26-G-ID walk wasn't added because the wizard was broken — it was added because someone noticed that CO/combo variant markets existed in the bet365 API and wanted to capture them. The completeness instinct ("what if we're missing data?") drove the addition of 25 extra HTTP navigations per game without validating whether the additional data had any value in the devigging pipeline.

The value analysis reveals the trap: 8 of the 26 G-IDs returned CO/combo markets that have no OpticOdds sharp equivalent and therefore can never be devigged. They produce zero +EV picks. The scanner was executing 26x the request budget for markets that were architecturally guaranteed to be worthless.

| Version | Approach | PAs | Requests | Value |
|---------|----------|-----|----------|-------|
| v1 | Single wizard | 838 | 1 | All deviggable |
| v2 | Lazy-subscribe + clicks | ~400 | 5-10 | Mixed |
| v3 | 26-G-ID hash-nav walk | 76 (rate-limited) | 26 | 8/26 worthless |
| **v4 (wizard-first)** | **Single wizard** | **865** | **1** | **All deviggable** |

The regression wasn't visible at any individual step. Each version was a reasonable evolution from its predecessor: v2 adapted to bet365's API migration, v3 optimized v2's click-heavy approach with URL-based navigation, and v4's G-ID walk captured previously-uncapturable CO markets. Only comparing v4 directly against v1 revealed that the net effect of three versions of "improvement" was an 11x reduction in useful output and a 26x increase in request cost.

## Evidence

On 2026-05-08, lcash investigated the v1 scraper (`bet365_mlb_game_v1.py`) in response to a user question about historical approaches. The v1 code used a single BB wizard endpoint (`/I99/`) — identical to the NBA scraper's existing architecture. A proof-of-concept returned 838 PAs (9 prop types, 20 players) in a single 268KB response, versus the v4 G-ID walk's 76 PAs across 26 requests (rate-limited down from the theoretical maximum).

The `_refresh_loop` bug compounded the regression: after refactoring `add_game()` to wizard, `_refresh_loop` was still using the old 26-G-ID walk — meaning the initial population used 1 request but every subsequent refresh used 26. This produced 364 requests/min instead of 14, and was only caught because the developer audited all callers of the data-fetch pattern.

## The General Anti-Pattern

This maps to a broader software engineering pattern:

1. **v1 works well** — simple, correct, sufficient
2. **v2 "improves" v1** — adds complexity to handle an edge case or new requirement
3. **v3 "improves" v2** — adds complexity to fix v2's performance issues
4. **v4 "improves" v3** — adds complexity to handle v3's new failure modes
5. **Someone compares v4 to v1** — realizes v1 was better along every dimension that matters

The prevention is to periodically re-evaluate the fundamental approach against current requirements, not just iterate on the previous version. In this case, asking "does the wizard endpoint still work for MLB?" at any point during v2-v4 development would have short-circuited the entire regression.

## Related Concepts

- [[concepts/bet365-mlb-wizard-first-regression-fix]] - The specific regression discovery and fix; wizard-first restores v1's simplicity at v4's integration quality
- [[concepts/bet365-mlb-hash-nav-mg-fetching]] - The v3 26-G-ID approach that was the peak of complexity; architecturally clever but 11x worse in practice
- [[concepts/bet365-mlb-lazy-subscribe-migration]] - The v1→v2→v3→v4 evolution history that produced the regression
- [[concepts/mlb-parallel-scraper-workers]] - The MLB scraper's full architectural evolution; wizard-first is the endpoint
- [[concepts/co-milestone-one-sided-pairing-imbalance]] - CO markets that motivated the G-ID walk have no sharp pairs; the "completeness" motivation was based on worthless data
