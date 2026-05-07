---
title: "Pinnacle MLB Player Prop Coverage Gap"
aliases: [pinnacle-mlb-gap, pinnacle-specials-api, pinnacle-zero-mlb-props, opticodds-par-gap]
tags: [value-betting, pinnacle, mlb, coverage, methodology, sharp-books]
sources:
  - "daily/lcash/2026-05-06.md"
created: 2026-05-06
updated: 2026-05-07
---

# Pinnacle MLB Player Prop Coverage Gap

On 2026-05-06, lcash performed a comprehensive Pinnacle player prop API audit that revealed Pinnacle has essentially zero MLB player props — out of 14+ active MLB games, only 1 had any specials (player prop matchups), and even those only returned lines for 6 of 29 listed props via the guest API. Max bet $250 confirms Pinnacle doesn't take MLB props seriously. This makes Pinnacle unusable as a sharp reference for MLB devigging, requiring Novig + DraftKings/FanDuel as the primary MLB sharp sources. A separate finding: OpticOdds never ingests Pinnacle's NBA PAR (Points + Rebounds + Assists) combo lines despite Pinnacle offering them (~12 props/game).

## Key Points

- **Pinnacle MLB player props**: Essentially zero — 1/14 games had specials, only 6/29 returned lines; max bet $250 confirms minimal liquidity commitment
- **Public API key discovered**: `CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R` — Pinnacle API is fully reversible without auth for available props
- **Pinnacle prop structure**: Player props are encoded as "specials" — each prop is its own matchup ID found via `/matchups/{id}/related`, not in standard game endpoints
- **OpticOdds NBA vs Pinnacle**: 97.7% exact match (42/43 props), with one systematic gap: PAR (`player_points_+_rebounds_+_assists`) — Pinnacle has it (~12 props/game) but OpticOdds never ingests it
- **Mitchell Robinson bug**: Over/under labels swapped on rebounds in OpticOdds — a data quality issue
- **MLB sharp hierarchy**: Novig (119 lines/23 players) > DraftKings (241) > FanDuel (187) > Kalshi (34/5 players) > Sporttrade (72/14) — DK/FD have volume but Novig has sharpness
- Polymarket and Betfair Exchange have **zero** MLB player prop coverage on OpticOdds

## Details

### Pinnacle API Architecture

Pinnacle's player props are not exposed in the standard `/matchups` game endpoint. They are encoded as "specials" — separate matchup entries linked to the parent game via `/matchups/{game_id}/related`. Each special has its own `matchup_id`, market type (`type=total, key="s;0;ou"`), and participant list.

The public API key `CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R` provides full access to available props without user authentication. This means Pinnacle's prop data could be scraped directly, bypassing OpticOdds entirely — useful for filling the PAR gap or for sports where OpticOdds has limited Pinnacle coverage.

### Why Pinnacle Ignores MLB Props

The $250 max bet limit on Pinnacle's MLB player props is the definitive signal: Pinnacle's business model depends on accepting large wagers from sharp bettors. A $250 limit means Pinnacle doesn't have confidence in their MLB prop pricing, doesn't want significant exposure, and hasn't invested in market-making infrastructure for these markets. This is consistent with the finding in [[concepts/pinnacle-prop-type-sharpness-variance]] that Pinnacle's sharpness varies dramatically by market type — they're sharp on game lines (high liquidity, heavy institutional action) and weak on niche props (thin markets, retail action).

### MLB Sharp Book Ecosystem

With Pinnacle effectively absent, the MLB sharp reference must come from US-facing books:

| Book | MLB Props | Players | Assessment |
|------|----------|---------|------------|
| **Novig** | 119 lines | 23 | Sharpest MLB reference — low margin, designed to be near-true-odds |
| **DraftKings** | 241 lines | ~30+ | Broadest coverage, 29% pairing rate |
| **FanDuel** | 187 lines | ~25+ | Second-broadest, 1% pairing rate |
| **Sporttrade** | 72 lines | 14 | Thin but deeper than Kalshi |
| **Kalshi** | 34 lines | 5 | Very thin — limited to marquee players |
| **Polymarket** | 0 | 0 | Zero MLB prop coverage |
| **BetMGM** | 0 | 0 | Zero MLB prop coverage on OpticOdds |
| **BetRivers** | 0 | 0 | Zero MLB prop coverage on OpticOdds |

Novig + DraftKings/FanDuel is the recommended multi-book consensus sharp set for MLB devigging (see [[concepts/crypto-edge-non-pinnacle-strategy]] for the theory configuration).

### OpticOdds NBA PAR Gap

OpticOdds NBA coverage is 97.7% aligned with Pinnacle (42/43 props match exactly). The systematic gap is PAR (Points + Rebounds + Assists) — Pinnacle offers ~12 PAR lines per game, but OpticOdds never ingests them. This means any theory using PAR markets must either:
- Use DraftKings/FanDuel/Novig as the sharp reference for PAR specifically
- Scrape Pinnacle's API directly using the public key to fill the gap

The Mitchell Robinson rebounds over/under swap is a one-off data quality issue (not systematic) and may self-correct.

### Implications for Multi-Book Consensus Devig

The Pinnacle MLB gap reinforces the need for the multi-book consensus devig approach discussed in the same session: instead of relying on a single sharp book's no-vig line, devig across all sharp books that offer the market simultaneously. For MLB, this means consensus across Novig + DK + FD, with confidence scaling by the number of books in agreement. For NBA, Pinnacle remains the primary sharp but PAR markets need the multi-book approach.

## Related Concepts

- [[concepts/pinnacle-prop-type-sharpness-variance]] - Pinnacle's sharpness varies by prop type and sport; MLB props confirmed as a fundamental gap, not just weak coverage
- [[concepts/crypto-edge-non-pinnacle-strategy]] - The Crypto Edge strategy already uses DK/Novig/FD as sharps for non-Pinnacle markets; the MLB gap confirms this is the correct architecture
- [[concepts/co-milestone-one-sided-pairing-imbalance]] - DraftKings broadest MLB sharp confirmed (29% pairing); Pinnacle selective coverage now shown to be near-zero for MLB
- [[concepts/opticodds-critical-dependency]] - OpticOdds PAR gap adds a fifth dependency risk: not just availability, bias, completeness, scope, and SSE behavior, but selective prop type ingestion
- [[concepts/pinnacle-prediction-market-pipeline]] - The Pinnacle pipeline confirmed non-viable for MLB props; Crypto Edge is the correct MLB strategy

## Sources

- [[daily/lcash/2026-05-06.md]] - Pinnacle API audit: public key CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R; props as "specials" via /matchups/{id}/related; 1/14 MLB games had specials, 6/29 returned lines, $250 max; OpticOdds NBA 42/43 match, PAR gap (~12 props/game); Mitchell Robinson swap bug; 78 books scanned for MLB: Novig 119, DK 241, FD 187, Kalshi 34, Sporttrade 72, Polymarket/BetMGM/BetRivers 0 (Session 14:46)
