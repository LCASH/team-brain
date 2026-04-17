---
title: "Connection: Silent Type Coercion and Data Corruption"
connects:
  - "concepts/pick-id-float-int-hashing-bug"
  - "concepts/dd-td-resolver-bias"
  - "concepts/silent-worker-authentication-failure"
  - "concepts/alt-line-mismatch-poisoned-picks"
sources:
  - "daily/lcash/2026-04-17.md"
created: 2026-04-17
updated: 2026-04-17
---

# Connection: Silent Type Coercion and Data Corruption

## The Connection

Multiple bugs in the value betting scanner share a root pattern: implicit type assumptions or encoding assumptions about API data produce plausible-looking but wrong results, with zero error signals. The pick ID float/int hashing bug, the DD/TD encoded stat field, and the alt-line interpolation each silently corrupted different parts of the pipeline — trail collection, resolution grading, and EV calculation respectively — while the system appeared to function normally.

## Key Insight

The non-obvious insight is that **plausible wrong output is worse than no output.** Each of these bugs produced data that passed all validation checks and appeared reasonable at a glance:

| Bug | What It Produced | Why It Looked Correct |
|-----|-----------------|----------------------|
| **Pick ID float/int** | 0 trails for moneyline picks | Trail absence is a valid state ("market not tracked yet") |
| **DD/TD encoded stat** | 100% Over win rate on 350+ picks | Appeared to be an edge, not a bug — stats were "resolved" |
| **Alt-line interpolation** | 50-200% phantom EV | High but not impossible — scanner occasionally finds large edges |

In each case, the output fell within the range of plausible values, so no sanity check or threshold alarm fired. The float/int hash produced valid-looking UUIDs (just different ones). The DD/TD resolver produced win/loss grades (just wrong ones for 645 of 773 picks). The alt-line interpolation produced EV values (just massively inflated ones).

This contrasts with the silent worker authentication failure (see [[concepts/silent-worker-authentication-failure]]), where the output is **zero** — also bad, but at least detectable by "expected N workers, found M" health checks. Plausible wrong output evades quantity-based monitoring entirely. It requires **correctness monitoring**: sanity checks on value distributions, cross-verification against independent data sources, and anomaly detection on statistical properties.

## The Detection Gap

The three bugs were detected through different means, none automated:

1. **Pick ID float/int**: Noticed when investigating low trail hit rate on prediction market picks — only 5/50 had trails
2. **DD/TD encoded stat**: Noticed when 100% Over / 0% Under win rate was flagged as statistically implausible during a manual audit
3. **Alt-line interpolation**: Noticed when 153.7% EV picks appeared in the dashboard — high enough to be suspicious to a human

Each required human pattern recognition. An automated defense would include:
- **Type-stable hashing**: Canonicalize all inputs to deterministic types before string formatting
- **Extreme win rate alerts**: Any prop_type+side with >90% or <10% win rate on 20+ picks triggers investigation
- **EV distribution monitoring**: Alert when the EV distribution changes shape (e.g., new cluster of >50% EV picks)
- **Cross-verification**: Compute derived stats from primitives, compare against provider's derived field

## The Three Forward Rules

The DD/TD investigation on 2026-04-17 codified three rules that address this pattern:

1. **Never trust pre-computed derived stats from APIs — compute from primitives.** OpticOdds' `player_double_double` was an encoded concatenation, not a binary flag. The resolver should compute DD/TD by counting individual stat categories ≥10.
2. **Extreme win rates are a bug signal, not an edge.** 100% win rate on 350+ picks should trigger an automatic sanity alert, not celebration.
3. **Pick deduplication is needed at the analytics layer.** Same outcome tracked 2.6x across soft books inflates all aggregate metrics, making bugs harder to spot in the noise.

## Related Concepts

- [[concepts/pick-id-float-int-hashing-bug]] - Float/int type coercion producing different hashes for the same logical value
- [[concepts/dd-td-resolver-bias]] - Encoded stat field trusted as binary, producing 645/773 mis-graded picks
- [[concepts/alt-line-mismatch-poisoned-picks]] - Line interpolation across mismatched markets producing phantom EV
- [[concepts/silent-worker-authentication-failure]] - The contrasting "zero output" failure mode that is easier to detect
- [[connections/operational-compound-failures]] - The operational chain (drift + silence + no monitoring) that lets these bugs persist
