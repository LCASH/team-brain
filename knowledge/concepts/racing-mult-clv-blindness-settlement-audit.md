---
title: "Racing-Mult CLV Blindness and Settlement Audit"
aliases: [racing-mult-clv-null, place-bsp-settlement-gap, racing-mult-audit, mult-min-ev-analysis]
tags: [superwin, racing, settlement, clv, data-integrity, edge-detection, audit]
sources:
  - "daily/lcash/2026-05-30.md"
created: 2026-05-30
updated: 2026-05-30
---

# Racing-Mult CLV Blindness and Settlement Audit

On 2026-05-30, a deep audit of THE MULT (racing-mult) edge — the worst performer at -26.5% ROI — revealed that all racing-mult CLV values were null due to a code path mismatch in `betfair.py`. The `_handle_race_result()` function correctly fetches `place_bsp_by_sel` and `place_ltp_by_sel` from Betfair's API, but the result-builder loop reads `rd.get("place_bsp")` from settlement scanner runner dicts that never populate place-specific keys. Three of four call sites in `betfair.py:1473` don't pass place BSP/LTP fields. The PnL itself (-120.4u, -26.5% ROI) was confirmed correct by auditing 15/15 WIN picks — the edge genuinely loses money, and the inverse correlation between detection EV and ROI (≥20% EV = -57.9% ROI) is a smoking gun for noise, not signal.

## Key Points

- **CLV was null for all racing-mult picks**: `_handle_race_result()` fetches place BSP/LTP correctly, but result-builder reads `rd.get("place_bsp")` from settlement scanner data that never populates those keys
- **3 of 4 call sites in `betfair.py:1473` don't pass `place_bsp`/`place_ltp`** in runner dicts — the settlement scanner only carries WIN-market BSP/LTP
- **Fix: read from locally-fetched place BSP/LTP dicts** instead of settlement scanner's empty fields; deployed live; historical CLV cannot be backfilled (Betfair returns no SP data on markets settled >24h ago)
- **PnL is real, not a bug**: -120.4u, -26.5% ROI confirmed by auditing 15/15 WIN picks individually
- **High detection EV inversely correlates with ROI**: ≥20% EV band = -57.9% ROI; this is a reliable noise indicator — genuine edges show positive correlation
- **`min_ev: 1%` is structurally too loose** for place markets (median odds ~$1.50; 1% of $1.50 = $0.015 absolute edge, overwhelmed by bid-ask spread); recommendation: bump to 5%
- **"Fast" mode confirmation**: TAB corrects place odds in seconds, so the T-CONFIRM waiting pattern doesn't apply; recommended filter: `trail ≤ 2 AND ev_last ≥ 8`
- Only 3/34 VOIDs were misclassified (Nowra R2 anomaly), +2.3u impact — immaterial
- Full audit saved as THEORY T-MULT in edge-pick-theories.md

## Details

### The CLV Pipeline Gap

The settlement flow for racing-mult has two data sources:

1. **Settlement scanner** (`_settle_race()`): streams Betfair results in real-time, building runner dicts with `status`, `position`, `bsp`, `ltp` — all WIN-market fields. The scanner does NOT query Betfair's paired PLACE markets, so `place_bsp` and `place_ltp` are never populated in the runner dicts.

2. **Race result handler** (`_handle_race_result()`): called after settlement, separately fetches `place_bsp_by_sel` and `place_ltp_by_sel` from Betfair's PLACE market API.

The bug: the result-builder loop sits between these two data sources. It reads `rd.get("place_bsp")` from the settlement scanner's runner dicts (source 1), which are always empty for place data. The locally-fetched place dicts (source 2) are available in the same function scope but not wired into the result builder.

The fix is a direct read from the locally-fetched dicts: `place_bsp = place_bsp_by_sel.get(sel_id)` instead of `rd.get("place_bsp")`. This was deployed on 2026-05-30 and forward CLV now populates correctly.

### The min_ev Structural Problem

Place markets have fundamentally different economics than win markets:

| Market | Median Odds | 1% EV Absolute | 5% EV Absolute |
|--------|-------------|-----------------|-----------------|
| Win | ~$5.00 | $0.05 | $0.25 |
| Place | ~$1.50 | $0.015 | $0.075 |

At `min_ev: 1%`, the scanner accepts opportunities with only $0.015 of absolute edge on a typical place bet. The Betfair bid-ask spread alone can exceed this — meaning the "edge" disappears at execution. The inverse correlation between detection EV and ROI confirms this: the scanner is capturing momentary pricing noise that corrects within seconds, and higher "EV" just means more extreme noise.

### Confirmation Score Integration

Racing-mult is a "fast" mode edge — unlike SuperPicks or Normal edges where TAB slow-corrects odds over minutes, TAB's place odds settle within seconds of the boost appearing. The T-CONFIRM waiting pattern (wait for trail confirmation before staking) is counterproductive here because the odds correct before any trail can build.

The recommended approach: `trail ≤ 2 AND ev_last ≥ 8` — stake early on high-EV detections, don't wait. This was documented in THEORY T-CONFIRM alongside the other 4 edge modes' confirmation score dispatchers.

## Related Concepts

- [[concepts/superwin-mult-place-market-edge]] - The parent article covering THE MULT's architecture, settlement bug, and field-size rules; the CLV blindness and min_ev analysis are the latest layer of understanding
- [[concepts/settlement-scanner-restart-state-loss]] - The settlement scanner's state management issues are the same system that fails to carry place BSP/LTP data
- [[concepts/multiple-comparison-edge-validation-trap]] - The -26.5% ROI result and inverse EV correlation are consistent with the broader over-fitting analysis from the same day
- [[concepts/superwin-racing-profitability-dimensions]] - The profitability matrix now has a 5th mode (racing-mult) that demonstrably loses money — the min_ev and confirmation score recommendations feed directly into dimension tuning

## Sources

- [[daily/lcash/2026-05-30.md]] - Session 11:58: Racing-mult missing from 5-mode confirmation score analysis; initial hypothesis was CLV using WIN BSP instead of PLACE BSP — turned out PnL was correct but CLV was blind; `_handle_race_result()` fetches place_bsp correctly but result-builder reads from settlement scanner's empty fields; 3/4 call sites in betfair.py:1473 don't pass place fields; fix deployed; -120.4u/-26.5% ROI confirmed by 15/15 WIN audit; >=20% EV = -57.9% ROI (inverse correlation); min_ev 1% too loose for place odds ~$1.50; confirmation score: trail <= 2, ev_last >= 8 (fast mode); 3/34 VOID misclassified +2.3u immaterial; saved as THEORY T-MULT
