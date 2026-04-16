---
title: "EV Pipeline Dropout Logging"
aliases: [dropout-logging, ev-funnel-analysis, pipeline-dropout, filter-stage-logging]
tags: [value-betting, debugging, observability, methodology]
sources:
  - "daily/lcash/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# EV Pipeline Dropout Logging

A reusable debugging pattern for diagnosing EV theory pipelines: log the market count at each filter stage to produce a funnel analysis showing exactly where and why markets are eliminated. Applied to the Pinnacle prediction-market pipeline, it immediately revealed that the pipeline was working correctly but the market was too efficient for large edges — resolving the mystery of "0 picks despite 2,456 markets" without any code changes needed.

## Key Points

- The pattern logs counts at each stage: `total → live → propSkip → noPair → noSoft → softStale → noResult → evNeg → evLow → PASS`
- Applied to Pinnacle: 2,456 → -734 live → -855 propSkip → -569 noSoft → -50 lineGap → 298 eval → 247 negEV → 1 belowThreshold → 0 pass
- Immediately distinguished "pipeline broken" from "market efficient" — the pipeline processed markets correctly, Pinnacle just doesn't produce large edges against prediction markets on props
- The funnel reveals which filter is the biggest bottleneck: `noSoft` (569 markets with no matching soft book entry) was the largest unexpected loss, suggesting data coverage gaps
- Reusable across any EV theory — add the same counter instrumentation and the funnel works for AFL, NHL, or any new sport/theory combination

## Details

### The Diagnostic Problem

The Pinnacle prediction-market theory (see [[concepts/pinnacle-prediction-market-pipeline]]) showed 38 server-side picks but 0 picks on the dashboard at min_ev=5. The typical debugging approach would involve inspecting individual markets, checking theory configuration, verifying data flows — a time-consuming process. Without structured observability, the developer is essentially guessing at which pipeline stage is the bottleneck.

### The Pattern

The dropout logging pattern instruments each filter stage in the EV evaluation loop with a simple counter. Before and after each filter, the count of remaining markets is logged. The output is a single-line funnel:

```
total/live/propSkip/noPair/noSoft/softStale/noResult/evNeg/evLow/PASS
2456 / 1722 / 867 / 298 / 298 / 298 / 298 / 51 / 1 / 0
```

Each step represents a filter in the evaluation pipeline:

| Stage | What it filters | Pinnacle result |
|-------|----------------|-----------------|
| **total** | All markets from OpticOdds | 2,456 |
| **live** | Remove live/in-play markets | -734 (1,722 remain) |
| **propSkip** | Remove excluded prop types | -855 (867 remain) |
| **noPair** | No matching sharp-soft pair | (absorbed into noSoft) |
| **noSoft** | No soft book entry for this market | -569 (298 remain) |
| **softStale** | Soft book odds too old | 0 dropped |
| **noResult** | Can't compute EV (line gap, etc.) | -50 (248 remain) |
| **evNeg** | Negative EV after devig | -247 (1 remain) |
| **evLow** | Below min_ev threshold | -1 (0 remain) |
| **PASS** | Pick triggered | **0** |

### What the Funnel Revealed

The Pinnacle funnel told three stories simultaneously:

1. **The pipeline is not broken.** Markets flow through all stages without errors. The 0 picks are not caused by a bug but by market efficiency.

2. **The biggest filter-stage loss is `noSoft` (569 markets).** These are Pinnacle markets where no prediction market (Kalshi, Polymarket) offers the same market. This suggests data coverage gaps — either the prediction markets don't offer these props, or OpticOdds doesn't carry them. This is a data partnership issue, not a code issue.

3. **The 298 markets that reach EV evaluation produce near-zero edges.** 247 are negative EV, and the 1 that's positive is below the min_ev=5 threshold. Pinnacle and prediction markets price NBA player props similarly enough that devigging produces <5% edge on all but a handful of markets.

### Generality

The pattern is reusable because the filter stages are common to all EV theory evaluations. Any theory — AFL, NHL, soccer — goes through the same pipeline: load markets → filter live → filter prop types → find sharp-soft pairs → compute EV → apply threshold. Adding counter instrumentation at each stage costs ~10 lines of code and provides permanent observability into theory performance.

The pattern is also useful for monitoring theory health over time: if the `noSoft` count suddenly increases, it signals a data source regression. If `evNeg` increases, sharp-soft convergence may have changed. The funnel is a lightweight operational health signal for the theory system.

## Related Concepts

- [[concepts/pinnacle-prediction-market-pipeline]] - The pipeline where dropout logging was first applied
- [[concepts/pinnacle-prop-type-sharpness-variance]] - Discovered via the funnel analysis: the per-prop breakdown that dropout logging enabled
- [[concepts/value-betting-theory-system]] - The theory system whose pipelines benefit from this debugging pattern
- [[concepts/worker-status-observability]] - A parallel observability pattern for scraper health (reporting actual state vs. hardcoded status)

## Sources

- [[daily/lcash/2026-04-16.md]] - Dropout logging added to Pinnacle pipeline: 2456 → 734 live → 855 propSkip → 569 noSoft → 50 lineGap → 298 eval → 247 neg → 1 low → 0 pass; immediately distinguished "pipeline works, market efficient" from "pipeline broken"; reusable across any EV theory (Sessions 13:04, 13:38)
