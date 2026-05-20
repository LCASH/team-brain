---
title: "Betr BlueBoost Racing Edge"
aliases: [blueboost, racing-blueboost, betr-blueboost, blueboost-edge, betr-boosted-odds]
tags: [superwin, racing, betr, edge-detection, boosted-odds]
sources:
  - "daily/lcash/2026-05-19.md"
created: 2026-05-19
updated: 2026-05-19
---

# Betr BlueBoost Racing Edge

On 2026-05-19, the SuperWin racing scanner deployed `racing-blueboost` — a new edge type exploiting betr's BlueBoost promotional pricing. BlueBoost applies boosted odds per-runner from the API (`odds.tote_win` field), with a pricing pattern where favourites get small boosts (~3%) while longshots get 20-25% — the same convexity as TabTouch SuperPicks. The edge is deployed using a `boost_field` criteria on the scanner, which reads the boosted price directly from betr's API response rather than requiring a lookup table.

## Key Points

- **BlueBoost pricing pattern**: Favourites get tiny boosts (~3%), longshots get 20-25% boosts — same shape as TabTouch SuperPicks
- **Implementation via `boost_field`** criteria (reads `odds.tote_win` from betr adapter) rather than the lookup-table path used by SuperPicks — cleaner since BlueBoost prices arrive per-runner from the API
- **Edge config**: priority 3, min_ev 5%, min_liq 200 — deployed as `racing-blueboost` edge type
- **No new adapter code needed** — the betr adapter was already capturing BlueBoost data into `odds.tote_win` since Phase 1
- **Not all races offer BlueBoost** — scanner handles null `tote_win` gracefully; the "0 entries" warning on deploy is benign (lookup-table loader checking for non-existent `betr|blueboost` table, but `boost_field` path bypasses this)
- **Expected 30-80 picks/day** — needs ~500 settled picks (~1 week) for meaningful ROI evaluation

## Details

### BlueBoost vs SuperPicks Architecture

The scanner supports two boost-detection architectures:

| Dimension | SuperPicks (TabTouch) | BlueBoost (Betr) |
|-----------|----------------------|------------------|
| Price source | Lookup table (`tabtouch\|superpicks`) | Per-runner API field (`odds.tote_win`) |
| Scanner criteria | `boost_table` | `boost_field` |
| Boost calculation | `base_odds × lookup_multiplier` | Direct from API (already boosted) |
| Availability | Specific promoted races only | Varies per race — null when no BlueBoost |

The `boost_field` path is architecturally simpler because the boosted price comes directly from the API response — the scanner doesn't need to maintain a separate table or calculate the boost. The betr adapter parses BlueBoost prices as part of its normal odds extraction, storing them in `odds.tote_win` alongside the standard `odds.win` price. The edge scanner compares the BlueBoost price against Betfair lay to determine if the boost creates +EV.

### Comparison with SuperPicks Performance

The SuperPicks edge on TabTouch (see [[concepts/superwin-racing-profitability-dimensions]]) has been validated at +38.6% ROI across 181 settled picks, with harness racing dominating (+157% ROI). BlueBoost is expected to show a similar profile because the boost shape is identical: small boosts on favourites (where the base price is already efficient, leaving no room for edge) and large boosts on longshots (where the base price has more margin, and a 20-25% boost can overcome it).

Key differences that may affect relative performance:
- **Betr's base odds may differ from TabTouch** — different pricing models mean the "before boost" starting point is different
- **BlueBoost availability may be more or less selective** — if betr offers BlueBoost on more races, the average quality per pick may be lower
- **Detection speed advantage**: Our 1Hz polling is 14x faster than betr's own UI (see [[concepts/betr-no-websocket-xhr-only-architecture]]), vs TabTouch where the speed advantage is smaller

### betr Integration Context

betr was onboarded as a racing bookie in the same session, with 419 races exposed (including tomorrow's card via `DaysToRace=0,1`) vs ~170 for other bookies. Three operational improvements were made alongside BlueBoost:

1. **Empty odds filtering**: Races without actual win odds are now universally filtered (not just betr) — Betfair exempt since it provides scaffold via lay prices
2. **Proxy timeout tuning**: Reduced from 10s→4s with 60s quarantine for dead proxies, eliminating 18s stalls
3. **DaysToRace look-ahead**: betr's tomorrow-card exposure acts as a "scout" — races auto-merge when Betfair/TAB open markets later

## Related Concepts

- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal that BlueBoost picks will flow into; same insert-only pattern, BSP→LTP CLV cascade
- [[concepts/superwin-racing-profitability-dimensions]] - SuperPicks ROI by race type, liquidity band, and mode provides the comparison framework for BlueBoost evaluation
- [[concepts/betr-no-websocket-xhr-only-architecture]] - The transport investigation confirming betr's XHR-only architecture; our 1Hz polling provides the speed advantage for detecting BlueBoost opportunities
- [[concepts/scanner-warmup-false-ev-guard]] - Warmup guard applies to betr ramp-up (20-40s for REST discovery) just as it does to TAB/TabTouch
- [[connections/liquidity-efficiency-inverse-in-betting]] - BlueBoost's longshot premium follows the liquidity-efficiency inverse: thin markets (longshots) sustain larger mispricings

## Sources

- [[daily/lcash/2026-05-19.md]] - BlueBoost deployed as `racing-blueboost` edge: `boost_field` criteria reads `odds.tote_win`; priority 3, min_ev 5%, min_liq 200; favourites ~3% boost, longshots 20-25%; "0 entries" warning benign (lookup-table path not used); expected 30-80 picks/day; compare vs SuperPicks after 500 settled picks (Session 14:18). betr adapter onboarding: 419 races with DaysToRace=0,1 look-ahead; empty odds filtering added universally; proxy timeout 10s→4s with 60s quarantine (Sessions 13:47, 15:20)
