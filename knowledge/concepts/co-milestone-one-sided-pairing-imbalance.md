---
title: "CO Milestone One-Sided Pairing Imbalance"
aliases: [co-pairing, one-sided-milestone, over-only-flooding, co-vs-ou, book-pairing-rates, mlb-sharp-coverage]
tags: [value-betting, data-quality, bet365, mlb, methodology, devig]
sources:
  - "daily/lcash/2026-04-30.md"
created: 2026-04-30
updated: 2026-04-30
---

# CO Milestone One-Sided Pairing Imbalance

bet365's CO (Column) milestone props (e.g., "1+ hits" at line 0.5, "2+ hits" at line 1.5) are structurally one-sided Overs — they map to `side="Over"` with no corresponding Under. When combined with standard O/U props for the same stat type, the CO milestones flood the dataset with unpaired Overs, dragging pairing rates down dramatically. A cross-book audit on 2026-04-30 revealed extreme variation: FanDuel and Sportsbet AU pair only 1% of their MLB markets, while Coolbet achieves 100%. DraftKings is the broadest sharp source for MLB player props; Pinnacle covers only Bases, Home Runs, and Pitcher Strikeouts. Two new pitcher G-ids were added (Pitcher Outs O/U and Pitcher Record Win), expanding the MLB catalogue from 16 to 18 prop types and odds from 2,208 to 6,706.

## Key Points

- CO milestone props (from `batchmatchbettingcontentapi` CO segments) are **structurally one-sided Overs** — "1+ hits" at line 0.5 has no "Under 0.5 hits" counterpart
- Cross-book pairing rates: **FanDuel 1%**, Sportsbet AU 1%, DraftKings 29%, **bet365 76%**, **Coolbet 100%** — extreme variance in how books structure prop offerings
- bet365's internal `Bases` pairing rate drops to **8%** because CO milestones outnumber O/U entries within the same prop_type
- CO milestones and O/U props both map to the same `prop_type` (e.g., `Bases`) — treated as the same market despite fundamentally different structures
- Unpaired one-sided markets require **interpolation** (via `interpolate.py`) to compute EV — the standard multiplicative devig needs both Over and Under
- **DraftKings (book 200)** is the broadest MLB sharp; **Pinnacle (250)** is selective — only Bases, Home Runs, Pitcher Strikeouts
- Pitcher to Record the Win (G160294) captured but **unusable** — no sharp book covers this market, making devig impossible

## Details

### The CO Milestone Structure

bet365's `batchmatchbettingcontentapi` response (see [[concepts/bet365-mlb-batch-api-co-format]]) uses CO (Column) segments to deliver milestone threshold props. Each CO segment represents a threshold (CO NA=1 → "1+ stat", CO NA=2 → "2+ stat"), with participant entries carrying odds for that threshold. These milestones are inherently one-sided: "1+ hits" is an Over-only proposition — there is no "Under 0.5 hits" counterpart because the market structure only expresses the probability of reaching a threshold, not falling below it.

When the scraper parses CO milestones, they map to `side="Over"` at `line = N - 0.5` (e.g., CO NA=1 → Over 0.5, CO NA=3 → Over 2.5). The standard O/U props from the same bet365 response include both Over and Under sides. Both formats map to the same `prop_type` identifier (e.g., `"Bases"`), creating a mixed dataset where CO milestones (Overs only) dramatically outnumber paired O/U entries.

### Cross-Book Pairing Rate Analysis

The 2026-04-30 audit revealed that pairing rates — the percentage of markets with both Over and Under sides present — vary dramatically across sportsbooks:

| Book | Pairing Rate | Structure |
|------|-------------|-----------|
| **Coolbet** | 100% | Always provides both sides |
| **bet365** | 76% (overall), 8% (`Bases`) | Strong O/U pairing, but CO milestones drag specific types to single digits |
| **DraftKings** | 29% | Many one-sided markets |
| **FanDuel** | 1% | Almost exclusively one-sided milestone Overs |
| **Sportsbet AU** | 1% | Almost exclusively one-sided milestone Overs |

FanDuel and Sportsbet AU's near-zero pairing rates mean their MLB player prop offerings are almost entirely one-sided Overs — structurally similar to bet365's CO milestone format but without a corresponding O/U section. For these books, standard multiplicative devigging is impossible on the vast majority of markets.

The 8% pairing rate for bet365's `Bases` prop type is particularly striking — bet365 offers both CO milestones and O/U for Total Bases, but the CO entries vastly outnumber the O/U entries within the same `prop_type`, diluting the effective pairing rate.

### Impact on the EV Pipeline

The standard multiplicative devig method requires both Over and Under odds from the sharp reference to compute true probability (removing the bookmaker's margin from both sides simultaneously). When only one side exists, the pipeline falls back to:

1. **Interpolation** via `interpolate.py` — devigs the sharp book at its available line, then interpolates to the soft book's different line using Poisson (for count props like hits, runs, RBIs) or calibrated logit. This is the production method for handling line gaps (see [[concepts/alt-line-mismatch-poisoned-picks]])
2. **One-sided consensus** — uses consensus across multiple books' one-sided pricing. This method has known structural biases (see [[concepts/one-sided-consensus-structural-bias]])
3. **Skip** — exclude unpaired markets entirely, accepting reduced coverage

The CO/O/U conflation creates a subtle data quality issue: within a single `prop_type` like `Bases`, some entries are paired (from O/U format) and can be devigged accurately, while others are unpaired (from CO format) and require interpolation. The pipeline does not currently distinguish between these — a potential split (e.g., `Bases_CO` vs `Bases_OU`) was discussed but not yet decided.

### Sharp Book Coverage for MLB Props

| Sharp Book | Coverage | Notes |
|-----------|----------|-------|
| **DraftKings (200)** | Broadest MLB props | Most prop types available, though only 29% paired |
| **Pinnacle (250)** | Selective — Bases, HR, Pitcher K's only | Sharp where available but narrow |

DraftKings being the broadest MLB sharp has implications for theory configuration: MLB theories should weight DraftKings for prop types where Pinnacle has no coverage. However, DraftKings' low pairing rate (29%) means many of its markets require interpolation-based devig rather than standard multiplicative.

### Pitcher Market Expansion (2026-04-30)

Two new pitcher prop G-ids were added to the MLB v3 catalogue:

| G-id | Market | Odds Impact |
|------|--------|-------------|
| G160297 | Pitcher Outs O/U | Major — contributed to odds jump 2,208 → 6,706 |
| G160294 | Pitcher to Record the Win | Captured but **unusable** — zero sharp book coverage |

Both markets were already mapped in the parser (`"Pitcher Outs O/U" → ("Outs", "ou")` and `"Pitcher to Record the Win" → ("Record Win", "yesno")`); only the catalogue G-ids were missing. The Player Total Bases Match Up market (head-to-head format) was also identified as missing but skipped — its schema differs from standard Over/Under and would require a separate parser path.

Pitcher Record Win is flagged as unusable because no sharp book (DraftKings, Pinnacle, or otherwise) prices this market on OpticOdds. Without a sharp reference, no devig or EV calculation is possible. The market is captured for completeness but filtered from dashboard display to avoid noise.

## Related Concepts

- [[concepts/bet365-mlb-batch-api-co-format]] - The CO segment format that produces one-sided milestone props; Pitcher Outs (G160297) and Record Win (G160294) added to catalogue
- [[concepts/alt-line-mismatch-poisoned-picks]] - Interpolation via `interpolate.py` handles unpaired one-sided markets; Poisson model for count props
- [[concepts/one-sided-consensus-structural-bias]] - One-sided consensus devig method's structural Over-only bias; applicable to CO milestones but with known limitations
- [[concepts/pinnacle-prop-type-sharpness-variance]] - Pinnacle's selective MLB coverage (Bases, HR, K's only) directly affects which markets can be devigged; DraftKings fills the gap
- [[connections/devig-method-market-structure-mismatch]] - CO milestones are inherently one-sided; applying two-sided devig without detection is another structural mismatch case

## Sources

- [[daily/lcash/2026-04-30.md]] - Deep audit of CO vs O/U pairing rates: FanDuel 1%, Sportsbet AU 1%, DraftKings 29%, bet365 76% (overall) / 8% (Bases internally), Coolbet 100%; DraftKings broadest MLB sharp, Pinnacle selective (Bases, HR, Pitcher K's); G160297 (Pitcher Outs O/U) and G160294 (Pitcher Record Win) added — Record Win unusable (no sharp coverage); Player Total Bases Match Up skipped (head-to-head schema); odds expanded 2,208 → 6,706; cross-line matching handled by `interpolate.py` (Session 16:23)
