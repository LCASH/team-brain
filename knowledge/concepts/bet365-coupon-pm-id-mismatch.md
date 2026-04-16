---
title: "bet365 Coupon-PM Participant ID Mismatch"
aliases: [coupon-pm-mismatch, barrier-number-join, participant-id-mismatch, runner-name-matching]
tags: [bet365, racing, data-quality, streaming, reverse-engineering]
sources:
  - "daily/lcash/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# bet365 Coupon-PM Participant ID Mismatch

bet365's racing coupon HTTP responses use different participant IDs than the PM (price message) WebSocket subscriptions. Direct `participant_map.get(pa_id)` fails for a significant portion of runners because the IDs from coupon parsing don't match the IDs used in PM subscriptions. The reliable join key between the two data sources is `(fixture_id, barrier_number)`, not participant ID. Adding this secondary lookup doubled race coverage from 23→46 matched races and odds-bearing races from 16→39.

## Key Points

- bet365 coupon PA entries use different participant IDs than PM (price message) WebSocket subscriptions — direct ID match fails for many runners
- Barrier number is the reliable join key between coupon data and PM subscription data: `(fixture_id, barrier_number)` lookup succeeds where `participant_map.get(pa_id)` fails
- Adding secondary barrier-number lookup doubled race coverage: 23→46 matched races, 16→39 with live odds
- Horses and harness match 80-100% of runners reliably with the barrier fallback
- Greyhounds remain broken at 0/7 matched — different naming/numbering scheme (trap/box vs barrier) requires separate handling
- bet365 only sends odds for races close to jump time (~60 min window), so far-out races legitimately show no prices

## Details

### The ID Divergence

The bet365 racing adapter's pipeline (see [[concepts/bet365-racing-adapter-architecture]]) has two data paths that must be reconciled:

1. **Coupon path (HTTP):** The `racecoupon` endpoint returns full race card data including runner names, jockeys, weights, and participant IDs. These IDs are used as keys in the `participant_map` built during the runner map phase.

2. **PM path (WebSocket):** The WS stream delivers odds updates keyed by PM subscription topics (`PM{fixture}-{participant}`). The participant IDs in PM messages are the IDs used when subscriptions were sent.

The assumption that these IDs would match was incorrect. When the adapter iterates coupon data to name runners in the `participant_map`, `participant_map.get(pa_id)` returns `None` for runners whose coupon ID doesn't match their PM subscription ID. This produced the initial 39% naming rate (198/502 participants named on Mac test, 221/484 on Dell).

### The Barrier Number Solution

The barrier/post number (`PN=` field in the bet365 protocol — see [[concepts/bet365-racing-data-protocol]]) is consistent across both data paths. The same horse running from barrier 3 will have `PN=3` in the coupon response and will be the third participant in the fixture's PM subscription ordering. This makes `(fixture_id, barrier_number)` a reliable composite key for joining coupon metadata with PM streaming data.

The fix adds a secondary lookup path: when the primary `participant_map.get(pa_id)` fails, the adapter falls back to searching for a participant in the same fixture with a matching barrier number. This doubled the matched race count from 23 to 46 and the odds-bearing races from 16 to 39, because many runners that were previously unnamed and unmatchable could now be associated with their coupon metadata.

### Greyhound Exception

The barrier-number fallback solves horses and harness racing (80-100% match rate) but not greyhounds (0/7 matched). Greyhound racing uses a trap/box numbering system that doesn't align with Betfair's barrier numbering scheme. The mismatch is fundamental: a greyhound in trap 4 at bet365 may not correspond to box 4 at Betfair, because the numbering conventions differ between the two platforms. Greyhound matching requires a separate fix — likely name-based matching or a trap-to-box mapping table.

### Production Deployment Metrics

The multi-fixture streaming system was deployed to both Dell server and VPS on 2026-04-16:

- **Mac local test:** 502 participants, 24 fixtures, 13 meetings, 198/502 named (39%)
- **Dell deployment:** 484 participants, 25 fixtures, 12 meetings, 221/484 named (44%)
- **After barrier fix:** 46 races matched to Betfair catalogue, 39 with live odds, bookies=2 (bet365 merged alongside Betfair)
- **Dell CPU impact:** 66-94% utilization (avg ~78%), adding ~15-20% over the ~60% baseline from NBA/MLB workers

The slight variance between Mac (13 meetings) and Dell (12 meetings) is normal — meeting availability changes over time as races start and finish.

## Related Concepts

- [[concepts/bet365-racing-adapter-architecture]] - The adapter whose runner map phase was affected by this mismatch
- [[concepts/bet365-racing-data-protocol]] - The `PN=` barrier number field used as the join key
- [[concepts/websocket-constructor-injection]] - The WS capture technique that provides the PM subscription IDs
- [[concepts/cdp-browser-data-interception]] - The CDP technique that captures the coupon HTTP response IDs

## Sources

- [[daily/lcash/2026-04-16.md]] - Coupon PA IDs ≠ PM subscription IDs; barrier number as secondary join key doubled coverage (23→46 races, 16→39 with odds); horses/harness 80-100%, greyhounds 0/7; Dell 484 participants 12 meetings; CPU 66-94% (Sessions 12:26, 14:10, 15:16, 15:46)
