---
title: "bet365 MLB Lazy-Subscribe API Migration"
aliases: [mlb-api-migration, bb-wizard-to-lazy-subscribe, bet365-mlb-v3, lazy-subscribe]
tags: [bet365, mlb, scraping, api-migration, value-betting]
sources:
  - "daily/lcash/2026-04-14.md"
created: 2026-04-14
updated: 2026-04-14
---

# bet365 MLB Lazy-Subscribe API Migration

bet365 migrated MLB player props from the `betbuilderpregamecontentapi/wizard` endpoint (v1, shared with NBA) to a lazy-subscribe `matchbettingcontentapi` model (v2) around April 8, 2026. The v2 migration silently broke three critical behaviors in the MLB game scraper: tab clicking, scroll-triggered lazy loading, and largest-response retention. A v3 hybrid was built merging v1's UI interaction triggers with v2's parser.

## Key Points

- **Sport-specific migration:** NBA player props still work on the BB wizard endpoint; only MLB props were moved to the lazy-subscribe model
- **v2 (Apr 8, commit `9d3eee4` area) silently broke 3 behaviors:** tab clicking (`_click_sgm_tab()`), scroll-triggered lazy loading via intersection observers, and keeping the largest HTTP response
- **Hash navigation alone doesn't trigger bet365's UI JS routing** — real DOM tab clicks are needed to fire WS subscription messages for prop markets
- **bet365 uses intersection observers** that require scroll events to fire lazy-load subscriptions for off-viewport markets
- **v3 hybrid approach:** always click tab + scroll + keep largest response, re-enabling UI-triggered subscription flow while using v2's parser
- **WS frame capture experiment failed** — the shared WS channel carries cross-sport noise (esoccer, tennis), not MLB-specific prop data

## Details

### The Migration

The bet365 MLB game scraper originally used the same `betbuilderpregamecontentapi/wizard` endpoint that the NBA scraper uses successfully. This "BB wizard" endpoint returns player prop data in a single HTTP response when the correct game page is navigated to. Around April 8, 2026, bet365 changed the MLB player props to a lazy-subscribe model: prop data is no longer returned in a single HTTP response but is instead loaded incrementally via WebSocket subscriptions triggered by UI interactions (clicking the Same Game Multi tab, scrolling through market sections).

Git archaeology (commit `9d3eee4`) confirmed the v1 scraper had `_click_sgm_tab()` and scroll interaction methods that the v2 rewrite dropped in favor of hash-navigation-only fetching. The v2 approach worked for the main match odds but failed for player props because the lazy-subscribe endpoint requires actual UI events.

### Why v2 Broke

The v2 migration made three specific cuts that turned out to be critical:

1. **Tab clicking removed:** v2 used hash navigation to reach game pages, but bet365's lazy-subscribe model requires a real DOM click on the SGM (Same Game Multi) tab to trigger the WS subscription that requests player prop data. Hash navigation changes the URL but does not fire the SPA's internal click handlers.

2. **Scroll triggers removed:** bet365 uses intersection observer APIs on its prop market sections. Off-viewport markets are not loaded until the user scrolls them into view — the intersection observer fires a WS subscription for each newly-visible section. Without scroll events, only above-the-fold markets load.

3. **Largest-response retention removed:** v1 kept the largest HTTP response seen during a game page visit, which naturally selected the response containing the most prop data. v2 used only the response from the initial hash navigation, which in the lazy-subscribe model contains only match-level odds, not player props.

### The v3 Hybrid

The v3 approach merges v1's interaction strategy with v2's parser:

- Navigate to the game page via hash navigation (from v2)
- Click the SGM/player props tab (from v1's `_click_sgm_tab()`)
- Scroll through the page to trigger intersection observers (from v1)
- Capture all HTTP responses during the interaction window
- Keep the largest response (from v1's strategy — the largest response is most likely to contain the full prop payload)
- Parse the response using v2's parser (which handles the current response format)

v1 was first tested in isolation as `bet365_mlb_game_v1.py` before modifying production code — a safe parallel-test pattern that confirmed the click/scroll behaviors were still effective.

### WebSocket Noise

An initial attempt to capture MLB prop data via WebSocket frame dumps was abandoned. The shared WS channel carries cross-sport data (esoccer, tennis results, etc.) with no MLB-specific prop content visible in a 10-second capture window. The WS lazy-subscribe messages for MLB props are triggered by UI interaction and appear on specific subscription topics, not as ambient traffic — confirming that the UI interaction path is required.

### Cross-Sport Risk

This migration is sport-specific: NBA player props continue to work on the BB wizard endpoint as of April 14, 2026. However, there is a risk that bet365 will apply the same lazy-subscribe migration to NBA, which would break the NBA game scraper in the same way. Monitoring for this regression is recommended.

## Related Concepts

- [[concepts/bet365-racing-adapter-architecture]] - A different bet365 scraper facing similar SPA interaction challenges
- [[concepts/spa-navigation-state-api-access]] - The broader SPA navigation constraints that affect all bet365 scrapers
- [[concepts/betstamp-bet365-scraper-migration]] - The Bet365 game scraper ecosystem where this MLB adapter operates
- [[concepts/value-betting-operational-assessment]] - Browser scraping fragility (weakness #5) exemplified by this migration

## Sources

- [[daily/lcash/2026-04-14.md]] - WS frame dumps showed cross-sport noise not MLB props; git archaeology confirmed v1 had click/scroll triggers dropped in v2; v3 hybrid built merging v1 interactions with v2 parser; bet365 uses intersection observers for lazy-load; NBA still on BB wizard (Session 10:44)
