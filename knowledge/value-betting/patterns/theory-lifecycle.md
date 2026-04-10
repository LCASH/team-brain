# Pattern: Theory Lifecycle

> How theories are created, tested, promoted, evaluated, and retired.

---

## Lifecycle Stages

```
CREATE → CALIBRATE → PROMOTE → EVALUATE → RETIRE
```

### 1. Create
Define a theory with specific parameters:
- Devig method weights (e.g., `{mult: 0.4, add: 0.3, power: 0.2, shin: 0.1}`)
- Sharp book weights (e.g., `{802: 1.0, 803: 0.9, 125: 0.95}`)
- Thresholds: min_ev, min_confidence, min_confidence_weighted_ev
- Sport scope

**Sources:** Manual creation, `calibrate_weights.py` grid search, `optimizer.py` differential evolution.

### 2. Calibrate
Run the theory against historical data:
- Input: resolved picks from `nba_resolved_picks`
- Metrics: Brier score (primary), log loss (secondary), hit rate, CLV
- Compare against existing theories and BetIQ benchmark

Write results to `nba_optimization_runs` with `is_active = false`.

### 3. Promote
Mark as `is_active = true` in `nba_optimization_runs`. The pipeline picks it up within 5 minutes (cache TTL). Multiple theories can be active simultaneously — this is by design for A/B testing.

### 4. Evaluate
Monitor live performance over days/weeks:
- Hit rate vs other active theories
- CLV average (is the engine catching real value?)
- ROI (the ultimate metric)
- Comparison tab: delta vs BetIQ on shared picks

The resolver grades every pick per theory independently, so you can compare apples to apples.

### 5. Retire
Set `is_active = false` when:
- A better theory supersedes it
- Performance degrades (market conditions changed)
- Calibration data shows it's no longer optimal

Retired theories remain in the table for historical reference.

---

## Key Principle

The theory system is what makes the scanner **improvable over time**. Without it, you'd have to restart the server every time you change devig weights. With it, you can iterate rapidly and let data decide.

---

## Related Pages
- [[wiki/theories]] — Technical details of the theory system
- [[wiki/calibration]] — How calibration works
- [[infra/resolver]] — How theories are graded
