---
title: "SSE vs Polling Staleness Threshold Mismatch"
aliases: [sse-staleness-mismatch, max-odds-age-sse, captured-at-sse-semantics, memoization-poisoning]
tags: [value-betting, sse, architecture, bug, data-quality, dashboard]
sources:
  - "daily/lcash/2026-05-06.md"
created: 2026-05-06
updated: 2026-05-07
---

# SSE vs Polling Staleness Threshold Mismatch

The V3 value betting dashboard showed 0 EV picks despite 1,175+ markets and 4 theories because the `MAX_ODDS_AGE_S=600` staleness filter was designed for REST polling architecture but applied to SSE-ingested data. SSE-based ingestion only updates `captured_at` when odds *change* — stable lines from sharp books that haven't moved in 10+ minutes are silently rejected as "stale" even though they represent current, valid prices. The fix increased `maxAge` to 7200s (2 hours), which is architecturally correct for SSE because unchanged odds are still valid. A secondary bug — memoization cache poisoned with 0-pick results using `pulse` (always 0) as the cache key — compounded the issue.

## Key Points

- SSE `captured_at` reflects **last change time**, not **last observed time** — stable lines aged out past `MAX_ODDS_AGE_S=600` despite being current
- REST polling updates `captured_at` on every poll cycle regardless of whether odds changed — 600s threshold was tuned for this behavior
- V3 SSE architecture requires `maxAge=7200s` (2 hours) — a permanent architectural difference, not a temporary workaround
- **Memoization poisoning**: Cache primed with 0 picks when `pulse` (server always returns 0) was the cache key; cache never invalidated because key never changed
- Fix: Changed cache key from `pulse` to `market_count` — observable data state that actually changes when new markets arrive
- Zero error signals from either bug — dashboard displayed "1,175 markets, 4 theories, 0 picks" which appeared to be a legitimate "market is efficient" result

## Details

### The Semantic Difference

In a REST polling architecture, each poll cycle fetches the latest odds and stamps `captured_at = now()`. Even if Pinnacle's Points line hasn't changed in 30 minutes, each poll refreshes the timestamp. A 600-second (10-minute) staleness filter safely rejects data that hasn't been polled recently — evidence of a polling failure.

In an SSE streaming architecture, the stream only delivers events when odds change. If Pinnacle's Points line is set at 25.5 and doesn't move for 45 minutes, no SSE event fires, and `captured_at` remains at the 45-minute-old timestamp. A 600-second filter rejects this as "stale" — but the line is still valid. The SSE stream IS connected and would deliver an update instantly if the line moved.

The fix (7200s = 2 hours) accommodates the SSE semantic: odds that haven't changed in 2 hours are still potentially valid but should eventually be refreshed. The REST reseed mechanism (see [[concepts/opticodds-sse-reconnect-state-loss]]) ensures odds are refreshed at least every 5 minutes regardless of SSE activity.

### The Memoization Poisoning Bug

After fixing the staleness threshold, the dashboard still showed 0 picks. The DeVig engine was correctly computing picks, but the dashboard's memoization cache was stuck on the initial 0-pick result.

The cache used `pulse` (a counter from the server's health endpoint) as its invalidation key. However, the V3 server's health endpoint always returned `pulse=0` — the counter was never incremented. With a constant cache key, the memoized result (0 picks from the initial computation with stale data) was served indefinitely. Even after the staleness fix allowed the engine to compute 43+ picks, the cache still returned its stale 0-pick result.

Changing the cache key to `market_count` — which actually changes when new market data arrives — fixed the invalidation. The cache now recomputes when the underlying data changes, not based on a counter that never increments.

### Compound Silent Failure

Both bugs produced zero error signals:

- The staleness filter silently rejected markets → `computeEVForTheory()` ran against 0 eligible markets → returned 0 picks (a valid computation result)
- The memoization cache returned its stored result → same 0 picks rendered → appeared as "market is efficient, no edge"
- The dashboard displayed "1,175 markets, 4 theories, 0 picks" — a plausible state that doesn't trigger investigation

Only tracing through the computation pipeline revealed that markets were being filtered at the age check, not failing at the EV calculation.

## Related Concepts

- [[concepts/opticodds-sse-reconnect-state-loss]] - SSE reconnect behavior where stable lines vanish; the REST reseed pattern provides a completeness safety net that partially mitigates this staleness issue
- [[concepts/opticodds-tcp-drop-max-age-tuning]] - The original `MAX_ODDS_AGE_S` tuning (180→600) for REST polling; the SSE migration requires a further increase to 7200
- [[concepts/odds-staleness-pipeline-diagnosis]] - The broader staleness pipeline analysis; SSE introduces a new staleness semantic not covered in the original 7-cause diagnosis
- [[concepts/dashboard-pick-flashing-stale-odds]] - Pick flashing from staleness filters is the same class of bug; SSE staleness is a V3-specific variant
- [[connections/silent-type-coercion-data-corruption]] - The compound silent failure (staleness filter + memoization poisoning) follows the established "plausible wrong output" pattern
- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture where SSE is the primary data ingestion path, making this staleness mismatch a permanent architectural concern

## Sources

- [[daily/lcash/2026-05-06.md]] - V3 dashboard 0 picks despite 1,175 markets and 4 theories; `MAX_ODDS_AGE_S=600` designed for polling rejected stable SSE lines; increased to 7200s; memoization cache stuck on 0-pick result because `pulse` (always 0) used as cache key; changed to `market_count`; SSE `captured_at` = last change time not last seen time (Session 14:26)
