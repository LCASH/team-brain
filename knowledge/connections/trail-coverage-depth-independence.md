---
title: "Connection: Trail Coverage and Depth Are Independent Metrics"
connects:
  - "concepts/trail-depth-phase-b-scope-regression"
  - "concepts/trail-change-detection-architecture"
  - "concepts/trail-preseeding-coverage-bug"
  - "concepts/tracker-sharp-trail-soft-gating-staleness"
sources:
  - "daily/lcash/2026-06-03.md"
created: 2026-06-03
updated: 2026-06-03
---

# Connection: Trail Coverage and Depth Are Independent Metrics

## The Connection

Trail coverage (does each pick have at least one trail entry?) and trail depth (how many trail entries does each pick have?) are independent metrics that can diverge dramatically. On 2026-06-03, trail coverage was 99.25% while trail depth had collapsed to a median of 1 sharp trail row per pick — down from 61 just 6-10 days earlier. Coverage audits that only check "does a trail exist?" give false confidence when the underlying depth has regressed.

## Key Insight

The non-obvious insight is that **a single trail entry satisfies coverage requirements while being useless for backtesting.** Phase A (pick creation) writes an initial trail row — this one row makes the pick appear "covered" in any coverage audit. Phase B (subsequent trail updates) was silently broken, writing zero updates to existing picks on every normal cycle. The coverage audit saw 99.25% coverage and reported "healthy," while the actual data quality for CLV computation, odds trajectory analysis, and bet-timing backtesting had collapsed to near-zero.

This is a general monitoring pattern: **metrics that measure existence rather than quality can mask severe regressions.** The coverage metric answered "does data exist?" (yes — initial rows from Phase A). The depth metric answers "is data sufficient for its intended use?" (no — single-row picks have no odds evolution data). Both must be tracked independently.

The pattern has appeared three times in the scanner's trail system, each time with coverage appearing healthy while a different dimension of quality was degraded:

| Incident | Coverage | Quality Dimension Degraded | Root Cause |
|----------|----------|---------------------------|------------|
| Trail pre-seeding (May 18) | 5.9% | Coverage itself | VPS pre-seeded cache prevented baseline writes |
| Sharp trail soft-gating (May 25) | 100% | Anchor freshness (28-min median gap) | Sharp writes gated inside soft-book loop |
| **Phase B scope regression (Jun 3)** | **99.25%** | **Depth (median 1 vs 61)** | **Per-cycle books dict didn't retain tracked picks** |

The coverage audit passed every time Phase B was broken because Phase A always wrote initial rows. Only a depth check (median trail rows per pick, trail rows per hour, or percentage of picks with >5 entries) would have caught the regression.

## Evidence

On 2026-06-03 (Session 10:04), lcash verified that 397/400 sampled recent picks had at least one trail entry (99.25% coverage). Sharp trail depth told a different story: picks created 6-10 days ago had median 61 sharp trail rows; picks from the last 1-2 days had median 1. Even fully settled picks showed median=1, confirming this was a regression rather than "picks haven't accumulated yet."

The diagnostic fingerprint was the tracker log pattern: `0 updated` on every normal cycle, with thousands of updates only on cold-start (first cycle after restart). This means Phase B executed but found no eligible picks to update on warm cycles — the per-cycle `books` dict was the gate that prevented updates.

## Related Concepts

- [[concepts/trail-depth-phase-b-scope-regression]] - The specific Phase B regression where depth collapsed while coverage remained healthy
- [[concepts/trail-change-detection-architecture]] - The change-only recording model; even with change-only, median 61 rows per pick is normal, not 1
- [[concepts/trail-preseeding-coverage-bug]] - A prior trail bug that affected coverage directly (5.9%); this connection shows coverage can be healthy while depth regresses
- [[concepts/tracker-sharp-trail-soft-gating-staleness]] - Another trail quality dimension (anchor freshness) that degraded independently of coverage; three independent quality dimensions all passed coverage checks
