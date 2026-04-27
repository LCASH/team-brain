---
title: "Connection: Dual-Codebase EV Computation Drift"
connects:
  - "concepts/dashboard-client-server-ev-divergence"
  - "concepts/per-theory-true-odds-display"
  - "concepts/theory-aware-sharp-book-filtering"
  - "concepts/alt-line-mismatch-poisoned-picks"
sources:
  - "daily/lcash/2026-04-27.md"
created: 2026-04-27
updated: 2026-04-27
---

# Connection: Dual-Codebase EV Computation Drift

## The Connection

The value betting scanner maintains the same devig/EV computation in two independent codebases: Python (backend tracker at `server/tracker.py`) and JavaScript (dashboard at `dashboard/index.html`). On 2026-04-27, a systematic audit found six specific dimensions where the two implementations had drifted apart — each producing subtly different EV values for the same market. Unlike the `loadTheories()` bug (missing data) or the theory name exclusion (wrong filtering), this is about **the same algorithm implemented with different assumptions** in two languages.

## Key Insight

The non-obvious insight is that **implementation drift in duplicated math is invisible at the individual pick level.** A pick showing +3.8% EV on the dashboard and +4.1% in the tracker looks like rounding or timing — no single discrepancy is dramatic enough to trigger investigation. But six small differences compound: the dashboard might show a pick as +EV while the tracker correctly computed it as -EV (or vice versa), creating false confidence or missed opportunities.

The six dimensions of drift, ordered by impact:

| Dimension | Dashboard (before fix) | Backend (correct) | Impact |
|-----------|----------------------|-------------------|--------|
| **Poisson interpolation** | Falls back to logit for line gaps >1.0 | Always uses Poisson for count props | Inflates EV for count props with large gaps |
| **Line-gap penalty** | Prob-shrink toward 0.5 | Weight decay inside `computeTrueProb` | Prob-shrink disproportionately inflates low-probability EV |
| **EV cap** | Hard 50% cap | No cap | Dashboard hides extreme EVs that backend tracks |
| **Soft odds freshness** | 600 seconds | 300 seconds | Dashboard uses odds the backend rejects as stale |
| **Cross-validation check** | Missing | Sharp-vs-soft devig >5pp filter | Dashboard shows picks the backend skips |
| **`is_over` detection** | Case-sensitive `=== 'Over'` | Case-insensitive comparison | Misidentifies side for non-standard case formats |

Each discrepancy is a real mathematical difference, not a display bug. The prob-shrink-toward-0.5 penalty is particularly insidious: it appears to work like weight decay (both reduce confidence for high-gap interpolation), but prob-shrink disproportionately inflates EV for low-probability events by pushing the true probability toward 50% — making longshot bets appear more valuable than they are.

## The Architectural Anti-Pattern

The root cause is that devig/EV math was duplicated in two codebases rather than shared. JavaScript and Python cannot share a library, so the math was reimplemented in JS for real-time dashboard rendering. Over time, as fixes were applied to the backend (Poisson for count props, cross-validation gate, tighter freshness), the frontend was not updated in lockstep.

This creates a ratchet effect: each backend fix increases the gap because the frontend misses it. The `loadTheories()` bug (April 15) was a different class — missing data, not wrong math. The theory name exclusion (April 18) was wrong filtering. This connection captures a third class: **algorithmic drift in duplicated implementations.**

Prevention requires either: (1) extracting shared devig/EV math into a single source of truth (e.g., a WASM module or generated constants), or (2) a systematic audit protocol triggered whenever the backend computation changes.

## Evidence

On 2026-04-27 (Session 11:34), lcash audited six computation paths between `dashboard/index.html` and `server/tracker.py`:

1. **Poisson fallback**: Dashboard's `interpolateForProp()` fell back to logit for gaps >1.0. Backend always uses Poisson for count props (Rebounds, Assists, Threes, etc.). Logit produces higher true probabilities at large gaps → inflated EV for count props.
2. **Line-gap penalty**: Dashboard used "prob-shrink toward 0.5" which inflates low-probability events. Backend uses weight decay inside `computeTrueProb` — mathematically different, produces more conservative EV estimates.
3. **EV cap**: Dashboard had a hard 50% cap. Backend has none. This hid extreme EVs on the dashboard that the backend tracked — the dashboard operator couldn't see the full picture.
4. **Freshness threshold**: Dashboard accepted odds up to 600s old. Backend rejected at 300s. Dashboard showed picks the backend had already discarded as stale.
5. **Cross-validation**: Dashboard was missing the sharp-vs-soft devig >5pp divergence filter. Backend skips picks where the interpolated true probability and the soft book's own devigged price disagree by more than 5 percentage points.
6. **Case sensitivity**: Dashboard checked `m.side === 'Over'` (case-sensitive). Backend uses `.lower()` comparison. Markets with non-standard casing (e.g., `"over"`, `"OVER"`) were misidentified only on the dashboard.

## Related Concepts

- [[concepts/dashboard-client-server-ev-divergence]] - The broader chronicle of dashboard-vs-server divergence, starting with `loadTheories()` (April 15) and extending through multiple manifestations; this connection identifies a specific subclass (algorithmic drift vs data drift)
- [[concepts/per-theory-true-odds-display]] - Per-theory display was built in the same session as this audit, using the corrected devig math
- [[concepts/theory-aware-sharp-book-filtering]] - Another devig correctness fix (theory-specific sharps); this connection extends the principle from "right books" to "right algorithm"
- [[concepts/alt-line-mismatch-poisoned-picks]] - Poisson interpolation for count props was specifically developed to fix alt-line phantom EVs; the dashboard was still using the old logit fallback
- [[connections/silent-type-coercion-data-corruption]] - Case sensitivity in `is_over` is another instance of the plausible-wrong-output pattern; the market appears correctly processed but the side is misidentified
