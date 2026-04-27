---
title: "SuperWin Edge Pick Backtesting System"
aliases: [edge-picks, racing-backtesting, superwin-backtesting, edge-scanner-persistence]
tags: [superwin, racing, backtesting, architecture, supabase]
sources:
  - "daily/lcash/2026-04-23.md"
  - "daily/lcash/2026-04-25.md"
  - "daily/lcash/2026-04-26.md"
  - "daily/lcash/2026-04-27.md"
created: 2026-04-23
updated: 2026-04-27
---

# SuperWin Edge Pick Backtesting System

A backtesting infrastructure for the SuperWin racing scanner that journals every EV opportunity at detection time, settles against race results (BSP/finishing position), and enables profitability analysis by mode, edge type, and EV band. The system uses a `superwin_edge_picks` Supabase table with racing-specific filters (time-to-jump >2 min, max odds $30, Betfair spread <20%) and peak EV tracking. Twelve backtesting flaws were identified and ranked by severity during design review.

## Key Points

- `superwin_edge_picks` Supabase table journals every EV opportunity at detection time with detection context (edge_slug, mode_slug, bookie, odds, EV%), race identity (canonical_id, venue, race_number), and settlement fields (result, BSP, LTP, PNL)
- Backtesting is **mode-based** — the core question is "which modes actually deliver EV?" not just "are picks profitable"
- Racing-specific filters block noise: time-to-jump >2 min (excludes jumped races), max odds $30 (excludes longshot noise like $51 at 34% EV), Betfair spread <20% — all configurable per edge via `criteria` JSONB
- **Insert-only pattern** (not upsert) preserves first-detection odds — if odds move from $4.00 to $3.50 between scans, the user saw $4.00 but upsert would overwrite with $3.50
- Peak EV tracking via `peak_bookie_odds`, `peak_ev_pct`, `peak_detected_at` columns — updated only when a higher EV is observed
- Settlement resolver runs on a 90-second loop, matching edge picks to race results by `canonical_id` + `runner_number`
- CLV against BSP (Betfair Starting Price) is the gold standard for racing, not detection-time EV

## Details

### Architecture

The backtesting system operates in three layers:

**1. Capture (EdgeScanner):** The existing `EdgeScanner._scan_racing()` method detects EV opportunities. On detection, it INSERTs into `superwin_edge_picks` with the current odds, EV%, mode, edge type, and race metadata. The INSERT uses `UNIQUE (canonical_id, edge_slug, bookie, runner_number)` for deduplication across scan cycles. Subsequent scans that see the same opportunity compare the current EV against `peak_ev_pct` and UPDATE only the peak columns if the new EV is higher.

**2. Settlement (Resolver):** A background task running every 90 seconds matches unsettled edge picks against `race_results` using `canonical_id` and `runner_number`. Settlement writes: finishing position, BSP (Betfair Starting Price), LTP (Last Traded Price), and calculates PNL based on the detection-time odds.

**3. Query (Backtest API):** The `/api/v1/edges/backtest` endpoint provides aggregated performance metrics grouped by mode, edge type, race type, and EV band. This enables questions like "which modes produce genuine CLV?" and "what's the minimum EV threshold for profitability?"

### Twelve Identified Backtesting Flaws

A deep analysis during design review identified 12 flaws ranked by severity:

1. **Upsert destroys first-detection odds** — fixed with insert-only pattern
2. **Missing CLV calculation** — BSP-based CLV is the real benchmark, not detection-time EV
3. **"Open" race status ≠ not jumped** — need explicit time-to-jump check
4. **Place market completely ignored** — missing half the picture for modes that boost place odds
5. **No near-miss tracking** — picks below threshold would enable retrospective threshold optimization
6. **Dead heats need special handling** — half-stakes, not full void
7. **Abandonments need void handling** — neither win nor loss
8. **Longshot noise** — $51 at 34% EV is noise, not signal; max-odds filter needed
9. **Betfair spread check missing** — wide spreads indicate illiquid or uncertain markets
10. **Boost table versioning absent** — mode parameter changes invalidate historical comparisons
11. **VPS downtime creates invisible gaps** — no detection during downtime = missed opportunities in backtest
12. **Time-to-jump filter missing** — detecting "opportunities" on races that already jumped

### Insert-Only vs Upsert

The insert-only pattern is critical for backtest integrity. The scanner runs on a cycle, re-evaluating opportunities every scan. If odds move between scans — e.g., bookie drops from $4.00 to $3.50 while BSP ends at $3.80 — an upsert would overwrite the $4.00 with $3.50, making the backtest show a negative CLV ($3.50 vs $3.80 BSP) when the bettor actually had a positive CLV opportunity at $4.00.

The insert preserves what the user would have seen at detection time. Peak tracking captures the best moment. Together, they provide the full opportunity profile without retroactive data corruption.

### CLV vs Detection-Time EV

Detection-time EV uses the scanner's devigged true probability at the moment of detection. BSP (Betfair Starting Price) is the market-clearing price at race jump — the closest available proxy to "true odds" for horse racing. CLV measured as `(detection_odds / BSP - 1)` tells whether the bettor consistently got prices better than what the market settled at. This is more meaningful than detection-time EV because it benchmarks against an independent market outcome rather than the scanner's own model.

### Racing Cron Schedule

The racing cron stops around 1:00 PM UTC (11 PM AEST) when Australian racing ends for the day. Late deploys won't see new racing picks until the next day's racing begins. Sports and golf picks bypass racing-specific filters (max odds, time-to-jump, spread check) as they operate in different domains.

### LTP as CLV Proxy When BSP Unavailable (2026-04-25)

On 2026-04-25, lcash discovered that only 21% of settled picks had BSP data — most Australian greyhound and harness markets don't have BSP enabled on Betfair at all. The `sp` objects in Betfair API responses are empty for these markets. LTP (Last Traded Price) is available for 88% of picks and serves as a viable CLV proxy.

The resolver was updated to cascade: BSP → LTP for CLV calculation. A backfill of 53 historical picks with LTP-based CLV brought coverage from 21% to 88%. Nine picks have no CLV at all (zero Betfair trading data) — an acceptable gap.

### Early Backtesting Results (2026-04-25)

Review of all 80 journal picks across 3 days revealed:
- **TAB profitable**: +13.7% ROI
- **TabTouch bleeding**: -100% (every pick lost)
- **By race type**: Greyhounds losing (-29.3%), Thoroughbreds winning (+21.9%)
- **Detection timing**: 84% of picks detected under 10 minutes before jump — most edges found very late, clustering at 2-5 minutes. This is too late for practical bet placement and requires investigation into earlier detection.
- **Mode tracking gap**: `mode_slug` column exists but is always NULL because no edges have `boost_mode` configured yet

### Cron Toggle Design Gap (2026-04-25)

A cron architecture gap was identified: toggling the `enabled` flag in Supabase doesn't hot-load adapters. If the service restarts during off-hours (e.g., midnight AEST), only bet365 loads because TAB/TabTouch/Betfair adapters aren't running. The 9am cron just toggles DB flags without actually starting the adapters. The fix is for the cron to `systemctl restart superwin` rather than just flipping DB flags.

### Two-Minute Gate Removal and EV Tracking Blindspot (2026-04-27)

On 2026-04-27, the 2-minute-to-jump gate was **removed entirely** — it had been blocking both new picks AND re-detections near post time, cutting off the most valuable data (odds closest to jump are truest; BSP = closing price = gold standard). Picks are now tracked from first detection right up to race jump (only cutoff: MTJ < 0).

A significant tracking blindspot was also identified: the scanner only persists picks when EV >= 10% (`min_ev` threshold). Picks that appear on the TAKEOVER UI at 6% EV and grow to 14% are missed in the journal — the 6-9% EV band is where edges start forming, and first-detection odds tend to be the most profitable (per earlier analysis). An "Option 2" design was proposed but not yet built: track EV trail in memory from first detection at ANY EV level, but only persist to journal when the pick crosses 10% — writing the full history including the sub-10% lead-up phase.

### Trail Depth Fields (2026-04-27)

Three market depth fields were added to every trail entry: `lay_sz` (Betfair available lay depth — "can I bet this?"), `bk_sz` (bookie size), and `sel_m` (selection matched — total $ traded on this runner). The 3% EV-change threshold for trail writes keeps storage lean at ~43KB/day — avg 3.1 entries per pick, not hundreds. Trail data is retained permanently on pick rows (~22MB/year worst case).

`sel_m` shows null for stream-based updates (needs `trd` field not all markets emit) — a known gap.

### Time Gate Removal Validation (2026-04-27, Session 22:52)

The evening session validated the time gate removal: picks were detected down to 0.3 minutes (18 seconds) before jump with 100% trail coverage and full depth data. The 1-2 minute MTJ band was the **only profitable window** on this day (+129% ROI, 35% win rate), directly confirming the removal was the right call — the old 2-minute gate would have blocked every profitable pick.

Cumulative stats reached **769 picks across 6 days, +68.8 units** (down from +181u after the worst single day: 341 picks, 44 winners, -112u). The volume spike (341 vs ~100 normal) came from the time gate removal enabling near-jump detections plus evening greyhound meetings. Trail behavior confirmed: the 3% EV-change threshold correctly suppresses entries when EV is stable, with both TAB/TabTouch discrete-step and Betfair continuous-movement odds captured in trails.

### Supabase Constraints

DDL operations (CREATE TABLE, ALTER TABLE) cannot be executed via PostgREST or the service-role key — they must be run in Supabase's SQL Editor dashboard. RLS follows the TAKEOVER pattern: `service_role` has full access, `authenticated` has read-only (no org-scoped RLS needed since picks aren't user-owned). The table is in the SuperWin Supabase project (`swryqkixpqhvuagnqqul`), not the TAKEOVER project.

## Related Concepts

- [[concepts/value-betting-operational-assessment]] - The value betting scanner's operational weaknesses (no monitoring, no backtesting) motivated a more rigorous approach for SuperWin
- [[concepts/sharp-clv-theory-ranking]] - The CLV methodology from the value betting scanner applied to racing with BSP as the sharp reference
- [[concepts/betting-window-roi-methodology]] - The ROI methodology pattern (closing odds, dedup, window filtering) adapted for racing with detection-time vs BSP framing
- [[concepts/trail-stats-precomputed-columns]] - A parallel pre-computation architecture: VB scanner computes trail stats at resolution time, SuperWin computes settlement stats at result time
- [[concepts/superwin-racing-profitability-dimensions]] - The 16-dimension empirical analysis of backtesting data revealing harness dominance, liquidity goldmine, and mode-specific edges

## Sources

- [[daily/lcash/2026-04-23.md]] - VPS disk crisis (100% → 77% via 40GB volume + symlinks); designed edge_picks schema with mode-based backtesting, UNIQUE dedup, RLS pattern; 12 backtesting flaws ranked by severity; insert-only over upsert for first-detection preservation; racing filters (time-to-jump, max odds $30, spread <20%); CLV against BSP as gold standard; settlement resolver 90s loop (Sessions 12:05, 12:38). Peak EV tracking: peak_bookie_odds, peak_ev_pct, peak_detected_at columns; racing cron stops ~1:00 PM UTC; sports/golf bypass racing filters (Session 13:13)
- [[daily/lcash/2026-04-25.md]] - BSP only available for 21% of settled picks (AU greyhound/harness markets lack BSP); LTP available for 88%; resolver cascades BSP→LTP; backfilled 53 picks, coverage 21%→88%; 9 picks zero Betfair trading data. Early results: TAB +13.7% ROI, TabTouch -100%, Greyhounds -29.3%, Thoroughbreds +21.9%; 84% of picks detected <10min before jump — too late for practical betting. Cron toggle gap: toggling DB enabled flag doesn't hot-load adapters; cron should restart service not just flip flags. mode_slug always NULL — no edges have boost_mode configured yet (Session 13:07)
- [[daily/lcash/2026-04-26.md]] - TAB Cash Multiplier added as new edge (`racing-cash-multi`): flat `odds * 1.1` boost via `boost_multiplier` field in criteria (vs lookup table for SuperPicks). SuperPicks profitability deep-dive: **+70.0u, +38.6% ROI** across 181 settled picks; harness +157% vs thoroughbred +15.6% vs greyhound ~0%; sub-12% EV loses money (-18.7% ROI), 12%+ EV = +79.2% ROI on 106 picks; 4-5 detection scans sweet spot (+101% ROI); $5K+ Betfair liquidity worst (-40.5% ROI), $200-$1K profitable zone. `liquidity` column switched from `total_matched` (market-level) to `selection_matched` (per-runner Betfair `trd` field). Warmup guard deployed: 2+ bookies with 50+ races before persisting picks to journal. 9am cron changed from DB flag toggle to full systemctl restart. Sandown venue fuzzy matched to Sandown Park clearing 44h stuck pick (Sessions 13:19, 19:32)
- [[daily/lcash/2026-04-27.md]] - 2-minute-to-jump gate removed entirely — was cutting off most valuable near-jump data; EV tracking blindspot below 10% (6-9% band = edge formation phase); Option 2 proposed: memory-based pre-threshold trail; trail depth fields (lay_sz, bk_sz, sel_m) added; 3% EV-change threshold = 3.1 entries/pick avg, 43KB/day; sel_m null for stream-based updates; 502 picks/5 days; today -36.8u, all-time still +144u; 5 sub-2min picks detected with 100% depth coverage after gate removal (Sessions 09:58, 15:55, 20:26). Time gate validation: 1-2min MTJ was ONLY profitable window on day 6 (+129% ROI, 35% WR); cumulative 769 picks +68.8u; worst day: 341 picks -112u from 3x volume (gate removal + evening greyhounds); trail detection confirmed to 0.3min (18s) before jump with 100% depth coverage (Session 22:52)
