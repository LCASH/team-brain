---
title: "Server-Side Snapshot Cache"
aliases: [snapshot-cache, pre-serialized-response, odds-snapshot-cache]
tags: [performance, architecture, caching, serialization, value-betting]
sources:
  - "daily/lcash/2026-04-13.md"
created: 2026-04-13
updated: 2026-04-13
---

# Server-Side Snapshot Cache

A performance pattern where a background task periodically rebuilds a fully serialized API response (bytes), and the HTTP endpoint serves the pre-built payload instead of serializing on demand. Applied to the value betting scanner's sport servers, this pattern reduced the push worker cycle from 55 seconds to 1.9 seconds by eliminating per-request serialization of large odds payloads.

## Key Points

- The push worker cycle bottleneck was server-side serialization, not network or compression — NBA's `/api/v1/odds` took 7.15s to serialize 2.6MB, MLB took 20.26s for 8.6MB
- A background `asyncio` task rebuilds the serialized odds snapshot every 2 seconds; the endpoint serves pre-built bytes with zero serialization overhead
- Moving `gzip.compress()` to `asyncio.to_thread()` was a red herring — the real bottleneck was the JSON serialization inside the endpoint itself
- Results: NBA 7.15s→1.63s, MLB 20.26s→1.25s (16x faster), total push cycle 55s→1.9s (29x faster)
- Trail data flow immediately recovered: 35 new picks and 867 updates observed in the first 5 push cycles after deployment

## Details

### The Diagnosis Path

The push worker aggregates odds from multiple sport servers and pushes them to the VPS. The initial cycle time was 55 seconds, far too slow for a system where sharp odds have a 30-second freshness cutoff. The first optimization attempt moved `gzip.compress()` to `asyncio.to_thread()` and parallelized server fetches, dropping the cycle to 27 seconds — still unacceptable.

Profiling the individual endpoint calls revealed the true bottleneck: the sport servers were serializing their entire odds state on every request. NBA's odds endpoint took 7.15 seconds to build and serialize a 2.6MB JSON response. MLB was worse at 20.26 seconds for 8.6MB. These are local HTTP calls (push worker → sport server on the same machine), so network latency is negligible — the time was entirely spent in Python's JSON serialization of deeply nested odds dictionaries with thousands of markets.

The key insight was that `asyncio.gather()` doesn't help when the work is CPU-bound serialization running synchronously within an async endpoint. Gathering four sport server calls in parallel still blocks on the slowest one. The solution had to eliminate the serialization from the request path entirely.

### The Pattern

The snapshot cache decouples serialization from request handling:

1. A background `asyncio` task runs every 2 seconds, serializes the current odds state to bytes (JSON + optional gzip), and stores the result in memory.
2. When a request hits the `/api/v1/odds` endpoint, the handler returns the pre-built bytes directly — no serialization, no dictionary traversal, no nested object conversion.
3. The 2-second rebuild interval means odds data is at most 2 seconds stale, which is well within the 30-second sharp freshness cutoff used by the tracker.

This is a classic read-heavy optimization: the odds state is written by scrapers continuously but read by the push worker only every few seconds. Pre-computing the read path at a fixed interval amortizes the serialization cost across all requests in that window.

### Impact on Trail Data Quality

The 55-second push cycle had a cascading effect on trail data quality. The tracker's sharp freshness cutoff (30 seconds) meant that by the time odds arrived at the VPS after a 55-second push cycle, many sharp comparisons were already stale. This produced trail data at wider sampling intervals — real data points but far fewer per unit time than expected. The 1.9-second cycle eliminates this bottleneck entirely, making trail data capture near-real-time. See [[connections/push-latency-trail-quality-cascade]] for the full analysis.

### Generality

The pattern applies to any API that serializes large, slowly-changing state on every request. The preconditions are: (1) the response payload is large enough that serialization is the dominant cost, (2) the underlying data changes at a rate slower than the cache rebuild interval, and (3) slight staleness (bounded by the rebuild interval) is acceptable. Other examples include dashboard APIs serving aggregated metrics, configuration endpoints for distributed systems, and status pages for monitoring systems.

## Related Concepts

- [[connections/push-latency-trail-quality-cascade]] - How the 55s push cycle cascaded into trail data quality issues
- [[concepts/trail-data-temporal-resolution]] - The trail quality caveat that this fix resolves going forward
- [[concepts/value-betting-operational-assessment]] - The operational assessment that identified performance as a secondary concern (before this fix elevated it)

## Sources

- [[daily/lcash/2026-04-13.md]] - Push worker optimization: gzip.compress to asyncio.to_thread was a red herring, real bottleneck was endpoint serialization (NBA 7.15s, MLB 20.26s); snapshot cache reduced push cycle 55s→1.9s; 35 picks + 867 updates in first 5 cycles (Session 07:45 ongoing)
