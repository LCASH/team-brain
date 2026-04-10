# Glossary

## Status: current
## Last verified: 2026-04-08

> Domain terminology for sports betting and value betting.

---

## Betting Fundamentals

| Term | Definition |
|------|-----------|
| **Decimal odds** | European odds format. 2.00 = even money. Payout = stake × odds. |
| **Implied probability** | 1 / decimal_odds. Includes the vig. |
| **Vig (vigorish)** | The bookmaker's margin. Both sides sum to >100% implied probability. |
| **True probability** | The estimated fair probability after removing vig. |
| **True odds** | 1 / true_probability. The fair price without margin. |
| **Edge** | The mathematical advantage: `(book_odds / true_odds - 1)` |
| **+EV (positive expected value)** | A bet where edge > 0. You expect to profit long-term. |
| **Line** | The threshold in a prop bet (e.g., 25.5 in "Over 25.5 Points") |
| **Prop (proposition)** | A bet on a specific player stat rather than game outcome |
| **Over/Under** | Two sides of a prop: player goes over or under the line |

## Value Betting Concepts

| Term | Definition |
|------|-----------|
| **Sharp book** | A bookmaker with accurate, low-margin odds. Prices move to true value quickly. |
| **Soft book** | A bookmaker with higher margins, slower adjustments. Where you find +EV. |
| **Devig / Devigging** | Removing the vig from a book's odds to estimate true probabilities. |
| **CLV (Closing Line Value)** | How much the line moved in your favor after your bet. Proxy for edge quality. |
| **Consensus** | Agreement across many books. Used as fallback when no sharp books have data. |
| **Interpolation** | Adjusting true probability when sharp and soft books have different lines. |

## Statistical Methods

| Term | Definition |
|------|-----------|
| **Brier score** | `mean((predicted_prob - actual_outcome)^2)`. Measures calibration. Lower = better. |
| **Log loss** | `-mean(actual*log(pred) + (1-actual)*log(1-pred))`. Measures discrimination. Lower = better. |
| **Multiplicative devig** | Proportional vig removal: `p = (1/odds) / sum(1/odds)` |
| **Additive devig** | Equal margin removal: `p = 1/odds - margin/2` |
| **Power devig** | Favorite-longshot bias correction via exponent solving |
| **Shin devig** | Insider-trading model (≈ additive for 2-way) |
| **Logit interpolation** | Line adjustment via sigmoid transform for continuous props |
| **Poisson interpolation** | Line adjustment via Poisson distribution for count props |

## System Terms

| Term | Definition |
|------|-----------|
| **Theory** | A named config of devig weights, book weights, and thresholds |
| **Confidence** | 0–5.0 score reflecting how much sharp book data supports a pick |
| **Trail** | The sequence of odds changes for a tracked pick over time |
| **Trail entry** | A single odds change record (append-only, ~200 bytes) |
| **Cycle** | One iteration of the scrape → devig → track loop (~20 seconds) |
| **Resolver** | Auto-grades picks as hit/miss/push using actual player stats |
| **Push worker** | Aggregates all sport servers into a single stream |
| **Relay mode** | Server mode that reads from other servers instead of running its own pipeline |
