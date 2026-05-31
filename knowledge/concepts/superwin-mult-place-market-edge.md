---
title: "SuperWin THE MULT Place-Market Edge"
aliases: [the-mult, racing-mult, place-market-edge, tab-place-boost, place-settlement-bug, place-clv-blindness]
tags: [superwin, racing, edge-detection, place-market, tab, settlement, clv]
sources:
  - "daily/lcash/2026-05-20.md"
  - "daily/lcash/2026-05-22.md"
  - "daily/lcash/2026-05-30.md"
created: 2026-05-20
updated: 2026-05-30
---

# SuperWin THE MULT Place-Market Edge

On 2026-05-20, lcash added `racing-mult` ("THE MULT") as a new SuperWin racing edge: a 10% boost on TAB **place** odds, with EV calculated as `(tab.place × 1.1) / bf.place_lay - 1`. This is the first place-market edge in the system — all prior edges (Cash Multiplier, SuperPicks, Normal, BlueBoost) targeted win markets. A critical settlement bug was immediately discovered: the resolver was checking `status == "WINNER"` (win market semantics) instead of top-3 finish (place market semantics), causing ROI to swing from **-62.6% to +48.45%** after the fix. Thoroughbred place dominates at +55% ROI.

## Key Points

- **THE MULT**: 10% boost on TAB place odds; EV = `(tab.place × 1.1) / bf.place_lay - 1`; TAB-only, min_ev 5%, min_liq $200
- Implemented via a single `place_market` boolean flag in `scanner.py` — swaps bookie price to `.place`, Betfair price to `.place_lay`, liquidity to `.place_total_matched`; all existing logic (MTJ gate, confidence scorer, persistence, EV trail) applies unchanged
- **Critical settlement bug**: Resolver checked `status == "WINNER"` (win) instead of top-3 finish (place) — ROI swung from **-62.6% to +48.45%** after fix (3W→15W out of 29 settled)
- CLV now uses **`place_bsp`** (fallback `place_ltp`) — Betfair paired PLACE markets provide place-specific BSP; greyhound/harness usually lack paired PLACE markets (LTP fallback)
- **Field-size-aware thresholds deployed (2026-05-22)**: 8+ active runners → 3 places, 5-7 → 2 places, ≤4 → VOID; historical audit: only 1/53 mis-resolved (Warwick Farm R3, -3.19u correction)
- No new DB column needed — market is implicit via `edge_slug='racing-mult'` for filtering
- Committed as `875f4ff` (edge config) and `57a3600` (settlement fix)
- **CLV blindness discovered (2026-05-30)**: `_handle_race_result()` fetches `place_bsp_by_sel` correctly but result-builder loop reads `rd.get("place_bsp")` from settlement scanner data that never populates place fields — all racing-mult CLV was null until fix
- **Honest ROI after full audit: -120.4u, -26.5% ROI** — not a settlement bug, the edge genuinely loses money at `min_ev: 1%`; high detection EV inversely correlates with ROI (≥20% EV = -57.9% ROI), confirming noise not signal

## Details

### Place Market Architecture

The place market integration was deliberately minimal: a single boolean flag (`place_market`) on the edge configuration swaps three price fields:

| Dimension | Win Edge | Place Edge (THE MULT) |
|-----------|----------|----------------------|
| Bookie price | `runner.odds.win` | `runner.odds.place` |
| Betfair price | `runner.betfair.lay` | `runner.betfair.place_lay` |
| Liquidity | `runner.betfair.total_matched` | `runner.betfair.place_total_matched` |

Everything else — the MTJ gate, warmup guard, confidence scorer, EV trail recording, persistence to Supabase — operates identically. This demonstrates the edge scanner's flexibility: new edge types are configuration changes, not code rewrites.

### The Settlement Bug

The resolver at `server/app/edges/resolver.py` used `status == "WINNER"` to determine if a pick won. For win markets, this is correct — only the race winner qualifies. For place markets, the top 2-3 finishers qualify (depending on field size). The resolver was checking for race winner only, meaning every place pick where the runner finished 2nd or 3rd was incorrectly graded as a loss.

The magnitude of the error was dramatic: 3 wins out of 29 settled picks (-62.6% ROI) became 15 wins (+48.45% ROI) after fixing to check finishing position ≤ 3. This is because place markets have a much higher win rate (~40-50%) than win markets (~15-25%), and the bug was specifically suppressing the additional 2nd/3rd place wins.

### Place Payout Field Size Rules

The top-3 heuristic is correct for standard fields (8+ runners) but Australian racing has variable place terms:

| Field Size | Place Terms | Number of Places |
|-----------|-------------|-----------------|
| 8+ runners | 1st, 2nd, 3rd | 3 |
| 5-7 runners | 1st, 2nd | 2 |
| <5 runners | Win only | 0 (no place market) |

On 2026-05-22, the resolver was updated to implement field-size-aware thresholds: 8+ active runners → 3 places, 5-7 runners → 2 places, ≤4 runners → VOID (no place market), scratched → SCRATCHED. This matches TAB/Betfair place-market rules. A historical audit confirmed only 1 of 53 settled racing-mult picks was actually mis-resolved (Warwick Farm R3: 7 runners, position=3 incorrectly marked WIN), with a -3.19u net portfolio adjustment.

### place_bsp Capture and CLV (2026-05-22)

`place_bsp` was added to the resolver for racing-mult CLV computation. Betfair's paired PLACE markets provide place-specific BSP/LTP data. The resolver now uses `place_bsp` (fallback `place_ltp`) instead of leaving CLV null. End-to-end validation was confirmed via Hastings R3 (NZ thoroughbred) — first live race to show `place_bsp` populating correctly (e.g., Ashoka: bsp=$1.66, place_bsp=$1.33). Key coverage limitation: greyhound and harness races usually lack paired Betfair PLACE markets. `place_bsp` is always < `bsp` (placing easier than winning) — a useful data quality sanity check.

A stuck-pick alert was deployed (≥3 races stuck >60min past jump, rate-limited 30min) to catch missing settlements going forward.

### CLV Blindness and Settlement Scanner Gap (2026-05-30)

On 2026-05-30, a deep audit of racing-mult's -26.5% ROI revealed that **all racing-mult CLV values were null** — not from missing Betfair data, but from a code path mismatch. The `_handle_race_result()` function correctly fetches `place_bsp_by_sel` and `place_ltp_by_sel` dicts from Betfair's API. However, the result-builder loop that writes settlement data reads `rd.get("place_bsp")` from the settlement scanner's runner dicts — and the settlement scanner never populates `place_bsp`/`place_ltp` keys in its runner data. Three of four call sites in `betfair.py:1473` don't pass place-specific fields.

The fix reads directly from the locally-fetched place BSP/LTP dicts rather than relying on the settlement scanner's empty fields. This is a structural lesson: **place-market edges need their own CLV pipeline** — the WIN-market settlement fields don't carry place data, and assuming they do silently produces null CLV without any error.

Historical CLV cannot be backfilled because Betfair's `listMarketBook` API returns no SP data on markets settled >24 hours ago. Only forward picks will benefit from the fix.

### Honest Performance: min_ev Analysis (2026-05-30)

The full audit confirmed racing-mult's PnL (-120.4u, -26.5% ROI) is the real economic outcome, not a settlement bug. Auditing 15/15 WIN picks confirmed correct grades. The critical diagnostic: **high detection EV inversely correlates with ROI**:

| EV Band | ROI | Assessment |
|---------|-----|------------|
| 1-5% | ~breakeven | Structural floor — median place odds ~$1.50, 1% of $1.50 = $0.015 margin |
| 5-10% | Slightly negative | Marginal but within variance |
| 10-20% | Negative | Edge eroding |
| **≥20%** | **-57.9%** | Smoking gun — detection noise, not genuine edge |

The inverse correlation (highest EV = worst ROI) is a reliable indicator that the "edge" is noise: the scanner is detecting extreme EV from momentary pricing anomalies that correct within seconds. For place markets with low base odds (~$1.50), a `min_ev: 1%` gate is structurally too loose — 1% of $1.50 is only $0.015 of absolute edge, easily overwhelmed by the bid-ask spread.

The recommended fix is `min_ev: 5%` and a confirmation score filter: `trail ≤ 2 AND ev_last ≥ 8` for racing-mult's "fast" mode (TAB corrects place odds in seconds, so the T-CONFIRM waiting pattern doesn't apply).

### Performance Breakdown

After the settlement fix, 29 of 31 tracked MULT picks were re-settled:

| Race Type | ROI | Assessment |
|-----------|-----|------------|
| Thoroughbred place | **+55%** | Dominant — same harness > thoroughbred > greyhound hierarchy as win edges |
| Greyhound place | Negative | Small sample (4 picks), inconclusive |

### NZ vs AU Harness Analysis (Same Session)

A concurrent analysis of NZ vs AU harness revealed Cambridge (NZ's most-watched harness venue) as a -60% ROI trap that single-handedly kills the NZ aggregate. Without Cambridge, NZ harness is +23% ROI. AU harness thrives on country meetings (Bathurst, Bendigo, Wagga) where bookies are soft.

## Related Concepts

- [[concepts/superwin-edge-pick-backtesting]] - The backtesting infrastructure that THE MULT picks flow into; place settlement uses the same resolver loop
- [[concepts/superwin-racing-profitability-dimensions]] - THE MULT adds a 5th edge mode to the profitability matrix; NZ Cambridge venue identified as a performance trap
- [[concepts/betr-blueboost-racing-edge]] - BlueBoost uses `boost_field` criteria; THE MULT uses `place_market` flag — different implementation patterns for the same scanner
- [[concepts/scanner-warmup-false-ev-guard]] - Warmup guard applies to THE MULT identically (2+ bookies, 50+ races before persisting)
- [[concepts/superwin-racing-profitability-dimensions]] - THE MULT honest -26.5% ROI feeds into the overall profitability picture; the mode-level analysis must use post-audit numbers

## Sources

- [[daily/lcash/2026-05-20.md]] - THE MULT edge added: 10% TAB place boost, `place_market` boolean flag, min_ev 5%, min_liq $200; settlement bug: `status == "WINNER"` → top-3 finish check swung ROI -62.6% → +48.45% (3W→15W/29); CLV disabled for place (BSP/LTP win-only); thoroughbred place +55% ROI; committed 875f4ff + 57a3600 (Sessions 09:00, 14:47). NZ harness: Cambridge -60% ROI trap; AU harness +39% ROI on 919 picks vs NZ +0.5% on 81 (Session 14:47)
- [[daily/lcash/2026-05-22.md]] - Field-size-aware place thresholds: 8+→3 places, 5-7→2, ≤4→VOID; historical audit 1/53 mis-resolved (Warwick Farm R3 -3.19u); place_bsp capture via Betfair PLACE markets; CLV now uses place_bsp (fallback place_ltp); Hastings R3 NZ end-to-end validation; greyhound/harness lack paired PLACE markets; stuck-pick alert deployed (Sessions 09:27, 12:42)
- [[daily/lcash/2026-05-30.md]] - CLV blindness: result-builder reads `rd.get("place_bsp")` from settlement scanner (never populated) instead of locally-fetched place BSP/LTP dicts; all racing-mult CLV was null; fix: read from local dicts; historical backfill impossible (Betfair API no SP on settled >24h). Honest ROI: -120.4u, -26.5% (confirmed via 15/15 WIN pick audit); high detection EV inversely correlates with ROI (≥20% → -57.9%); min_ev 1% too loose for place market odds ~$1.50; recommended min_ev 5% + confirmation score filter. Theory T-MULT saved to edge-pick-theories.md (Session 11:58)
