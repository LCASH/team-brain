---
title: "Power Devig Method Empirical Validation"
aliases: [power-devig, power-vs-multiplicative, devig-method-bakeoff, shin-equals-additive]
tags: [value-betting, methodology, devig, calibration, analytics]
sources:
  - "daily/lcash/2026-06-01.md"
created: 2026-06-01
updated: 2026-06-01
---

# Power Devig Method Empirical Validation

On 2026-06-01, an empirical devig method bake-off across the value betting scanner's settled pick data confirmed that the **power method outperforms multiplicative** for both NBA and MLB. The finding is window-independent (survives both closing-time and stake-window analysis), making it safe to ship immediately. Power was recommended for 10 of 13 active theories, with a special `MLB-HR-Additive` theory for home runs where the additive/Shin method wins in the longshot regime.

## Key Points

- **Power > multiplicative** empirically: NBA Brier 0.23320 vs 0.23358; MLB Brier 0.16786 vs 0.16955 — small but consistent improvement across both sports
- **Window-independent**: The power advantage holds at both closing-time and stake-window analysis — safe to ship without waiting for more stake-window data
- **Shin = additive analytically for 2-way markets** — they collapse to the same numbers, so testing one tests both
- **MLB Home Runs: additive/Shin wins** in the longshot regime (high-odds, low-probability events) — a dedicated `MLB-HR-Additive` theory proposed
- **10 of 13 theories recommended for power switch** — the remaining 3 are either already power or need special handling (HR additive, one-sided)
- **MLB Poisson interpolation routing untestable**: Commit `4a643c9` has zero settled exposure — needs instrumentation before the Poisson path can be empirically validated

## Details

### The Bake-Off Methodology

Four devig methods were compared using Brier scores on settled picks from the post-decouple era (after 2026-05-26 tracker boundary):

| Method | NBA Brier | MLB Brier | Notes |
|--------|-----------|-----------|-------|
| **Power** | **0.23320** | **0.16786** | Best overall |
| Multiplicative | 0.23358 | 0.16955 | Current production default |
| Additive | Higher | Lower for HR | Best for longshot regime |
| Shin | = Additive | = Additive | Analytically identical for 2-way |

The power method's advantage is small in absolute terms but consistent across both sports and across different analysis windows. For a system processing thousands of picks per week, even a 0.001 Brier improvement compounds into meaningful EV accuracy gains.

### Why Power Beats Multiplicative

The multiplicative method assumes the bookmaker's margin is applied proportionally to each outcome's probability. The power method assumes the margin is applied as a power transformation. For markets where the true probability is near 50% (most player props), the methods produce similar results. The power method gains its advantage in markets with asymmetric probabilities (e.g., Home Runs Over 0.5 at 20% vs 80%), where the multiplicative method's proportional margin assumption breaks down.

### The Longshot Regime Exception

For MLB Home Runs — where the typical implied probability is 8-15% for Over and 85-92% for Under — the additive method outperforms power. In this extreme probability regime, the additive assumption (margin distributed equally in probability space) more accurately models how sportsbooks actually price longshot events. This motivates a dedicated theory rather than a global method switch.

### Implementation

The switch requires updating the `devig_method` field in 10 Supabase theory rows from `"multiplicative"` to `"power"` — a zero-code-change configuration update via the theory system (see [[concepts/value-betting-theory-system]]). The `devig_method` field is one of the 7 theory knobs that is NOT stored per-pick in `sharp_snapshot`, meaning historical replay would need to look up the theory definition — but this is acceptable since the method change is going forward only.

## Related Concepts

- [[concepts/value-betting-theory-system]] - The theory system where `devig_method` is configured per-theory via Supabase rows; power switch is a 1-field update per theory
- [[concepts/closing-time-vs-stake-window-sharpness]] - The window distinction discovered in the same session; power's advantage is window-independent, unlike book weight changes
- [[connections/devig-method-market-structure-mismatch]] - The broader pattern of devig method assumptions needing to match market structure; power is a better structural match for most 2-way markets
- [[concepts/alt-line-mismatch-poisoned-picks]] - Poisson interpolation for count props was validated alongside this bake-off; MLB Poisson routing has zero settled exposure and needs instrumentation

## Sources

- [[daily/lcash/2026-06-01.md]] - Agent C (devig method bake-off): power beats multiplicative for NBA (0.23320 vs 0.23358) and MLB (0.16786 vs 0.16955); Shin = additive for 2-way markets; MLB-HR-Additive theory proposed; 10/13 theories recommended for power switch; MLB Poisson untestable at commit 4a643c9 (Sessions 16:12, 17:36)
