---
title: "Tracker Pipeline 9-Phase End-to-End Audit"
aliases: [9-phase-audit, 7-phase-audit, tracker-audit, pipeline-audit, ev-replay-validation, mlb-profitability-audit, bundle-alignment-audit, position-consistency-audit]
tags: [value-betting, audit, methodology, analytics, data-quality, architecture]
sources:
  - "daily/lcash/2026-05-14.md"
  - "daily/lcash/2026-05-15.md"
  - "daily/lcash/2026-05-18.md"
  - "daily/lcash/2026-05-20.md"
created: 2026-05-14
updated: 2026-05-20
---

# Tracker Pipeline 9-Phase End-to-End Audit

On 2026-05-14, lcash executed a comprehensive 7-phase end-to-end audit of the value betting tracker pipeline, later expanded to 9 phases on 2026-05-15 with bundle alignment (Phase 8) and position consistency (Phase 9). The original 7 phases validated core math (EV replay within ±0.5pp, median drift 0.01pp) while surfacing critical operational findings. Phases 8-9 revealed that closing odds don't reliably trace to soft trail rows (NBA only 52.6% match rate) and that Eve was running code 8 commits behind main — missing the position-model deploy entirely, producing duplicate pick rows from the v1 hash.

## Key Points

- **10-phase methodology**: schema → trails → CLV → resolution + OpticOdds → analytics → replay → pathology → **bundle alignment** → **position consistency** → **hash version** — each phase validates a different pipeline layer
- **Phases 1-7 pass cleanly** on 2026-05-15 rerun; Phase 7 confirmed alt-line collision fix holding (0 line-flips in 656 NBA + 981 MLB picks) and MLB sub-market disambiguation working (13 distinct prop types)
- **Core math is solid**: EV replay validated within ±0.5pp, median drift 0.01pp — the devig/interpolation engine produces correct results
- **OpticOdds historical integration is non-functional**: 0/200 resolved picks have `optic_lookup_at` set — the backfill script has never run in production; three blockers: strict line equality, loose fixture string matching, empty `PROP_TO_OPTIC_MARKET["mlb"]`
- **MLB profitable, NBA negative**: MLB +8.4% ROI (+309u), NBA -4.4%; MLB Bet365 is the best single soft book at +18.97% ROI
- **Dramatic Over/Under splits**: MLB Over +14.5% vs Under -41%; NBA Under +3.5% vs Over -12.8% — side selection matters more than theory selection
- **Top theory deactivated**: `MLB Novig+BR Additive` (+23% ROI, 332 bets) was accidentally set `is_active=false` but still generated picks from cached theory list in memory — a silent misconfiguration
- **44.5% MLB void rate**: Nearly half of recent MLB resolved picks are `result=void` (DNP/postponed/suspended) — always filter `actual_stat IS NOT NULL` alongside `result IS NOT NULL` for clean analytics

## Details

### The 7-Phase Methodology

The audit is designed as a dependency chain where each phase validates a prerequisite for the next:

| Phase | Layer | Key Check | Result |
|-------|-------|-----------|--------|
| 1. Schema | Database | Migration-033 columns present, pick_id hash consistency | PASS — 400/400 validated, 0 mismatches in 24h window |
| 2. Trail | Data capture | Every pick has ≥1 soft + ≥1 sharp trail entry | PASS — 100% coverage; MLB 72% single-snapshot (expected for fresh picks) |
| 3. CLV | Computation | `calc_clv_pct` matches production stored values | PASS — 100/100 within tolerance (max drift 0.005%) after sign bug fix |
| 4. Resolution + OO | Grading + external | Resolver O/U grades correct; OpticOdds CLV populates | PARTIAL — resolver passes 100%, OpticOdds never ran (0/200) |
| 5. Analytics | Profitability | Per-sport, per-book, per-side, per-theory ROI | COMPLETE — MLB profitable, NBA negative |
| 6. Replay | Math validation | Reconstruct EV from `sharp_snapshot` and compare to `triggered_ev` | PASS — ±0.5pp, median 0.01pp |
| 7. Pathology | Anomaly detection | Deactivated theories, orphaned picks, configuration gaps | FOUND — top theory deactivated, 6 books missing from theory soft_books |

### Phase 1-2: Schema and Trail Integrity

Phase 1 confirmed all four migration-033 columns (`pick_filter_reason`, `model_take`, `model_take_reason`, `extra_sharp_data`) are present and correctly typed across 400 sampled rows. Pick ID hash validation found zero mismatches in the 24-hour window — older mismatches from parallel sessions are historical artifacts, not active bugs.

Phase 2 validated trail coverage at 100% for recent picks — every pick has at least one soft trail entry and one sharp trail entry. The notable finding was MLB's 72% single-snapshot rate: most MLB picks have only one trail data point. This is **expected behavior**, not a bug — these are fresh picks where odds haven't moved past the 0.001 change detection threshold yet (see [[concepts/trail-change-detection-architecture]]). Confirmation requires re-checking closer to game time when odds become more volatile.

### Phase 3: CLV Sign Convention Trap

The audit helper function `calc_clv_pct` had an **inverted sign** compared to production. Production stores positive CLV as "line moved in our favor" — the audit helper initially computed the inverse. After fixing the sign, 100/100 sampled picks matched within tolerance (maximum drift 0.005%).

This is a general trap when writing audit/validation code: the sign convention of computed metrics must match the storage convention exactly, and the difference between "positive = good for us" and "positive = line moved up" is subtle enough to invert without obvious errors in the intermediate calculations.

### Phase 4: OpticOdds Historical Integration — Never Ran

The most significant finding: **OpticOdds historical CLV integration has never executed in production**. Of 200 sampled resolved picks, zero had `optic_lookup_at` populated. The `backfill_optic_clv.py` script exists and works locally, but was never scheduled as a production cron job.

Three structural blockers were identified in the script's filterability:

1. **Strict line equality**: The script requires exact line match between the scanner's pick and OpticOdds' historical entry. Alt-line picks (29% of NBA) can never match because Pinnacle quotes one main line per player per prop — see [[concepts/opticodds-clv-backfill-audit]] for the structural ceiling analysis.
2. **Loose fixture string matching**: Team name format differences between the scanner and OpticOdds cause ~20% false negatives. The nickname-based fuzzy matching improvement (described in the updated CLV audit article) addresses this.
3. **Empty MLB mapping**: `PROP_TO_OPTIC_MARKET["mlb"]` was an empty dict, silently skipping all MLB picks. 18 MLB prop type mappings were added during this audit session.

Additionally, the OpticOdds filter accuracy is approximately 20% — meaning even with correct configuration, only ~1 in 5 picks can be matched against OpticOdds historical data due to the combination of alt-line structural limits, fixture matching gaps, and Pinnacle coverage gaps (754 picks with zero Pinnacle historical entries from data retention limitations).

### Phase 5: Profitability by Sport, Book, and Side

The analytics phase revealed sharply divergent performance across dimensions:

**By sport:**

| Sport | ROI | Units | Assessment |
|-------|-----|-------|------------|
| MLB | **+8.4%** | +309u | Profitable — the scanner's primary edge |
| NBA | **-4.4%** | Negative | Losing — needs theory refinement or deactivation |

**By soft book (MLB):**

| Book | ROI | Notes |
|------|-----|-------|
| Bet365 (365) | **+18.97%** | Best single book — widest coverage + persistent mispricing |
| Sportsbet (900) | ~+5% | Moderate edge |
| Other AU books | Mixed | Thinner coverage |

**By side (dramatic divergence):**

| Sport | Over ROI | Under ROI |
|-------|----------|-----------|
| MLB | **+14.5%** | **-41%** |
| NBA | **-12.8%** | **+3.5%** |

The Over/Under split is the most actionable finding: side selection matters more than theory selection. MLB Overs and NBA Unders are profitable; MLB Unders and NBA Overs are money-losing. This suggests the devigging pipeline systematically misprices one side per sport — possibly because the sharp books used for devigging have different calibration accuracy on Over vs Under lines, or because soft book pricing biases differ by side.

### Phase 6: EV Replay Validation

The replay phase reconstructed EV from the stored `sharp_snapshot` field and compared against `triggered_ev`. The `sharp_snapshot` schema in production is `{book_id: {odds, under_odds, interp_prob, weight}}`, and the replay reconstructs `true_prob` as `Σ(weight × interp_prob) / Σ(weight)`.

Results: median drift of 0.01pp with maximum deviation of ±0.5pp. This confirms the core EV math — devigging, interpolation, Poisson model, cross-validation gate — is implemented correctly and consistently. The small deviations are from timing differences between when the sharp snapshot was captured and when the EV was computed.

### Phase 7: Pathology Detection

Three pathologies were discovered:

**1. Top theory deactivated:** `MLB Novig+BR Additive` showed +23% ROI on 332 resolved bets — the strongest individual theory in the scanner — but was set `is_active=false` in Supabase. Despite deactivation, picks continued flowing because the V3 scanner loads theories once at startup (see [[concepts/v3-scanner-centralized-architecture]]) and the cached in-memory copy retained the theory. A server restart would have silently killed this theory's picks.

**2. Missing soft_books:** Six books (907, 909, 911, 980, 981, 982) had active markets but were not listed in any MLB theory's `soft_books` array. These books' odds were being scraped and stored but never evaluated for +EV — free edge opportunities left on the table.

**3. MLB void inflation:** 44.5% of recent MLB resolved picks have `result=void` — players who didn't play (DNP), postponed games, and suspended games. This inflated Phase 4's "unresolvable" count and would distort any analytics query that doesn't explicitly filter `actual_stat IS NOT NULL`.

### Resolver Deployment Verification Pattern

In the same day (Session 17:14), the anchored-closing-bundle resolver fix was deployed to production. A key operational lesson emerged: **void/skip code paths don't write `closing_source`** — only win/loss/push grading populates this new column. Post-deploy verification showed the resolver running correctly (3 cron cycles fired) but zero grades written — because the resolver queue was full of stale MLB picks that all resolved as void/skip. Verification of `closing_source` population requires waiting for actual live game results.

This creates a diagnostic trap: a deploy can appear broken ("zero grades written") when the resolver is working correctly but processing a queue of non-gradeable picks. The correct verification is checking logs for `resolved: 0` (no eligible picks) vs errors (code failing), combined with patience for the next game slate.

### Phase 8: Bundle Alignment (2026-05-15)

Phase 8 checks whether closing odds reliably trace to soft trail rows — validating the temporal alignment between soft and sharp trail data used for CLV computation and backtesting. **This phase failed**: NBA showed only 52.6% soft trail match rate (target 99%), MLB showed 87.5%. Migration 036 columns (`closing_line` + `synthetic_clv_pct`) were 0% populated post-cutover — the resolver write path for these columns was dormant or unwritten on Eve.

Sharp-lag outliers were significant: NBA max 597s, MLB max 1,149s — confirming that the temporal mismatch between independently-queried soft and sharp streams can be minutes, not seconds. This finding directly motivated the `anchored_bundle()` read-layer fix documented in [[concepts/trail-anchored-bundle-read-layer-fix]].

### Phase 9: Position Consistency (2026-05-15)

Phase 9 checks for duplicate position-group rows — multiple pick rows for the same `(sport, player, prop, side, game_date, soft_book_id)` with distinct lines. **This phase failed**: 4 duplicate position-group rows (3 NBA, 1 MLB) were found, all on AU soft books (PointsBet, Sportsbet), all post-cutover.

Root cause: **Eve was running commit `bea0186` (May 7) — 8 commits behind main**, missing both `8a3f9e3` (position-model deploy) and `694236a` (theory rebuild). The VPS tracker was still on v1 pick_id hash, generating new rows when lines moved instead of updating the existing position row.

The fix was surgical SCP of `server/tracker.py` + `news_agent/pick_writer.py` to Eve, followed by V3 restart in a fresh tmux session. Cutover timestamp `2026-05-15T06:39:09Z` recorded for follow-up audit validation. Phase 7 orphan-theory warnings were confirmed as expected artifacts from friend's commit `694236a` that retired theory names.

### Eve Deploy Drift as Recurring Risk

The Phase 9 failure exposed a systematic operational risk: Eve deploy drift. The production VPS was 8 commits behind main with no mechanism to detect the gap. `scripts/deploy.sh` apparently doesn't cover all deployment paths (or wasn't run after the position-model commit). The surgical SCP approach was chosen over full git pull for narrower blast radius — only the two files driving Phase 8+9 failures were deployed.

This is a deployment variant of the configuration drift pattern documented in [[concepts/configuration-drift-manual-launch]]: instead of environment variables drifting from their intended state, the deployed code drifts from the repository's main branch. An Eve version check in `/vb health` or the deploy script would catch this earlier.

### Phase 10: Hash Version Monitor (2026-05-18)

Phase 10 (`scripts/tracker_audit/10_hash_version.py`) was built on 2026-05-18 to permanently detect v1/v2 pick_id hash version leaks. The monitor computes the expected v2 hash for recent picks and compares against the stored `pick_id`. Any mismatch indicates a stale v1 writer is active — the bug class discovered when the VPS legacy `value-betting.service` wrote v1 picks for 3+ days from stale in-memory imports (see [[concepts/stale-in-memory-import-writer-leak]]).

The monitor was wired into `run_all.sh` alongside the existing 9 phases. The `run_all.sh` script was also rewritten with timestamped log filenames (eliminating duplicate sections from re-runs), per-phase PASS/FAIL exit codes (replacing `set -e` which masked downstream failures), and macOS bash 3.2 compatibility (`declare -A` associative arrays replaced with parallel indexed arrays).

Phase 7 also surfaced a hard failure on 2026-05-18: `unknown_triggered_by: news_v1_IL` and `missing_sharp_hash` on 2 MLB rows — pending investigation. Phase 9 found a new position-model violation: `('mlb', 'Will Smith', 'Hits', 'Over', '2026-05-16', 900)` with 2 post-cutover rows.

### M8 Ground-Truth Cross-Check (2026-05-20)

M8 — a weekly ground-truth cross-check comparing resolver `actual_stat` against the MLB Stats API — was created on 2026-05-20 after the adjacent-day merge bug (see [[concepts/resolver-adjacent-day-merge-bug]]) proved that Phases 1-7 (internal consistency checks) cannot catch grading bugs. Only external ground-truth comparison detected that 16.4% of MLB batting picks had wrong `actual_stat` values.

The M8 audit ran against a 500-pick sample covering a 35-day window (2026-04-15 to 2026-05-20) after the mass re-resolution sweep completed: MLB 98.9% resolved (33,640/34,002), NBA 96.1% (25,658/26,699). M8 result: **0.00% disagreement** (48 unknowns from doubleheaders/no box-score row, all expected).

M8 was added to `scripts/audit_mlb_resolver_vs_truth.py` and referenced in the healthcheck skill. It addresses the fundamental gap: internal consistency (M1-M7) verifies that the pipeline's outputs are self-consistent but cannot verify they are **correct**. M8 provides the external validation layer.

## Related Concepts

- [[concepts/opticodds-clv-backfill-audit]] - The OpticOdds CLV pipeline whose non-functional production state was discovered during Phase 4; MLB prop mappings and fixture matching fixes deployed during this audit
- [[concepts/value-betting-theory-system]] - The theory system where the top-performing `MLB Novig+BR Additive` was accidentally deactivated; theories loaded once at startup mask Supabase state changes
- [[concepts/trail-change-detection-architecture]] - Trail coverage validated at 100% in Phase 2; MLB's 72% single-snapshot rate is expected behavior from the change-only recording model
- [[concepts/sharp-clv-theory-ranking]] - The CLV ranking methodology that Phase 3 validated; sign convention trap is a specific hazard when building audit tooling against the CLV computation
- [[concepts/v3-scanner-centralized-architecture]] - V3's startup-once theory loading explains how a deactivated theory still generates picks from cached memory
- [[concepts/theory-auto-creation-pollution]] - Theory misconfiguration patterns: the deactivated top theory and missing soft_books are related to the recurring theory hygiene problem
- [[connections/silent-type-coercion-data-corruption]] - The CLV sign inversion is another instance of "plausible wrong output" — the audit values looked reasonable but had inverted meaning
- [[concepts/trail-anchored-bundle-read-layer-fix]] - Phase 8 failure motivated the anchored bundle fix for temporal alignment between soft and sharp trail streams
- [[concepts/pick-id-position-model-redesign]] - Phase 9 duplicate position groups validate the need for pick_id redesign; v1 hash on Eve produced the duplicates
- [[concepts/deploy-file-dependency-mismatch]] - Eve 8 commits behind main is a code-level deployment drift variant; surgical SCP was the fix
- [[concepts/stale-in-memory-import-writer-leak]] - Phase 10 was built specifically to detect the v1 hash leak from stale in-memory imports; the legacy VPS service writing v1 picks for 3+ days
- [[concepts/resolver-adjacent-day-merge-bug]] - The adjacent-day merge bug that M8 was created to detect; Phases 1-7 all passed despite 16.4% wrong MLB results — internal consistency ≠ correctness

## Sources

- [[daily/lcash/2026-05-14.md]] - Phase 1-2: All migration-033 columns present, 400/400 validated, 0 hash mismatches in 24h; 100% trail coverage, MLB 72% single-snapshot expected for fresh picks. Phase 3: `calc_clv_pct` sign inversion bug found and fixed, 100/100 within tolerance after fix. Phase 4: OpticOdds historical integration never run (0/200 picks), ~20% filter accuracy, strict line equality blocks alt-lines (29% of NBA), empty `PROP_TO_OPTIC_MARKET["mlb"]`, 22/50 MLB resolved picks have non-float `actual_stat`. Phase 5: MLB +8.4% ROI (+309u) vs NBA -4.4%; Bet365 best single book +18.97%; MLB Over +14.5% vs Under -41%; NBA Under +3.5% vs Over -12.8%. Phase 6: EV replay ±0.5pp, median drift 0.01pp — core math validated. Phase 7: `MLB Novig+BR Additive` deactivated but top performer (+23% ROI, 332 bets), picks flowing via cached memory; 6 books missing from MLB theory soft_books; 44.5% MLB void rate. Resolver deployment: void/skip paths don't write closing_source — verification requires actual game results (Sessions 10:06, 11:22, 17:14)
- [[daily/lcash/2026-05-15.md]] - Phases 1-7 pass cleanly on rerun; Phase 7 confirmed alt-line fix holding (0 line-flips, 13 distinct MLB prop types). Phase 8 (bundle alignment) failed: NBA 52.6% soft trail match, MLB 87.5%; closing_line + synthetic_clv_pct 0% populated; sharp-lag outliers NBA 597s, MLB 1,149s. Phase 9 (position consistency) failed: 4 duplicate position groups all AU soft books; Eve running bea0186 (May 7, 8 commits behind); surgical SCP of tracker.py + pick_writer.py; cutover 2026-05-15T06:39:09Z. Analytics snapshot: NBA 1,841 resolved at -4.27% ROI, MLB 6,871 resolved at -30.55% over last 7 days (Sessions 15:36, 16:39)
- [[daily/lcash/2026-05-18.md]] - Phase 10 (hash version) built and wired into run_all.sh: detects v1/v2 pick_id hash leaks from stale in-memory imports; VPS legacy value-betting.service confirmed as v1 leak source (PID 920843 started 8 min before position-model commit, wrote v1 picks for 3+ days, 661 duplicates); Phase 7 hard-failure: `unknown_triggered_by: news_v1_IL` + `missing_sharp_hash` on 2 MLB rows; Phase 9 violation: Will Smith Hits Over 2026-05-16 book 900 has 2 post-cutover rows; run_all.sh rewritten with timestamped logs and macOS bash 3.2 compatibility (Sessions 11:27, 12:04)
- [[daily/lcash/2026-05-20.md]] - M8 ground-truth audit added: weekly cross-check vs MLB Stats API; 500-pick sample 0.00% disagreement (48 expected unknowns); created after adjacent-day merge bug proved internal consistency ≠ correctness; mass re-resolve: MLB 98.9%, NBA 96.1%; healthcheck skill updated with M8 reference and 5 new monitoring areas (Sessions 13:34, 17:34, 20:03)
