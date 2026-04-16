---
title: "Niche League Tracker Pipeline Bottlenecks"
aliases: [niche-league-bottlenecks, active-sports-auto-merge, sharp-freshness-cutoff, tracker-snapshot-bypass]
tags: [value-betting, pipeline, debugging, niche-leagues, compound-failures]
sources:
  - "daily/lcash/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# Niche League Tracker Pipeline Bottlenecks

Three independent bottlenecks in the value betting scanner's tracker compounded to silently produce zero picks for niche league markets (Euroleague, CBA, Turkey BSL, soccer leagues) despite 454+ markets with Pinnacle-prediction-market overlap. Each bottleneck looked reasonable in isolation; only tracing the full pipeline from OpticOdds polling through to tracker iteration revealed all three. The fixes were: expanding `ACTIVE_SPORTS` auto-merge to include all `PINNACLE_LEAGUE_KEYS`, increasing the sharp freshness cutoff from 30s to 120s, and adding a `get_tracker_snapshot()` that bypasses the SSE display filter.

## Key Points

- Three independent filters each silently discarded niche league data: (1) `ACTIVE_SPORTS` iteration skipped non-core sports, (2) 30s sharp freshness cutoff expired niche league data polled at 60s intervals, (3) SSE display filter also filtered the tracker's market view
- The 30s sharp freshness cutoff was tuned for major leagues (5-10s polling) but broke niche leagues (60s polling) — increased to 120s to accommodate the slower poll interval while still rejecting stale data
- `get_tracker_snapshot()` was added to provide the tracker with an unfiltered view of market state, bypassing the SSE browser-crash-prevention filter that legitimately hides niche markets from the SSE stream
- After all three fixes, picks will appear automatically as games enter the 24-hour pre-game window — most niche league games were 27-124 hours away, which is why zero picks was correct behavior post-fix
- The compound bottleneck pattern — each filter reasonable alone, zero output together — is a recurring anti-pattern in the scanner's architecture

## Details

### The Three Bottlenecks

**1. ACTIVE_SPORTS iteration (relay mode).** The tracker's main loop iterates `ACTIVE_SPORTS` — a list containing only the core sports (`nba`, `mlb`, `nrl`, `afl`). When running in relay mode on the VPS (receiving data from the mini PC), the tracker auto-merges sport data from push payloads, but only for sports in `ACTIVE_SPORTS`. Niche leagues polled by VPS-side Pinnacle pollers (Euroleague, CBA, Turkey BSL, etc.) were written to the server state but never iterated by the tracker because their league keys weren't in the `ACTIVE_SPORTS` list. The fix expands `ACTIVE_SPORTS` auto-merge to include all `PINNACLE_LEAGUE_KEYS` (29 sports) when in relay mode.

**2. Sharp freshness cutoff (30s → 120s).** The tracker silently discards sharp book comparisons older than 30 seconds — a threshold tuned for major leagues that poll every 5-10 seconds. VPS-side Pinnacle pollers for niche leagues poll every 60 seconds. By the time the tracker iterated to niche league data (after processing core sports), the sharp odds were often >30s old and silently discarded. No logging or metrics existed for this discard, making it invisible during debugging. The fix increases the freshness cutoff to 120 seconds, which accommodates the 60s polling interval with margin while still rejecting genuinely stale data that could produce phantom picks.

**3. SSE display filter hiding tracker data.** The SSE stream has a browser-crash-prevention filter that excludes niche league markets from the payload to keep it under the ~5MB threshold (see [[concepts/sse-display-tracking-market-separation]]). This filter was implemented at the state-access level, meaning it also filtered the tracker's view of market data — not just the SSE output. The tracker couldn't see niche league markets because the same function served both the SSE stream and the tracker's market snapshot. The fix adds a separate `get_tracker_snapshot()` function that returns the full unfiltered state, while the SSE endpoint continues to use the filtered view.

### The Compound Effect

Each bottleneck independently looked reasonable:
- `ACTIVE_SPORTS` limiting iteration to configured sports is a sensible default
- A 30s freshness cutoff protects against stale-data phantom picks
- Filtering large payloads prevents browser crashes

But together, they created a pipeline where niche league data was polled successfully, stored in state, and then invisible to every consumer. The compound effect is zero output with zero errors — the most dangerous failure mode because it mimics "no data available" (which is the expected state when no games are within the game window).

### Distinguishing "Fixed Pipeline, No Games" from "Broken Pipeline"

After deploying all three fixes, the system still showed zero niche league picks — but now for the correct reason: all niche soccer and basketball league games were 27-124 hours away, outside the 24-hour pre-game window. The 24-hour window filter is working as designed; picks will appear automatically as games enter the window over the following days. This is a critical diagnostic distinction: the pipeline is now confirmed healthy, and the absence of picks is market-driven rather than filter-driven.

### Debugging Methodology

The investigation required tracing the full pipeline end-to-end: OpticOdds polling → market snapshot → state storage → tracker iteration → freshness check → EV evaluation. At each stage, lcash verified whether niche league data was present and flowing. The breakthrough came from instrumenting each filter stage rather than testing them in isolation — individual filter tests would have passed (each filter worked correctly on its own), but the pipeline-level trace revealed the compound zero-output effect.

A VPS deploy during debugging returned exit code 7 from a dashboard push timeout during restart — confirmed as benign and unrelated to the pipeline investigation.

## Related Concepts

- [[concepts/pinnacle-prediction-market-pipeline]] - The Pinnacle pipeline whose niche league expansion exposed these bottlenecks
- [[concepts/sse-display-tracking-market-separation]] - The SSE filter that inadvertently also filtered the tracker's market view
- [[concepts/trail-capture-soft-ids-gap]] - A parallel "silent exclusion by hardcoded set" pattern — SOFT_IDS excluding prediction markets, ACTIVE_SPORTS excluding niche leagues
- [[concepts/ev-pipeline-dropout-logging]] - The per-stage dropout logging pattern that could have detected the freshness discard earlier
- [[connections/operational-compound-failures]] - The same compound failure pattern (independent filters × no logging × no monitoring) applied to pipeline filters rather than operational config

## Sources

- [[daily/lcash/2026-04-16.md]] - Three compound bottlenecks: ACTIVE_SPORTS skipping niche leagues in relay mode, 30s sharp freshness cutoff expiring 60s-polled data, SSE filter hiding tracker's market view; fixes: auto-merge all PINNACLE_LEAGUE_KEYS, freshness 30s→120s, `get_tracker_snapshot()` bypass; post-fix: 0 picks correct because games 27-124h away; VPS deploy exit code 7 benign (Session 23:12)
