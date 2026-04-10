# Interpolation

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> Adjusting true probabilities when the sharp book's line differs from the soft book's line.

---

## The Problem

Sharp books and soft books don't always offer the same line. Example:
- **BetRivers** (sharp): LeBron Over **26.5** Points at 1.85
- **Bet365** (soft): LeBron Over **25.5** Points at 2.10

We can devig BetRivers' odds to get true probability at 26.5, but we need true probability at **25.5** to compare against Bet365. Interpolation bridges this gap.

**Source:** `ev_scanner/interpolate.py` (~8.3KB)

---

## Two Models

### Logit Interpolation (Continuous Props)
For stats that are approximately continuous: **Points, Points+Rebounds, Points+Assists, Pts+Rebs+Asts**, and other combo markets.

```python
# Convert probability to log-odds (logit)
logit_p = log(p / (1 - p))

# Shift by beta * line_difference
logit_adjusted = logit_p - beta * (target_line - sharp_line)

# Convert back to probability
adjusted_p = sigmoid(logit_adjusted) = 1 / (1 + exp(-logit_adjusted))
```

**Why logit?** The sigmoid function naturally bounds probabilities between 0 and 1, and the logit transform makes the relationship between line and probability approximately linear.

### Poisson Interpolation (Count Props)
For discrete counting stats: **Assists, 3-Pointers, Blocks, Steals, Turnovers** — events that come in whole numbers.

```python
# Back out the Poisson rate parameter (lambda) from the over probability
# P(X > line) = 1 - CDF(line, lambda)
# Solve for lambda using scipy

# Then recalculate at the target line
adjusted_p = 1 - poisson.cdf(target_line, lambda)
```

**Why Poisson?** Counting stats follow a Poisson-like distribution. A player averaging 5.2 assists has discrete outcomes (4, 5, 6, 7...) that Poisson models well.

---

## Beta Calibration

Each prop type has a calibrated beta value (0.15–0.65) that controls how sensitive probability is to line changes:

| Prop Type | Beta | Model | Rationale |
|-----------|------|-------|-----------|
| Points | ~0.15 | Logit | Low sensitivity — 1 point change in 25+ point line is small |
| Assists | ~0.45 | Poisson | High sensitivity — 1 assist change in 5-6 assist line is large |
| 3-Pointers | ~0.55 | Poisson | Very sensitive — 1 three change in 2-3 three line is huge |
| Pts+Rebs | ~0.12 | Logit | Low — combo lines are large numbers (35+) |
| Blocks | ~0.65 | Poisson | Most sensitive — 1 block change in 1-2 block line |

**Source:** Beta values are in `sport_config.py` per sport, calibrated via backtesting.

---

## When Interpolation is Skipped

- **Same line:** sharp_line == target_line → no interpolation needed
- **No Over/Under pair:** Can't devig without both sides → no true odds → no interpolation
- **Line difference too large:** Some implementations cap at ±3 line difference to avoid unreliable extrapolation

---

## Known Issues

- **Beta precision:** Current betas are ballpark estimates from calibration, not rigorously optimized per-sport. Room for improvement.
- **Poisson assumption:** Not all count stats are truly Poisson. Rebounds in particular may be over-dispersed (negative binomial might fit better). Practical difference is small.
- **Half-line handling:** Lines like 25.5 are treated as continuous in logit but as floor(25.5)=25 in Poisson CDF. This is correct but worth knowing.

---

## Related Pages
- [[devig-engine]] — Where interpolation fits in the pipeline
- [[sport-config]] — Per-sport beta values
- [[calibration]] — How betas are tuned
