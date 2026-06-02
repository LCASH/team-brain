---
title: "Sharp Snapshot Soft-Book Contamination"
aliases: [sharp-snapshot-contamination, bet365-in-sharp-consensus, soft-book-in-sharps, au-soft-book-misclassification, unmapped-book-ids]
tags: [value-betting, data-quality, bug, architecture, devig, sharp-books]
sources:
  - "daily/lcash/2026-06-02.md"
created: 2026-06-02
updated: 2026-06-02
---

# Sharp Snapshot Soft-Book Contamination

On 2026-06-02, a per-book calibration analysis of trail snapshot data revealed that **Bet365 (book_id 365) — the scanner's primary soft target — appears as the 3rd/4th largest contributor to `sharp_snapshot` data** with n=10,000+ observations on MLB alone. Additionally, four AU "soft" books (Sportsbet 900, Neds 901, Ladbrokes 902, PointsBet AU 903) appear in the sharp consensus at meaningful volume. This means the devig pipeline's "true probability" is contaminated by the very books it is supposed to find +EV against — the soft book's own pricing feeds into the sharp reference used to evaluate it, creating a partially self-referential devig.

## Key Points

- **Bet365 (365) is the 3rd/4th largest contributor to `sharp_snapshot`** with n=10,000+ on MLB — it is the primary soft target but is feeding into the sharp consensus that evaluates it
- **AU "soft" books (900, 901, 902, 903) also appear in sharp_snapshot** at meaningful volume — classified as soft for EV evaluation but treated as sharp for devigging
- **~10 unidentified book IDs** (804, 805, 806, 809, 810, 811, 904, 909, 910, 911, 912) rank near the top by sample size — some may be legitimate sharps, others may be additional soft books contaminating the consensus
- **Pinnacle (250) is surprisingly thin** at the 30-min mark: only 466 NBA / 1,804 MLB observations — far fewer than Bet365's 10,000+
- **Self-referential devig risk**: When the soft book feeds into the sharp consensus, the EV calculation becomes partially circular — the "true probability" is biased toward the soft book's own pricing, understating the real edge or creating phantom edges
- **The contamination was invisible** until per-book sample size analysis was performed — the aggregate sharp consensus appeared reasonable while individual contributor analysis revealed the pollution

## Details

### The Contamination Mechanism

The value betting scanner stores a `sharp_snapshot` JSONB column on each pick, capturing per-book odds at trigger time. The `_build_sharp_snapshot()` function (see [[concepts/theory-aware-sharp-book-filtering]]) should only include books configured as sharps in the theory's weights. However, the calibration analysis on 2026-06-02 revealed that Bet365 and AU soft books appear in the sharp snapshot data at volumes that suggest they are being included in the sharp consensus computation.

The mechanism could be:
1. **Theory misconfiguration** — some theories incorrectly list 365/900/901/902/903 in their `weights` or `sharp_books` configuration
2. **`_build_sharp_snapshot()` captures ALL books** — the function may be designed to snapshot every book for replay flexibility (see [[concepts/pick-id-position-model-redesign]]), and the devig engine may be consuming the full snapshot rather than filtering to theory-specific sharps
3. **Default weight fallback** — the engine's weight lookup may default to 1.0 for unconfigured books instead of 0.0, meaning any book with data in the snapshot receives equal weight (the b8steel finding documented in [[concepts/unverified-fix-deployment-anti-pattern]])

Regardless of the specific mechanism, the consequence is identical: soft book pricing contaminates the "true probability" that is compared against those same soft books to compute EV.

### Impact on EV Accuracy

When a soft book's own odds feed into the sharp consensus:
- The devigged "true probability" is pulled toward the soft book's pricing
- The EV gap between "true probability" and "soft book price" shrinks
- Some genuine edges are hidden (EV understated because true prob is biased toward soft price)
- Some phantom edges are created (when the soft book's contribution to sharp consensus disagrees with other sharps, producing noise)

This is structurally similar to the AFL circular devig trap (see [[concepts/afl-circular-devig-trap]]), but less severe — Bet365 is one of many contributors to the consensus, not the sole "sharp" reference. The dilution effect depends on how many genuine sharps are also present. With Pinnacle at only 466 NBA observations while Bet365 contributes 10,000+, the contamination could be substantial for NBA markets where Pinnacle coverage is thin.

### Unmapped Book IDs

Approximately 10 unidentified book IDs appear in the trail snapshot data at meaningful volumes:

| Book ID | Status | Risk |
|---------|--------|------|
| 804 | Unmapped | Unknown — could be sharp or soft |
| 805 | Unmapped | Unknown |
| 806 | Unmapped | Top-3 MLB Bases/RBIs per closing-time analysis |
| 809 | Unmapped | Unknown |
| 810 | Unmapped | #1 MLB HRs at extraordinary Brier 0.072 |
| 811 | Unmapped | Unknown |
| 904 | Unmapped | Unknown |
| 909 | TabTouch Kambi | Already classified as soft (book 909) |
| 910 | Unmapped | Unknown |
| 911 | Unmapped | Unknown |
| 912 | Unmapped | Unknown |

Book 810's extraordinary MLB HR Brier (0.072) from the June 1 analysis (see [[concepts/closing-time-vs-stake-window-sharpness]]) makes identification critical — it could be a genuine sharp that should receive high weight, or a data artifact from a book with unusual pricing on a small sample.

### MLB vs NBA Observation Asymmetry

MLB has approximately 10x more observations per book than NBA at the 30-minute mark, driven by higher daily game volume (10-15 MLB games vs 1-4 NBA games in late season / playoffs). This means MLB calibration findings are more statistically robust, but also that MLB is more affected by contamination in absolute terms — Bet365's 10,000+ MLB observations represent a larger fraction of the sharp consensus for MLB than its proportionally smaller NBA contribution.

## Related Concepts

- [[concepts/afl-circular-devig-trap]] - The extreme case of circular devig where ALL "sharps" are correlated retail shops; Bet365 contamination is a milder version where one soft book dilutes genuine sharps
- [[concepts/theory-aware-sharp-book-filtering]] - The fix deployed on 2026-04-23 for theory-specific sharp filtering; the contamination suggests this fix may not cover `_build_sharp_snapshot()` or the engine's weight lookup
- [[concepts/closing-time-vs-stake-window-sharpness]] - The parent calibration study where unmapped book IDs and Bet365 in sharp_snapshot were first flagged as open questions
- [[concepts/trail-snapshot-dual-axis-book-calibration]] - The per-book calibration methodology that exposed the contamination through sample-size analysis
- [[concepts/unverified-fix-deployment-anti-pattern]] - b8steel's finding about engine.py weight fallback defaulting to 1.0 — a potential mechanism for the contamination

## Sources

- [[daily/lcash/2026-06-02.md]] - Bet365 (365) as 3rd/4th largest sharp_snapshot contributor with n=10k+ on MLB; AU soft books (900, 901, 902, 903) in sharp consensus; Pinnacle thin at 466 NBA / 1,804 MLB; ~10 unmapped book IDs near top by sample size; trail `books` JSONB stores raw odds (devig at eval time); contamination invisible until per-book sample analysis (Sessions 16:41, 17:11)
