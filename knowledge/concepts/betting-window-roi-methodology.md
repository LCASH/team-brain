---
title: "Betting Window ROI Methodology"
aliases: [betting-window, closing-odds-roi, tdDedupeAndWindow, data-tab-methodology]
tags: [value-betting, analytics, methodology, dashboard, roi]
sources:
  - "daily/lcash/2026-04-17.md"
created: 2026-04-17
updated: 2026-04-17
---

# Betting Window ROI Methodology

A methodology overhaul for the value betting scanner's "The Data" analytics tab, addressing five issues that made historical performance metrics inaccurate: ROI calculated from `opening_odds` instead of `closing_odds`, no betting window filter, missing temporal fields, no deduplication across soft books, and EV heatmap bucketing by detection-time EV. The fix introduces `tdDedupeAndWindow()` — a unified pipeline that all heatmap, summary, and drilldown flows pass through for consistent deduplication and window filtering.

## Key Points

- ROI should use `closing_odds` (game-time price the bettor actually gets) instead of `opening_odds` (detection-time price) — reflects actual bet economics, not theoretical detection value
- Betting window filter uses "earliest trail entry within 3h of game start" — not a fixed 3h-out snapshot, because trail collection often starts at 3h so there's no data at exactly that mark
- Deduplication: same `(player, prop, side, line, date)` across multiple soft books counts as 1 pick, not N — raw counts were inflated ~2.6x
- Of 819 total picks, only 107 had +EV within the 3h betting window — these showed 45.8% WR / +24.32% ROI vs 52.7% WR / +6.43% ROI for all tracked picks
- 712 of 819 picks had no trail data in the 3h window (older picks from before trail system worked) — stats will improve as trail system matures
- `tdDedupeAndWindow()` pipeline ensures all analytics views (heatmap, summary, drilldown) use consistent logic

## Details

### The Five Issues

The Data tab was producing misleading performance metrics due to five independent problems, all surfacing on 2026-04-17:

**1. ROI from opening_odds.** The tab calculated ROI using `opening_odds` — the odds at the moment the scanner first detected the pick. But the bettor places the bet hours later, closer to game time, at whatever the book offers then. `closing_odds` (the last known odds before game start) is a more accurate proxy for the actual bet price. The difference matters because lines move: a pick detected at +150 might close at +130, and the bettor gets something close to the closing price.

**2. No betting window filter.** The tab showed all tracked picks regardless of whether they still had +EV at a realistic betting time. Many picks are detected 6-12 hours before game time but lose their edge before a bettor would act. Filtering to picks that showed +EV within 3 hours of game start dramatically changes the performance picture: from 52.7% WR / +6.43% ROI (all picks) to 45.8% WR / +24.32% ROI (window-filtered). The lower win rate with higher ROI suggests the window picks have better odds (higher payoff per win) despite winning less often.

**3. Missing temporal fields.** The API endpoint `/api/v1/picks/resolved` did not return `game_start` or `triggered_at`, making it impossible to compute the betting window on the client side. These fields needed to be added to the API response.

**4. No deduplication.** The same player+prop+side+line+date appearing on Sportsbet, Neds, and Ladbrokes counted as 3 picks. For ROI and win rate analysis, this is one betting opportunity, not three. The ~2.6x inflation (documented in [[concepts/pick-dedup-multi-theory-limitation]]) distorted all aggregate metrics.

**5. EV heatmap bucketing.** The heatmap bucketed picks by detection-time EV, not window EV. A pick detected at 15% EV that dropped to 2% EV by the betting window would appear in the 15% bucket, overstating the edge available to the bettor.

### The Window Mechanics

Trail data collection starts at `max_hours_before_start` (3 hours for most theories). This means looking for a trail entry at exactly 3 hours before game start often yields nothing — the first trail entry is at 2:58 or 2:55, depending on the push cycle timing. The betting window therefore uses "earliest trail entry within 3 hours of game start" rather than a snapshot at a fixed offset.

For picks where no trail data exists in the 3-hour window (712 of 819 on 2026-04-17), the pick is excluded from window-filtered analysis. These are primarily older picks from before the trail system was fully operational (see [[concepts/trail-data-temporal-resolution]]). As the trail system matures and new picks accumulate proper trail coverage, the "no data" count will shrink and window-filtered statistics will become more representative.

### The tdDedupeAndWindow() Pipeline

All analytics views — heatmap, summary cards, and drilldown tables — now pass through `tdDedupeAndWindow()` before rendering. This function:

1. Deduplicates by `(player, prop, side, line, date)` — keeping the pick with the best closing odds (since the bettor would choose the best available book)
2. Applies the betting window filter when enabled — checking for trail entries within the configured window
3. Returns a consistent dataset that all downstream views consume

This eliminates the class of bugs where one view applies different logic than another (the multiple-render-paths anti-pattern documented in [[concepts/dashboard-client-server-ev-divergence]]).

### Performance Considerations

The Data tab initially loaded 60 days of resolved picks (21K picks, 11MB, 25 seconds) causing browser timeouts. The default range was reduced to 7 days, loading in ~3 seconds. Large Supabase paginated responses (22 pages x 1000 rows) can silently succeed on the API but choke browser-side JavaScript parsing. The 7-day default balances recency with load performance; users can expand the range manually when needed.

### Remaining Caveats

The 40% average window EV figure on 2026-04-17 was inflated by phantom soccer moneyline EVs from the 3-way devig bug (see [[concepts/soccer-three-way-devig-phantom-ev]]). These phantom picks were voided but their trails may still appear in historical windows. Additionally, alt lines with extreme odds (e.g., 36.00) produce garbage EV calculations when devigged against main lines — the `max_line_gap` / `is_alt` safety checks are not catching all cases, contributing to outlier inflation in the heatmap.

## Related Concepts

- [[concepts/pick-dedup-multi-theory-limitation]] - The ~2.6x dedup inflation that the analytics pipeline must correct; established the principle that dedup belongs at analytics layer not tracker
- [[concepts/trail-data-temporal-resolution]] - Trail data quality determines whether window filtering has sufficient data; pre-fix trails were sparse
- [[concepts/dashboard-client-server-ev-divergence]] - The multiple render paths anti-pattern that `tdDedupeAndWindow()` prevents by centralizing logic
- [[concepts/alt-line-mismatch-poisoned-picks]] - Alt-line phantom EVs that contaminate heatmap analysis despite the interpolation fix
- [[concepts/soccer-three-way-devig-phantom-ev]] - Voided soccer phantom picks still appearing in historical window EV data

## Sources

- [[daily/lcash/2026-04-17.md]] - Betting window analysis: 107/819 picks in 3h window → 45.8% WR, +24.32% ROI vs 52.7% / +6.43% all; 5 Data tab issues identified; `tdDedupeAndWindow()` pipeline; closing_odds for ROI; 712/819 no window trail data; 21K picks / 11MB / 25s → 7-day default; alt-line extreme odds still producing garbage EV (Sessions 17:14, 21:11)
