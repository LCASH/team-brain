---
title: "Trail Capture SOFT_IDS Gap"
aliases: [soft-ids-gap, phase-b-trail-gap, trail-capture-exclusion, book-id-inclusion]
tags: [value-betting, data-quality, bug, trail-data, configuration]
sources:
  - "daily/lcash/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# Trail Capture SOFT_IDS Gap

Phase B trail capture in `tracker.py:977` iterates a hardcoded `SOFT_IDS` set containing only Australian soft book IDs (365, 366, 900-961). When the Pinnacle prediction-market pipeline added new soft book types (Kalshi 950, Polymarket 970/971, DraftKings Predictions 971, Underdog 980, Crypto.com 981/982), their IDs were not added to `SOFT_IDS`. This caused 0% trail coverage for all prediction-market picks — trail entries silently failed to capture. The fix was immediate: adding prediction-market IDs to the iteration set produced 47 trail entries across 20 picks within 90 seconds.

## Key Points

- Phase B trail capture in `tracker.py:977` only iterates the hardcoded `SOFT_IDS` set (AU soft books 365, 366, 900-961)
- Prediction-market book IDs (Kalshi 950, Polymarket 970/971, Underdog 980, Crypto.com 981/982) were excluded — **0% trail coverage** for prediction-market picks
- The failure is completely silent: no errors, no warnings, trail entries simply never written for excluded book IDs
- Fix: add prediction-market IDs to `SOFT_IDS` iteration set — verified with 47 trail entries across 20 picks in 90s
- **Any new book type added to theories must also be added to `SOFT_IDS`** — this coupling is undocumented and easy to miss

## Details

### The Architecture Gap

The value betting scanner's trail capture operates in two phases. Phase A writes the initial pick with its triggered odds and EV. Phase B runs on subsequent tracker cycles, iterating through all soft book IDs to capture how odds evolve over time for each tracked pick — this is the trail data used for CLV analysis, backtesting, and performance monitoring.

Phase B's iteration is bounded by a hardcoded `SOFT_IDS` set. When the Pinnacle prediction-market pipeline (see [[concepts/pinnacle-prediction-market-pipeline]]) was deployed, it introduced a new category of soft books — prediction market platforms — with book IDs in the 950-982 range. The theory system correctly configured these as soft books for EV evaluation, and the tracker correctly triggered picks against them. But Phase B's trail capture loop never saw these IDs because they weren't in `SOFT_IDS`.

The result was a complete trail gap: 38 server-side picks existed for the Pinnacle pipeline, but zero trail entries were being written for any of them. Without trail data, there is no CLV analysis, no odds movement tracking, and no backtesting capability for the entire prediction-market strategy.

### Silent Failure Pattern

This is the same class of silent failure documented across the scanner's operational history: missing configuration produces zero output rather than errors. Compare with:

- [[concepts/silent-worker-authentication-failure]] — workers with missing API keys produce zero log output
- [[concepts/one-sided-consensus-structural-bias]] — `one_sided_consensus` silently skips all Unders without logging
- [[concepts/dashboard-client-server-ev-divergence]] — `loadTheories()` silently drops fields via JS destructuring

The common anti-pattern is "silent exclusion by omission" — when a loop iterates a fixed set, items outside the set are invisible rather than flagged. The fix is either to make the set dynamic (derived from active theory configurations) or to log a warning when a pick's soft book ID doesn't appear in the trail capture set.

### Systemic Coupling Risk

The coupling between `SOFT_IDS` and the theory system's `soft_books` configuration is undocumented. A developer (or operator) adding a new book type to a theory via Supabase has no reason to know that `SOFT_IDS` in `tracker.py` also needs updating — the theory system is explicitly designed to be code-free (see [[concepts/value-betting-theory-system]]). This creates a predictable failure mode: every new book type addition will silently break trail capture until someone notices the gap and updates the hardcoded set.

A more robust design would derive the trail capture iteration set from the active theories' `soft_books` configurations at cache refresh time, eliminating the manual synchronization requirement.

## Related Concepts

- [[concepts/pinnacle-prediction-market-pipeline]] - The pipeline whose trail capture was broken by this gap
- [[concepts/value-betting-theory-system]] - The theory system that allows code-free book addition — but SOFT_IDS coupling breaks this contract
- [[concepts/trail-data-temporal-resolution]] - Trail data quality depends on trail entries being captured at all; this gap was a total capture failure, not a sparsity issue
- [[concepts/silent-worker-authentication-failure]] - Same anti-pattern: missing configuration → zero output → no error signal
- [[connections/operational-compound-failures]] - The silent trail gap + no monitoring chain echoes the established compound failure pattern

## Sources

- [[daily/lcash/2026-04-16.md]] - Phase B trail capture only iterated `SOFT_IDS` (AU books 365, 366, 900-961); prediction market IDs (950, 970, 971, 980-982) excluded; 0% trail coverage for 38 Pinnacle picks; fix produced 47 trail entries across 20 picks in 90s; coupling between SOFT_IDS and theory soft_books is undocumented (Sessions 16:30, 20:38)
