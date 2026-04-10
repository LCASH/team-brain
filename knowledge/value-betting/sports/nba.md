# NBA

## Status: current
## Last verified: 2026-04-09

> NBA player props — our most mature sport. Most data, most calibration, most findings.

---

## Scanner Parameters
→ See `docs/methodology/sports/nba/context.md` for full technical params.

---

## Sharp Book Landscape (Props)

| Book | Role | Notes |
|------|------|-------|
| BetRivers (802) | Sharpest for props | Weight 1.0 in calibrated theories |
| Hard Rock (803) | Sharp for props | Weight 0.9 |
| PropBuilder (125) | Sharp for props | Weight 0.95 |
| DraftKings (200) | Moderate | Weight 0.8 |
| Circa (808) | Moderate | Weight 0.5 |
| FanDuel (100) | NOT sharp for props | Weight 0 (sharp for game lines, not player props) |
| Pinnacle (250) | NOT sharp for props | Weight 0 (same — sharp for totals/spreads, not props) |

**Key insight:** FanDuel and Pinnacle are widely considered "the sharp books" but this is for game lines. For player props, BetRivers and PropBuilder are significantly sharper.

---

## Soft Book Performance (from 1,000 pick CLV analysis)

| Book | Avg CLV | CLV+ Rate | Win Rate |
|------|---------|-----------|----------|
| PointsBet | +2.68% | 64% | 66.7% |
| Ladbrokes | +2.00% | 50% | 61.4% |
| Neds | +1.99% | 48% | 59.3% |
| Sportsbet | +1.21% | 41% | 53.8% |
| Bet365-Game | +0.58% | 20% | 57.1% |
| Bet365 | +0.46% | 17% | 50.0% |

**AU books (PointsBet, Ladbrokes, Neds) outperform Bet365 by 3-5x.** Bet365 adjusts faster and prices tighter on props.

---

## Prop Type Performance

| Prop | Avg CLV | Win Rate | Avg Sharps | Notes |
|------|---------|----------|------------|-------|
| Reb+Asts | +1.99% | 46.6% | 1.6 | Highest CLV, lowest sharp coverage — inefficient market |
| Threes | +1.78% | 57.6% | 3.0 | |
| Assists | +1.53% | 45.9% | 2.7 | |
| PRA | +1.40% | 64.4% | 4.2 | |
| Points | +1.23% | 57.0% | 4.1 | Most efficient — highest sharp coverage |
| Pts+Rebs | +1.21% | 67.3% | 2.2 | |
| Rebounds | +0.99% | 55.2% | 3.6 | |
| Pts+Asts | +0.97% | 55.2% | 2.3 | |

---

## Known Biases
→ See `docs/methodology/sports/nba/context.md` for full list.

Key ones for the scanner:
- **Over bias** — Public bets overs more, soft books shade over prices. Unders may have more edge.
- **Star player inflation** — Props for big names have tighter lines and more sharp attention. Role players may offer more edge.
- **Back-to-back games** — Player stats drop on B2Bs but markets are slow to adjust.

---

## Timing Sweet Spot

| Window | Avg CLV | Win Rate |
|--------|---------|----------|
| 20-40 min pre-game | +2.00% | 64.2% |
| 10-20 min | +1.19% | 69.7% |
| 40-60 min | +1.44% | 54.2% |
| 60-120 min | +1.51% | 55.2% |
| 120+ min | +0.99% | 64.4% |

**20-40 minutes before tip is the sweet spot.** Sharp books have priced in late lineup/injury info but soft books haven't caught up.

---

## Highest-Conviction Filters

Based on 1,000 pick analysis (all books):
1. **5+ sharps, 2-6% EV** → +2.25% CLV, 70.8% WR (best overall)
2. **AU books (PointsBet/Ladbrokes/Neds), any EV** → 3-5x better CLV than Bet365
3. **Reb+Asts with 2+ sharps** → +2.49% CLV (inefficient market)
4. **20-40 min pre-game** → +2.00% CLV (timing edge)

---

## Bet365-Specific Findings (from 1,000 NBA Bet365 picks, 2026-04-10)

→ See [[findings/2026-04-10-nba-bet365-deep-dive]] for full analysis.

**Overall: 500W/452L (52.5%).** Positive but thinner edge than AU books.

**Best segments on Bet365:**
- 5-7.5% EV with 2-4 sharps → 68-88% WR (38 picks — need more data)
- 2-3% EV with 5+ sharps → 74% WR (23 picks)
- Double Double props → 76.3% WR, +1.79% CLV (38 picks)
- Combo props (Pts+Reb, Pts+Ast) → 57-59% WR at low EV thresholds

**Avoid on Bet365:**
- Blocks → 18.2% WR, -0.36% CLV (11 picks)
- High EV (10%+) with 4-5 sharps → mostly losing (false positives)
- 3-5% EV with 5+ sharps → 39% WR (anomalous, needs more data)

**Bet365 vs Bet365 2.0:** Identical for NBA. The +42.8% ROI gap was MLB longshots in the direct scraper, not NBA differences.

---

## Open Questions
- Are alt line picks profitable? (Phase 1 AltLine-V1 collecting data — only 17 resolved on Bet365)
- Is power devig better than multiplicative for assists/blocks? (low-count props)
- Why is 3-5% EV with 5+ sharps underperforming (39% WR)? Sample size or real signal?
- At what sample size per EV×Sharp cell can we make confident decisions? (Currently most cells <50)

---

## Related Pages
- [[wiki/devig-engine]] — How devig works and why sport/market differences matter
- [[wiki/theories]] — Theory configs for NBA
- [[findings/2026-04-07-clv-1000-picks]] — Full CLV analysis
