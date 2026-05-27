---
title: "Mug-Bet Qualifying Loss Edges"
aliases: [mug-bet, qualifying-loss, mug-edge, account-sustainability-mugging, ql-formula]
tags: [superwin, racing, edge-detection, matched-betting, account-sustainability]
sources:
  - "daily/lcash/2026-05-27.md"
created: 2026-05-27
updated: 2026-05-27
---

# Mug-Bet Qualifying Loss Edges

On 2026-05-27, lcash added mug-bet (qualifying loss) edges to the SuperWin racing scanner as a new edge type for account sustainability. Mug bets are deliberately placed losing bets at controlled QL% (qualifying loss percentage) to make an account appear like a normal recreational punter, preventing bookmaker account restrictions (gubbing). The formula is `QL% = ((X - c) - B * (1 - c)) / (X - c)` where X=lay odds, B=back odds, c=BF commission. Eight `mug-{bookie}` edges were deployed across all bookies with criteria-driven configuration via Supabase.

## Key Points

- **Qualifying loss formula**: `QL% = ((X - c) - B * (1 - c)) / (X - c)` where X=lay odds, B=back odds, c=BF commission (5%)
- **8 bookie-specific edges deployed**: tab, tabtouch, betr, boostbet, neds, pointsbet, sportsbet, bet365 — each configurable independently via Supabase
- **Natural QL% floor is ~4.2%** due to bookie/exchange spread + 5% BF commission — a strict 4% gate fires zero picks on a normal day
- **Distribution heavily skewed**: 98%+ of back/lay pairs have QL >20%; only 3 pairs were sub-6% across 5,180 checked on deployment day
- **New Opportunity fields**: `mug_ql_pct`, `mug_lay_stake`, `mug_guaranteed_loss`, `mug_lay_odds`, `mug_back_odds` — all streamed via SSE alongside +EV picks
- **Guard constraints**: `min_field_size: 6`, `min_back_odds: 2.0` to avoid favorites and tiny fields
- **Per-bookie thresholds may be optimal**: tight (4%) on watched accounts (Sportsbet/Bet365), loose (8%) on relaxed ones

## Details

### Why Mug Bets Matter

Sportsbook accounts that consistently bet only on +EV opportunities get restricted (gubbed) — the bookmaker limits max stake or closes the account entirely. Mug bets counteract this by creating a betting pattern that looks recreational: occasional losing bets on standard markets at normal odds, alongside the +EV edge picks. The scanner now identifies the best available mug opportunities — back/lay pairs where the guaranteed loss is minimized while the bet still looks natural.

The QL% represents the guaranteed loss as a percentage of the back stake when the bet is matched (back at the bookie, lay on Betfair Exchange). A 4% QL means a $100 back bet with a matched lay loses approximately $4 regardless of outcome. Lower QL% means cheaper mugging; the scanner filters for opportunities below a configurable threshold.

### Implementation Architecture

Mug mode plugs into the scanner alongside existing edge modes (normal, SuperPicks, Cash Multiplier, BlueBoost, THE MULT, refund-bonus) via a criteria-driven branch — no per-bookie code needed. The scanner evaluates each race's back/lay pairs for mug opportunities the same way it evaluates +EV opportunities, applying the QL formula and checking against the configured threshold.

Each mug edge is a separate Supabase row with its own `min_ql` threshold, `min_field_size`, and `min_back_odds` criteria. This allows per-bookie threshold tuning: Sportsbet (which aggressively gubs) might use 4% while Betr (more relaxed) might use 8%.

### Distribution Reality

The deployment day analysis of 5,180 back/lay pairs revealed the practical constraints:

| QL Band | Count | Assessment |
|---------|-------|------------|
| < 4% | 0 | Unreachable with 5% BF commission |
| 4-5% | 3 | Extremely rare — requires near-zero bookie/exchange spread |
| 5-8% | ~30 | Occasional — best opportunities when bookie=Betfair lay |
| 8-20% | ~200 | Regular — sufficient for daily mugging needs |
| > 20% | ~4,900 | Vast majority — too expensive for systematic mugging |

The 4.2% floor is mathematical: with 5% Betfair commission, even when the bookie price exactly matches the Betfair lay (zero spread), the commission alone produces 4.2% QL. The user needs to decide whether to keep the 4% gate (essentially zero fires), loosen to 6% (~10-30 opportunities/day), or 8% (~13+/day). The threshold is flippable via Supabase PATCH with no code change.

## Related Concepts

- [[concepts/superwin-edge-pick-backtesting]] - Mug picks flow through the same backtesting journal alongside +EV picks; settlement uses standard WIN/LOSE outcomes
- [[concepts/superwin-execution-gap-price-band-discipline]] - Mug bets address the account sustainability dimension that the execution gap analysis highlighted: accounts get gubbed before the profitable price bands can be fully exploited
- [[concepts/superwin-racing-profitability-dimensions]] - Mug-bet is a 6th edge mode alongside Normal, SuperPicks, Cash Multiplier, BlueBoost, and THE MULT
- [[concepts/racing-refund-bonus-edge]] - Another non-standard edge type with custom settlement logic (PLACE_REFUND); mug bets have simpler settlement (standard WIN/LOSE)

## Sources

- [[daily/lcash/2026-05-27.md]] - 8 mug-{bookie} edges deployed; QL formula with BF commission; natural 4.2% floor from 5% commission; 5,180 pairs checked, 3 sub-6%; new Opportunity fields (mug_ql_pct, mug_lay_stake, etc.); guard constraints min_field_size 6, min_back_odds 2.0; per-bookie threshold suggestion; pending user decision on QL% threshold (Session 10:24)

```
