---
title: "VPS Proxy Byte-Level Response Cache"
aliases: [vps-byte-cache, proxy-response-cache, fastapi-serialization-bottleneck, odds-proxy-cache, eve-payload-cache]
tags: [value-betting, performance, architecture, caching, vps, dashboard]
sources:
  - "daily/lcash/2026-05-09.md"
  - "daily/lcash/2026-05-10.md"
created: 2026-05-09
updated: 2026-05-12
---

# VPS Proxy Byte-Level Response Cache

The VPS dashboard's `/api/v1/odds` endpoint was taking 21 seconds to respond because FastAPI re-serialized the 6.5–9.6 MB upstream payload from the mini PC (Eve) on every request. The fix caches the pre-serialized bytes and returns a raw `Response(content=cached_bytes)` with a 2-second TTL, achieving **~200× speedup** (21s cold → 97ms warm). This is the VPS-side complement to the mini PC's server-side snapshot cache (see [[concepts/server-side-snapshot-cache]]) — the same "cache serialized bytes, not Python objects" pattern applied at a different pipeline layer.

## Key Points

- Eve (mini PC) `/v1/odds` returns 6.5–9.6 MB uncompressed — the fundamental upstream bottleneck; no amount of proxy caching fixes the cold-start for the first viewer
- FastAPI re-serializing a multi-MB Python dict on every cache hit took **10+ seconds** even on "warm" hits — the cache was storing Python objects, not bytes
- Fix: cache the serialized bytes (`orjson.dumps()` once) and return `Response(content=cached_bytes, media_type="application/json")` — bypasses FastAPI's serialization layer entirely
- 2-second TTL balances freshness with performance; auto-poll runs every 3s so users see one slow load then instant thereafter
- Cold start remains 15–25s for the first viewer (6–9 MB traveling through Tailscale relay) — a fundamental constraint of the upstream payload size
- Single-flight dedup initially misfired but was **re-added on 2026-05-10** after concurrent cold-cache requests starved the event loop — multiple 14 MB upstream fetches simultaneously blocked all other handlers

## Details

### The Serialization Double-Tax

The V3 architecture uses the VPS as a proxy: the dashboard requests `/api/v1/odds`, the VPS fetches from the mini PC's Eve server at `:8900/v1/odds`, and forwards the response. The initial implementation stored the upstream response as a Python dict in a cache dict. On cache hits, FastAPI's response serialization ran `json.dumps()` (or equivalent) on the 8.7 MB dict — a CPU-bound operation taking 10+ seconds on the VPS's limited compute.

This created a paradox: the cache was "hit" (the upstream fetch was skipped) but the response time was nearly as bad as a cache miss because serialization dominated. The cache was saving network I/O but not CPU. For large payloads, serialization cost exceeds network cost.

### The Byte Cache Pattern

The fix stores the upstream response as raw bytes, not Python objects:

1. On cache miss: fetch upstream → `orjson.dumps(response_data)` once → store bytes + timestamp
2. On cache hit: return `Response(content=cached_bytes, media_type="application/json")` — zero serialization
3. TTL check: if `time.time() - cache_ts > 2.0`, treat as miss

By returning a raw `Response` object with pre-serialized content, FastAPI's automatic JSON serialization is completely bypassed. The response is just bytes copied to the HTTP output buffer — effectively free.

This is architecturally identical to the mini PC's server-side snapshot cache (see [[concepts/server-side-snapshot-cache]]) which solved a 55s→1.9s push worker bottleneck by pre-serializing sport server odds. Both solve the same problem — Python JSON serialization of deeply nested multi-MB dicts is surprisingly expensive — at different layers of the pipeline.

### Cold Start Constraint

The 15–25 second cold start for the first viewer is a fundamental constraint that no proxy-layer caching can fix. The upstream Eve payload is 6.5–9.6 MB, traveling from the mini PC through Tailscale VPN to the VPS. This is the time-to-first-byte for any viewer who arrives when the cache is empty (VPS restart, TTL expiry, or simply the first request of the day).

After the first successful fetch populates the cache, all subsequent requests within the 2-second TTL window return in ~97ms. The dashboard's auto-poll (every 3 seconds) means the cache is continuously refreshed, so only the very first viewer experiences the cold start.

### Concurrent Cold Request Handling and Event-Loop Starvation

A subtle failure mode was discovered during testing on 2026-05-09: back-to-back `curl` requests (e.g., running 3 curl commands rapidly) can all start before the first one writes to the cache. All three requests go cold and hit the upstream simultaneously, each taking 21 seconds. A single-flight / dedup pattern was initially attempted (only allow one upstream fetch, queue other waiters) but misfired — race conditions between the first cache write and concurrent reads produced stale or missing responses.

The initial pragmatic solution was the simple cache-or-fetch pattern without dedup: concurrent cold requests each independently fetch from upstream, and the last to complete wins the cache write.

However, on 2026-05-10, the dedup pattern was **re-added** after discovering a more severe failure mode: on cold cache (e.g., after VPS restart), concurrent requests to `/api/v1/odds` each independently triggered a 14 MB upstream fetch from Eve via Tailscale. With the dashboard's auto-poll running every 3 seconds and multiple concurrent cold requests, the VPS event loop was saturated with simultaneous upstream fetches — 0 of 5 test requests reached the handler because the event loop was blocked processing prior fetches. This is the same event-loop starvation pattern previously seen on Eve itself (see [[connections/response-serialization-caching-pipeline]]).

The single-flight dedup ensures that only one upstream fetch executes at a time; concurrent requesters wait for the in-flight fetch to complete rather than each independently fetching. This was deployed as commit `f927e1e`.

### Production Payload Size

Production measurements on 2026-05-10 revealed the upstream payload had grown to **~17 MB** (up from the 6.5–9.6 MB measured at initial deployment). At 700 KB/s bandwidth (typical Tailscale relay throughput), this means ~25 seconds for a cold start. This is not a real user issue since the dashboard uses SSE with small deltas rather than repeatedly polling `/api/v1/odds`, but it affects diagnostic tools like `curl` and any future API consumers. gzip middleware was identified as a potential future optimization (6-8× compression on JSON), but deemed not urgent given the SSE usage pattern.

### Sport-Scoped SSE Interaction

The byte cache was deployed alongside sport-scoped SSE (see [[concepts/dashboard-sport-scoped-sse-routing]]), which reduces per-sport payload size by only streaming markets for the active sport. The cache benefits from sport-scoping: cached payloads are smaller (sport-filtered rather than all-sport), reducing both serialization time on miss and memory footprint.

However, sport-scoped SSE requires SSE reconnection on sport switch, which means the first load after switching sports experiences a cold start (the new sport's data isn't in the cache). The 2-second TTL ensures this cold start quickly resolves for subsequent auto-polls.

## Related Concepts

- [[concepts/server-side-snapshot-cache]] - The mini PC's equivalent pattern: pre-serialized odds response every 2s, reduced push cycle 55s→1.9s; the VPS byte cache is the proxy-side complement
- [[concepts/v3-scanner-centralized-architecture]] - The V3 query-response architecture where the VPS proxies the mini PC; the byte cache makes this proxy performant
- [[concepts/v3-dashboard-ev-computation-architecture]] - The V3 dashboard that consumes data through this cached proxy endpoint
- [[concepts/sse-polling-staleness-threshold-mismatch]] - SSE staleness semantics affect when cached data is considered stale; the 2s TTL is much shorter than the 7200s SSE threshold
- [[connections/response-serialization-caching-pipeline]] - How the same cache-serialized-bytes pattern was independently discovered and applied at both mini PC and VPS layers

## Sources

- [[daily/lcash/2026-05-09.md]] - `/api/v1/odds` timing out from 6.45–9.6 MB upstream; initial cache stored Python objects, FastAPI re-serialized 8.7 MB on every hit (10+ s); fix: cache bytes + raw Response → 97ms warm (200× faster); 2s TTL; single-flight dedup initially misfired, simple cache-or-fetch attempted; cold start 15–25s is fundamental Tailscale relay constraint (Sessions 11:15, 11:53)
- [[daily/lcash/2026-05-10.md]] - Single-flight dedup re-added (commit `f927e1e`) after concurrent cold-cache requests starved the event loop — multiple 14 MB upstream fetches simultaneously blocked all handlers (0/5 requests reached handler); production payload grew to ~17 MB; gzip middleware identified as future optimization but not urgent since dashboard uses SSE not polls (Session 14:34)
