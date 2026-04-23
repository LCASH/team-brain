---
title: "Trail Stats Pre-Computed Columns"
aliases: [trail-stats, peak-ev-columns, precomputed-trail-stats, resolver-trail-stats, trail-roi-dashboard]
tags: [value-betting, analytics, performance, dashboard, architecture]
sources:
  - "daily/lcash/2026-04-23.md"
created: 2026-04-23
updated: 2026-04-23
---

# Trail Stats Pre-Computed Columns

Nine pre-computed trail statistic columns were added to `nba_tracked_picks` to eliminate expensive client-side trail fetching. The trail-ROI dashboard previously made N/30 batch API calls to `trail_entries` for every pick on page load, taking 30-60 seconds. With pre-computed columns (`peak_ev`, `peak_odds`, `peak_true_odds`, `peak_at`, `avg_ev`, `ev_positive_count`, `closing_ev`, `closing_true_odds`, `trail_count`), the dashboard loads in under 1 second. Stats are computed automatically by the resolver at resolution time when trail data exists.

## Key Points

- Dashboard load time dropped from **30-60 seconds to <1 second** by replacing N/30 batch trail_entries API calls with pre-computed columns on the pick row
- Nine columns: `peak_ev`, `peak_odds`, `peak_true_odds`, `peak_at`, `avg_ev`, `ev_positive_count`, `closing_ev`, `closing_true_odds`, `trail_count`
- Stats computed at resolution time by the resolver (not incrementally during Phase B trail writes) — cleaner since the resolver already reads trail data when grading
- Peak EV is the moment where `(soft_odds x true_prob - 1)` is maximized — requires pairing soft odds with their contemporaneous sharp true probability, not just highest soft odds
- `avg_ev` is the mean of all positive EV moments (more useful than `min_ev` as a noise filter)
- `closing_true_odds` stores the last sharp consensus odds separately from `closing_odds` (soft book side) — needed for CLV calculation
- Picks without trails stay NULL for all trail stat columns — never backfill with zeros
- SVG trail chart per pick (soft odds, true odds, EV% over time, peak EV marker) fetches on-demand per click

## Details

### The Performance Problem

The trail-ROI dashboard (`trail-roi.html`) displayed trail statistics for each tracked pick: peak EV opportunity, average EV, closing line value, and trail count. The initial implementation fetched trail entries from Supabase for every pick visible on the page, using batched API calls (30 picks per batch). With 200+ picks, this produced 7+ sequential API requests, each returning hundreds of trail rows. The client-side JavaScript then computed peak EV, average EV, and other statistics from the raw trail data.

This architecture scaled poorly: 200 picks x ~10 trails each = ~2,000 rows fetched and processed client-side. The Supabase round-trips alone took 20-30 seconds, and JavaScript computation added another 10-30 seconds depending on browser performance. The dashboard was unusable for regular monitoring.

### The Pre-Computation Architecture

The fix moves computation to the server side at resolution time. When the resolver grades a pick (win/loss/push), it already reads the pick's trail data to determine closing odds. The resolver now additionally computes all nine statistics and writes them to the pick row in a single UPDATE. The dashboard reads only the pick table — no trail_entries join needed for the summary view.

The nine columns capture the complete trail profile:

| Column | Description |
|--------|-------------|
| `peak_ev` | Maximum EV% observed during trail period |
| `peak_odds` | Soft book odds at the peak EV moment |
| `peak_true_odds` | Sharp consensus true odds at the peak EV moment |
| `peak_at` | Timestamp of the peak EV moment |
| `avg_ev` | Mean of all positive EV trail entries |
| `ev_positive_count` | Count of trail entries with positive EV |
| `closing_ev` | EV at the last trail entry before game start |
| `closing_true_odds` | Last sharp consensus odds (for CLV calculation) |
| `trail_count` | Total number of trail entries for this pick |

### Peak EV Semantics

Peak EV is NOT the same as highest soft odds. It is the moment where `(soft_odds x true_probability - 1)` is maximized. This requires pairing each soft book odds observation with its contemporaneous sharp true probability. A soft book price of 3.00 at a moment when the sharp true probability is 40% produces +20% EV, while the same 3.00 at 30% true probability produces -10% EV. The peak is the best *opportunity* adjusted for the market's evolving view of true value.

This distinction matters because soft odds and true odds can move independently. The soft book might have its highest odds when the sharp market has already moved against the bet (making the high soft odds not actually the best EV moment).

### avg_ev Over min_ev

The user corrected the initial design from `min_ev` (worst EV moment) to `avg_ev` (mean of positive EV moments). The reasoning: `min_ev` is the least informative statistic — it captures the moment right before the edge disappears, which doesn't help evaluate pick quality. `avg_ev` captures the typical EV available to a bettor who places the bet at an arbitrary moment during the +EV window — a better proxy for the realistic return expectation.

### closing_true_odds for CLV

The existing `closing_odds` field captures the soft book's closing odds — what the bettor would get if they placed the bet at the last possible moment. `closing_true_odds` captures the sharp market's closing view of true probability. The difference between these two values is Closing Line Value (CLV) — the gold standard metric for evaluating whether a bettor consistently beats the market. Without `closing_true_odds`, CLV could only be computed from raw trail data, requiring the expensive join that the pre-computation eliminates.

### Historical Data Caveat

Historical trail data (pre-size-gate-fix) shows wild oscillations from the bet365 size-gate bug (see [[concepts/bet365-size-gate-stale-odds]]) — soft odds bouncing between ~1.3 and ~4.3, producing fake 191% peak EVs. Post-fix data will be clean. The trail-ROI dashboard should be filtered to only show post-fix picks (2026-04-23 onwards) to avoid misleading historical data.

During backfill, 551 picks were incorrectly set to `peak_ev=0` (these had no trails). These were cleaned back to NULL. The 361 picks with real trail data retained their computed stats.

### On-Demand Trail Charts

Individual pick expansion shows an SVG trail chart with three lines: soft odds, true odds, and EV% over time, with a marker at the peak EV moment. These charts fetch trail entries on-demand per click (not on page load), so the summary table loads instantly and charts are rendered only when the user wants detail.

## Related Concepts

- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV uses `closing_true_odds` for theory ranking; pre-computed columns make this accessible without trail joins
- [[concepts/betting-window-roi-methodology]] - The ROI methodology that these trail stats extend with peak EV and average EV dimensions
- [[concepts/trail-data-temporal-resolution]] - Trail data quality determines the reliability of pre-computed stats; pre-fix sparse trails produce less precise peak/avg values
- [[concepts/theory-aware-sharp-book-filtering]] - The devig bug fix (theory-specific sharps) directly affects the accuracy of `peak_true_odds` and `closing_true_odds`
- [[concepts/bet365-size-gate-stale-odds]] - Size-gate bug produced oscillating odds in historical trails; post-fix data clean

## Sources

- [[daily/lcash/2026-04-23.md]] - Trail-ROI dashboard 30-60s → <1s via pre-computed columns; 9 columns designed (peak_ev, peak_odds, peak_true_odds, peak_at, avg_ev, ev_positive_count, closing_ev, closing_true_odds, trail_count); resolver computes at resolution time; peak EV = max(soft_odds x true_prob - 1) not max(soft_odds); avg_ev over min_ev; closing_true_odds for CLV; 551 false-zero picks cleaned; SVG trail chart on-demand (Sessions 16:17, 16:48). Dashboard deployed to VPS trail-roi.html; N/30 batch pattern replaced with pre-computed columns (Session 10:39)
