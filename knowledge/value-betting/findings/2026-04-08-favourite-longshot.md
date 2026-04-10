# Finding: Favourite-Longshot Bias Implications

**Date:** 2026-04-08
**Source:** `raw/articles/What is the favourite-longshot bias.md` (Pinnacle)

---

## What the Research Shows

Pinnacle's own tennis data (2011-2015, ~48,000 bets):
- Betting at odds >10.00 → lost **22.45%**
- Betting at odds <1.40 → lost **nearly 0%**
- Vig is overwhelmingly loaded on longshots, not distributed evenly

Larger-margin books have stronger bias. Example: Pinnacle priced Coric at 13.00, Interwetten (bigger margin) at 8.00. Extra margin goes almost entirely on the longshot.

Academic evidence from horse racing, football, tennis all confirm the same pattern.

---

## Implications for Our Devig Methods

### Multiplicative devig underestimates the bias
Multiplicative distributes vig proportionally: `p = (1/odds) / sum(1/odds)`. This assumes vig is spread evenly. The data shows it isn't — longshots carry disproportionate vig.

### Power devig corrects for this
Power devig solves for exponent k where `p^(1/k)` accounts for uneven vig loading. For markets with extreme prices (assists overs at 3.50+, blocks at 4.00+), power devig should produce more accurate true probabilities.

### Additive devig is wrong for lopsided markets
Additive removes equal margin from each side. For a 1.20/6.00 market, this is clearly wrong — the data shows the longshot carries ~11% margin while the favourite carries ~1%.

### What this means for our scanner
- **For low-count props** (assists, blocks, steals at longshot odds): power devig may significantly outperform multiplicative
- **For points/PRA** (typically closer to even money): multiplicative is probably fine
- **When devigging soft books** (Bet365, higher margin than Pinnacle): expect even MORE vig loaded on longshots
- **Theory configs should test**: multiplicative vs power method weights per prop type, especially for props where one side trades at 3.00+

---

## Action Items
- Run calibration comparing multiplicative vs power devig specifically for assists, blocks, steals
- Check if the 1,000 pick analysis shows different CLV for picks at longshot vs favourite odds
- Consider per-prop-type devig method weights in future theories

---

## Related Pages
- [[wiki/devig-engine]] — The 4 devig methods and when to use each
- [[wiki/interpolation]] — How line differences compound with devig method choice
- [[sports/nba]] — NBA-specific prop type findings
