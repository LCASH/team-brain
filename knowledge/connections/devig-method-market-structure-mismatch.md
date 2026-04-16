---
title: "Connection: Devig Method Must Match Market Structure"
connects:
  - "concepts/soccer-three-way-devig-phantom-ev"
  - "concepts/one-sided-consensus-structural-bias"
  - "concepts/afl-circular-devig-trap"
  - "concepts/value-betting-theory-system"
sources:
  - "daily/lcash/2026-04-16.md"
  - "daily/lcash/2026-04-14.md"
created: 2026-04-16
updated: 2026-04-16
---

# Connection: Devig Method Must Match Market Structure

## The Connection

Three independent bugs in the value betting scanner share a single root cause: the devigging method's assumptions about market structure did not match the actual structure of the market being evaluated. Each case produced phantom EV signals — confidently wrong picks that appeared profitable but were systematically losers.

## Key Insight

The non-obvious insight is that **devig method selection is a safety-critical configuration choice, not a mathematical preference.** Choosing the wrong devig method doesn't merely produce suboptimal results — it produces structurally biased EV signals that look correct but point in a systematically wrong direction. All three cases were invisible to standard monitoring because the pipeline operated without errors, picks were triggered with plausible-looking EVs, and only outcome analysis (or manual inspection) revealed the bias.

The three cases form a taxonomy of market structure mismatches:

| Case | Structural Mismatch | Effect | Magnitude |
|------|---------------------|--------|-----------|
| **Soccer 3-way** | 3-outcome market evaluated as 2-outcome | Draw probability redistributed across both sides | 20-41% phantom EV |
| **AFL one_sided_consensus** | 2-sided market evaluated as 1-sided | All Under selections silently skipped | 951:13 Over/Under imbalance |
| **AFL circular devig** | Correlated retail books treated as independent sharps | Self-referential "true odds" | +1.16% CLV but -34.2% ROI |

Each mismatch operates at a different level — outcome count, side coverage, and book independence — but the consequence is identical: the devigged "true probability" is wrong, and every EV calculation downstream inherits the error.

## The Compound Risk

These mismatches are particularly dangerous because they are **invisible at the pick level.** An individual soccer pick showing +25% EV looks exactly like a genuine value opportunity. The phantom signal is only detectable through:

1. **Aggregate outcome analysis** — actual win rates deviate from implied probabilities (AFL: 28% WR vs implied ~50%)
2. **Structural sanity checks** — implied probabilities summing to <100% (soccer: ~77%) or extreme side imbalance (AFL: 73:1 Over/Under)
3. **Per-prop calibration** — comparing devigged probabilities against empirical hit rates by market type

None of these checks were automated in the scanner when the bugs were active. The theory system (see [[concepts/value-betting-theory-system]]) allows any devig method to be assigned to any market via Supabase configuration — with no validation that the method matches the market's actual structure. This means future misconfigurations of the same type are not prevented by the current fixes.

## Prevention Architecture

A robust prevention layer would include:

1. **Market-type validation at theory creation** — when a theory is configured with `one_sided_consensus`, validate that the target markets are genuinely one-sided
2. **Outcome-count enforcement** — when evaluating a market with 3 outcomes under a 2-way devig, flag or reject rather than silently dropping the third outcome
3. **Automated calibration alerts** — periodic comparison of devigged probabilities against actual outcomes by (sport, market_type, devig_method), alerting when calibration diverges beyond a threshold
4. **Implied probability sanity check** — flag any market where post-devig probabilities sum to <95% or >105%, as this indicates structural model mismatch

## Evidence

- **Soccer (2026-04-16):** 22 theories across soccer leagues used 2-way devig on 3-way moneyline markets. 30 phantom picks voided, all showing 20-41% EV. A manually 3-way devigged sample showed zero edge.
- **AFL one_sided_consensus (2026-04-14):** 4 of 6 AFL theories used `one_sided_consensus` which hard-skips Unders at `tracker.py:548`. 951 Over picks vs 13 Under picks. Method was used on 83% of AFL picks.
- **AFL circular devig (2026-04-14):** 964 settled AFL picks showed +1.16% CLV but -34.2% ROI. All "sharp" books on OpticOdds for AFL are correlated retail shops; US books confirmed as wholesale copies.

## Related Concepts

- [[concepts/soccer-three-way-devig-phantom-ev]] - The 3-way → 2-way market structure mismatch
- [[concepts/one-sided-consensus-structural-bias]] - The 2-sided → 1-sided market structure mismatch
- [[concepts/afl-circular-devig-trap]] - The correlated → independent book structure mismatch
- [[concepts/value-betting-theory-system]] - The theory system that allows unconstrained method assignment
- [[concepts/alt-line-mismatch-poisoned-picks]] - A fourth phantom EV mechanism (alt-line interpolation) from mismatched line data rather than mismatched method
- [[connections/circular-devig-provider-dependency]] - The provider dependency dimension of the AFL circular devig case
