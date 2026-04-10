# Devig Engine

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> The core algorithm that removes bookmaker vig from sharp book odds to estimate true probabilities.

---

## What It Does

Takes raw odds from sharp bookmakers (with built-in margin) and removes the vig to estimate the true probability of each outcome. This is the foundation of the entire EV calculation pipeline.

**Source:** `ev_scanner/devig.py` (~5.4KB), orchestrated by `ev_scanner/engine.py` (~31KB)

---

## The 4 Devig Methods

### 1. Multiplicative (Proportional)
The default and most common method. Distributes vig proportionally to each side.

```
r_over = 1/over_odds
r_under = 1/under_odds
true_p_over = r_over / (r_over + r_under)
true_p_under = r_under / (r_over + r_under)
```

**When it's best:** General purpose. Works well when vig is distributed evenly across outcomes.

### 2. Additive (Equal Margin)
Removes equal margin from each side. BetIQ appears to use something close to this.

```
margin = (r_over + r_under) - 1.0
true_p_over = max(0.001, min(0.999, r_over - margin/2))
# then normalize
```

**When it's best:** When the bookmaker applies flat vig regardless of price. Often the closest match to BetIQ's numbers.

### 3. Power (Odds-Ratio / Favorite-Longshot Bias)
Corrects for the well-documented bias where longshots carry more vig than favorites.

```
Solve for k: r_over^(1/k) + r_under^(1/k) = 1.0
# Uses scipy.optimize.brentq
true_p_over = r_over^(1/k)
```

**When it's best:** Markets with extreme favorites/longshots. Computationally expensive (scipy solver).

### 4. Shin (Insider Trading Model)
Models the bookmaker as protecting against informed bettors. For 2-way markets, equivalent to additive.

**When it's best:** Markets with suspected insider information. In practice, rarely different from additive for binary props.

---

## Aggregation Across Books

The engine doesn't just use one sharp book — it deviggs ALL available sharp books and aggregates:

1. For each market pair (Over/Under), find all sharp books with data
2. Run all 4 devig methods on each book's odds
3. Weight the results by **sharp book weights** (from the active theory):
   - BetRivers (802): 1.0 (sharpest for props)
   - Hard Rock (803): 0.9
   - PropBuilder (125): 0.95
   - DraftKings (200): 0.8
   - Circa (808): 0.5
   - FanDuel (100), Pinnacle (250), Novig (192): weight 0 (overrated for props)
4. Weighted average of true probabilities → final true odds

**Why weights matter:** Not all sharp books are equally sharp for player props. BetRivers consistently beats others on prop pricing. FanDuel and Pinnacle are sharp for game lines but NOT for player props — hence weight 0.

---

## Consensus Fallback

When NO sharp books have data for a market (common for combo props like Pts+Rebs):
- Devig each available book independently
- Take weighted average across all books
- Cap confidence at 2.5 (out of 5.0) to reflect lower certainty
- This catches markets that BetIQ finds but we'd otherwise miss entirely

See [[confidence-scoring]] for how confidence interacts with consensus.

---

## Per-Market Resilience

Each market is processed in a try/except block. One corrupt or malformed market doesn't crash the cycle — it's logged and skipped. This is critical since we process ~24k odds per cycle.

---

## Why Each Sport and Market Is Different

This is the most important thing the brain carries. The devig engine is general-purpose, but the **inputs** and **behavior** change dramatically across sports and markets.

### Sharpness Varies by Sport
- **NBA player props:** BetRivers, Hard Rock, PropBuilder are sharp. FanDuel and Pinnacle are NOT sharp here despite being sharp for NBA game lines.
- **MLB player props:** Similar sharp landscape to NBA but with thinner markets (fewer books post odds early). Bet365 requires non-headless Chrome (Cloudflare).
- **NRL/AFL:** OpticOdds only. Sharp book coverage is thinner. The AU market is less liquid, so line movement patterns differ from US sports. Consensus may matter more here.

### Vig Distribution Varies by Market
- **Points (NBA):** High-volume, tight lines. Multiplicative devig works well because vig is distributed relatively evenly.
- **Assists / 3-Pointers:** Lower-volume, wider spreads. Longshots carry disproportionate vig → power devig may be more accurate here.
- **Combo markets (Pts+Rebs, etc.):** Often no sharp book data at all. Relies entirely on consensus fallback. Vig structure is less understood.
- **Game props vs player props:** Entirely different sharp book landscape. Don't apply player prop weights to game lines.

### Interpolation Sensitivity Varies by Stat
- **Points:** β ≈ 0.15. A 1-point line shift on a 25.5 line barely moves the probability. Low risk of interpolation error.
- **Assists:** β ≈ 0.45. A 1-assist shift on a 5.5 line is significant. Interpolation is load-bearing here.
- **3-Pointers / Blocks:** β ≈ 0.55–0.65. A 1-unit shift on a 2.5 line changes probability dramatically. Interpolation errors here can generate false +EV signals.

### What This Means for Theories
A single theory config cannot be optimal across all markets and sports. The system needs:
- **Per-sport theories** at minimum (already supported via `sport` column)
- Ideally **per-market-type awareness** (e.g., different min_confidence for combo markets vs main props)
- **Market-specific devig method weights** (power may outperform multiplicative for low-count props)

This is the calibration frontier — the place where getting it right determines long-term profitability.

---

## Key Decisions & Why

| Decision | Reason |
|----------|--------|
| FanDuel weight = 0 | BetIQ reverse engineering showed FanDuel is NOT sharp for player props despite being sharp for game lines |
| All 4 methods run | Theories can weight methods differently; A/B testing via theory system |
| Aggregation before EV calc | Combining multiple sharp opinions before comparing to soft book gives more stable true odds |
| Consensus fallback | Closes the combo market coverage gap that was losing ~20% of BetIQ's best picks |
| Per-sport configs | Each sport has different sharp books, different vig structures, different interpolation sensitivities |

---

## Related Pages
- [[ev-calculation]] — What happens after devigging
- [[interpolation]] — Adjusting when lines differ
- [[confidence-scoring]] — Data quality scoring
- [[theories]] — How devig configs are managed
- [[calibration]] — How weights are optimized
