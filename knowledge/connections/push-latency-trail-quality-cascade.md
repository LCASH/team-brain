---
title: "Connection: Push Latency and Trail Data Quality Cascade"
connects:
  - "concepts/server-side-snapshot-cache"
  - "concepts/trail-data-temporal-resolution"
  - "concepts/value-betting-operational-assessment"
sources:
  - "daily/lcash/2026-04-13.md"
created: 2026-04-13
updated: 2026-04-15
---

# Connection: Push Latency and Trail Data Quality Cascade

## The Connection

The push worker's 55-second cycle time — caused by server-side JSON serialization of large odds payloads — cascaded into degraded trail data quality on the VPS. The serialization bottleneck was in the sport servers' HTTP endpoints, but its effects propagated through the push pipeline to the tracker's sharp freshness cutoff, producing sparse trail captures that undermined backtesting reliability.

## Key Insight

The non-obvious insight is that a **performance bottleneck in an internal HTTP endpoint** — something that would normally only affect latency — became a **data quality problem** because of an interaction with a downstream timeout threshold. The tracker discards sharp comparisons older than 30 seconds (the sharp freshness cutoff). When the push cycle took 55 seconds, odds that were fresh when the sport server serialized them were stale by the time they reached the VPS tracker. This meant trail entries were only written during windows when sharp odds happened to remain stable through the long cycle — creating selection bias where trail data preferentially captured stable periods and missed volatile ones.

The cascade has three stages:

1. **Serialization bottleneck** — NBA's `/api/v1/odds` took 7.15s to serialize 2.6MB, MLB took 20.26s for 8.6MB, making the total push cycle 55 seconds
2. **Freshness threshold violation** — the 55s cycle exceeded the 30s sharp freshness cutoff, so many sharp comparisons arrived stale and were silently dropped
3. **Sparse trail capture** — trail entries were only written when enough sharps survived the latency, producing wider sampling intervals (~55s) instead of the expected ~2s

The fix (server-side snapshot cache reducing the cycle to 1.9s) was a performance optimization, but its real impact was on data quality. The 35 new picks and 867 updates observed in the first 5 push cycles after the fix confirmed that the pipeline had been severely underperforming, not just slow.

## Evidence

The full cascade was diagnosed on 2026-04-13 during push worker optimization:

- **Before fix:** Push cycle 55s, trail entries captured at ~55s intervals, many gaps during volatile periods. The `captured_at` timestamps reflected VPS arrival time (post-55s delay), not scraper observation time.
- **First optimization attempt:** Moving `gzip.compress()` to `asyncio.to_thread()` and parallelizing server fetches reduced the cycle to 27s — still above the 30s cutoff, so trail quality remained degraded.
- **Root cause identified:** Profiling individual endpoint calls revealed NBA took 7.15s and MLB took 20.26s for serialization alone. These are local HTTP calls — the time was entirely CPU-bound JSON serialization of deeply nested odds dictionaries.
- **After fix:** Snapshot cache (background task rebuilds serialized response every 2s) reduced the cycle to 1.9s. Trail data flow immediately recovered: 35 picks and 867 updates in the first 5 cycles, confirming the prior bottleneck was suppressing trail writes.

The critical reframing (Session 09:32) was that pre-fix trail data is **sparse, not corrupt** — each captured value is a genuine observation, just at wider intervals. Aggregate backtesting (CLV, win rate, ROI) is unaffected, but sub-minute tick-level analysis is not possible from pre-fix data.

## Related Concepts

- [[concepts/server-side-snapshot-cache]] - The fix that eliminated the serialization bottleneck
- [[concepts/trail-data-temporal-resolution]] - The data quality consequences and usability assessment
- [[concepts/value-betting-operational-assessment]] - The broader operational context
- [[connections/operational-compound-failures]] - A parallel cascade pattern: multiple weaknesses compounding
