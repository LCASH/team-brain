---
title: "PM Edge Statistical Audit: Pinnacle as Side-Direction Signal"
aliases: [pm-edge-audit, pinnacle-side-direction, kalshi-not-broken, cross-book-replication, pm-theory-v2]
tags: [value-betting, prediction-markets, analytics, methodology, kalshi, pinnacle]
sources:
  - "daily/lcash/2026-05-27.md"
created: 2026-05-27
updated: 2026-05-27
---

# PM Edge Statistical Audit: Pinnacle as Side-Direction Signal

On 2026-05-27, lcash performed a deep statistical audit of 2,924 resolved MLB PM (prediction market) Edge picks across 9 days. The breakthrough finding: **Pinnacle in the sharp set is a side-direction signal, not a confidence signal.** Under picks with Pinnacle in the devig produce +37.3% ROI (t=2.80), while Over picks with Pinnacle produce -28.8% ROI (t=-2.39) — mirror outcomes from the same theory. This signal replicated independently across Kalshi (+58.4% ROI), Polymarket (+56.3%), and Polymarket USA (+44.3%), confirming it is mechanism-driven, not book-specific. The initial diagnosis — "Kalshi is the problem" — was wrong; Kalshi works under all winning filters.

## Key Points

- **Pinnacle in sharps = Under-side profitability**: Under x Pinnacle = +37.3% ROI (t=2.80); Over x Pinnacle = -28.8% ROI (t=-2.39) — identical theory, mirror outcomes by side
- **Cross-book replication validates mechanism**: Pinnacle-Under signal at +50% ROI across Kalshi, Polymarket, and Polymarket USA independently — not a lucky pattern on one book
- **"Kalshi is the problem" was wrong**: Kalshi is 91% of volume and 100% of losses at aggregate, but applying winning filters (Under + Pinnacle) yields +58.4% ROI on Kalshi — book-level exclusion is unnecessary
- **Drop HR/Bases/Hits props**: Structurally unprofitable due to devig failure on Kalshi counting-stat markets (t=-2.73)
- **Drop `one_sided_fallback` devig**: Worst performer at -20.9% ROI
- **Drop solo-DraftKings-sharp picks**: -39.5% ROI (t=-2.46); exclude PropBuilder from PM devig (-46.6% ROI with Pinnacle pair)
- **Narrowest profitable stack**: Moneyline Under + Pinnacle in sharps = 47 picks, +62.8% ROI, t=4.44

## Details

### The Pinnacle Side-Direction Discovery

Standard value-betting theory assumes sharp books are uniformly informative: if Pinnacle is in the sharp set, the devigged true probability should be equally reliable for Over and Under. The MLB PM audit disproved this for prediction-market soft books.

When Pinnacle participates in the sharp consensus, Under picks are systematically profitable (+37.3%) while Over picks are systematically unprofitable (-28.8%). The t-statistics (2.80 and -2.39) exceed 2.0, indicating the signal is unlikely from noise given the 9-day window.

The mechanism hypothesis: Pinnacle's MLB lines are calibrated for sportsbook-style O/U markets where both sides are liquid. When the devigged consensus (including Pinnacle) is compared against prediction market soft books (Kalshi, Polymarket), the Under side captures a genuine pricing gap while the Over side reflects prediction market participants' tendency to overprice excitement events (home runs, hits, total bases).

### Cross-Book Replication

The gold-standard validation for any betting signal is independent replication across unrelated soft books. The Pinnacle-Under signal was tested against three PM platforms:

| Soft Book | ROI (Under + Pinnacle) | Picks | Assessment |
|-----------|----------------------|-------|------------|
| Kalshi (950) | +58.4% | ~200 | Dominant volume |
| Polymarket (970) | +56.3% | ~30 | Independent confirmation |
| Polymarket USA (971) | +44.3% | ~15 | Third independent confirmation |

The signal landing at +50% ROI across three structurally different prediction market platforms (crypto-native Polymarket, regulated-US Kalshi, US-market Polymarket USA) is strong evidence of a genuine pricing mechanism rather than a lucky pattern on one book.

### Why "Drop Kalshi" Was Wrong

At the aggregate level, Kalshi appeared to be the problem: 91% of volume, 100% of net losses, -13% ROI overall. The natural conclusion was to create a "Non-Kalshi PM" theory excluding Kalshi. However, this diagnosis confused volume concentration with causal failure. Kalshi wasn't losing because it's Kalshi — it was losing because the volume was concentrated in Over-side counting-stat props (HR, Hits, Bases) which are structurally unprofitable regardless of soft book.

Applying the winning filters to Kalshi specifically:
- Kalshi Under + Pinnacle: +58.4% ROI
- Kalshi Under only (no Pinnacle filter): +12.1% ROI
- Kalshi Over + Pinnacle: -35.2% ROI (losses concentrated here)

The signal is soft-book-agnostic — it's about the interaction between Pinnacle in the sharp set and the side direction, not about which prediction market is the soft target.

### Proposed New Theories

Three theories were proposed for user review:

1. **MLB PM Edge v2 (broad)**: Drop HR/Bases/Hits, drop one_sided_fallback, drop solo-DK sharps — ~550-600 picks, moderate improvements
2. **MLB Game Lines Premium (narrow)**: Moneyline + Strikeouts Under only, Pinnacle required — ~150-180 picks, concentrated edge
3. **MLB Pinnacle-Anchored Under (highest precision)**: Under only, Pinnacle required in sharps, exclude PropBuilder — ~50-70 picks, projected +40-55% ROI

### Caveats

- 9-day window (May 19-27) means t>2 is "real given the window" but needs 2-3 more weeks before scaling stake
- Structural fixes (drop HR/Bases) are more robust than edge estimates
- DraftKings Predictions (book 971) reverses the Pinnacle pattern — possibly because it's regulated US vs crypto-native; flagged for re-audit at n>50
- Don't filter to specific players/teams — every "+200% player" has 5-9 picks, that's longshot variance pretending to be skill

## Related Concepts

- [[concepts/pm-edge-prediction-market-theory]] - The original PM Edge theory design (May 19); this article represents the first empirical audit of that theory's live performance
- [[concepts/pinnacle-prop-type-sharpness-variance]] - Pinnacle's sharpness varies by prop type; this finding extends the variance principle to a side-direction interaction with prediction markets
- [[concepts/crypto-edge-non-pinnacle-strategy]] - The inverse strategy (PMs as truth vs non-Pinnacle sharps); PM Edge uses PMs as soft targets — the audit shows which PM Edge configurations work
- [[connections/silent-type-coercion-data-corruption]] - Volume concentration masking root cause (Kalshi at 91% volume appeared to be the problem) follows the plausible-wrong-diagnosis pattern

## Sources

- [[daily/lcash/2026-05-27.md]] - Full sweep of 2924 resolved MLB PM picks (May 19-27): Pinnacle in sharps predicts Under profitability (+37.3%, t=2.80) and Over losses (-28.8%, t=-2.39); cross-book replication at +50% ROI across Kalshi/Polymarket/Polymarket USA; "drop Kalshi" diagnosis retracted — Kalshi works under winning filters (+58.4%); drop HR/Bases/Hits (t=-2.73), drop one_sided_fallback (-20.9%), drop solo-DK (-39.5%); 3 new theories proposed; findings doc at brain/findings/2026-05-27-pm-edge-theories-audit.md (Session 15:26)

```
