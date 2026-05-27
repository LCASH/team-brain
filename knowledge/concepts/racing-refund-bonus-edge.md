---
title: "Racing Run-2nd-3rd Refund-Bonus Edge"
aliases: [refund-bonus-edge, run-2nd-3rd, place-refund-edge, sportsbet-refund-bonus, racing-run-2nd-3rd]
tags: [superwin, racing, edge-detection, settlement, architecture]
sources:
  - "daily/lcash/2026-05-26.md"
created: 2026-05-26
updated: 2026-05-26
---

# Racing Run-2nd-3rd Refund-Bonus Edge

On 2026-05-26, lcash deployed the `racing-run-2nd-3rd-sportsbet` refund-bonus edge end-to-end — a new edge type where sportsbooks refund the stake as a bonus bet if the selected runner finishes 2nd or 3rd. The EV formula incorporates `bonus_conversion` (assumed 0.80 — the expected value of a bonus bet vs cash) and requires both bookie win odds and Betfair place lay for accurate calculation. The edge includes a new `PLACE_REFUND` settlement outcome and `position_settlement` resolver branch. Expected volume: 5-15 picks/day, concentrated in Saturday metro + Wednesday night metro blocks. First real pick landed at +6.5% EV.

## Key Points

- **EV formula**: Incorporates `bonus_conversion_assumed` (0.80) to value the refund-as-bonus — a $10 refund as a bonus bet is worth ~$8 in expected cash value
- **New settlement outcome**: `PLACE_REFUND` — WIN returns `+(bookie_odds−1)`, PLACE_REFUND returns `−0.20` (stake lost but 80% recovered via bonus), LOSE returns `−1`
- **Requires both bookie win odds AND Betfair place lay** — EV only goes positive when sportsbet drifts long on metro-Saturday mid-priced runners in 10+ fields
- **INSERT path gated on `bonus_conversion_assumed is not None`** — prevents non-refund edges from being affected by the DDL timing
- **`min_field_size: 8`** criteria prevents firing on small fields where 2nd/3rd probability is too high (refund probability inflates EV unrealistically)
- **First real pick at +6.5% EV** with both new DB columns populated (`bf_place_lay=1.15`, `bonus_conversion_assumed=0.80`)
- **Expected volume**: 5-15 picks/day; Sportsbet prices are shorter than Betfair lay on morning meets — EV only positive when sportsbet drifts long

## Details

### The Refund-Bonus EV Model

Standard racing edge EV is simple: `(bookie_odds / betfair_lay) - 1`. The refund-bonus edge adds a second component: the expected value of receiving a bonus bet if the runner finishes 2nd or 3rd. The full formula:

```
EV = P(win) × (bookie_odds - 1) + P(2nd_or_3rd) × bonus_conversion - P(lose) × 1
```

Where `bonus_conversion` (assumed 0.80) represents the fraction of a bonus bet's face value that can be converted to cash through subsequent betting. This is an empirical estimate — a perfect bettor could extract ~85-90% of bonus bet value, but a realistic bettor achieves ~75-80%.

The edge fires only when the combined win + refund EV exceeds the threshold. This is most likely when sportsbooks offer longer odds than Betfair's lay price on mid-priced runners ($5-15 range) in fields of 8+ runners — conditions that concentrate on Saturday metro and Wednesday night metro racing cards.

### Settlement Architecture

The resolver handles three outcomes for refund-bonus edges:

| Outcome | Condition | PnL |
|---------|-----------|-----|
| WIN | Runner finishes 1st | `+(bookie_odds - 1)` |
| PLACE_REFUND | Runner finishes 2nd or 3rd | `-(1 - bonus_conversion)` = `-0.20` |
| LOSE | Runner finishes 4th or worse | `-1.00` |

The `PLACE_REFUND` outcome means the bettor loses the cash stake but receives a bonus bet of equal value. At 80% conversion, the net loss is only 20% of stake — dramatically better than a full loss but still negative.

### Multi-Bookie Expansion

The refund-bonus pattern is configured per-bookie in Supabase — `racing-run-2nd-3rd-sportsbet`, `racing-run-2nd-3rd-neds`, `racing-run-2nd-3rd-boostbet` etc. Each uses the same EV formula and settlement logic but targets a specific bookie's run-2nd-3rd promotion. Not all bookies offer this promotion, and the terms (which races, field size requirements, bonus bet restrictions) vary by bookie.

## Related Concepts

- [[concepts/superwin-mult-place-market-edge]] - THE MULT is a different place-market edge (10% TAB place boost); refund-bonus is a win-market edge with place-outcome insurance
- [[concepts/superwin-edge-pick-backtesting]] - Refund-bonus picks flow through the same backtesting journal; PLACE_REFUND is a new outcome category alongside WIN/LOSE/VOID/SCRATCHED
- [[concepts/settlement-queue-starvation-ordering]] - Settlement scanner restart blind spot particularly affects refund-bonus edges since place outcome requires Betfair result data
- [[concepts/superwin-racing-profitability-dimensions]] - Refund-bonus adds a new edge dimension to the profitability matrix; expected 5-15 picks/day

## Sources

- [[daily/lcash/2026-05-26.md]] - Full implementation: scanner criteria (min_field_size, EV formula with bonus_conversion), resolver (PLACE_REFUND outcome, position_settlement branch), persistence (ev_trail with pl_lay + bn_cv); first real pick +6.5% EV with bf_place_lay=1.15, bonus_conversion=0.80; expected volume 5-15 picks/day Saturday metro + Wednesday night; INSERT gated on bonus_conversion_assumed is not None; 500 stuck picks discovered from settlement scanner blind spot (Session 11:13)
