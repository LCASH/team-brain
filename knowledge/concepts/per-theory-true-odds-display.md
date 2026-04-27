---
title: "Per-Theory True Odds Display"
aliases: [per-theory-lines, multi-theory-chart, sharp-disagreement-signal, theory-colored-lines, ev-flip-flop]
tags: [value-betting, dashboard, visualization, architecture, data-quality]
sources:
  - "daily/lcash/2026-04-27.md"
created: 2026-04-27
updated: 2026-04-27
---

# Per-Theory True Odds Display

The value betting dashboard's trail chart originally displayed a single blended "true odds" purple line computed from all available sharp books. On 2026-04-27, this was replaced with separate colored lines per qualifying theory, each computed using that theory's specific sharp books, weights, and devig method. This surfaces sharp disagreement as a confidence signal: when FanDuel (Aggressive theory) says -EV and DraftKings (AltLine-V1) says +EV, the per-theory display shows the conflict rather than hiding it in a blended average. The table was also updated to display per-theory true odds above each EV% column.

## Key Points

- Single blended true-odds line is misleading because different theories (Aggressive, AltLine-V1, Pinnacle Only) use different sharps with different weights — the "true" line IS different per theory
- Per-theory colored lines in the trail chart show where theories agree (high confidence) vs disagree (low confidence) — previously invisible
- Data freshness causes EV flip-flops: FanDuel goes stale periodically (captured_at drifts past 600s); when only DraftKings is fresh → true=1.83 (+EV); when both fresh → FanDuel drags average to 1.96 (breakeven)
- Per-theory true odds now displayed inline in table EV columns (true odds, EV%, CLV per theory) — each independently computed
- Under picks require visual interpretation: soft ABOVE true = +EV (opposite of Over picks), which is mathematically correct but easy to misread

## Details

### The Blended Line Problem

The original trail chart drew a single purple "true odds" line representing the devigged fair value. This line was computed by blending odds from all available sharp books at each trail timestamp. The problem is fundamental: different theories define different sharp book sets with different weights. The "Aggressive" theory might weight FanDuel at 1.0 and DraftKings at 1.0, while "AltLine-V1" uses only DraftKings with different line-gap handling. These produce genuinely different true-probability estimates for the same market at the same moment.

When blended into one number, the conflict is invisible. A pick might show "+3.8% EV" which appears confident, but the underlying reality is that one theory says +8% and another says -2%. The blended value hides a meaningful disagreement about whether the pick has edge at all.

### FanDuel Staleness and EV Oscillation

A concrete example illustrates the problem. For an NBA Rebounds Under pick, the dashboard showed EV oscillating between positive and negative on successive render cycles. The cause was FanDuel's data freshness: FanDuel's `captured_at` periodically drifts past the `MAX_ODDS_AGE_S` threshold (600s), causing it to be excluded from the devig computation. When only DraftKings is fresh, the devigged true odds = 1.83 (+3.8% EV). When both are fresh, FanDuel's different pricing drags the weighted average to 1.96 (-0.4% EV).

This is not a bug — it is the mathematical consequence of blending sharp books with different freshness windows. The per-theory display resolves it by showing each theory's assessment independently: the DraftKings-only theory consistently shows +EV, while the multi-sharp theory fluctuates based on FanDuel availability. The operator can then decide which signal to trust.

### Implementation

The fix required changes in two places:

**Trail chart**: Instead of one purple line, multiple colored lines are drawn — one per qualifying theory. Each line's true-odds value is computed using only that theory's configured sharp books and weights. The operator can visually see whether theories converge (all lines close together = high confidence) or diverge (lines spread apart = low confidence, sharp disagreement).

**Table columns**: Each theory's EV column now displays that theory's specific true odds above the EV%, computed independently using that theory's sharp books, weights, and devig method. Previously, all theories shared one blended true-odds value.

### Under Pick Visual Interpretation

For Under picks, the visual relationship between soft odds (green) and true odds (purple/colored) is inverted compared to Over picks. For Overs, soft BELOW true = +EV (you're getting paid more than fair). For Unders, soft ABOVE true = +EV. This is mathematically correct but creates a visual trap: an operator accustomed to reading "green above purple = bad" from Over picks will misread Under charts. A visual EV direction indicator (shaded region or arrow) is planned but not yet implemented.

### Combo vs Solo Prop Confusion

During chart debugging, a user confusion was resolved: "Rebounds Assists" combo at line 8.5 is a completely different market from "Rebounds" solo at line 5.5. The dashboard's market matching was correct, but the user was comparing the dashboard's combo prop against bet365's solo Rebounds page, producing an apparent odds mismatch that was actually two different markets.

## Related Concepts

- [[concepts/dashboard-client-server-ev-divergence]] - The broader pattern of dashboard displaying different values than the backend; per-theory display is the architectural fix for one dimension of this divergence
- [[concepts/theory-aware-sharp-book-filtering]] - The theory lookup mechanism (triggered_by → weights → sharp IDs) that per-theory display reuses; both fixes share the principle that devig must be theory-specific
- [[concepts/sharp-clv-theory-ranking]] - Theory ranking by sharp CLV provides the "which theory to trust" context; per-theory display surfaces this ranking visually in real-time
- [[concepts/value-betting-theory-system]] - Theories define different sharp book sets; per-theory display is the UI consequence of this configurability
- [[concepts/opticodds-tcp-drop-max-age-tuning]] - FanDuel staleness driving EV oscillation is related to the MAX_ODDS_AGE tuning; both involve sharp data aging affecting EV computation

## Sources

- [[daily/lcash/2026-04-27.md]] - Trail chart showed single blended true-odds line hiding sharp disagreement; FanDuel staleness caused EV flip-flops between +3.8% and -0.4% as it drifted past freshness threshold; per-theory colored lines deployed; per-theory true odds in table columns; Under pick visual interpretation issue; combo vs solo prop confusion resolved (Sessions 08:10, 08:45, 09:23)
