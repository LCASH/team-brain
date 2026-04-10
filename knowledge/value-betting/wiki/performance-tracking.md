# Performance Tracking

## Status: current
## Last verified: 2026-04-09 (added sharp CLV findings, trail timing purpose)

> The segmented performance analysis system that determines which picks are actually profitable.

---

## Core Principle

**Track everything, filter later.** Don't exclude segments (consensus picks, low confidence, etc.) before the data tells you what's profitable. There could be segments that are very profitable but you'd never know if you excluded them upfront.

---

## What We Track (Per Pick)

Already captured in `nba_tracked_picks`:
- `triggered_ev` — EV% at the moment pick first crossed threshold
- `opening_odds` — first-seen soft book odds (the "would-have-bet-at" price)
- `triggered_at` — timestamp when pick was first identified
- `sharp_count` — number of sharp books with data
- `sharp_books_used` — which specific sharp books contributed
- `triggered_by` — which theory flagged it
- `devig_method` — which method was primary
- `prop_type` — Points, Assists, Rebounds, etc.
- `side` — Over/Under
- `line` — the number (25.5, 6.5, etc.)
- `is_alt` — alt line or main line
- `line_gap` — difference between sharp and soft line
- `sport` — NBA, MLB, NRL, AFL
- `soft_book_id` — which soft book (Bet365, etc.)

Captured by resolver:
- `result` — win/loss/push
- `actual_stat` — real player stat
- `closing_odds` — soft book odds at game start
- `clv_pct` — closing line value percentage

---

## Segmentation Dimensions

### Primary: EV Range × Confidence Score
The power view. Cross-tabulation of:

**EV Buckets:** 2–3%, 3–5%, 5–7.5%, 7.5–10%, 10–15%, 15%+

**Confidence Tiers:** 0–1.0, 1.0–2.0, 2.0–3.0, 3.0–4.0, 4.0–5.0
(Note: confidence ≤ 2.5 = consensus-only picks)

Each cell shows: sample size, hit rate, ROI, CLV average, confidence interval

### Secondary Dimensions
- **Prop type:** Points, Assists, Rebounds, 3PT, Blocks, Combos, etc.
- **Sport:** NBA, MLB, NRL, AFL
- **Theory:** which theory config generated the pick
- **Soft book:** Bet365 vs others
- **Timing:** hours before game when triggered

### Derived Dimensions (from trail_entries)
- **Odds decay rate:** how fast EV erodes after identification (unique competitive advantage)
- **Line gap:** interpolation distance (validates interpolation accuracy)

---

## Key Metrics Per Segment

| Metric | What It Shows | Converges At |
|--------|--------------|-------------|
| **CLV** | Did the market agree with us? (leading indicator) | ~50 bets (statistically significant) |
| **CLV beat rate** | % of picks where we beat closing line | ~200 bets |
| **Hit rate** | Simple win percentage | ~400 bets |
| **ROI** | Actual profitability (flat stake) | ~2,000 bets |
| **Sample size** | How much data we have | — |
| **95% CI** | Confidence interval on ROI | Narrows with more data |

**CLV is the primary early indicator.** Research shows:
- CLV standard deviation ≈ 0.1 per bet (vs ≈ 1.0 for P/L)
- CLV converges ~100x faster than ROI in variance terms
- 50 bets with consistent positive CLV = statistically significant evidence of edge
- Professional bettors sustaining positive CLV over 2,000+ bets are almost always profitable
- A consistent 2% CLV edge → ~4% ROI long-term

---

## Sample Size Thresholds

For our typical odds range (1.50–2.00):

| Sample | CLV Signal | ROI Signal | Recommended Action |
|--------|-----------|-----------|-------------------|
| < 50 | Noise | Noise | "Insufficient data" |
| 50–200 | Directional | Noise | CLV reliable, ROI ignore |
| 200–400 | Reliable | Directional | Can trust CLV-based decisions |
| 400–1,000 | Strong | Moderate | Hit rate meaningful, ROI directional |
| 1,000–2,000 | Very strong | Reliable | ROI approaching convergence |
| 2,000+ | Definitive | Definitive | Full confidence in all metrics |

At 1,000 bets with 5% true edge at odds ~2.0:
- 95% CI for ROI: approximately ±6.3%
- Observed ROI could be anywhere from -1.3% to +11.3%
- This is why CLV matters more early on

---

## Odds Snapshot Rules

- **Triggered odds** = snapshot at the moment pick first crosses EV threshold
- **Same pick, new odds** = trail update on existing pick (not a new pick)
- **Same pick, new line** = NEW pick (different market entirely)
- **Closing odds** = last soft book odds before game start (for CLV)
- **Decay rate** = how fast EV erodes after identification (computed from trail_entries)

---

## Brier Score Role

Brier score is a **diagnostic metric for the devig engine**, not the primary performance metric.

**Use it for:** validating that probability estimates are calibrated (when we say 55%, it hits 55%)
**Don't use it for:** deciding whether to bet a segment (use CLV + ROI for that)

More actionable than raw Brier: **reliability diagrams** — bucket picks by predicted probability and plot predicted vs actual hit rate. Shows *where* miscalibration lives.

---

## One-Sided Market Handling

When sharp books only post Over odds (no Under):
1. Devig the Over using estimated vig
2. Under probability ≈ 1 - devigged Over probability
3. Use distribution model (Poisson for counts, logit for continuous) to refine
4. Apply confidence penalty — one-sided data is inherently lower quality
5. Track performance of one-sided picks separately to validate

---

## What This System Answers

The segmented tracking system answers one question across every dimension:
**"If I bet every pick in this segment, would I be profitable?"**

The answer determines:
- Which EV/confidence combinations are worth betting
- Which prop types the scanner is good/bad at
- Whether consensus picks have real edge or not
- Whether to adjust minimum EV threshold (currently 5%)
- Which theories to promote/retire

---

## First Sharp CLV Data (Apr 8, 2026)

The resolver now computes two types of CLV:

### Soft CLV (`clv_pct`)
Uses Bet365's own closing odds. **Problem:** Bet365 barely moves on props, so soft CLV is often 0.00%. Avg soft CLV on Apr 8: **+1.79%**.

### Sharp CLV (`sharp_clv_pct`)
Uses devigged sharp book closing true probability from `trail_entries`. Much more meaningful — sharp books actually move on information. Avg sharp CLV on Apr 8: **+8.9%**.

**Coverage:** 109/1,000 resolved picks had sharp trail data (~11%). The gap exists because trail_entries only records when odds change — if sharp odds don't move between tracking and game start, no closing snapshot exists.

**Implication:** Sharp CLV confirms the scanner has real edge (~5× what soft CLV suggests). As trail coverage grows, sharp CLV becomes the primary validation metric.

---

## Trail Data & Bet Timing Analysis

The purpose of collecting many odds snapshots per pick (via `trail_entries`) extends beyond CLV calculation. The trail data enables **backtesting optimal bet timing windows**:

- **2 hours before tipoff** — maximum data, lines may still move
- **30 minutes before tipoff** — most sharp movement complete
- **20 minutes before tipoff** — near-closing, minimal edge decay remaining

By replaying trail_entries, we can determine which timing window maximizes both EV retention and safety (avoiding line movement against us). This is a unique competitive advantage — no consumer tool surfaces odds decay analysis.

---

## Sources

- [Buchdahl: CLV converges ~100x faster than ROI](https://www.pinnacleoddsdropper.com/blog/closing-line-value--clv-demystified-by-expert-joseph-buchdahl)
- [RebelBetting: average flat ROI 2.1–2.6% across 200k+ trades](https://www.rebelbetting.com/faq/expected-value-and-variance)
- [Sports-AI: miscalibrated probabilities distort edge computation](https://www.sports-ai.dev/blog/ai-model-calibration-brier-score)
- [OddsJam: top bettors beat CLV ~75% of the time](https://oddsjam.com/betting-education/closing-line-value)

## Related Pages
- [[ev-calculation]] — How EV% is computed
- [[confidence-scoring]] — How confidence scores work
- [[theories]] — How theory configs are evaluated
- [[resolver]] — How picks are graded
- [[calibration]] — Brier score and optimization
