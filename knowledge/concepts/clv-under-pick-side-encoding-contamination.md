---
title: "CLV Under-Pick Side-Encoding Contamination"
aliases: [clv-side-encoding, under-pick-clv-bug, resolver-wrong-field-under, trail-alternation-race]
tags: [value-betting, clv, resolver, bug, data-quality, trail-data]
sources:
  - "daily/lcash/2026-05-23.md"
  - "daily/lcash/2026-05-25.md"
created: 2026-05-23
updated: 2026-05-25
---

# CLV Under-Pick Side-Encoding Contamination

On 2026-05-23, lcash conducted a deep investigation into CLV side-encoding bugs in the v3 value-betting pipeline. Two distinct issues were confirmed: (1) the resolver functions `_build_closing_sharps` and `_compute_closing_true_prob` read the wrong odds field for ~85% of Under picks, storing pick-side decimals instead of the canonical (Over) convention — contaminating ~17,000 picks' CLV values; (2) a real data race in the Trea Turner trail data showing alternating 1.353 ↔ 2.57 on the same market_key, confirmed as a race condition between multiple pipeline components writing to state, not classifier noise.

## Key Points

- **~85% of Under pick trail rows store pick-side decimals** instead of the canonical (Over) convention — resolver reads the wrong field for these picks
- **~17,000 picks have contaminated CLV values** from the resolver using pick-side odds instead of canonical Over odds for `_build_closing_sharps` and `_compute_closing_true_prob`
- **`optic_clv_pct` (OO-direct path) is clean** — independent calculation path unaffected by the side-encoding bug
- **Trea Turner trail shows real alternation** between 1.353 ↔ 2.57 on the same market_key — confirmed race condition, not float noise or classifier error
- **Bug A (live-play leak via `anchored_closing_bundle`) already fixed and deployed** — this investigation is about Bug B (side encoding) and Bug C (trail alternation)
- **Static code analysis hit its ceiling** — every parser path looks clean; the race exists empirically but can't be identified from source alone; needs instrumented logging on Eve
- **Top 3 mechanism priors**: (1) dual pipeline instances (Eve + VPS both running), (2) OO sending pathological SSE events, (3) state.py `is_main` guard race

## Details

### The Side-Encoding Problem

The value betting scanner stores trail entries with odds values that should follow a canonical convention: Over-side decimal odds. When the resolver later reads these trails to compute CLV (closing line value), it expects the canonical format. For Over picks, this works correctly — the stored value matches what the resolver expects. For Under picks (~50% of all picks), the stored value may be the Under-side decimal instead of the canonical Over-side decimal.

The discrepancy arises because `_build_closing_sharps` and `_compute_closing_true_prob` in the resolver read the `odds` field from trail entries without checking whether the pick is an Over or Under. For Under picks, the `odds` field contains the Under-side decimal (e.g., 2.57 for "Rebounds Under 5.5") when the resolver expected the Over-side decimal (e.g., 1.353 for "Rebounds Over 5.5"). The CLV computation then compares the pick's opening Under odds against what it thinks is the closing Over odds — producing a meaningless CLV value.

The ~85% figure comes from the proportion of Under picks where the trail entries happen to store pick-side rather than canonical odds. The remaining ~15% may have been written through a different code path that correctly canonicalizes.

### The Trail Alternation Race Condition

A separate but related bug was discovered empirically in the Trea Turner trail data: soft trail entries alternate between 1.353 and 2.57 for the same `market_key`. These values are the Over and Under decimals for the same market — the trail is switching between storing the Over-side and Under-side value on consecutive writes.

This is a real race condition, not float noise. The alternation is too large (1.353 vs 2.57 — a 90% difference) to be floating-point jitter, and the values correspond exactly to the Over/Under pair for the market. Initial investigation with a classifier tolerance of 0.4 decimal produced a false "5 flipping picks" finding; tightening the filter to 0.1 reduced to 2 genuinely flipping picks — confirming the race is real but narrow in scope.

### Mechanism Enumeration

Rather than hypothesis-driven testing (which risks confirmation bias), an exhaustive mechanism enumeration identified 14+ potential causes. The top 3 priors:

1. **Dual pipeline writing to state (highest prior)**: Both Eve (mini PC) and VPS may be running `v3/startup.py` simultaneously, each writing to the same DataStore with different timing — one writes the Over-side value, the other writes the Under-side, and the last writer wins on each cycle
2. **OO sending pathological SSE events**: OpticOdds SSE stream may occasionally deliver events with Over/Under sides swapped or duplicated, causing the parser to write the wrong side
3. **state.py `is_main` guard race**: The `is_main` flag that prevents alt-line overwrites may have a timing window where an Under-side write slips through before the guard activates

### Investigation Status

Static code analysis reached its ceiling — every parser path (`_parse_oo_event`, `_apply_to_store`, bet365 wizard parsers) correctly handles side encoding when traced manually. The empirical race exists but the triggering condition isn't visible in source code. Next steps require instrumented logging on Eve: temporary debug logging in the OO SSE consumer to capture raw payloads and verify OO isn't sending pathological events, plus `pgrep -f v3.startup` on both Eve and VPS to check for duplicate pipeline instances.

### Relationship to Prior CLV Bugs

This is distinct from the three previous CLV-related bugs: (1) **CLV post-game-start contamination** (see [[concepts/clv-post-game-start-contamination]]) — in-play odds entering closing computation, already fixed; (2) **engine consensus-fallback EV contamination** (see [[concepts/engine-consensus-fallback-ev-contamination]]) — identical EV across theories from consensus path, already fixed; (3) **trail-anchored-bundle temporal mismatch** (see [[concepts/trail-anchored-bundle-read-layer-fix]]) — soft/sharp temporal misalignment in the read layer. Bug B (side encoding) is a different failure: the resolver reads the correct trail row at the correct time but interprets the odds value with the wrong side convention.

## Related Concepts

- [[concepts/clv-post-game-start-contamination]] - Bug A (live-play leak) was already fixed; this article covers Bug B (side encoding) and Bug C (trail alternation) — separate issues at different pipeline stages
- [[concepts/trail-anchored-bundle-read-layer-fix]] - The anchored bundle fixes temporal misalignment; the side-encoding bug is about value interpretation, not temporal alignment
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV is the primary theory evaluation metric; ~17,000 contaminated CLV values corrupt per-theory rankings
- [[connections/silent-type-coercion-data-corruption]] - The side-encoding bug is another "plausible wrong output" — the CLV values look reasonable (small percentages, correct sign) but are computed against the wrong odds convention
- [[concepts/dual-tracker-redundancy-architecture]] - Mechanism #1 (dual pipeline) is a consequence of the dual-tracker design; if both Eve and VPS run v3/startup.py, they'd race on DataStore writes
- [[concepts/tracker-pipeline-7-phase-audit]] - The audit validated core EV math (±0.5pp) but didn't check CLV side encoding — a gap that this investigation exposed

### Backfill Completion (2026-05-25)

On 2026-05-25, lcash completed the full CLV Under-pick backfill across all ~15,788 affected picks using `scripts/recompute_clv_under_picks.py` — an idempotent, dry-run-by-default script with `--sport`, `--limit`, `--pick-id`, `--apply` flags. Progressive rollout (20 → 500 → full 15,788) caught edge cases early. Austin Riley manual verification confirmed Over-price was being stored as Under-price; post-fix shows correct positive American odds (+156 to +192).

Results: CLV delta distribution centered near zero (median +0.82, mean -1.08) — most picks weren't dramatically wrong because Over/Under decimals are similar magnitude. Extreme outliers (-453, +95) were longshot-side picks where sign-flip math produced wildly inflated bogus CLV. 310 picks reclassified to `now_empty` (honest nulls where only alt-line trail rows existed — line filter correctly rejected all books). 4,273 picks reclassified to `entry_snapshot`/`opening_fallback` closing source.

Dashboard CLV fallback chain reordered: `optic_clv_pct` (OO-direct) now first in `getProductionCLV()`, before `sharp_clv_pct_true`. Bug A+B declared **functionally verified** on thin forward sample (3/3 sign-clean post-deploy Under player-prop picks, no regression signal).

Bug B (alt-line race in `server/state.py` where market_key doesn't include line, causing alt-line odds to overwrite main-line odds) was separately confirmed via Otto Lopez verification against OO. Option 3 (trail-layer de-noise, ~10 LOC) identified as pragmatic fix; Option 2 (per-line slot refactor, ~150 LOC) as correct long-term fix.

## Related Concepts

- [[concepts/clv-post-game-start-contamination]] - Bug A (live-play leak) was already fixed; this article covers Bug B (side encoding) and Bug C (trail alternation) — separate issues at different pipeline stages
- [[concepts/trail-anchored-bundle-read-layer-fix]] - The anchored bundle fixes temporal misalignment; the side-encoding bug is about value interpretation, not temporal alignment
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV is the primary theory evaluation metric; ~17,000 contaminated CLV values corrupt per-theory rankings
- [[connections/silent-type-coercion-data-corruption]] - The side-encoding bug is another "plausible wrong output" — the CLV values look reasonable (small percentages, correct sign) but are computed against the wrong odds convention
- [[concepts/dual-tracker-redundancy-architecture]] - Mechanism #1 (dual pipeline) is a consequence of the dual-tracker design; if both Eve and VPS run v3/startup.py, they'd race on DataStore writes
- [[concepts/tracker-pipeline-7-phase-audit]] - The audit validated core EV math (±0.5pp) but didn't check CLV side encoding — a gap that this investigation exposed
- [[concepts/tracker-sharp-trail-soft-gating-staleness]] - Sharp trail staleness (28-min median anchor gap) was discovered during Bug A+B verification; a separate CLV accuracy issue that compounds with the side-encoding bug

## Sources

- [[daily/lcash/2026-05-23.md]] - Confirmed Bug A (live-play leak) already fixed; resolver `_build_closing_sharps` and `_compute_closing_true_prob` read wrong field for ~85% of Under picks; ~17,000 picks contaminated; `optic_clv_pct` clean (independent path); Trea Turner trail alternation 1.353↔2.57 confirmed race condition; classifier tolerance 0.4 too loose (5 false flips) → 0.1 (2 real flips); 14+ mechanisms enumerated, top 3 priors: dual pipeline, OO pathological events, is_main guard race; static analysis hit ceiling, needs instrumented logging on Eve; wrong OO market name (`batter_*` vs `player_*`) caused false "OO has no data" conclusion; progress docs at brain/findings and ~/.claude/plans/ (Session 12:39)
- [[daily/lcash/2026-05-25.md]] - Full 15,788-pick backfill completed via `recompute_clv_under_picks.py`; CLV Δ median +0.82, mean -1.08; 310 `now_empty` picks (honest nulls from alt-line-only trails); 4,273 reclassified to entry_snapshot/opening_fallback; dashboard fallback reordered (optic_clv_pct first); Bug A+B functionally verified 3/3 sign-clean; Bug B alt-line race confirmed via Otto Lopez OO comparison; commits aabb975 (backfill script), 8976d63 (dashboard fallback), d968539 (resolver fix) (Sessions 07:57, 08:29, 10:47, 13:06, 13:37)
