---
title: "Settlement Queue Starvation from ASC Ordering"
aliases: [settlement-starvation, resolver-asc-limit, orphan-void-sweep, settlement-cliff, queue-starvation]
tags: [superwin, racing, resolver, bug, architecture, operations]
sources:
  - "daily/lcash/2026-05-26.md"
created: 2026-05-26
updated: 2026-05-26
---

# Settlement Queue Starvation from ASC Ordering

The SuperWin racing settlement resolver used `detected_at ASC + LIMIT 200` to process unsettled picks, which meant the oldest picks always occupied the 200-slot queue. When cumulative orphan picks (from service restarts during racing hours) exceeded 200, the resolver could never reach today's picks — creating a "settlement cliff" where no new picks settled despite the system appearing healthy. The cliff traced to 2026-05-21 when cumulative orphans first exceeded 200. Fix: flipped to `detected_at DESC` (newest first) and added a >72h orphan VOID sweep. Results within 90s: today's unsettled dropped from 39→6, historical 4,431 draining at ~100/min.

## Key Points

- `detected_at ASC + LIMIT 200` meant oldest orphan picks always filled the queue — today's picks were permanently starved
- **Settlement cliff at 2026-05-21** when cumulative orphan count exceeded 200 (from commit `00b6827` shipped 2026-05-19)
- **Fix 1**: `detected_at DESC` (newest first) + orphan VOID sweep (>72h) — smallest change, biggest unblock
- **4,431 stuck picks** drained at ~100/min after fix; today's unsettled dropped 39→6 in 90 seconds
- **95% of stuck picks were queue starvation** not settlement logic failures — the resolver was working correctly but never reached them
- **Residual 1-3 races/day failing** traced to Betfair streaming 200-market subscription cap (separate issue)
- Service restarts during racing hours (9am-11pm AEST) compound the problem — each restart orphans all markets that close before the new subscription list is built

## Details

### The Starvation Mechanism

The settlement resolver's `get_unsettled_picks` query sorted by `detected_at ASC` with a `LIMIT 200`. This design assumed that the oldest unsettled picks should be processed first — a reasonable default when the queue is small and picks settle normally.

The failure occurs when orphan picks accumulate. Orphan picks are those created during a race that closes before a service restart completes — the settlement scanner only tracks markets it's actively subscribed to at suspension time, so markets that close during a restart window never get `race_results` saved. These orphans are permanently unsettleable because no result data exists for them. With `ASC` ordering, they fill the first 200 slots of every query, blocking all newer (settable) picks.

The critical threshold was crossed on 2026-05-21. Before that date, orphan accumulation was manageable (fewer restarts, fewer racing hours affected). After 2026-05-19 (commit `00b6827`), multiple deploys during racing hours created a burst of orphans that pushed the total past 200. From that point forward, the resolver processed 200 unsettleable orphans per cycle, returned "0 settled," and the cycle repeated — an infinite loop of wasted work.

### The Settlement Scanner Blind Spot

A deeper architectural issue underlies the orphan accumulation: the settlement scanner has no retroactive result-fetching capability. Markets that close BEFORE a service restart get no `race_results` saved because:

1. The scanner subscribes to Betfair market channels on startup
2. It receives `CLOSED` events for subscribed markets and records results
3. Markets that closed between the old process dying and the new process subscribing are invisible
4. No background job re-fetches results via Betfair `listMarketBook` REST API

Multiple restarts during racing hours (3-4 on May 26 alone for deploys) compound this into hundreds of orphan picks per day. The recommended fix is a backfill scanner that re-fetches results via Betfair REST for races jumped in the last N hours after any restart.

### Fix and Immediate Impact

The fix had two components:

**Component 1 — DESC ordering**: Flipping to `detected_at DESC` ensures the most recent picks (which are most likely to have settlement data available) are processed first. Older orphans sink to the bottom of the queue and are only processed when the newer picks are cleared.

**Component 2 — Orphan VOID sweep**: Picks older than 72 hours with no settlement data are automatically voided (`result='VOID'`). This prevents orphans from accumulating indefinitely. 72 hours is conservative — Betfair typically processes results within minutes of race completion, so any pick still unsettled after 72 hours is almost certainly an orphan.

The impact was immediate: within 90 seconds of deployment, today's unsettled picks dropped from 39 to 6 (the remaining 6 were awaiting race results from today's ongoing races). The historical backlog of 4,431 picks began draining at ~100/min as the orphan sweep voided permanently unsettleable entries.

### Operational Impact: Restart Timing

The starvation pattern has a clear operational implication: **restarts during racing hours (9am-11pm AEST) should be minimized.** Each restart creates a window where closing markets are missed. Batching code changes into single deploys outside racing hours reduces orphan accumulation. When restarts during racing hours are unavoidable (critical bug fixes), the backfill scanner (when built) would retroactively fill the gap.

## Related Concepts

- [[concepts/betfair-streaming-subscription-cap]] - The 200-market streaming cap that causes residual 1-3 races/day to fail even after the queue fix
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal that orphan VOIDs affect; voided picks are filtered from ROI calculations
- [[connections/permanent-blacklist-no-expiry-anti-pattern]] - Related pattern: in-memory state accumulating without cleanup. The settlement queue is a database-level variant where accumulating orphans block all forward progress
- [[concepts/resolver-sequential-sport-bottleneck]] - The value betting resolver had a parallel bottleneck: NRL slow fallback blocked all subsequent sports. Both are "oldest items block newest" queue ordering bugs

## Sources

- [[daily/lcash/2026-05-26.md]] - Settlement cliff traced to 2026-05-21 when orphans exceeded 200; ASC+LIMIT 200 from commit 00b6827 (2026-05-19); fix: DESC ordering + >72h orphan VOID sweep; today's unsettled 39→6 in 90s; 4,431 draining at ~100/min; 95% were queue starvation not logic failures; settlement scanner blind spot: no retroactive result fetch; restarts during racing hours compound orphan accumulation; Betfair `SUBSCRIPTION_LIMIT_EXCEEDED, max allowed: 200` confirmed as separate issue (Session 12:16)
