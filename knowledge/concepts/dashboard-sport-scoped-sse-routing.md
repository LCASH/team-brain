---
title: "Dashboard Sport-Scoped SSE and Pathname Routing"
aliases: [sport-scoped-sse, sport-routing-fix, pathname-sport-detection, thin-trail-empty-state, sport-sse-reconnect]
tags: [value-betting, dashboard, architecture, sse, routing, ux]
sources:
  - "daily/lcash/2026-05-09.md"
  - "daily/lcash/2026-05-10.md"
created: 2026-05-09
updated: 2026-05-12
---

# Dashboard Sport-Scoped SSE and Pathname Routing

Two related dashboard fixes on 2026-05-09: (1) sport-scoped SSE streaming that only sends markets for the active sport (reducing payload size from 9 MB all-sports to sport-filtered), and (2) a sport routing fix that reads `window.location.pathname` against `SPORT_INSTANCES` instead of hardcoding `currentSport = 'nba'` for non-localhost environments. Additionally, a thin-trail-data empty state was added for picks with only a single snapshot (<30s timestamp span), which affects ~5% of picks.

## Key Points

- **Sport routing bug**: Non-localhost paths hardcoded `currentSport = 'nba'` — navigating to `/mlb` still loaded NBA picks because the sport was never read from the URL
- **Fix**: Read `window.location.pathname` and match against `SPORT_INSTANCES` (mapping path segments to sport keys) to determine active sport
- **Sport-scoped SSE**: Only stream markets for the active sport instead of all sports — reduces SSE snapshot size from 9 MB to sport-specific subset
- **SSE reconnection required on sport switch**: `switchSport` must tear down and reconnect SSE (not just re-render) because sport-scoped streams need a new subscription
- **Stale cross-sport markets**: When SSE becomes sport-scoped, switching sports must clear stale markets from the previous sport's stream before connecting the new one
- **Thin trail data (~5% of picks)**: Picks with only 1 trail snapshot (timestamp span < 30s) show an explainer message instead of a near-empty canvas — edge case that made the trail chart look completely broken

## Details

### The Sport Routing Bug

The V3 dashboard serves multiple sports on separate URL paths (`/nba`, `/mlb`, etc.) but the JavaScript initialization hardcoded `currentSport = 'nba'` when running on non-localhost origins. This meant that navigating to `http://170.64.213.223:8803/mlb` rendered the page with MLB branding but loaded NBA data — the sport variable controlling data fetching and EV computation was never set from the URL.

The fix parses `window.location.pathname` on page load and matches it against a `SPORT_INSTANCES` mapping (e.g., `"/mlb" → "mlb"`, `"/nba" → "nba"`). This is a one-time initialization — the sport doesn't change during a session without a page navigation.

### Sport-Scoped SSE

Previously, the SSE stream delivered all markets across all sports in a single snapshot. With the full V3 pipeline streaming NBA + MLB + OpticOdds, this produced 6–9 MB payloads (see [[concepts/sse-display-tracking-market-separation]] for the historical context of SSE payload management). Sport-scoping reduces the per-connection payload to only the markets relevant to the currently viewed sport.

The architectural implication is that `switchSport` can no longer just re-render the existing market state — it must:

1. Close the current SSE connection
2. Clear stale markets from the previous sport (markets from the old sport are no longer refreshed and would appear with growing staleness)
3. Open a new SSE connection with the sport parameter
4. Wait for the initial snapshot before rendering

This adds a brief loading state on sport switch (the SSE cold start) but prevents the 9 MB all-sport payload that caused browser parsing delays documented in earlier sessions.

### Thin Trail Data UX

Investigation of the trail chart feature revealed that approximately 5% of picks have only a single trail snapshot — the initial detection with no subsequent odds movement recorded. When plotted on a chart, a single data point renders as a near-empty canvas with a single dot, which looks like a broken chart rather than a legitimate "no movement" state.

The fix detects when the trail timestamp span is less than 30 seconds (indicating a single snapshot or a cluster of snapshots taken within the same poll cycle) and shows an explainer text with the snapshot count and first-seen timestamp instead of rendering the canvas. This distinguishes "chart is broken" from "there's simply no odds movement to show" for the ~5% of picks that fall into this category.

The specific rendering failure mechanism was identified on 2026-05-10: when a pick has only one trail entry, `tMin === tMax` (the minimum and maximum timestamps are identical), which causes all x-coordinate calculations to produce `NaN` or collapse to a single point. The canvas renders but appears completely empty — no lines, no dots, no axes — because every data point maps to the same x-coordinate. This is distinct from "no trail data" (where the fetch returns empty and the chart doesn't render at all) — the single-snapshot case renders a broken-looking chart that appears to be a bug.

This edge case was particularly confusing during debugging because it made the entire trail chart feature appear non-functional — the first several picks tested all happened to have only 1 snapshot, creating a false impression of a systemic bug rather than a data sparsity edge case. An additional debugging red herring on 2026-05-10: `_trailChartCache` was declared as `const` in a function scope, making it inaccessible via `window._trailChartCache` in the browser console — leading to a false conclusion that the cache was empty when it was actually populated but invisible to console probes. See [[concepts/trail-change-detection-architecture]] for why some picks have minimal trail data (change-only recording + newly created picks + illiquid props).

### Browser Fetch Queue Contention

During debugging, a secondary finding was that browser fetch queue contention from polling requests (`nba_tracked_picks`, `scanner_taken_bets`) could delay the trail data fetch by 20+ seconds. The dashboard runs multiple periodic fetches, and when several fire simultaneously, the browser queues them. The trail chart's on-demand fetch (triggered by user click) enters the back of the queue behind scheduled polls, creating a perceived delay in chart rendering that is actually a fetch scheduling issue.

## Related Concepts

- [[concepts/sse-display-tracking-market-separation]] - The original SSE payload management pattern (display vs tracking markets); sport-scoped SSE is a further refinement that filters by sport at the connection level
- [[concepts/v3-dashboard-ev-computation-architecture]] - The V3 dashboard architecture where sport routing determines which markets the DeVig engine evaluates
- [[concepts/trail-change-detection-architecture]] - Change-only trail recording explains why ~5% of picks have only 1 snapshot; the thin-trail UX handles this edge case
- [[concepts/vps-proxy-byte-cache-optimization]] - The byte cache deployed in the same session; sport-scoped SSE reduces the payload that the cache must store
- [[concepts/dashboard-client-server-ev-divergence]] - The sport routing bug is a 10th documented manifestation of dashboard display issues — loading the wrong sport's data due to hardcoded initialization

## Sources

- [[daily/lcash/2026-05-09.md]] - Sport-scoped SSE requires reconnection on sport switch + clearing stale cross-sport markets; 2s TTL cache balances freshness with performance; `switchSport` must tear down SSE (Session 11:15). Sport routing: read `window.location.pathname` matching against `SPORT_INSTANCES` instead of hardcoded `currentSport = 'nba'`; thin-trail empty state for picks with timestamp span < 30s (Session 13:30). ~5% of picks have only 1 trail snapshot; browser fetch queue contention from polling delayed trail fetch 20+ seconds; `const` variables in JS closures not accessible via `window.varName` wasted debug time (Session 13:30)
- [[daily/lcash/2026-05-10.md]] - Trail chart "click does nothing" traced to two separate issues: sport-routing showing wrong sport's picks, and `tMin === tMax` x-coordinate collapse for thin-data picks; `_trailChartCache` const-scope debugging red herring; Supabase fetches confirmed fine (200 OK, 0.7s) — apparent slowness was fetch queue contention from aggressive polling; three commits shipped: `c0cdbc6` (sport routing + thin-trail), `a269c43` (sport-scoped SSE/polling + byte cache), `f927e1e` (single-flight dedup) (Session 14:34)
