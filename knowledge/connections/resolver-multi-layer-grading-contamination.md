---
title: "Connection: Resolver Multi-Layer Grading Contamination"
connects:
  - "concepts/resolver-adjacent-day-merge-bug"
  - "concepts/resolver-merged-fallback-cross-game-contamination"
  - "concepts/resolver-utc-scan-window-gap"
sources:
  - "daily/lcash/2026-05-21.md"
  - "daily/lcash/2026-05-20.md"
created: 2026-05-21
updated: 2026-05-21
---

# Connection: Resolver Multi-Layer Grading Contamination

## The Connection

Three independently discovered resolver bugs — the `dates_to_fetch` ordering bug (May 20), the merged-dict fallback contamination (May 21), and the UTC scan window gap (May 21) — compound to create a multi-layer grading contamination risk. Each operates at a different stage of the resolution pipeline, and each converts a benign state ("no data yet" or "not scanned yet") into a harmful one ("wrong data applied" or "grading delayed 24 hours"). Together they represent a systematic vulnerability in how the resolver handles date boundaries and multi-source data.

## Key Insight

The non-obvious insight is that the resolver had **three independent ways to produce wrong results** from date-boundary effects, each at a different pipeline stage:

| Stage | Bug | Mechanism | Effect |
|-------|-----|-----------|--------|
| 1. Which dates to scan | UTC scan window gap | Loop only scanned `yesterday UTC` | Picks delayed ~24h |
| 2. Which stats to fetch | `dates_to_fetch` ordering | Day-before stats won via first-wins merge | 16.4% wrong results |
| 3. What to do when data is missing | Merged-dict fallback | "No data" → fell through to wrong-date OO stats | Cross-game contamination |

Each bug is individually fixable, but the **pattern** is the important finding: the resolver's date handling was fragile at every layer. Fixing Bug 2 without fixing Bug 3 would have left a different contamination path active. Fixing Bug 1 without fixing Bug 3 would have brought picks into the scan window but potentially graded them with wrong-date stats. Only the combination of all three fixes creates a robust grading pipeline.

## Evidence

The three bugs were discovered across two consecutive days:

**May 20 (Session 12:38)**: The `dates_to_fetch = [day-1, target, day+1]` ordering bug was found via cross-referencing imported journal picks against MLB Stats API ground truth. Salvador Perez H=2 from May 17 stamped on May 18 picks. 133/809 (16.4%) wrong `actual_stat`. Fix: per-pick ET-date derivation via `ZoneInfo("America/New_York")`.

**May 21 (Sessions 07:57, 09:55, 14:47)**: Two more bugs found in the same pipeline. The UTC scan window gap prevented picks from being scanned at all. The merged-dict fallback + fixture gate SELECT bug created a second contamination path: stats from the wrong game applied when the fixture gate couldn't fire (because `fixture_name` wasn't in the SELECT clause) and the OO fallback provided wrong-date data.

The cumulative fix required changes across 5 commits touching the resolver loop, the pick SELECT query, the MLB stats fetcher, and the OpticOdds fallback path.

## The Defense-in-Depth Principle

The three-layer fix (fixture gate + per-date-only stats + no OO fallback for MLB) follows a defense-in-depth principle: any single layer would catch the specific bug that motivated it, but only the combination prevents the entire class of date-boundary contamination. This is the correct architecture for resolvers, which must never produce wrong results — "skip and retry" is always preferable to "grade with uncertain data."

## Related Concepts

- [[concepts/resolver-adjacent-day-merge-bug]] - Bug 2: first-wins merge ordering contamination; the initial discovery that exposed the pattern
- [[concepts/resolver-merged-fallback-cross-game-contamination]] - Bug 3: OO fallback providing wrong-date stats when MLB Stats API correctly returned empty
- [[concepts/resolver-utc-scan-window-gap]] - Bug 1: picks not scanned because the loop only checked yesterday UTC
- [[connections/first-wins-merge-iteration-anti-pattern]] - The broader anti-pattern that Bug 2 exemplifies; Bug 3 is a related "fallback-to-wrong-source" variant
- [[concepts/tracker-pipeline-7-phase-audit]] - The audit framework (especially M8 ground-truth) that caught Bug 2; Bugs 1 and 3 were found through operational debugging
