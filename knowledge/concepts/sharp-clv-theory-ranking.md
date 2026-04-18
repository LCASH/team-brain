---
title: "Sharp CLV Theory Ranking"
aliases: [sharp-clv, closing-line-value, theory-ranking, clv-analytics, altline-v1]
tags: [value-betting, analytics, methodology, clv, dashboard]
sources:
  - "daily/lcash/2026-04-18.md"
created: 2026-04-18
updated: 2026-04-18
---

# Sharp CLV Theory Ranking

Closing Line Value (CLV) measured against sharp book closing lines — not soft book closing lines — is the primary metric for evaluating which betting theories produce genuine edge. A comprehensive CLV analytics system was built across the value betting scanner's backend and dashboard, revealing that **AltLine-V1 is the clear winner** at +28.4% sharp CLV across all NBA history, while Aggressive-Wide has no edge (-9.3% CLV, only 6.2% CLV>0 rate). Soft CLV was confirmed as useless (~0% for Australian books that don't move lines).

## Key Points

- Sharp CLV uses sharp book trail data as the closing reference; soft CLV uses the soft book's own closing odds — soft CLV is always ~0% for AU books (they don't move lines pre-game)
- Theory ranking by sharp CLV: **AltLine-V1 +28.4%** (sharpest), Conservative 72.7% CLV>0 rate (most consistent), Aggressive-Wide -9.3% (no edge)
- CLV is more reliable than win/loss for evaluating edge — a theory with high win rate but negative CLV (like Aggressive-Wide at 62% WR but -13.5% CLV) is winning by luck, not skill
- Sharp CLV coverage jumped from 27% → 53%+ after deploying interpolation fix in the resolver (was exact-match only for line lookups)
- `avg_sharp_clv` added to all 10+ breakdown functions (theory, side, prop, book, EV bucket, timing, daily) in analytics backend
- MLB Calibrated (+6.4% CLV) and Conservative (+6.5% CLV) are the sharpest MLB theories — recommended for real money

## Details

### Why Sharp CLV Over Soft CLV

The scanner previously displayed soft CLV — comparing the bet odds against the soft book's own closing odds. For Australian retail books (Sportsbet, Ladbrokes, PointsBet AU), this metric was always approximately 0% because these books rarely move their lines pre-game. A bettor who gets +150 at detection time is still getting approximately +150 at game time, so soft CLV shows no change. This makes soft CLV useless for evaluating whether a theory is finding genuine value.

Sharp CLV compares the bet odds against the sharp book's closing line at game time. If the sharp closing line moves toward the bettor's price (e.g., sharp opens at +140, bettor takes +150, sharp closes at +148), the bettor has positive CLV — they got a price better than the market's final estimate of true probability. This is the gold standard metric in professional sports betting: consistent positive sharp CLV is the strongest evidence of genuine edge, regardless of short-term win/loss variance.

### Theory Ranking Results

Analysis across 7,724 resolved picks with sharp CLV data produced a definitive theory ranking:

| Theory | Sharp CLV | CLV>0 Rate | Win Rate | Assessment |
|--------|-----------|------------|----------|------------|
| AltLine-V1 | **+28.4%** | — | — | Clear winner, sharpest theory |
| Conservative | — | **72.7%** | — | Most consistent edge |
| MLB Calibrated | +6.4% | 70%+ | — | High volume, sharp on MLB |
| MLB Conservative | +6.5% | 70%+ | — | Low volume, equally sharp |
| Aggressive | ~0% | — | 49% | Most picks, not beating close |
| Aggressive-Wide | **-9.3%** | 6.2% | 62% | No edge — high WR is noise |

The AltLine-V1 result is particularly striking: +28.4% sharp CLV suggests the theory is consistently finding prices that the sharp market later confirms were underpriced. The Aggressive-Wide result is equally important as a negative finding: 62% win rate looks impressive, but -9.3% CLV and only 6.2% CLV>0 rate means the wins are on low-value bets that the market correctly priced — the apparent profitability is sampling noise that will regress to negative returns.

### Trail Coverage and Interpolation Fix

Sharp CLV requires trail data capturing the sharp book's odds at different points in time. Coverage was initially only 27% because the resolver used exact-match line lookups — if the sharp trail had data at line 25.5 but the pick was at line 25.0, no CLV could be computed. Deploying an interpolation fix in the resolver (allowing approximate line matching across small gaps) jumped coverage from 27% to 53%+.

Bet365 2.0 had particularly poor coverage (24/475 picks, ~5%) because of the trail pre-seeding bug documented in [[concepts/trail-preseeding-coverage-bug]] — the mini PC inserted picks but the VPS never wrote baseline trails for them.

### Peak EV vs CLV

During the analytics build, lcash explored using "peak EV opportunity" — the moment during a trail where the soft book was most mispriced relative to sharp consensus — instead of CLV. The thesis was that peak EV represents the best opportunity available to the bettor, while CLV only measures the closing snapshot. However, CLV was retained as the primary metric because it is the industry standard and enables comparison with published research. Peak EV may be added as a supplementary metric.

### Resolver Closing Odds Fix

The resolver was using a stale `current_odds` scalar column for closing odds instead of the last real trail entry. All three resolution paths (moneyline, game-line, player-prop) were updated to use `soft_trails.get(pick_id)` — the actual last-observed odds from trail data. This affects future resolutions only; historical picks retain their original closing odds. The -1.7% ROI on 9,695 picks may be partially inaccurate because of this stale closing odds source.

### Historical Backfill

A backfill script was built to compute sharp CLV for historical picks that had trail data but no CLV column value. The script uses PATCH requests (not upsert, which fails due to NOT NULL constraints on `player_name` when doing partial inserts) to update existing rows. Supabase GET requests with large `in` filters exceed URL length limits (502 errors), so the backfill processes picks individually — 3,603 PATCHes for the current batch. Of the total pick population, 16,762 picks have no sharp trail data at all (pre-trail-migration) and can never be backfilled.

### Dashboard Integration

`avg_sharp_clv` was added to all 10+ breakdown functions in the analytics backend: theory, side, prop type, book, EV bucket, timing, and daily breakdowns. The dashboard displays sharp CLV instead of the previously useless soft CLV. A `theory_ranking` view sorted by sharp CLV with `sharp_clv_positive_pct` was added as the primary "which theory to trust" interface. A fallback pattern `(t.avg_sharp_clv ?? t.avg_clv)` ensures backward compatibility with theories that don't yet have sharp CLV data.

A `_fetch_fixture_scores()` positional argument bug was discovered and fixed during deployment — `fetch_date` was being passed into the `sport` parameter position, causing a duplicate keyword argument error.

## Related Concepts

- [[concepts/pinnacle-prop-type-sharpness-variance]] - Per-prop-type sharpness variance is the granular layer beneath theory-level CLV ranking
- [[concepts/betting-window-roi-methodology]] - The ROI methodology that CLV analytics complement — CLV is the predictive metric, ROI is the outcome metric
- [[concepts/value-betting-theory-system]] - The theory system whose configurations the CLV ranking evaluates
- [[concepts/trail-data-temporal-resolution]] - Trail data quality directly determines sharp CLV coverage — pre-fix sparse trails limit historical CLV computation
- [[concepts/trail-preseeding-coverage-bug]] - The pre-seeding bug that caused 5% trail coverage on Bet365 2.0 picks
- [[concepts/afl-circular-devig-trap]] - The AFL case where +1.16% CLV against non-sharp books was meaningless; sharp CLV would have shown the truth immediately

## Sources

- [[daily/lcash/2026-04-18.md]] - Sharp CLV as #1 metric; theory ranking: AltLine-V1 +28.4%, Conservative 72.7% CLV>0, Aggressive-Wide -9.3%; soft CLV always ~0% for AU books; coverage 27%→53% after interpolation fix; `avg_sharp_clv` added to 10+ breakdown functions; resolver Fix A (trail-based closing odds); backfill 3,603 PATCHes, 16,762 picks never backfillable; MLB Calibrated/Conservative +6.4-6.5% CLV sharpest; `_fetch_fixture_scores()` positional arg bug fixed; peak EV concept explored (Sessions 16:34, 17:04, 17:35, 21:07)
