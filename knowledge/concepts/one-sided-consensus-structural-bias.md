---
title: "One-Sided Consensus Structural Bias"
aliases: [one-sided-consensus-bug, over-only-devig, over-under-imbalance]
tags: [value-betting, devig, bug, afl, methodology]
sources:
  - "daily/lcash/2026-04-14.md"
created: 2026-04-14
updated: 2026-04-14
---

# One-Sided Consensus Structural Bias

The `one_sided_consensus` devigging method in the value betting scanner structurally skips all Under selections by filtering at line 548 of `server/tracker.py` (`if not key.endswith("_over"): continue`). When applied to two-sided markets like AFL Disposals — which have real Over/Under lines — it produces an invisible 100% Over bias. Combined with the alphabetical theory ordering for `triggered_by` attribution, this broken method dominated AFL pick tagging, contributing to a 951:13 Over/Under production imbalance.

## Key Points

- `one_sided_consensus` hard-skips any key not ending in `_over` at line 548 — structurally appropriate only for one-sided markets (e.g., goal-scoring props where "Under 0.5 goals" is meaningless)
- Applied to AFL Disposals (a legitimate two-sided market), it produced 951 Over picks vs 13 Under picks — a 73:1 imbalance
- The method was used by 83% of AFL picks and was never calibrated against actual outcomes
- Alphabetical theory ordering + pick dedup compounded the bias: `AFL Disposals` (broken, uses `one_sided_consensus`) sorted before `AFL Disposals 5-Book` (correct, uses `multiplicative`), hijacking `triggered_by` on shared pick IDs
- 4 of 6 active AFL theories used `one_sided_consensus`, making the aggregate Over-only signal appear intentional when it was accidental

## Details

### The Bug

The `one_sided_consensus` devigging method was designed for markets where only one side is meaningful — typically goal-scoring props in lower-scoring sports where "Under 0.5 goals" is either not offered or not meaningfully priced. For these markets, the method legitimately focuses on the Over side and derives the implied true probability from consensus across multiple books.

The bug occurs when this method is applied to two-sided markets like AFL Disposals. AFL Disposals Over/Under markets have genuine two-sided pricing: "Disposals Over 24.5" and "Disposals Under 24.5" are both offered at real odds. The `one_sided_consensus` method's line 548 filter (`if not key.endswith("_over"): continue`) silently drops all Under evaluations, meaning the tracker never even considers Under picks for these markets. This is not a data issue or a configuration error — it is a structural limitation of the method being applied to the wrong market type.

### The Attribution Hijack

The bias was amplified by the pick deduplication and theory attribution system. Picks are deduped by a deterministic UUID based on `(player, prop, side, line, game_date, soft_book)`. When multiple theories evaluate the same pick, only the first theory alphabetically gets recorded in the `triggered_by` field. 

The `AFL Disposals` theory (which used `one_sided_consensus`) sorted alphabetically before `AFL Disposals 5-Book` (which used `multiplicative` and correctly evaluates both sides). Even when `AFL Disposals 5-Book` independently identified a valid Under pick, if `AFL Disposals` had already claimed the pick ID for the Over side, the `triggered_by` field showed the broken theory as the originator. This made it appear that the Over-dominant signal was coming from the "correct" theory when it was actually the broken one dominating.

### Theory Proliferation

An audit of the `nba_optimization_runs` table on 2026-04-14 revealed 6 active AFL theories — not the 2 previously assumed. Three were for Goals markets and three for Disposals. Of the six, four used `one_sided_consensus`:

- `AFL Disposals` — `one_sided_consensus` (structurally Over-only)
- `AFL Goals Consensus` — `one_sided_consensus` (Over-only, but goals are inherently one-sided, so less harmful)
- Two other Goals theories — also `one_sided_consensus`
- `AFL Disposals 5-Book` — `multiplicative` (correct for two-sided markets)
- `AFL Disposals OLV` — near-duplicate of 5-Book (differs by one book: BetRivers 802 vs TAB 908)

The theory proliferation occurred over time without audit. No monitoring existed to flag that 4 of 6 theories were structurally Over-only, and the aggregate production signal (951:13 Over/Under) was never questioned because no calibration or outcome tracking was in place for AFL.

### Remediation

All 5 non-essential theories were deactivated:
- 3 Goals theories: calibration analysis across 6,180 parameter combinations proved -28.9% best case, no configuration is profitable
- `AFL Disposals` (wrong devig method)
- `AFL Disposals OLV` (legacy duplicate)

`AFL Disposals 5-Book` was retained as the baseline control alongside a new `AFL Disposals Net Cast` theory configured with liberal parameters (min_ev=1, multiplicative/poisson, books 900/901/903/908/911) for forward-looking data capture and offline variant replay.

## Related Concepts

- [[concepts/afl-circular-devig-trap]] - The broader AFL devig problem — even the "correct" method is circular without genuine sharps
- [[concepts/value-betting-theory-system]] - The theory configuration system that allowed these theories to accumulate
- [[concepts/pick-dedup-multi-theory-limitation]] - The dedup architecture that enabled attribution hijack
- [[concepts/alt-line-mismatch-poisoned-picks]] - Another data quality bug where tracker logic produced phantom EV signals

## Sources

- [[daily/lcash/2026-04-14.md]] - 6 active AFL theories discovered (not 2); 4 of 6 used `one_sided_consensus`; line 548 skips Unders; 951:13 Over/Under imbalance; alphabetical theory ordering hijacks `triggered_by`; all 5 non-essential theories deactivated; `AFL Disposals OLV` identified as near-duplicate (Sessions 14:31, 16:02)
