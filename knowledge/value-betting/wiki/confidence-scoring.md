# Confidence Scoring

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> Data quality scoring that reflects how much sharp book evidence supports a pick.

---

## How It Works

**Source:** `ev_scanner/confidence.py` (~6.1KB)

Each sharp book contributes a fixed score when it has 2-way (Over + Under) data for a market. The confidence score is the sum of all contributing books' scores, capped at 5.0.

---

## Per-Book Scores

| Book ID | Name | Score | Notes |
|---------|------|-------|-------|
| 100 | FanDuel | 1.25 | Primary sharp (game lines); overrated for props but still counts |
| 125 | PropBuilder | 1.25 | Primary sharp for props |
| 250 | Pinnacle | 0.75 | Secondary; sharp for game lines, less so for props |
| 642 | BookMaker | 0.75 | Secondary sharp |
| 726 | BetAmapola | 1.0 | Secondary sharp |
| 802 | BetRivers | — | Sharpest for props (high devig weight) but separate from confidence |
| 803 | Hard Rock | — | Sharp for props (high devig weight) |

**Important distinction:** Confidence scores and devig weights are DIFFERENT systems:
- **Confidence** = "how much data do we have?" (determines if pick is reliable)
- **Devig weights** = "which books are sharpest?" (determines true odds calculation)

A book can have high devig weight but no confidence contribution, or vice versa.

---

## Scoring Rules

| Condition | Score |
|-----------|-------|
| 2-way data (Over + Under) | Full book score |
| 1-way data (Over only or Under only) | 0.00 — can't devig reliably |
| No data from a reference book | 0.10 |
| Maximum total | 5.0 (hard cap) |
| Consensus-only (no sharp books) | 2.5 (hard cap) |
| One-sided consensus | 3.5 (hard cap) |

---

## How Confidence Is Used

1. **Theory gating:** Picks must meet `min_confidence` threshold (typically 1.5–2.5) to be tracked
2. **EV weighting:** `confidence_weighted_ev = ev_pct * (confidence / 5.0)` — see [[ev-calculation]]
3. **Pick quality signal:** Higher confidence = more sharp books agree = higher conviction

---

## Why Fixed Scores?

Discovered during BetIQ reverse engineering (2026-03-13): BetIQ uses fixed per-book scores regardless of the specific market or odds quality. This makes the system predictable and consistent. Dynamic scoring (based on line freshness, spread width, etc.) was considered but adds complexity without proven benefit.

---

## Related Pages
- [[ev-calculation]] — How confidence weights EV
- [[devig-engine]] — How books contribute to true odds (different from confidence)
- [[theories]] — Theory thresholds for min_confidence
