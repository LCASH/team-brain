# EV Calculation

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> How expected value is calculated from true odds vs soft book odds.

---

## The Formula

**Source:** `ev_scanner/ev_calc.py` (~1.6KB)

```python
ev_pct = (book_odds / true_odds - 1) * 100
```

Where:
- `book_odds` = decimal odds from the soft book (e.g., Bet365 at 2.10)
- `true_odds` = fair decimal odds from devigged sharp book consensus (e.g., 1.90)
- Result: percentage edge (e.g., +10.5% EV)

**Example:**
- Bet365 offers LeBron Over 25.5 Points at **2.10**
- Devigged sharp consensus says true odds are **1.90**
- EV% = (2.10 / 1.90 - 1) × 100 = **+10.5%**

---

## Confidence-Weighted EV

Raw EV% doesn't account for how much data supports the true odds estimate. A pick backed by 5 sharp books at 5.0 confidence is more trustworthy than one backed by a single book at 1.0 confidence.

```python
confidence_weighted_ev = ev_pct * (confidence / 5.0)
```

Where:
- `confidence` = sum of per-book scores (0.0 to 5.0) from [[confidence-scoring]]
- At max confidence (5.0), weighted EV = raw EV
- At low confidence (1.0), weighted EV = 20% of raw EV

**Why this matters:** Prevents the system from over-weighting picks that have high EV% but are based on thin data (e.g., only one obscure sharp book had the market).

---

## Theory Gating

A pick must pass ALL of the active theory's thresholds to be tracked:

| Threshold | Typical Value | What It Filters |
|-----------|--------------|-----------------|
| `min_ev` | 2.0–5.0% | Minimum raw EV% |
| `min_confidence` | 1.5–2.5 | Minimum data quality score |
| `min_confidence_weighted_ev` | 1.0–3.0% | Minimum weighted EV (combines both) |

Different theories set different thresholds — conservative theories require higher confidence, aggressive ones accept lower confidence if EV is very high.

See [[theories]] for how these configs are managed.

---

## Edge Cases

- **Negative EV:** When book_odds < true_odds. These picks are filtered out (no value).
- **Huge EV (>50%):** Usually indicates stale odds or a data error. Some theories cap max EV.
- **Zero confidence:** Pick is still calculated but confidence_weighted_ev = 0, so it won't pass any theory's threshold.
- **Consensus-only picks:** Capped at 2.5 confidence, so their weighted EV is at most 50% of raw EV.

---

## Related Pages
- [[devig-engine]] — How true odds are calculated
- [[confidence-scoring]] — How confidence scores work
- [[theories]] — Theory thresholds that gate picks
- [[tracker]] — What happens to picks that pass
