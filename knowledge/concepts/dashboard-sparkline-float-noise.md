---
title: "Dashboard EV Sparkline Floating-Point Noise"
aliases: [sparkline-noise, ev-sparkline-jitter, float-quantization, sparkline-phantom-movement]
tags: [value-betting, dashboard, visualization, data-quality, bug]
sources:
  - "daily/lcash/2026-05-09.md"
created: 2026-05-09
updated: 2026-05-09
---

# Dashboard EV Sparkline Floating-Point Noise

EV sparklines on the value betting dashboard showed wild up/down movement even though the displayed EV percentage never actually changed. The root cause was floating-point jitter from upstream odds data (e.g., 11.30 → 11.29997 → 11.30002) amplified by the sparkline's auto-scaled Y-axis. When the real EV range is 0.003%, auto-scaling stretches that micro-range to fill the chart height, making invisible noise look like dramatic price movement. Non-bet365 books had the worst phantom movement, likely from more decimal precision in their odds feeds.

## Key Points

- Upstream float jitter (e.g., `11.30 → 11.29997 → 11.30002`) produced phantom sparkline movement when the Y-axis auto-scaled to a tiny range
- Fix 1: **Quantize EV samples** to 1 decimal place (`Math.round(ev * 10) / 10`) before storing in sparkline history — eliminates sub-0.1% noise
- Fix 2: **Hide sparklines entirely** when the real EV range is < 0.5% — if EV hasn't meaningfully moved, don't draw a misleading chart
- Non-bet365 books showed worse phantom movement — likely more decimal precision in their odds feeds compared to bet365's rounded fractional odds
- The noise was in the sparkline history buffer, not in the displayed EV% value — the EV% column showed a stable number while the mini-chart beside it oscillated wildly
- This is a visualization-layer bug, not a data or computation bug — the underlying EV calculations were correct

## Details

### The Auto-Scale Amplification Mechanism

Sparkline charts typically auto-scale their Y-axis to fit the data range. When the EV% for a pick oscillates between 11.29997% and 11.30003% (a 0.00006% range from float arithmetic noise), the auto-scaler maps this range to the full chart height. A 0.00006% difference, which is completely meaningless for betting decisions, renders as a full-amplitude oscillation that looks like the market is moving rapidly.

The visual effect is particularly misleading because sparklines lack axis labels — the viewer sees "up-down-up-down" and interprets it as volatile EV, not as noise. A standard line chart with labeled axes would show a flat line at 11.30%; the sparkline's unlabeled auto-scale creates a false impression of movement.

### Why Non-Bet365 Books Are Worse

bet365's odds are internally represented as fractional values (e.g., `7/4`), which convert to clean decimal representations. OpticOdds and other data sources may deliver odds with higher decimal precision from their own internal computations. When these slightly-different-precision odds feed into the EV calculation, the output inherits the precision difference — producing the micro-jitter that the sparkline amplifies.

The user correctly identified this as noise rather than signal: the displayed EV% in the table column remained stable while the sparkline beside it showed phantom movement. This diagnostic observation — "the number doesn't change but the chart moves" — is the key indicator that the issue is float precision, not market movement.

### The Two-Part Fix

**Quantization** rounds each EV sample to 1 decimal place before appending to the sparkline history buffer. This collapses `11.29997, 11.30002, 11.29999` into a uniform `11.3, 11.3, 11.3` — the sparkline shows a flat line because all samples are identical after rounding. The 0.1% granularity is appropriate for EV visualization: a bettor would never act on a 0.01% EV change, so smoothing to 0.1% resolution preserves all decision-relevant information.

**Minimum-range hiding** suppresses the sparkline entirely when the quantized EV range is less than 0.5%. This handles the case where quantized values still show minor oscillation (e.g., `11.3 → 11.2 → 11.3`) from samples near the rounding boundary. A 0.5% range threshold means sparklines only render when there has been a meaningful EV shift — providing visual signal only when there is genuine information.

### Pattern: Auto-Scaled Micro-Range Visualization

This is a general pattern in dashboard visualization: any auto-scaled chart displaying high-precision floating-point data will amplify noise when the real data range is small. The defense is always the same: quantize inputs to decision-relevant precision and suppress the visualization when the data range is below a meaningful threshold. The specific thresholds (0.1% quantization, 0.5% minimum range) are domain-specific but the pattern applies to any dashboard displaying computed financial metrics.

## Related Concepts

- [[concepts/dashboard-client-server-ev-divergence]] - The broader chronicle of dashboard display issues; sparkline noise is a visualization-layer bug distinct from the computation-layer bugs documented there
- [[concepts/v3-dashboard-ev-computation-architecture]] - The V3 dashboard architecture where the sparklines are rendered; the EV computation feeding the sparklines is correct, only the visualization is noisy
- [[connections/dual-codebase-ev-computation-drift]] - A different class of EV display bug: algorithmic drift produces wrong numbers, while sparkline noise produces correct numbers with misleading visualization
- [[concepts/sse-polling-staleness-threshold-mismatch]] - SSE-based data updates mean odds timestamps change only on real price movement, but float precision in the EV computation still introduces jitter between identical inputs

## Sources

- [[daily/lcash/2026-05-09.md]] - User noticed sparklines showing wild movement despite stable EV%; non-bet365 books worst phantom movement; fix: quantize to 1 decimal place (`Math.round(ev * 10) / 10`) + hide when range < 0.5%; two merges with friend's branch auto-merged cleanly (Session 11:53)
