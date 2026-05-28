---
title: "Settlement Scanner In-Memory State Loss on Restart"
aliases: [settlement-restart-loss, market-start-times-volatile, persistent-sel-map-loss, settlement-backfill-on-restart]
tags: [superwin, racing, settlement, reliability, architecture, operations]
sources:
  - "daily/lcash/2026-05-28.md"
created: 2026-05-28
updated: 2026-05-28
---

# Settlement Scanner In-Memory State Loss on Restart

The SuperWin racing settlement scanner maintains three critical in-memory dictionaries — `_market_start_times`, `_persistent_sel_map`, and `_persistent_races` — that are not persisted to disk and do not survive service restarts. When the scanner restarts, old markets that closed before the new subscription list is built become invisible, leaving their picks permanently stuck as unsettled. On 2026-05-28, 72 stuck picks were traced to this root cause, and a startup backfill was added that seeds the in-memory state from unsettled picks in Supabase.

## Key Points

- `_market_start_times`, `_persistent_sel_map`, and `_persistent_races` are in-memory only — lost on every restart, not persisted alongside the catalogue snapshot
- **Markets that close during restart window are permanently invisible** — the scanner only tracks markets it's actively subscribed to at suspension time
- **Startup backfill added**: Seeds from unsettled picks on restart so yesterday's races are visible to settlement scanner
- **Betfair `listMarketBook` with `SP_TRADED` projection** returns no position data for old closed markets — runner status but not winners
- **`listMarketCatalogue` returns empty** for most markets >1 day old — sel_map rebuild succeeded only 1/3 attempts
- **2+ day old picks not covered** by backfill — the orphan voider handles those at 72h (acceptable tradeoff)
- **Catalogue snapshot persists** to disk but scanner dicts don't — asymmetric persistence surface

## Details

### The Volatile State Problem

The settlement scanner operates by subscribing to Betfair market channels and listening for `CLOSED` lifecycle events. When a market closes (race result confirmed), the scanner looks up the market in `_persistent_sel_map` (maps market → selections → runners) and `_persistent_races` (maps market → canonical race identity) to grade picks. Both dictionaries are populated when the scanner discovers and subscribes to markets during normal operation.

On restart, these dictionaries are empty. The scanner rebuilds subscriptions from the current catalogue, which covers today's races. Yesterday's races — which may have closed between the old process dying and the new one subscribing — are missing from the new subscription list. Any unsettled picks from those races have no path to settlement because the scanner doesn't know they exist.

### The Backfill Solution

The startup backfill queries Supabase for all picks with `result IS NULL` and `detected_at > now() - 48h`, extracts their `canonical_id` and `race_number`, and seeds:

1. `_market_start_times` — so the scanner knows when these markets should have started
2. `_persistent_races` — so the scanner can map Betfair market events to canonical race identities

For `_persistent_sel_map` (selection → runner mapping), the backfill attempts `listMarketCatalogue` from Betfair. This works for recent markets (< 12h old) but returns empty for older ones. A fallback name-matching approach strips the "N. " prefix from Betfair runner names and matches by `sortPriority`, achieving ~33% success rate on old markets.

### Betfair API Limitations for Retroactive Settlement

Two Betfair API limitations constrain the backfill:

**`listMarketBook` (SP_TRADED)**: Returns runner `status` (WINNER/LOSER/REMOVED) for closed markets but does NOT return BSP, LTP, or position data. The runner can be identified as the winner, but the settlement record lacks the CLV metrics that fully-monitored races capture.

**`listMarketCatalogue`**: Returns empty for most markets older than ~24 hours. This means `_persistent_sel_map` can only be rebuilt for recent markets — older ones need the runner-name fallback or remain stuck until the 72h orphan voider kicks in.

### Restart Frequency Impact

Multiple deploys during racing hours (3-4 on May 26 alone) compound this problem. Each restart creates a window where closing markets are missed. The settlement queue starvation bug (see [[concepts/settlement-queue-starvation-ordering]]) had already caused 4,431 stuck picks from orphan accumulation — the restart state loss is a complementary mechanism producing orphans from a different cause.

### Future: Disk Persistence

The asymmetric persistence (catalogue snapshot on disk, scanner dicts in memory) is the root design issue. Persisting `_persistent_sel_map` and `_persistent_races` alongside the catalogue snapshot would eliminate the restart gap entirely. This is a larger project (serialization format, consistency guarantees, stale-data cleanup) but would make restarts during racing hours safe.

## Related Concepts

- [[concepts/settlement-queue-starvation-ordering]] - ASC+LIMIT 200 starvation from orphan accumulation; restart state loss is a complementary orphan-creation mechanism
- [[concepts/superwin-process-isolation-reliability]] - SIGABRT crashes from C extensions cause the restarts that trigger state loss; per-bookie subprocess isolation would contain crashes but not eliminate restart state loss
- [[connections/permanent-blacklist-no-expiry-anti-pattern]] - In-memory state that grows monotonically without persistence; the settlement scanner is the inverse: in-memory state that is lost (rather than accumulated) without persistence
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal where stuck picks appear as NULL-result rows; the 72h orphan voider converts them to VOID

## Sources

- [[daily/lcash/2026-05-28.md]] - 72 stuck picks traced to in-memory state loss; startup backfill seeds from unsettled picks; Betfair `listMarketBook` SP_TRADED returns no position data for old closed markets; `listMarketCatalogue` returns empty >1 day; sel_map rebuild 1/3 success; name matching with strip "N. " prefix + sortPriority fallback; 2+ day old picks not covered (orphan voider at 72h); catalogue snapshot persists but scanner dicts don't (Session 20:42)

