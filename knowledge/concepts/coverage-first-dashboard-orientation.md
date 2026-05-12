---
title: "Coverage-First Dashboard Orientation"
aliases: [coverage-dashboard, coverage-first, coverage-html, per-book-footprint, ev-name-map-gaps]
tags: [value-betting, dashboard, architecture, coverage, observability, bet365]
sources:
  - "daily/lcash/2026-05-12.md"
created: 2026-05-12
updated: 2026-05-12
---

# Coverage-First Dashboard Orientation

The dashboard goal pivoted from edge-first (showing +EV picks) to coverage-first — understanding which markets each sportsbook covers and where gaps exist before optimizing for edge. A dedicated `coverage.html` dashboard was built and served from Eve at `/dashboard/coverage.html` via a new generic static-file route in `server.py`, featuring a KPI strip, per-book footprint bars, coverage-first presets, and a matrix heatmap. The audit revealed bet365 is the widest-coverage book at 59.7% while Pinnacle covers only ~2% (missing player props). Of 26 NBA player prop markets available in bet365's wizard, only 15 are collected — the remaining 13 are present in the wizard body but not keyed into `EV_NAME_MAP`, each a one-liner to add.

## Key Points

- Dashboard pivot from edge-first to coverage-first: KPI strip, per-book footprint bars, coverage-first presets, matrix heatmap — understanding market coverage before optimizing edge
- Bet365 is the widest-coverage book at 59.7%; Pinnacle only ~2% (missing player props) — coverage gaps are the primary constraint on pick volume
- VPS state is NOT equal to Eve state — VPS has ~195 markets vs Eve's ~10k; Eve is the canonical data source for coverage analysis
- Of 26 NBA player prop markets in bet365 wizard, 15 collected, 13 missing from `EV_NAME_MAP` (1Q props, Points High/Low, FG Made/Attempted, Threes Attempted) — each is a one-liner to add
- `_bet365_push_loop` overwrites `captured_at` with `time.time()` every 5 seconds regardless of whether wizard data actually refreshed — makes the 300-second staleness gate a permanent no-op

## Details

### Coverage Dashboard Architecture

The coverage dashboard (`coverage.html`) is served from Eve's HTTP server via a new generic static-file route added to `server.py`. This route pattern allows any HTML file placed in the dashboard directory to be served without adding endpoint-specific code — a deliberate architectural choice to enable rapid iteration on diagnostic views.

The dashboard features four main visualization components:

1. **KPI strip**: Top-level metrics showing total markets, total books, average coverage percentage, and market freshness
2. **Per-book footprint bars**: Horizontal bar chart showing each sportsbook's coverage as a percentage of all known markets, making it immediately visible that bet365 dominates at 59.7% while Pinnacle's ~2% player prop coverage is a structural limitation
3. **Coverage-first presets**: Filter presets oriented around coverage questions ("Which books cover NBA Points?", "What markets does bet365 miss?") rather than the previous edge-first presets ("Show me +5% EV picks")
4. **Matrix heatmap**: Book-by-market-type grid with color intensity showing coverage depth, revealing systematic gaps (e.g., no book covers 1Q props, FG Made/Attempted universally missing)

### VPS vs Eve State Divergence

A critical finding from the coverage audit: VPS state and Eve state are fundamentally different data sets. The VPS maintains approximately 195 markets — a filtered, cached subset used for the real-time dashboard SSE stream. Eve maintains approximately 10,000 markets — the complete canonical state from all scrapers. Coverage analysis must use Eve's state as the source of truth, not VPS, since VPS's filtering (staleness gates, sport routing, theory filtering) hides the majority of the market universe.

### EV_NAME_MAP Coverage Gaps

An audit of all 26 NBA player prop markets available in bet365's wizard revealed that 15 are currently collected and mapped through `EV_NAME_MAP`, while 13 are present in the wizard's response body but not keyed into the mapping. The missing markets include:

- First quarter (1Q) variants of standard props
- Points High/Low
- Field Goals Made and Attempted
- Three-Pointers Attempted

Each missing market requires only a one-liner addition to `EV_NAME_MAP` to begin collection — the data is already flowing through the bet365 WebSocket connection, it is simply being ignored at the parsing layer. This represents a low-effort, high-impact coverage expansion.

### Captured_at Staleness Bug

The `_bet365_push_loop` function overwrites `captured_at` with `time.time()` every 5 seconds regardless of whether the underlying wizard data has actually refreshed. This means the 300-second staleness gate — designed to filter out markets where odds have not been updated recently — is a permanent no-op for bet365 data. Every market always appears "fresh" because the push loop rewrites the timestamp on each iteration, even when the wizard page has not re-rendered with new data.

The architectural direction to address this is per-(soft book x market) asynchronous time series instead of one global fresh state. Each market would track its own last-actual-change timestamp independently, rather than inheriting a global `captured_at` from the push loop's heartbeat cycle.

### Restarting v3 Operational Cost

A related operational finding: restarting the v3 scanner clears all AdsPower Chrome sessions. The login flow for each sport blocks for approximately 5 minutes, meaning a full restart with 3 sports configured incurs ~15 minutes of downtime. This high restart cost reinforces the importance of the hot-reload and graceful-restart patterns over full process restarts for configuration changes.

## Related Concepts

- [[concepts/v3-dashboard-ev-computation-architecture]] - The V3 dashboard's EV computation pipeline that the coverage dashboard complements; edge-first views depend on coverage-first data completeness
- [[concepts/odds-staleness-pipeline-diagnosis]] - The `captured_at` overwrite bug in `_bet365_push_loop` is a new instance of the staleness pipeline issues diagnosed earlier; the 300s gate being a no-op means stale odds pass through unchecked

## Sources

- [[daily/lcash/2026-05-12.md]] - Dashboard pivot to coverage-first with KPI strip, per-book footprint bars, presets, matrix heatmap; `coverage.html` served from Eve via generic static-file route; bet365 widest at 59.7%, Pinnacle ~2%; VPS ~195 markets vs Eve ~10k; 15/26 NBA bet365 wizard props collected, 13 missing from EV_NAME_MAP (one-liner each); `_bet365_push_loop` overwrites `captured_at` every 5s making 300s staleness gate no-op; restarting v3 clears AdsPower sessions, ~5 min login per sport (Sessions 09:42, 11:03)
