---
title: "Connection: Response Serialization Caching at Multiple Pipeline Layers"
connects:
  - "concepts/server-side-snapshot-cache"
  - "concepts/vps-proxy-byte-cache-optimization"
  - "concepts/v3-scanner-centralized-architecture"
sources:
  - "daily/lcash/2026-04-13.md"
  - "daily/lcash/2026-05-09.md"
  - "daily/lcash/2026-05-10.md"
created: 2026-05-09
updated: 2026-05-12
---

# Connection: Response Serialization Caching at Multiple Pipeline Layers

## The Connection

The same performance anti-pattern — re-serializing large Python dicts to JSON on every HTTP response — was independently discovered and fixed at two different layers of the value betting pipeline: the mini PC sport servers (April 13, push worker bottleneck) and the VPS proxy (May 9, dashboard latency). Both fixes use the identical solution: cache the pre-serialized bytes and return a raw response that bypasses the framework's automatic serialization. The pattern was discovered independently each time because the symptoms manifest at different scales and the code paths are completely separate.

## Key Insight

The non-obvious insight is that **JSON serialization of multi-MB Python dicts is surprisingly expensive — expensive enough to be the dominant latency component at every layer where it occurs.** The intuition that "serialization is free compared to network I/O" is wrong for deeply nested dicts with thousands of markets. At both layers, the serialization cost exceeded the actual data transfer time:

| Layer | Payload Size | Serialization Time | Network Time | Fix Impact |
|-------|-------------|-------------------|-------------|------------|
| Mini PC sport servers (Apr 13) | 2.6–8.6 MB | 7–20 seconds | ~1s (local) | 55s → 1.9s (29×) |
| VPS proxy (May 9) | 6.5–9.6 MB | 10–21 seconds | ~3s (Tailscale) | 21s → 97ms (200×) |

The fix is identical at both layers: a background task or cache stores the serialized bytes, and the HTTP handler returns the pre-built bytes as a raw `Response` object instead of a Python dict that the framework would serialize. At the mini PC, a background `asyncio` task rebuilds every 2 seconds. At the VPS, a TTL cache stores bytes from the last upstream fetch.

## Evidence

**Mini PC (2026-04-13):** The push worker aggregated odds from 4 sport servers, each serializing 2.6–8.6 MB per request. The total push cycle was 55 seconds — dominated by serialization, not network. `asyncio.gather()` didn't help because the bottleneck was CPU-bound serialization within each endpoint. The snapshot cache pattern (background task pre-serializing every 2s) reduced the cycle to 1.9 seconds.

**VPS (2026-05-09):** The dashboard proxy fetched 6.5–9.6 MB from the mini PC and cached the response as a Python dict. On cache hits, FastAPI re-serialized the dict — taking 10+ seconds even though the upstream fetch was skipped. Storing the response as raw bytes and returning `Response(content=cached_bytes)` reduced warm hits from 10+ seconds to 97ms.

The independent rediscovery happened because the codebases are separate (mini PC `server/` vs VPS `relay/`), the symptoms manifest differently (push worker slowness vs dashboard timeout), and the scales differ (29× vs 200× improvement). A developer fixing the mini PC bottleneck would not naturally think to check the VPS proxy code, and vice versa.

### Event-Loop Starvation as Shared Failure Mode (2026-05-10)

On 2026-05-10, a third manifestation was discovered at the VPS proxy layer: concurrent cold-cache requests each independently fetched the ~14 MB upstream payload from Eve simultaneously, starving the asyncio event loop. The handler for `/api/v1/odds` showed 0 of 5 test requests reaching the handler function — all were blocked behind prior in-flight upstream fetches consuming event loop capacity. This is the same concurrency-under-serialization-load pattern that the mini PC snapshot cache solved by pre-serializing (eliminating per-request serialization entirely) — but at the VPS layer, where the cache had been emptied and multiple requests arrived before the first fetch completed. The fix was re-adding single-flight dedup so only one upstream fetch executes at a time, with concurrent waiters sharing the result.

## Architectural Pattern

The pattern can be stated as a rule: **Never let an HTTP framework serialize a multi-MB Python dict per-request. Pre-serialize once and serve bytes.**

The preconditions are:
1. Response payload exceeds ~1 MB (below this, serialization cost is negligible)
2. The same data is served to multiple requesters within a short window
3. Slight staleness (bounded by the cache rebuild interval) is acceptable

The implementation varies by context:
- **Background rebuild** (mini PC): A periodic task serializes every N seconds, regardless of whether a request is pending. Best when the data changes frequently and requests are continuous.
- **TTL cache** (VPS proxy): Serialized bytes are cached on first request and served for the TTL duration. Best when requests are sporadic and upstream fetches are expensive.

Both variants share the core insight: move serialization from the request path to the write path.

## Related Concepts

- [[concepts/server-side-snapshot-cache]] - The mini PC implementation: background task rebuilds serialized response every 2s, eliminated push worker 55s bottleneck
- [[concepts/vps-proxy-byte-cache-optimization]] - The VPS implementation: TTL cache of serialized bytes, eliminated dashboard 21s timeout
- [[concepts/v3-scanner-centralized-architecture]] - The V3 query-response model where the VPS proxies the mini PC; the byte cache makes this proxy performant
- [[connections/push-latency-trail-quality-cascade]] - The mini PC serialization bottleneck cascaded into trail data quality; the VPS bottleneck cascaded into dashboard unusability — different downstream effects from the same root cause

## Sources

- [[daily/lcash/2026-04-13.md]] - Mini PC push worker bottleneck: NBA 7.15s, MLB 20.26s serialization; snapshot cache fixed 55s→1.9s
- [[daily/lcash/2026-05-09.md]] - VPS proxy bottleneck: 8.7 MB re-serialized per request; byte cache fixed 21s→97ms
- [[daily/lcash/2026-05-10.md]] - VPS event-loop starvation from concurrent 14 MB cold fetches; single-flight dedup re-added (commit `f927e1e`)

```
