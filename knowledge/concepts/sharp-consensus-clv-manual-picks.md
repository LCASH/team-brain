---
title: "Sharp Consensus CLV for Manual Picks"
aliases: [sharp-consensus-clv, closing-sharps-median, manual-pick-clv, consensus-clv-fallback]
tags: [value-betting, clv, analytics, journal, methodology]
sources:
  - "daily/lcash/2026-05-21.md"
created: 2026-05-21
updated: 2026-05-21
---

# Sharp Consensus CLV for Manual Picks

Manual "top-down" journal picks (see [[concepts/journal-manual-pick-pipeline-integration]]) structurally lack trail data — they have no `sharp_trail`, no `peak_ev`, no `avg_ev`, and no devigged CLV. On 2026-05-21, a `sharp_consensus` CLV fallback was built using the median of per-book CLV values from the `closing_sharps` JSONB column. This provides a reasonable sharp-consensus CLV estimate for manual picks by computing `(opening_odds / book_closing_odds - 1) × 100` for each matched book in `closing_sharps` at the exact line, then taking the median. Displayed as e.g., `+8.42% consensus n4`.

## Key Points

- Manual picks have no trail data → `sharp_clv_pct_true`, `synthetic_clv_pct`, and trail-derived CLV are all structurally NULL
- `closing_sharps` JSONB is populated by the Phase 5.6 closing-odds patcher (5-min loop PATCHing from `_closing_snapshots`) and contains per-book closing odds at game end
- `sharp_consensus` = median of `(opening_odds / book_close - 1) × 100` across all books in `closing_sharps` at the exact line — displays as `+8.42% consensus n4`
- CLV display priority chain: `sharp_clv_pct_true → optic_clv_pct → synthetic_clv_pct → sharp_consensus (NEW) → clv_pct (non-fallback only) → null`
- 3 picks remain permanently un-CLV-able (niche lines where no sharp book quotes the market) — structurally unrecoverable

## Details

### The CLV Gap for Manual Picks

Theory-fired picks flow through the full tracker pipeline: Phase A creates the pick, Phase B writes trail entries as odds evolve, and the resolver computes CLV from the anchored closing bundle (see [[concepts/trail-anchored-bundle-read-layer-fix]]). Manual picks bypass this entirely — they are inserted via the `POST /api/v1/journal/take` endpoint with frozen detection-time odds and no trail infrastructure. The Phase 5.6 closing-odds patcher fills `closing_odds` (the soft book's closing price) and `closing_sharps` (a JSONB dict of per-book closing prices), but no sharp CLV computation existed for this data.

The `sharp_consensus` fallback bridges this gap. Rather than requiring Pinnacle-specific historical data (which the `optic_clv_pct` backfill provides, but with only ~20% filter accuracy — see [[concepts/opticodds-clv-backfill-audit]]), the consensus approach uses whatever sharp books are available in `closing_sharps` at the exact line. The median across matched books provides a robust estimate that isn't sensitive to outliers from any single sharp book.

### Computation Method

For each manual pick with `closing_sharps` populated:

1. Parse the `closing_sharps` JSONB to extract per-book closing odds
2. Filter to books that quote at the same line as the pick's `opening_line`
3. For each matched book: compute `clv = (opening_odds / book_close - 1) × 100`
4. Take the median of all computed CLV values
5. Display as `+8.42% consensus n4` where `n4` indicates 4 books contributed

The median is preferred over the mean to reduce sensitivity to a single book with extreme pricing. The `n` count provides transparency about the consensus depth — `n1` is a single-book estimate (lower confidence), while `n5` draws from the full sharp set.

### Relationship to Other CLV Sources

The CLV display priority chain ensures the best available CLV source is always shown:

| Priority | Source | Available For | Mechanism |
|----------|--------|---------------|-----------|
| 1 | `sharp_clv_pct_true` | Theory picks with trails | Anchored bundle devig |
| 2 | `optic_clv_pct` | Picks with OO historical match | OpticOdds Pinnacle closing |
| 3 | `synthetic_clv_pct` | Theory picks with closing bundle | Synthetic computation |
| 4 | **`sharp_consensus`** | **Any pick with closing_sharps** | **Median of per-book CLVs** |
| 5 | `clv_pct` | Picks with non-fallback closing | Simple opening vs closing |
| 6 | null | No closing data available | — |

Manual picks typically fall through to priority 4 (sharp_consensus) since priorities 1-3 require trail data or OpticOdds historical matches that manual picks don't have. When `closing_sharps` is empty (3 documented cases — niche lines with no sharp coverage), the pick shows `—` in the CLV column.

## Related Concepts

- [[concepts/journal-manual-pick-pipeline-integration]] - The manual pick system that this CLV fallback serves; Phase 5.6 closing-odds patcher populates `closing_sharps`
- [[concepts/sharp-clv-theory-ranking]] - The primary CLV methodology using devigged blend; sharp_consensus is a simpler median-based approximation for picks without trails
- [[concepts/trail-anchored-bundle-read-layer-fix]] - The anchored bundle that theory picks use for CLV; manual picks bypass this entirely
- [[concepts/resolver-utc-scan-window-gap]] - Discovered in the same session; the 16 pending picks that needed CLV display were blocked by both the scan window gap and the CLV display gap

## Sources

- [[daily/lcash/2026-05-21.md]] - User asked why CLV showed "—" for resolved manual picks; `opening_fallback` guard hid CLV even when `closing_sharps` existed; sharp_consensus fallback built using median per-book CLV from closing_sharps JSONB; priority chain established; 3 picks permanently un-CLV-able from niche line gaps (Sessions 07:57, 08:36)
