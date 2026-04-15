---
title: "Pinnacle Prediction Market Pipeline"
aliases: [pinnacle-pipeline, prediction-markets, virtual-sport, kalshi-polymarket]
tags: [value-betting, pinnacle, prediction-markets, dashboard, integration]
sources:
  - "daily/lcash/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# Pinnacle Prediction Market Pipeline

A new theory pipeline in the value betting scanner that uses Pinnacle as the sharp reference to evaluate prediction market books (Kalshi, Polymarket, DraftKings Predictions, Underdog, Crypto.com) as soft books. Committed as `9a0b19d` on 2026-04-15 with dashboard support via a virtual sport pill and a `sportSupabaseFilter()` helper. The pipeline was verified end-to-end with data flowing but zero picks firing — confirmed as correct behavior due to the 3-hour pre-tipoff window constraint.

## Key Points

- Pinnacle serves as the sharp reference for devigging; prediction market platforms are evaluated as soft books for +EV opportunities
- Prediction market book IDs: Kalshi (950), Polymarket (970), DraftKings Predictions (971), Underdog (980), Crypto.com (981/982)
- Dashboard includes a virtual sport pill for the Pinnacle theory — not tied to a single sport but to the theory's cross-sport scope
- Pipeline verified end-to-end: Polymarket (348 markets), Kalshi (168), Pinnacle (402) all visible on VPS
- Zero picks firing confirmed correct — all NBA games were outside the 3-hour pre-tipoff window; no code change needed
- Committed as `9a0b19d` on main: 5 files changed, +177/-28 lines

## Details

### Architecture

The Pinnacle prediction market pipeline extends the existing theory system (see [[concepts/value-betting-theory-system]]) with a new sharp-vs-soft pairing. Traditional theories use OpticOdds sharp books (Pinnacle, Circa) as the "true odds" reference and evaluate Australian retail soft books (Ladbrokes, PointsBet AU, Sportsbet) for +EV. The Pinnacle theory uses Pinnacle directly as the sharp reference and evaluates prediction market platforms as soft books.

This is architecturally significant because it diversifies the system's soft book universe beyond traditional sportsbooks. Prediction markets operate with different pricing mechanisms (order books vs. market-maker spreads), different liquidity profiles, and different regulatory frameworks. Finding +EV on prediction markets relative to Pinnacle's sharp line represents a genuinely different edge source than finding +EV on Australian retail books.

### Book ID Assignment

New book IDs were assigned for the prediction market platforms:
- **Kalshi**: 950
- **Polymarket**: 970
- **DraftKings Predictions**: 971
- **Underdog**: 980
- **Crypto.com**: 981, 982 (two IDs, likely for different product tiers or regions)

These IDs follow the existing convention where traditional sportsbooks use lower ranges (365 for Bet365, 800-series for Australian books) and prediction markets occupy the 900+ range.

### Dashboard Integration

The dashboard was updated with two features:

1. **Virtual sport pill**: Since the Pinnacle theory evaluates prediction markets across sports (not tied to a single sport like NBA or AFL), a virtual sport pill was added to the dashboard. This allows filtering to see only Pinnacle-theory picks without conflating them with sport-specific theory picks.

2. **`sportSupabaseFilter()` helper**: A utility function for constructing sport-specific Supabase queries, ensuring the Pinnacle theory's cross-sport scope is correctly handled in database queries.

### The loadTheories() Discovery

The Pinnacle pipeline verification exposed a critical dashboard bug: the `loadTheories()` JavaScript function was silently dropping `soft_books` and five other fields when mapping Supabase rows to JS objects. This caused the Pinnacle pill to show EV against Australian soft books (Ladbrokes, PointsBet) instead of the intended prediction markets (Kalshi, Polymarket). The fix was deployed in the same commit. See [[concepts/dashboard-client-server-ev-divergence]] for the full bug analysis.

### End-to-End Verification

On 2026-04-15, lcash verified the pipeline after deployment:
- **Data flow confirmed**: Polymarket (348 markets), Kalshi (168 markets), Pinnacle (402 markets) all visible on VPS
- **Zero picks firing**: Confirmed correct. The Pinnacle theory has a 3-hour pre-tipoff window constraint, and all NBA games were either already tipped off (today's) or more than 24 hours out (tomorrow's). No code change needed.
- **Dashboard verified**: Pinnacle pill correctly filtered to prediction markets only after the `loadTheories()` bug fix and hard refresh

### Commit Details

Committed as `9a0b19d` on main — 5 files changed, +177/-28 lines. Includes:
- Prediction market book IDs (Kalshi 950, Polymarket 970, DraftKings Predictions 971, Underdog 980, Crypto.com 981/982)
- Virtual sport pill
- `sportSupabaseFilter()` helper
- The `loadTheories()` bug fix (soft_books, prop_filter, max_line_gap, line_gap_penalty, max_line, excluded_props explicitly mapped)

### Stash/Restore Workflow

The Pinnacle work was committed using a stash/restore pattern to isolate it from pre-existing uncommitted bet365 feature branch work. The uncommitted bet365 coupon endpoint changes (see [[concepts/bet365-nba-coupon-endpoint]]) were stashed, the Pinnacle commit was made on main, and the stash was restored afterward. This avoided mixing unrelated changes in a single commit.

## Related Concepts

- [[concepts/value-betting-theory-system]] - The theory system that the Pinnacle pipeline extends with a new sharp/soft pairing
- [[concepts/dashboard-client-server-ev-divergence]] - The loadTheories() bug discovered during Pinnacle pipeline verification
- [[concepts/opticodds-critical-dependency]] - Pinnacle data is accessed via OpticOdds; this pipeline depends on OpticOdds having Pinnacle coverage
- [[concepts/bet365-nba-coupon-endpoint]] - The bet365 work stashed/restored around this commit

## Sources

- [[daily/lcash/2026-04-15.md]] - Pinnacle theory committed (9a0b19d, +177/-28 lines): prediction market book IDs (Kalshi 950, Polymarket 970, DraftKings Predictions 971, Underdog 980, Crypto.com 981/982), virtual sport pill, sportSupabaseFilter helper; pipeline verified end-to-end (Polymarket 348, Kalshi 168, Pinnacle 402 markets); zero picks correct (outside 3h window); stash/restore pattern for branch isolation (Sessions 22:03, 22:36)
