---
title: "Engine Consensus-Fallback EV Contamination"
aliases: [consensus-fallback-gate, identical-ev-clusters, triggered-ev-contamination, consensus-gate-data-cleanliness]
tags: [value-betting, data-quality, engine, backtesting, methodology]
sources:
  - "daily/lcash/2026-05-19.md"
created: 2026-05-19
updated: 2026-05-19
---

# Engine Consensus-Fallback EV Contamination

On 2026-05-19, lcash confirmed that a consensus-fallback gate in the EV engine (commit `d4c9b14`) had produced widespread `triggered_ev` contamination: 52.3% of all picks had identical EV values across theories because the consensus path — which computes a single EV for all theories instead of per-theory devig — was firing as a fallback whenever the theory-specific computation path failed. After the gate fix, identical-EV clusters dropped from 52.3% to 0%. Forward picks (post-2026-05-19) are clean; historical `triggered_ev` values are contaminated and require a replay script to re-derive from `sharp_snapshot`.

## Key Points

- **52.3% of picks had identical `triggered_ev`** across theories — contaminated by the consensus-fallback gate firing as default instead of exception
- **Post-fix: identical-EV clusters dropped to 0%** — confirms the contamination was real, widespread, and engine-driven (not coincidental market pricing)
- **Forward data is clean** (post-2026-05-19); **historical `triggered_ev` is contaminated** and cannot be used for per-theory backtesting without a replay script
- **Replay script needed**: `scripts/replay_pick_with_new_engine.py` would re-derive historical `triggered_ev` from stored `sharp_snapshot` under new engine math — estimated half-day of work
- **Volume crash post-fix was dramatic**: Aggressive -82%, Pinnacle Only -100% — may indicate the fix is too aggressive (dropping picks that previously passed via consensus) or that those theories never had genuine edge
- **Cross-val threshold at 10pp** recovered 65 picks vs the previous 5pp — 49% of picks have no opposing-side soft odds, so the cross-val gate doesn't fire on half the universe

## Details

### The Contamination Mechanism

The EV engine evaluates each market against each active theory, computing a theory-specific `triggered_ev` based on that theory's configured sharp books, weights, devig method, and filters. When the theory-specific computation failed — due to missing sharp data, line-gap exceeding `max_line_gap`, or other filter failures — the engine fell back to a "consensus" computation that used all available sharp books with equal weights and a generic devig method.

The consensus fallback produced a single EV value regardless of which theory triggered it. When this value was stored in `triggered_ev`, all theories that fell back to consensus for the same market received identical EV values. This contaminated per-theory backtesting: a theory with aggressive settings (narrow line gap, specific sharps) appeared to have the same performance as a conservative theory (wide line gap, all sharps) because both inherited the same consensus EV.

### Impact on Backtesting

The contamination makes historical per-theory analysis unreliable for any metric derived from `triggered_ev`:

- **Per-theory Brier scores**: Contaminated — identical EVs across theories means calibration looks identical
- **Per-theory ROI by EV band**: Contaminated — picks bucketed by `triggered_ev` will cluster at consensus values
- **Per-theory CLV**: Partially affected — CLV is computed from closing odds, not `triggered_ev`, so it's cleaner but still influenced by which picks were tracked (consensus gate affected pick creation)
- **Aggregate ROI (all theories combined)**: Less affected — the consensus EV was still a reasonable market-level estimate, just not theory-specific

### The Replay Path

The stored `sharp_snapshot` on each pick contains the raw sharp book odds at trigger time, with per-book weights already baked in. A replay script can reconstruct the theory-specific EV by:

1. Loading the pick's `sharp_snapshot` (already stored as `{book_id: {odds, under_odds, interp_prob, weight}}`)
2. Looking up the `triggered_by` theory's configuration (devig method, max_line_gap, etc.)
3. Re-running the devig computation using only the theory's configured sharps from the snapshot
4. Storing the re-derived `triggered_ev` alongside the original (or replacing it)

This is estimated at half a day of work. The recommendation is to wait 14 days for a clean forward cohort before investing in the replay, ensuring the new engine math is stable.

### Observation Scripts

Three observation scripts were deployed following a "measure, don't auto-fix" principle:

1. **Volume shift observer**: Tracks pick volume per theory post-fix to detect over-aggressive filtering
2. **Cross-val distribution**: Measures the 5pp→10pp threshold impact — found 65 picks recovered by the 10pp bump, 10 more hidden at the current threshold
3. **Closing_source desync**: Monitors the `closing_source = entry_snapshot` label reliability — found ~100 picks (NBA 17.6%, MLB 30.6%) with desynced labels, though the actual `closing_odds` VALUE is reliable

### Relationship to B8steel's Claims

The consensus-fallback gate was identified as part of a broader engine investigation prompted by b8steel's findings. However, the consensus gate change was accepted as a modeling decision (not a bug fix) — it matched b8steel's stated intent to remove the fallback. An alternative approach (adding a `triggered_ev_source` column to distinguish consensus vs theory-specific EVs rather than dropping the fallback) was discussed but rejected for simplicity.

Three modeling decisions were deliberately left untouched for explicit human decision:
- Consensus-fallback gate threshold
- Cross-val threshold (5pp vs 10pp vs higher)
- `closing_source` label backfill

## Related Concepts

- [[concepts/value-betting-theory-system]] - The theory system whose per-theory math was bypassed by the consensus fallback; theory-aware CLV analysis revealed 7 knobs + 2 code paths that the fallback collapsed to 1
- [[concepts/sharp-clv-theory-ranking]] - CLV rankings are partially affected by the contamination; `closing_odds` (not `triggered_ev`) drives CLV, but pick selection was influenced by consensus gate
- [[concepts/tracker-pipeline-7-phase-audit]] - Phase 6 (EV replay) validated core math at +-0.5pp — the consensus gate was a separate engine-level issue discovered after the audit
- [[connections/dual-codebase-ev-computation-drift]] - A related class of EV computation divergence; the consensus gate is a within-codebase fallback issue rather than a cross-codebase drift
- [[concepts/trail-anchored-bundle-read-layer-fix]] - The closing_source desync finding (17.6% NBA, 30.6% MLB) suggests similar temporal alignment issues in the closing-odds computation

## Sources

- [[daily/lcash/2026-05-19.md]] - Identical-EV clusters 52.3%→0% post-consensus-gate fix (commit `d4c9b14`); forward picks clean, historical `triggered_ev` contaminated; replay script `replay_pick_with_new_engine.py` needed for historical re-derivation from `sharp_snapshot`; Aggressive -82%, Pinnacle Only -100% volume drop; 3 observation scripts deployed (volume shift, cross-val distribution, closing_source desync); 49% of picks have no opposing-side soft odds; cross-val 65 picks recovered at 10pp; closing_source desynced on ~100 picks but closing_odds VALUE reliable; sharable doc pushed to GitHub with honest/hedged tone (Session 15:15)
