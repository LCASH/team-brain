---
title: "Per-Soft-Book Temporal Lineage"
aliases: [temporal-honesty, per-book-freshness, all-soft-targets, book-specific-time-series, captured-at-decoupling]
tags: [value-betting, architecture, data-quality, tracker, pipeline]
sources:
  - "daily/lcash/2026-05-13.md"
created: 2026-05-13
updated: 2026-05-13
---

# Per-Soft-Book Temporal Lineage

On 2026-05-13, lcash shipped a "temporal honesty" overhaul to the v3 value betting scanner, replacing the global "is the scraper alive?" freshness model with per-(market_key, soft_book) async time series. The prior architecture stamped `captured_at = time.time()` on every push cycle regardless of whether odds had actually changed, making every market appear 5 seconds old even when the underlying data was hours stale. The new architecture records the real wizard parse time for Bet365 and preserves SSE change timestamps for OpticOdds, giving each of the 16 target soft books its own independent freshness timeline.

## Key Points

- **16 books get independent pick lineage**: 10 AU softs (365, 900-903, 907-911) + 6 prediction markets (950, 970-971, 980-982); thin books (Dabble, PickleBet, Unibet AU, Surge, BetIT) deferred
- **`ALL_SOFT_TARGETS = SOFT_BOOK_IDS | PREDICTION_MARKET_BOOK_IDS`** replaces fragmented iteration sets as the canonical tracker target, eliminating the recurring `SOFT_IDS` exclusion pattern
- **No pair-freshness gate needed**: sharps stream real-time via OpticOdds SSE, so only soft-side freshness matters for pick evaluation
- **`captured_at` decoupled into two concerns**: scraper-alive heartbeat (process monitoring) vs actual odds observation time (data quality) — the prior system conflated both into one timestamp
- **`datetime.utcnow()` on AEST host produces 10-hour offset**: Eve runs AEST, and naive datetimes' `.timestamp()` interprets as local time — must use `datetime.now(timezone.utc)` for correct UTC conversion
- Prediction markets have dual-use: sharp-substitute anchor (Crypto Edge theory) AND soft target — per-book lineage handles both without special-casing

## Details

### The Conflated Freshness Problem

The v3 scanner's push loop ran every 5 seconds, stamping `captured_at = time.time()` on every market in the payload regardless of whether the underlying odds had changed. This created "phantom freshness" — the staleness gate (`MAX_ODDS_AGE_S`) never triggered because every market appeared 5 seconds old. The tracker ground through full evaluation cycles on unchanged data, and operators saw "all markets fresh" when some books hadn't delivered new data in hours.

This is the same bug documented for `_bet365_push_loop` in [[concepts/coverage-first-dashboard-orientation]] and for the VPS ingest layer in [[concepts/dashboard-pick-flashing-stale-odds]] (state.py:2115). The May 13 overhaul addresses it comprehensively at the push loop layer by preserving the original scraper-side timestamps through the entire pipeline.

### The 16-Book Target Set

The `ALL_SOFT_TARGETS` constant consolidates two previously separate book ID sets into a single canonical iteration target:

| Category | Book IDs | Count |
|----------|----------|-------|
| AU Softs | 365 (Bet365), 900-903, 907-911 | 10 |
| Prediction Markets | 950 (Kalshi), 970-971, 980-982 | 6 |
| **Total** | | **16** |

Thin-coverage books (Dabble, PickleBet, Unibet AU, Surge, BetIT) were excluded from the initial set because they produce too few markets to warrant independent lineage tracking. They can be added when their coverage matures.

This unification eliminates the recurring `SOFT_IDS` exclusion pattern where new book types were silently excluded from trail capture (see [[concepts/trail-capture-soft-ids-gap]]) or theory evaluation because they weren't added to the correct hardcoded set.

### Architecture: Per-Book Async Time Series

The conceptual shift is from "one global captured_at for the entire push payload" to "each (market_key, soft_book) pair has its own last-changed timestamp." When the push loop sends data to the tracker:

- **Bet365**: `captured_at` reflects the wizard parse time (when Chrome actually captured the API response), not the push cycle time
- **OpticOdds SSE books**: `captured_at` reflects the SSE event timestamp (when the odds actually changed), which is the correct semantic for change-only streaming
- **Direct scrapers (TAB, Betr, TabTouch)**: `captured_at` reflects the REST poll response time

This means different books can have different freshness profiles: Bet365 might show 30-second-old data (wizard refresh cycle) while a Kambi book shows 5-minute-old data (REST poll interval) and both are accurately represented. The tracker evaluates each book's odds against its own timestamp rather than a global "last push" time.

### Phased Rollout

The temporal honesty work was shipped in four phases within a single session:

| Phase | Change | Impact |
|-------|--------|--------|
| 0 | Bet365 `captured_at` uses real wizard parse time | Actual data ages now visible (10-15s, was always 0s) |
| 1 | Push loop diff cache skips unchanged markets | Eliminates phantom `change_event` firing |
| 2 | Tracker iterates `ALL_SOFT_TARGETS` (16 books) | Prediction markets included in pick evaluation |
| 3 | Per-book latency panel on coverage.html | Operator visibility into per-book refresh cadence |

See [[concepts/push-loop-diff-cache-phantom-freshness]] for the Phase 1 diff cache mechanism.

### The Dual-Use Prediction Market Pattern

Prediction market books (Kalshi 950, Polymarket 970) serve two roles in the scanner:

1. **Sharp-substitute anchor** for Crypto Edge theories — used as the reference for devigging when Pinnacle has no coverage (see [[concepts/crypto-edge-non-pinnacle-strategy]])
2. **Soft target** for Pinnacle theories — evaluated as bet targets against Pinnacle's sharp line (see [[concepts/pinnacle-prediction-market-pipeline]])

Per-book lineage handles this naturally: the same book's odds are available for both roles, with the theory configuration determining how they're used. No special-casing is needed because the freshness tracking is orthogonal to the sharp/soft designation.

## Related Concepts

- [[concepts/push-loop-diff-cache-phantom-freshness]] - The diff cache mechanism (Phase 1) that eliminates phantom freshness signals from unchanged markets
- [[concepts/trail-capture-soft-ids-gap]] - The recurring SOFT_IDS exclusion pattern that ALL_SOFT_TARGETS prevents
- [[concepts/coverage-first-dashboard-orientation]] - The `_bet365_push_loop` captured_at overwrite bug that this overhaul fixes; per-book latency panel added
- [[concepts/odds-staleness-pipeline-diagnosis]] - The seven causes of odds drift; per-book temporal lineage addresses the `captured_at` re-stamping problem at the push loop layer
- [[concepts/sse-polling-staleness-threshold-mismatch]] - SSE captured_at semantics (last change time, not last seen) are preserved correctly under per-book lineage
- [[concepts/dashboard-pick-flashing-stale-odds]] - The state.py:2115 `captured_at` override that produced phantom freshness; a prior manifestation of the same conflated-timestamp problem

## Sources

- [[daily/lcash/2026-05-13.md]] - 4-phase temporal honesty overhaul: Phase 0 Bet365 captured_at uses wizard parse time, Phase 1 diff cache skips unchanged markets, Phase 2 tracker iterates ALL_SOFT_TARGETS (16 books), Phase 3 per-book latency panel; `datetime.utcnow()` on AEST host produces 10h offset; prediction markets dual-use (sharp anchor + soft target); captured_at decoupled into heartbeat vs observation time; 43 live books inventoried (Sessions 09:32, 10:02)
