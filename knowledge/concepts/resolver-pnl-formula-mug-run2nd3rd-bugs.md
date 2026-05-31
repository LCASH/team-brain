---
title: "Resolver PnL Formula Bugs: Mug Back-Only and Run-2nd-3rd Hardcoded Slug"
aliases: [mug-pnl-back-only, run-2nd-3rd-hardcoded-slug, pnl-formula-mug-bug, mode-slug-settlement-match]
tags: [superwin, racing, resolver, bug, settlement, pnl]
sources:
  - "daily/lcash/2026-05-29.md"
created: 2026-05-29
updated: 2026-05-29
---

# Resolver PnL Formula Bugs: Mug Back-Only and Run-2nd-3rd Hardcoded Slug

On 2026-05-29, lcash discovered two resolver bugs that massively distorted PnL reporting for mug-bet and run-2nd-3rd edge modes. Bug 1: the resolver computed back-only PnL for mug mode instead of the correct equalised lay-leg matched-betting formula, making mug mode appear profitable (+60.2u) when it was actually losing (−10.7u). Bug 2: run-2nd-3rd position settlement was hardcoded to match `racing-run-2nd-3rd-sportsbet` slug only, so boostbet/neds/pointsbet never received `PLACE_REFUND` settlement — silently settling as full losses instead.

## Key Points

- **Mug PnL swing: +60.2u → −10.7u (−70.9u swing)** — back-only formula ignores the lay-leg offset that defines matched betting; mug mode is designed to lose (qualifying loss), so positive PnL was the tell
- **Run-2nd-3rd PnL swing: −258.7u → −138.7u (+120u swing)** — hardcoded slug prevented all non-sportsbet bookies from receiving PLACE_REFUND settlement
- **BoostBet (+24.6u) and PointsBet (+34.7u) run-2nd-3rd edges are actually profitable** — previously hidden by the slug-match bug treating 2nd/3rd finishes as full losses
- **Fix: mug PnL now uses equalised lay-leg formula**; run-2nd-3rd settlement now matches on `mode_slug` instead of exact edge slug, so any bookie's run-2nd-3rd edge settles correctly
- **Impact on edge-config decisions**: any edges disabled or tuned down based on the old (incorrect) PnL data should be re-evaluated

## Details

### Bug 1: Mug Mode Back-Only PnL

The resolver was computing PnL for all modes using a back-only formula: `PnL = (bookie_odds - 1) * stake` for wins, `-stake` for losses. This is correct for value/boost/refund modes where the bettor takes directional risk. For mug mode (matched betting), the correct formula is the equalised lay-leg calculation that accounts for both the back bet at the bookie and the lay bet at the exchange:

```
Mug PnL = back_result - lay_result
        = (back_odds - 1) × back_stake - (lay_odds - 1) × lay_stake  [if back wins]
        = -back_stake + lay_stake                                      [if back loses]
```

The net outcome for a mug bet is always a small loss (the qualifying loss) regardless of the race result. The back-only formula showed mug mode as +60.2u because it counted the back-bet wins without subtracting the corresponding lay-bet losses. The corrected PnL of −10.7u is consistent with the expected qualifying loss profile.

The user spotted this anomaly because mug mode showing as the most profitable edge contradicted its fundamental design as a qualifying-loss mechanism for account sustainability.

### Bug 2: Run-2nd-3rd Hardcoded Slug

The position settlement branch in the resolver matched edge picks using a hardcoded string check:

```python
if pick.edge_slug == "racing-run-2nd-3rd-sportsbet":
    # Apply PLACE_REFUND settlement for 2nd/3rd
```

When boostbet, neds, and pointsbet run-2nd-3rd edges were deployed (slugs `racing-run-2nd-3rd-boostbet`, etc.), they never matched this condition. Picks that finished 2nd or 3rd were settled as full losses (`-1.00`) instead of `PLACE_REFUND` (`-0.20` at 80% bonus conversion).

The fix changed from exact slug matching to mode-slug matching:

```python
if pick.mode_slug == "run-2nd-3rd":
    # Apply PLACE_REFUND settlement for 2nd/3rd — works for ALL bookies
```

This revealed that boostbet and pointsbet run-2nd-3rd edges were actually profitable, previously hidden behind 120 units of phantom losses from incorrect settlement.

### Anti-Pattern: Hardcoding Entity Slugs in Settlement Logic

Hardcoding specific edge slugs instead of matching on the generic mode is a recurring trap when new bookies are added to an existing edge type. The slug-match approach silently breaks for every new bookie — there's no error, the settlement just grades picks wrong. Mode-slug matching is inherently extensible: any new `racing-run-2nd-3rd-{bookie}` edge automatically receives correct PLACE_REFUND settlement without code changes.

## Related Concepts

- [[concepts/mug-bet-qualifying-loss-edges]] - The mug-bet edge type whose PnL was distorted by Bug 1
- [[concepts/racing-refund-bonus-edge]] - The run-2nd-3rd edge type whose multi-bookie settlement was broken by Bug 2
- [[concepts/superwin-racing-profitability-dimensions]] - PnL corrections change the profitability matrix for two edge modes
- [[concepts/superwin-edge-pick-backtesting]] - Backtesting journal where the corrected PnL now reflects accurate edge performance

## Sources

- [[daily/lcash/2026-05-29.md]] - Mug mode appeared most profitable (contradicting design); back-only PnL swung +60.2u→−10.7u; run-2nd-3rd hardcoded slug swung −258.7u→−138.7u; boostbet +24.6u, pointsbet +34.7u now visible; mode-slug match fix deployed; Mode Library UI added to dashboard (Session 09:45)
