---
title: "SSE Display vs Tracking Market Separation"
aliases: [sse-payload-bloat, display-vs-tracking, sse-market-separation, pinnacle-poller-split]
tags: [value-betting, architecture, performance, dashboard, sse]
sources:
  - "daily/lcash/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# SSE Display vs Tracking Market Separation

Adding game-line markets (moneyline, run_line, total_runs) to the mini PC's core sport pollers caused the SSE payload to balloon from ~2MB to 6-9MB, causing browser parsing delays of 20-30 seconds and effective timeouts on dashboard load. The fix separates "display markets" (SSE-pushed, all books, player props) from "tracking-only markets" (state-only, restricted book set, game lines) — a permanent architectural pattern for managing payload size as market coverage expands.

## Key Points

- SSE payloads above ~5MB cause browser parsing delays of 20-30 seconds; at 6-9MB the dashboard effectively times out on load
- Root cause was multiplicative expansion: adding game-line markets to MLB pulled odds across all 52 books, ballooning MLB alone from ~2K to 5,040 markets
- Fix: revert game-line markets from mini PC sport configs (stays on player props only); add separate VPS-side Pinnacle pollers with a restricted 7-book set (Pinnacle + prediction markets)
- SSE push is disabled for ALL Pinnacle pollers (niche leagues AND core game lines) — they write to state for the tracker but never enter the SSE stream
- Pinnacle pill on the dashboard shows: (1) client-side computed picks from SSE player-prop data, (2) server-tracked picks from Supabase for niche leagues and game lines

## Details

### The Multiplicative Expansion Problem

When Pinnacle game-line markets (moneyline, run_line, total_runs) were added to the core sport pollers on the mini PC (NBA, MLB, NHL), each new market type was pulled across all configured books — not just the 7 books relevant to the Pinnacle strategy (Pinnacle + 6 prediction market platforms), but all 52 soft books in the poller's book set. MLB alone went from approximately 2,000 player-prop markets to 5,040 total markets. Across all three sports, the combined SSE payload grew to 6-9MB.

The SSE (Server-Sent Events) protocol delivers the full odds state to the browser on initial connection. Unlike WebSocket, which can stream incremental deltas, SSE's reconnection model means the browser must parse the complete state on every page load or reconnect. At 6-9MB of JSON, the browser's event parsing blocks the main thread for 20-30 seconds — long enough that the dashboard appears broken. The `openbrowser` CLI skill also timed out, confirming the issue is payload size, not a browser-specific bug.

This is a general risk when expanding market coverage: the relationship between "market types" and "payload size" is multiplicative (market_types × books × fixtures), not additive. Adding 3 market types to 3 sports with 52 books each can produce a 10x payload increase.

### The Separation Pattern

The architectural fix introduces a permanent distinction between two categories of markets:

**Display markets** are pushed via SSE to the dashboard for real-time visualization. These are player props across all configured soft books — the markets that bettors actively monitor and act on. The mini PC pollers continue to handle these exclusively, and the SSE push includes only this data.

**Tracking-only markets** are written to the server's internal state for the tracker to evaluate and persist picks, but are never included in the SSE stream. Game-line markets for the Pinnacle strategy (moneyline, spread, total) fall into this category because they serve a different purpose: the tracker evaluates them for +EV against prediction markets and persists any triggered picks to Supabase, but there is no need for real-time dashboard visualization of all 52-book game-line odds.

The tracking-only markets are handled by separate VPS-side Pinnacle pollers with a restricted book set (7 books: Pinnacle + Kalshi, Polymarket, DraftKings Predictions, Underdog, Crypto.com). This reduces the game-line market count from markets × 52 books to markets × 7 books, and since SSE push is disabled for these pollers, the payload impact is zero regardless of how many game-line markets are added.

### Dashboard Data Flow

The Pinnacle pill on the dashboard aggregates data from two independent paths:

1. **Client-side computed picks**: The SSE stream delivers player-prop odds data (from mini PC pollers). The dashboard's `computeEVForTheory()` function evaluates these against the Pinnacle theory in real-time, showing live +EV opportunities for player props.

2. **Server-tracked picks**: Game-line and niche-league picks are evaluated server-side by the tracker, persisted to Supabase, and loaded by the dashboard via database query. These appear as historical/tracked picks rather than live-computed opportunities.

This dual-path approach maintains full coverage (player props + game lines + niche leagues) while keeping the SSE payload under the ~5MB browser threshold.

### Operational Requirements

The mini PC server must be restarted after config changes — reverting `target_markets` in the sport config does not take effect until the poller is recycled. This was discovered when the game-line revert appeared to have no effect until a manual restart was performed. Additionally, SSE payload size should be monitored as new sports or market types are added, with ~5MB as the practical upper bound for reliable browser loading.

## Related Concepts

- [[concepts/pinnacle-prediction-market-pipeline]] - The Pinnacle pipeline whose game-line expansion caused the SSE bloat; VPS-side pollers are the resolution
- [[concepts/server-side-snapshot-cache]] - A related performance pattern: pre-serializing the odds response to avoid per-request serialization overhead
- [[concepts/odds-staleness-pipeline-diagnosis]] - The broader pipeline performance context; SSE ghost markets (cause #6) are related to payload management
- [[concepts/dashboard-client-server-ev-divergence]] - The dual computation path (client-side from SSE vs server-side from tracker) that the separation pattern relies on

## Sources

- [[daily/lcash/2026-04-16.md]] - SSE payload grew to 6-9MB after adding game-line markets to core pollers; MLB ballooned from ~2K to 5,040 markets (52 books × game lines); browser timeout at >5MB; fix: revert game lines from mini PC, add separate VPS-side Pinnacle pollers with 7-book set, disable SSE push for all Pinnacle pollers; Pinnacle pill shows client-computed (SSE props) + server-tracked (Supabase game lines); `openbrowser` CLI also timed out confirming payload issue (Session 21:31)
