---
title: "Push Loop Heartbeat for Static Market Freshness"
aliases: [push-heartbeat, captured-at-heartbeat, push-heartbeat-refresh, diff-dedup-staleness, static-market-freshness]
tags: [value-betting, architecture, data-quality, pipeline, staleness]
sources:
  - "daily/lcash/2026-06-03.md"
created: 2026-06-03
updated: 2026-06-03
---

# Push Loop Heartbeat for Static Market Freshness

On 2026-06-03, the `/topdown` dashboard showed zero picks despite healthy scrapers because diff-only push deduplication (`if prev == odds: continue`) silently starved downstream freshness gates when markets were legitimately static. Bet365 NBA median age was 13,426s (3.7h), MLB 11,115s (3h) — both far beyond the `MAX_SHARP_AGE_S = 600` threshold. The fix introduces a `PUSH_HEARTBEAT_S=120` (env-tunable) interval that re-pushes unchanged odds every 2 minutes to keep `captured_at` fresh, applied to both `_bet365_push_loop` and `_direct_scraper_push_loop`.

## Key Points

- Diff-only push deduplication starves downstream freshness gates when markets are legitimately static — closed NBA Finals markets and frozen MLB lines between scrapes had `captured_at` ages of 3+ hours
- `captured_at` semantically should mean "scraper still quoting this value at time T", not "odds last moved at time T" — the fix restores this intended semantics
- The `PUSH_HEARTBEAT_S = 120` parameter is env-tunable; the `last_pushed` cache structure changed from `{key: odds_value}` to `{key: (odds_value, last_push_time)}` tuple to track push timing alongside value
- Push volume impact is trivial: approximately 4 extra entries/sec total across all books
- Both push loops (bet365 and direct scraper) had identical dedupe structures and received the same heartbeat fix

## Details

The core distinction exposed by this bug is between "data freshness" and "observation freshness." The scraper was alive and actively confirming that a market was still quoting the same odds, but the push loop's dedup logic hid this confirmation from downstream consumers. From the pipeline's perspective, a market whose odds hadn't changed in 3 hours looked identical to a market whose scraper had crashed 3 hours ago — both had stale `captured_at` timestamps. The heartbeat fix ensures that continued observation is propagated even when the observed value hasn't changed, restoring the pipeline's ability to distinguish "stable market" from "dead scraper."

This is the same class of bug as the `captured_at` override at `state.py:2115` that caused the dashboard-pick-flashing-stale-odds issue, but manifesting at the push-loop layer rather than the state layer. During diagnosis, three fix options were evaluated: Option A (bump the `MAX_SHARP_AGE_S` threshold) was rejected because it would mask genuine staleness from actual scraper failures. Option B (the heartbeat, chosen) directly addresses the semantic gap between "unchanged" and "unobserved." Option C (per-book heartbeat field as a separate metadata channel) was deferred as a future architectural improvement that would cleanly separate observation metadata from odds data, but was unnecessary for the immediate fix.

## Related Concepts

- [[concepts/odds-staleness-pipeline-diagnosis]] - The broader class of staleness bugs in the odds pipeline
- [[concepts/dashboard-pick-flashing-stale-odds]] - The same `captured_at` semantic bug at the state.py layer
- [[concepts/trail-change-detection-architecture]] - Trail system that also depends on fresh `captured_at` timestamps

## Sources

- [[daily/lcash/2026-06-03.md]] - Session 09:56 (zero picks diagnosis from static market staleness, heartbeat fix designed and deployed to both push loops)
