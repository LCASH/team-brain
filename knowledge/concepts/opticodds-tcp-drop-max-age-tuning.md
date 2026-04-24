---
title: "OpticOdds TCP Drop Resilience and MAX_ODDS_AGE Tuning"
aliases: [max-odds-age, tcp-drop-resilience, opticodds-outage-resilience, pick-flashing-fix, remote-protocol-error]
tags: [value-betting, opticodds, resilience, configuration, dashboard]
sources:
  - "daily/lcash/2026-04-24.md"
created: 2026-04-24
updated: 2026-04-24
---

# OpticOdds TCP Drop Resilience and MAX_ODDS_AGE Tuning

Dashboard picks were "flashing out" — disappearing and reappearing — because intermittent OpticOdds TCP disconnections (`httpx.RemoteProtocolError: Server disconnected without sending a response`) caused sharp data to age past the `MAX_ODDS_AGE_S=180` threshold. Without fresh sharp data, true probability computation returns zero, which produces zero picks. The fix increased `MAX_ODDS_AGE_S` from 180 to 600 seconds (10 minutes), accepting slightly stale sharp data during outages rather than showing zero picks.

## Key Points

- `httpx.RemoteProtocolError: Server disconnected without sending a response` = upstream TCP-level drops (load balancer, server crash), NOT rate limiting; rate limits return HTTP 429 with response body
- Mini PC REST poller makes 4,782 requests/min across 57 sportsbooks — initially suspected as rate limiting cause, but confirmed as intentional and not the issue
- `MAX_ODDS_AGE_S` increased from 180 (3 min) to 600 (10 min) — sharp lines don't move much in 10 minutes, so slightly stale data is acceptable vs zero picks
- VPS SSE streams are more resilient than mini PC REST polling — persistent connections with auto-reconnect vs independent HTTP requests that each can fail
- The existing error handling in `_poll_opticodds()` (catch, log, retry in 5s) is correct; the problem was only that the staleness threshold was too tight

## Details

### The Failure Pattern

During intermittent OpticOdds infrastructure issues, random sportsbook REST poll batches fail with `httpx.RemoteProtocolError`. This is a TCP-level disconnect — the server drops the connection without sending any HTTP response. Unlike rate limiting (which produces HTTP 429 with a retry-after header), TCP drops indicate upstream infrastructure problems: load balancer connection limits, server process crashes, or network congestion.

The error is intermittent and self-healing: it affects random sportsbook batches, comes and goes, confirming flaky upstream rather than an IP ban or systematic rate limit. The mini PC's `_poll_opticodds()` handler correctly catches the exception, logs it, and retries in 5 seconds.

### Why Picks Disappeared

The problem wasn't the REST errors themselves — it was the downstream effect on `MAX_ODDS_AGE_S`. When a REST poll fails, the sharp book data it would have refreshed ages. After 180 seconds (3 minutes) without a successful refresh for a given sportsbook, the dashboard's staleness filter discards that book's data. If enough sharp books age out simultaneously (which happens during a cluster of TCP drops), the EV computation has no sharp reference to devig against — true probability becomes zero, and all picks vanish.

The picks reappear seconds later when the next successful poll refreshes the sharp data. This produces the "flashing" symptom: picks appear → TCP drops → sharp data ages → picks disappear → successful poll → picks reappear. The cycle repeats for every outage burst.

### The Tradeoff: Freshness vs Availability

Increasing `MAX_ODDS_AGE_S` from 180 to 600 trades freshness for availability:

- **At 180s**: Dashboard shows zero picks during any >3-minute OpticOdds hiccup — high data quality when picks are shown, but frequent zero-pick windows
- **At 600s**: Dashboard maintains picks through typical 1-5 minute outages — slightly stale sharp data but continuous pick visibility

The 600s threshold is justified because NBA sharp lines typically don't move significantly in a 10-minute window. The biggest line movements happen when injury news breaks or close to tip-off — in these scenarios, the REST poller would recover within a few retry cycles and refresh the data anyway. For the typical case (no news, lines moving slowly), 10-minute-old sharp data produces nearly identical EV computations to 30-second-old data.

### The 57-Sportsbook Polling Load

The mini PC's REST poller queries 57 sportsbooks per cycle: 5 sharp books (FanDuel, DraftKings, PropBuilder, Novig, Pinnacle) for devigging, 6 Australian soft books for bet targets, and ~46 consensus books for one-sided consensus devig theories. At 60-second cycles, this produces ~4,782 requests/minute.

Initially this appeared to be a rate-limiting smoking gun, but OpticOdds confirmed: rate limits return HTTP 429 with a response body, not raw TCP disconnects. The 57-sportsbook count is intentional and necessary for the scanner's multi-theory devig architecture.

### SSE vs REST Resilience

The VPS-side SSE streams stayed alive during the same outage windows that affected REST polling. SSE persistent connections with built-in auto-reconnect are more resilient than REST polling where each request is an independent HTTP connection that can individually fail. This asymmetry means the VPS receives more consistent data during OpticOdds instability than the mini PC.

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - OpticOdds TCP drops are an availability dimension of the single-provider dependency
- [[concepts/dashboard-pick-flashing-stale-odds]] - Previous pick flashing was from 5 stacking bugs (SSE snapshot clear, reconcile_sport, etc.); this is a sixth mechanism (sharp data aging from TCP drops)
- [[concepts/odds-staleness-pipeline-diagnosis]] - MAX_ODDS_AGE_S is a staleness threshold in the pipeline; tuning it trades freshness for availability
- [[concepts/opticodds-sse-streaming-scaling]] - SSE streams are more resilient than REST for the same data source, confirming the migration direction

## Sources

- [[daily/lcash/2026-04-24.md]] - Picks flashing out traced to OpticOdds REST `httpx.RemoteProtocolError` (TCP disconnects); 4,782 req/min across 57 sportsbooks is not rate limiting (confirmed by HTTP 429 absence); `MAX_ODDS_AGE_S` increased 180→600; VPS SSE more resilient than mini PC REST; error is intermittent and self-healing (Sessions 09:42, 09:48)
