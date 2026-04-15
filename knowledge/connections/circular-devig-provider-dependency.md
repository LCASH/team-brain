---
title: "Connection: Circular Devig and Provider Dependency"
connects:
  - "concepts/afl-circular-devig-trap"
  - "concepts/opticodds-critical-dependency"
  - "concepts/one-sided-consensus-structural-bias"
  - "concepts/value-betting-theory-system"
sources:
  - "daily/lcash/2026-04-14.md"
created: 2026-04-14
updated: 2026-04-14
---

# Connection: Circular Devig and Provider Dependency

## The Connection

The OpticOdds single-provider dependency (documented in [[concepts/opticodds-critical-dependency]]) has a second failure mode beyond availability: for sports without genuine market makers in OpticOdds' book catalog, the system's devigging pipeline becomes self-referential. AFL player props are the concrete case — OpticOdds provides odds from Australian retail books and US wholesaler copies, but no independent price-maker (Pinnacle, Betfair Exchange). The result is circular devig that produces systematically wrong "true odds," compounded by a structurally biased devig method.

## Key Insight

The OpticOdds dependency was previously understood as an **availability** risk: if OpticOdds goes down, the system has no sharp odds. The AFL experience reveals a second, more insidious dimension: even when OpticOdds is fully operational, its data can produce **systematically wrong signals** for sports where its "sharp" books are actually correlated retail operators.

This transforms the problem from "single point of failure" to "single point of bias." The system doesn't just risk going dark — it risks being confidently wrong. The +1.16% average CLV with -34.2% actual ROI is worse than no signal at all, because the positive CLV creates false confidence that the strategy is working. An availability outage is immediately visible; a calibration failure is invisible until actual P/L is measured against the reference signal.

The compounding with `one_sided_consensus` (see [[concepts/one-sided-consensus-structural-bias]]) adds a third layer: even if the "sharp" books were perfectly calibrated, the devig method used on 83% of AFL picks was structurally Over-only. So the system was: (1) devigging against biased books, (2) using a method that ignores half the market, (3) running unaudited for weeks because no outcome calibration existed.

## Evidence

The AFL portfolio on 2026-04-14 showed:
- 964 settled picks, 270-694 (28% WR), -34.2% flat-bet ROI
- +1.16% average CLV — positive but meaningless against non-sharp close
- 951 Over picks vs 13 Under picks — 73:1 imbalance from `one_sided_consensus`
- 5 "sharp" books all correlated: Bet Right (34.0% WR), PickleBet (34.5%), PointsBet AU, FanDuel, DraftKings
- Sportsbet (50.7% WR, near-fair calibration) classified as soft book, not sharp
- US books confirmed as AFL wholesale copies, not independent price-makers

The contrast with NBA — where OpticOdds does provide genuinely sharp references (Pinnacle, Circa) — demonstrates that the devig pipeline works correctly when the inputs are sound. The problem is sport-specific data quality, not algorithmic.

## Implications

1. **Per-sport sharp validation is required** — the system cannot assume that a book labeled "sharp" for NBA is also sharp for AFL. Sharp calibration should be validated empirically per sport/market before deployment.

2. **Positive CLV alone is insufficient** — CLV must be measured against a verified sharp reference. CLV against retail consensus is a vanity metric that can mask severe losses.

3. **Devig method must match market structure** — `one_sided_consensus` on a two-sided market is always wrong, regardless of book quality. Method selection should be enforced or at least audited per-theory.

4. **Theory proliferation without calibration audit compounds errors** — 6 theories accumulated over time, 4 structurally broken, none caught until the -34.2% ROI triggered investigation.

## Related Concepts

- [[concepts/afl-circular-devig-trap]] - The detailed mechanics of the circular devig problem
- [[concepts/opticodds-critical-dependency]] - The provider dependency that makes circular devig possible for non-major sports
- [[concepts/one-sided-consensus-structural-bias]] - The devig method bug that compounded the circular devig bias
- [[concepts/value-betting-theory-system]] - The theory system where misconfigured theories accumulated
- [[connections/scraper-consolidation-provider-dependency]] - The earlier analysis of deepening OpticOdds dependency; this connection reveals the bias dimension beyond availability
- [[concepts/pick-dedup-multi-theory-limitation]] - The architecture that hid which theories were actually driving picks
