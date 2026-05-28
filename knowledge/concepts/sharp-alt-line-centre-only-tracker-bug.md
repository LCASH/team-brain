---
title: "Sharp Alt-Line Centre-Only Tracker Bug and Data Poisoning"
aliases: [sharp-alt-centre-only, centre-only-sharp-reads, sharp-alt-matching, data-poisoning-c1-c2-c3, pair-line-tolerance-bug]
tags: [value-betting, tracker, bug, data-quality, architecture, alt-lines, devig]
sources:
  - "daily/lcash/2026-05-28.md"
created: 2026-05-28
updated: 2026-05-28
---

# Sharp Alt-Line Centre-Only Tracker Bug and Data Poisoning

The value betting tracker's four sharp-data-read call-sites (`_compute_true_prob:620`, `_build_sharp_snapshot:343`, `_compute_one_sided_true_prob:741`, and cross-validation at `~1124`) all used `_pick_main` to select the centre-line sharp entry, ignoring sharp alt-line data already stored in the DataStore. When bet365 emitted soft-side alts at lines far from the sharp centre (e.g., soft@25.5 vs sharp centre@30.5), the tracker interpolated across the gap instead of using the sharp's actual alt at line 25 — degrading EV accuracy. The fix ported `v3/core/engine.py:_find_best_entry` semantics (exact -> main -> closest) into `server/tracker.py`. However, the fix itself introduced **three critical data-poisoning bugs** (C1, C2, C3) that were live for ~6 hours before discovery and correction.

## Key Points

- **Four sharp-read sites locked to centre-only**: `_compute_true_prob`, `_build_sharp_snapshot`, `_compute_one_sided_true_prob`, and cross-validation all used `_pick_main` — ignoring sharp alt-line specialists (BetRivers #1 Brier 0.2426, Hard Rock #2) with 50-67% trail coverage but only 4-9% pick-time contribution
- **C1 — consensus_line poisoning**: `_compute_one_sided_true_prob` read the centre line via `books.get()` even when `_find_best_single_sharp_entry` selected an alt — produced ~25pp of spurious EV per affected pick; poisoned one-sided/MLB-fallback picks for ~6 hours
- **C2 — extra_sharp_data alt-unaware**: The JSONB column recorded centre-only sharp data while main devig used alts — would silently corrupt Phase 7 calibration data
- **C3 — cross-line synthetic vig**: `pair_line_tolerance=2.0` allowed pairing Over@24.5 with Under@25.5 from the same sharp — a synthetic pair no book actually quotes; tightened to 0.001
- **Sharp-alt fix was NOT flag-gated**: The math changes shipped to all sports/theories immediately, while only bet365 alt *parsing* was behind `BET365_ALTS_ENABLED` — the three bugs were live from deploy
- **7 production picks restamped** via `scripts/restamp_audit_2026_05_28.py`; Wembanyama pick flipped +2.98% -> -11.83% EV (should never have been tracked)

## Details

### The Centre-Only Read Problem

The v3 DataStore stores per-line sharp book entries: if Pinnacle quotes Points at lines 24.5, 25.5, and 30.5, three separate records exist. However, the tracker's devig functions only ever read the centre (main) line via `_pick_main`. When evaluating a soft book's alt-line at 25.5, the tracker used the centre sharp at 30.5 and interpolated across a 5-point gap — even though the sharp's own alt at 25.5 or 24.5 was already available in the store.

The v3 engine (`v3/core/engine.py:_find_best_entry`) already implemented the correct matching: exact line match -> fall back to main line -> fall back to closest line. This logic existed but was confined to the dashboard-only read path. The production persistence path (`server/tracker.py:compute_ev_picks`) never used it.

BetRivers and Hard Rock — the two sharpest books by Brier score — are alt-line specialists with 50-67% trail coverage. But because the tracker read centres only, their alt-line data contributed only 4-9% at pick-creation time. The brain finding `2026-05-04-sharp-clv-bias-alt-lines.md` had already documented negative sharp CLV on alt-line picks caused by interpolation noise — this was the root cause.

### The Three Data-Poisoning Bugs

All three bugs were introduced by the sharp-alt fix and discovered during a post-deploy data-flow audit requested by the user.

**C1 — consensus_line reads wrong source**: `_compute_one_sided_true_prob` is the fallback devig path for markets without an Over/Under pair (common in NRL/AFL and MLB one-sided props). The function called `_find_best_single_sharp_entry` to select the correct sharp — which now returned an alt-line entry. But the subsequent `consensus_line` computation read the centre line via a separate `books.get()` call that was never updated. The mismatch produced ~25 percentage points of spurious EV per affected pick.

**C2 — extra_sharp_data JSONB contamination**: The `extra_sharp_data` column on each pick records a JSONB snapshot of sharp book state at trigger time — used for Phase 7 calibration analysis and future replay. This column was still reading centre-only data while the main devig path now used alts. Any calibration or replay script comparing `extra_sharp_data` against `triggered_ev` would see unexplainable divergence.

**C3 — cross-line synthetic vig**: `pair_line_tolerance=2.0` was originally defensive against write races where Over and Under for the same line might arrive a few milliseconds apart with slightly different line values. With sharp alts enabled, the tolerance allowed pairing Over@24.5 with Under@25.5 from the same sharp book — a synthetic pair that no book actually quotes. The vig computed from this synthetic pair is meaningless. Tightened to 0.001 (effectively exact-match only), which is safe now that Phase 2's per-line storage eliminated the write-race scenario.

### Audit and Remediation

8 picks fell within the ~6-hour dirty window. Of these, 7 were restamped with corrected devig values using `scripts/restamp_audit_2026_05_28.py`. The 8th (Caruso) was flagged as `audit_no_valid_sharp_pair` because the fixed code returned `None` on the same trail data — meaning ALL its sharps had been cross-line synthetic pre-fix. The canonical query for excluding audit-window picks is `pick_filter_reason LIKE 'audit_%'`.

Three canaries were added to `/VB-V3-Healthcheck`: alt-rollout deployment check, C3 sharp-alt fix canary, and one-sided >100% EV phantom-EV visibility check.

### Architectural Lesson: Flag-Gate Math Changes, Not Just Parsing

The most important lesson is that `BET365_ALTS_ENABLED` only gated the bet365 alt *parsing* (whether alt-line records enter the DataStore). The sharp-alt *math* changes (how the tracker reads sharp data for devig) shipped to all sports and all theories immediately. This meant the three bugs affected every pick evaluated during the dirty window, not just bet365 alt-line picks. Future feature rollouts should gate both the data-entry and the data-consumption paths behind the same feature flag.

## Related Concepts

- [[concepts/bet365-same-book-alt-line-collision]] - The `_tag_main_lines()` post-processor that identifies alt vs main lines; the centre-only bug meant sharps' alt designations were stored but never consumed
- [[concepts/bet365-points-alt-line-main-tag-accumulation]] - The main-tag accumulation bug on the soft side; this article covers the sharp-read-side counterpart
- [[concepts/theory-aware-sharp-book-filtering]] - Theory-specific sharp book selection; the alt-line fix extends this from "right books" to "right books at the right line"
- [[connections/market-key-dateless-design-recurring-bugs]] - The lineless market_key design that enables alt-line collisions; sharp-side alt reads partially mitigate this for devig accuracy
- [[concepts/tracker-pipeline-7-phase-audit]] - Phase 7 calibration uses `extra_sharp_data` JSONB (C2 bug target); Phase 8 bundle alignment would benefit from tighter sharp-soft line matching

## Sources

- [[daily/lcash/2026-05-28.md]] - Session 11:47: four sharp-read sites using `_pick_main` (centre only); BetRivers/Hard Rock 50-67% trail coverage but 4-9% pick contribution; `_find_best_entry` semantics to port. Session 14:11: three data-poisoning bugs discovered during post-deploy audit — C1 consensus_line reads wrong source (~25pp spurious EV), C2 extra_sharp_data centre-only JSONB, C3 pair_line_tolerance 2.0→0.001 eliminating synthetic cross-line pairs; `BET365_ALTS_ENABLED` only gated parsing not math; 7 picks restamped, Caruso flagged; Wembanyama flipped +2.98%→-11.83%. Session 15:38: 3 canaries added to healthcheck; bet365 monopoly MLB props identified (9 types, no AU cross-validation)

