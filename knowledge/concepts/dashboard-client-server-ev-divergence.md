---
title: "Dashboard Client-Server EV Divergence"
aliases: [client-side-ev, server-side-ev, ev-computation-mismatch, loadtheories-bug-fix]
tags: [value-betting, dashboard, bug, architecture]
sources:
  - "daily/lcash/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# Dashboard Client-Server EV Divergence

The value betting dashboard's "+EV Picks" tab computes EV live in the browser against all soft books (ignoring per-theory restrictions), while the server-side tracker respects each theory's `soft_books` filter when persisting picks. This architectural disconnect means the dashboard can show different EV values and different soft book comparisons than what the tracker used to trigger the pick. The root cause was a `loadTheories()` JavaScript mapping bug that silently dropped six theory fields, and the fix was deployed on 2026-04-15.

## Key Points

- Dashboard `computeEVForTheory()` falls back to global `SOFT_IDS` (all Australian soft books) when the theory's `soft_books` field is missing from the JS object
- Server-side tracker correctly applies per-theory `soft_books` when evaluating and persisting picks
- The Pinnacle theory appeared to work (showing EV against Ladbrokes, PointsBet AU) but should have been showing EV against prediction markets (Kalshi, Polymarket)
- Root cause: `loadTheories()` JS destructuring silently dropped `soft_books`, `prop_filter`, `max_line_gap`, `line_gap_penalty`, `max_line`, and `excluded_props` when mapping Supabase rows to JS objects
- Fix deployed 2026-04-15 as part of Pinnacle commit `9a0b19d` (5 files, +177/-28 lines): all theory columns now explicitly mapped in `loadTheories()`
- Deploy on mini PC killed all workers (push worker, AFL, MLB, NRL) but only restarted NBA — required manual restart of all services

## Details

### The Mismatch

The value betting scanner has two independent EV computation paths:

1. **Server-side (tracker)**: The tracker loads theory configurations every 5 minutes from Supabase, including `soft_books` (which soft bookmakers to evaluate against). When a theory's EV threshold is met for a specific soft book, the pick is persisted with `triggered_by` set to the theory name. This path correctly respects all theory parameters.

2. **Client-side (dashboard)**: The "+EV Picks" tab receives odds data via SSE and computes EV live in the browser using `computeEVForTheory()`. This function should use the theory's `soft_books` list to determine which soft books to show EV for. However, when the `soft_books` field is missing from the theory object (due to the `loadTheories()` mapping bug), it falls back to the global `SOFT_IDS` constant, which includes all Australian soft books.

The practical impact was that the Pinnacle theory — configured to evaluate prediction markets (Kalshi, Polymarket) against Pinnacle's sharp line — appeared on the dashboard with EV values computed against Ladbrokes, PointsBet AU, and other Australian retail books. The numbers looked plausible (they were real EV computations), but they were against the wrong set of soft books, defeating the purpose of the Pinnacle theory configuration.

### The loadTheories() Bug and Fix

The root cause is a JavaScript anti-pattern: when mapping database rows to objects using destructuring, any column not explicitly included in the mapping is silently discarded. The `loadTheories()` function was mapping theory rows from Supabase but did not include `soft_books`, `prop_filter`, `max_line_gap`, `line_gap_penalty`, `max_line`, or `excluded_props` in its destructuring. These fields were all silently dropped.

This is particularly dangerous because there is no error signal. The theory objects are constructed successfully, downstream functions receive them without complaint, and the fallback behavior (using global defaults) produces plausible-looking results. Only a human comparing the dashboard output against the theory configuration would notice the mismatch — in this case, lcash noticed that the Pinnacle pill was showing Australian soft books instead of prediction markets.

The fix was to explicitly map every theory column in the `loadTheories()` function. This is a maintenance burden: any future column added to the `nba_optimization_runs` table must also be added to the client-side mapping, or it will be silently ignored.

### Verification: Pinnacle Pipeline

After deploying the fix, the Pinnacle pipeline was verified end-to-end. Data was flowing: Polymarket (348 markets), Kalshi (168), Pinnacle (402) all visible on VPS. Zero Pinnacle picks were firing, but this was correct behavior — all NBA games were outside the 3-hour pre-tipoff window (today's games already tipped off, tomorrow's >24h out). No code change was needed; the pipeline would produce picks when games entered the actionable window.

### Deploy-Kills-All-Workers

A related operational discovery during the same session: deploying changes to the mini PC killed all running workers (push worker, AFL, MLB, NRL servers, betstamp worker) but only restarted the primary service (NBA server). This required manually restarting all ancillary services. The NRL scheduled task had also been disabled and needed re-enabling via `schtasks /Change /TN NRL_Server /Enable`. This is a deployment variant of the configuration drift pattern — the deploy process doesn't match the full production service set.

## Related Concepts

- [[concepts/value-betting-theory-system]] - The theory system whose client-side consumption was broken by the loadTheories() bug
- [[concepts/one-sided-consensus-structural-bias]] - A different theory configuration bug with similarly invisible effects
- [[concepts/value-betting-operational-assessment]] - Weakness #2 (no monitoring) applies: the mismatch was discovered manually
- [[concepts/configuration-drift-manual-launch]] - Deploy-kills-all-workers is a deployment variant of the config drift pattern
- [[connections/operational-compound-failures]] - The silent field-dropping + no monitoring chain echoes the compound failure pattern
- [[concepts/pinnacle-prediction-market-pipeline]] - The Pinnacle pipeline whose verification exposed this bug; commit `9a0b19d` includes both the bug fix and prediction market book IDs

## Sources

- [[daily/lcash/2026-04-15.md]] - Pinnacle theory showing AU soft books instead of prediction markets; `loadTheories()` dropping 6 fields via JS destructuring; client-side EV ≠ server-side EV divergence; fix deployed; zero Pinnacle picks correct (games outside 3h window); deploy killed all workers requiring manual restart; NRL scheduled task re-enable needed (Session 22:03/16:20+)
