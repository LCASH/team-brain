---
title: "Closing-Time vs Stake-Window Book Sharpness"
aliases: [closing-time-sharpness, stake-window-sharpness, correlative-vs-causal-sharpness, book-calibration-windows]
tags: [value-betting, methodology, analytics, calibration, sharp-books]
sources:
  - "daily/lcash/2026-06-01.md"
  - "daily/lcash/2026-06-02.md"
created: 2026-06-01
updated: 2026-06-02
---

# Closing-Time vs Stake-Window Book Sharpness

On 2026-06-01, a comprehensive 4-agent sharpness calibration study for the value betting scanner revealed the cardinal methodological distinction: **closing-time sharpness** (which books agree with the final market) is correlative, while **stake-window sharpness** (which books have information before the market moves) is causal. Using closing-time Brier scores, all 4 sub-agents defaulted to the wrong metric because it had the cleanest data. When corrected to stake-window scoring, the book rankings flipped meaningfully — Novig dropped 10 ranks from NBA #1, PointsBet AU (903) rose to aggregate #1, and Hard Rock (803) reversed from "drop" to "keep."

## Key Points

- **Closing-time sharpness** = "who agrees with the final market consensus" — correlative, not useful for weight decisions because the information wasn't available at bet time
- **Stake-window sharpness** = "who had information BEFORE the market moved" — causal, directly useful for weight decisions because it measures predictive value at the moment it matters
- **All 4 sub-agents defaulted to closing-time scoring** because it has cleaner data (no timestamp alignment issues) — the correlative trap in action
- **Rankings flipped meaningfully**: PointsBet AU (903) became aggregate leader at stake window (was classified as SOFT); Novig (192) dropped (is a late-sharpener, not early leader); Hard Rock (803) reversal
- **Per-prop CIs overlap**: Bootstrap analysis showed all top-5 per-prop confidence intervals overlap — no single book is statistically significantly sharper than its neighbors at current sample sizes
- **Aggregate rankings hide prop-level regime structure**: PointsBet AU was #1 aggregate but doesn't crack any per-prop top 5; BetMGM is a batter specialist (Brier 0.106 vs 0.259 pitcher)
- **n-days matters more than n-picks**: Effective sample size is independent game-days, not correlated picks within the same slate

## Details

### The Correlative Trap

Standard Brier score analysis computes calibration against outcomes: for each book, how well did its closing line predict the actual result? This is the industry standard for "sharpness." However, it measures agreement with the final market state — a book that copies Pinnacle's line 5 minutes before close will score identically to one that set its own line 3 hours before close. The copy provides zero value for EV calculation at stake time; the independent price-setter provides enormous value.

The stake-window analysis restricts the comparison to odds captured within the bettor's realistic action window (typically 30-120 minutes before game start). Books that are sharp at stake time but move later (late sharpeners like Novig) look excellent at close but mediocre at stake time. Books that are sharp early but get copied by others (early leaders like PointsBet AU in some markets) look average at close but excellent at stake time.

### The Regime Structure

Aggregate book rankings hide sport-specific and prop-specific regime structure. The 2026-06-01 audit found:

| Dimension | Finding |
|-----------|---------|
| **Cross-sport** | DraftKings #1 in MLB at close, not top-2 in NBA; PointsBet AU tops NBA stake-window, irrelevant to MLB |
| **Cross-prop** | BetMGM is a batter specialist (0.106 Brier) but terrible on pitcher props (0.259); unmapped book 810 is #1 MLB HRs at extraordinary 0.072 |
| **Cross-line** | A book appearing top-5 across multiple independent props is stronger evidence than #1 on one prop with overlapping CIs |

### Implications for Theory Configuration

Two recommendations emerged that are window-independent (safe to ship regardless of the closing-vs-stake debate):

1. **Switch devig method from multiplicative to power** for 10 of 13 theories — power beats mult in both NBA (Brier 0.23320 vs 0.23358) and MLB (0.16786 vs 0.16955)
2. **Enforce min_sharp_count ≥ 2** as a sanity gate — sharp_count=1 confirmed negative-CLV; BetMGM-solo edge is variance

Weight changes (P1) were paused until stake-window data matures (~3 weeks), because the closing-time rankings that would have informed weight decisions were shown to be misleading.

### Open Questions

Several unmapped book IDs (804, 805, 806, 810, 811) appeared in the analysis. Book 806 is top-3 MLB Bases/RBIs, and 810 is #1 MLB HRs — identifying these is a prerequisite for correct weight configuration. Additionally, Bet365 (365, the soft target book) appeared in sharp_snapshot, suggesting a data pipeline configuration issue.

### Continuation: Per-Book Raw Trail Analysis (2026-06-02)

On 2026-06-02, lcash deepened the stake-window methodology with a full per-book calibration study using raw trail snapshot data at the 30-minute mark. The study analyzed 424,413 trail rows across 229,040 (pick × book) observations and revealed that **Brier score alone is insufficient** — a dual-axis approach combining Brier with calibration gap (systematic directional bias in pp) and firming direction (line drift toward/against picks) is required. Key finding: Coolbet had the best Brier (0.211) but a -9.6pp calibration gap (systematically underprices events), while TAB had worse Brier but near-perfect calibration. For devigging, calibration matters more than resolution.

Two extreme sport × prop findings emerged: MLB Hits has a universal -36pp calibration gap (betting stopped pending diagnosis), and MLB Strikeouts (pitcher) has a +13pp edge where all books overprice (increased stake sizing warranted). The analysis also confirmed that Bet365 (365) and AU soft books (900-903) contaminate `sharp_snapshot` at meaningful volume — see [[concepts/sharp-snapshot-soft-book-contamination]] for the full analysis. The expanded unmapped book ID set (804, 805, 806, 809-812, 904, 909-912) needs resolution before weight changes can proceed. See [[concepts/trail-snapshot-dual-axis-book-calibration]] for the complete methodology.

## Related Concepts

- [[concepts/pinnacle-prop-type-sharpness-variance]] - Pinnacle's sharpness varies by prop type; this article extends the principle from per-prop to per-window and per-book simultaneously
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV uses closing-line references; the window distinction means CLV computed at close may not reflect the book's value at stake time
- [[concepts/value-betting-theory-system]] - Theory weights should reflect stake-window sharpness, not closing-time; 7 knobs + 2 code paths need window-aware calibration
- [[concepts/multiple-comparison-edge-validation-trap]] - Another instance of correlative signals masquerading as causal — the same discipline (distinguish correlation from causation) applies
- [[concepts/trail-snapshot-dual-axis-book-calibration]] - The June 2 continuation: per-book, per-prop dual-axis scoring methodology using Brier + calibration gap + firming direction
- [[concepts/sharp-snapshot-soft-book-contamination]] - Bet365 and AU soft books contaminating sharp_snapshot, discovered during the per-book calibration analysis

## Sources

- [[daily/lcash/2026-06-01.md]] - 4-agent calibration study with corrective 5th agent; closing-time flipped to stake-window analysis; PointsBet AU rose to aggregate #1; Novig dropped 10 ranks; power devig > multiplicative; per-prop CIs all overlap at current n; edge-research SKILL.md updated with Step 0 (window + granularity + CI design) and 9 new catalog entries (Sessions 16:12, 17:36)
- [[daily/lcash/2026-06-02.md]] - Per-book raw trail analysis: 424,413 trail rows, 229,040 observations; dual-axis methodology (Brier + calibration gap + firming); Coolbet best Brier but -9.6pp gap; TAB near-perfect calibration; MLB Hits -36pp catastrophe; MLB Strikeouts +13pp edge; Bet365/AU soft contamination confirmed in sharp_snapshot; ~10 additional unmapped book IDs discovered (Sessions 16:41, 17:11)
