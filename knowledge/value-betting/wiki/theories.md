# Theories

## Status: current
## Last verified: 2026-04-09 (updated with weight config details, alt line theory)

> Named configurations of devig parameters that can be A/B tested and promoted.

---

## What a Theory Is

A theory is a named set of parameters that controls how the devig engine operates. Different theories can run simultaneously, each producing its own set of picks. This enables A/B testing of devig strategies.

**Source:** `ev_scanner/theories.py` (~5.7KB), stored in `nba_optimization_runs` table

---

## Theory Parameters

| Parameter | Type | Example | Controls |
|-----------|------|---------|----------|
| `devig_method_weights` | dict | `{mult: 0.4, add: 0.3, power: 0.2, shin: 0.1}` | Which devig methods to emphasize |
| `sharp_book_weights` | dict | `{802: 1.0, 803: 0.9, 125: 0.95, 200: 0.8}` | Which sharp books to trust most |
| `min_ev` | float | 3.0 | Minimum raw EV% to track |
| `min_confidence` | float | 2.0 | Minimum confidence score to track |
| `min_confidence_weighted_ev` | float | 1.5 | Minimum weighted EV to track |
| `max_line_gap` | float | 5.0 | Maximum gap between sharp and soft lines (alt lines) |
| `line_gap_penalty` | float | 0.03 | Per-unit penalty for line gap in interpolation |
| `sport` | string | "nba" | Which sport this theory applies to |
| `is_active` | bool | true | Whether the theory runs in the pipeline |

### Weight Key Convention

In `sharp_book_weights`, keys that parse as integers are sharp book IDs (e.g., `"802"` = BetRivers). **Absent books default to weight 0**, not 1.0. This is critical — if a theory config only specifies 4 books, only those 4 are used. Both the server tracker and dashboard must respect this convention.

**Bug fixed 2026-04-09:** The dashboard was falling back to weight 1.0 for absent books, meaning a 4-book theory was actually using 7+ books. Server was already correct. See [[dashboard]] and [[tracker]] for details.

---

## Theory Lifecycle

See [[patterns/theory-lifecycle]] for the full pattern.

1. **Create** — Define parameters (manually or via optimizer)
2. **Calibrate** — Run against historical data, measure Brier score / log loss
3. **Promote** — Mark as `is_active = true` in `nba_optimization_runs`
4. **Evaluate** — Monitor live performance: hit rate, CLV, ROI
5. **Retire** — Set `is_active = false` when superseded

---

## How Theories Are Loaded

`theories.py` fetches active theories from Supabase every 5 minutes (300s cache TTL). This means:
- Theory changes take up to 5 minutes to take effect
- No server restart needed to change theories
- Multiple theories can be active simultaneously

---

## Theory Evaluation

Every cycle, the engine evaluates each active theory against every market:
1. Run the devig pipeline with this theory's weights
2. Calculate EV with this theory's method weights
3. Check if pick passes this theory's thresholds
4. If yes → tracked as an EVPick tagged with this theory's ID

The tracker records which theory(s) each pick passed. The resolver later grades each pick independently, so you can compare theory performance.

---

## Key Insight: Theories Enable Calibration

The theory system is what makes the scanner improvable over time. Instead of hardcoding weights, you can:
- Run 5 different theories simultaneously
- After a week, compare hit rates, CLV, and ROI
- Promote the best performer, retire the worst
- Repeat

This is the feedback loop that closes the gap with BetIQ.

---

## Why One Theory Doesn't Fit All

The core reason this system exists: **each sport is different, and even within a sport, each market behaves differently.**

### Sport-Level Differences
- **NBA:** Deep sharp book coverage. BetRivers is king for props. Lots of calibration data. This is where theories are most refined.
- **MLB:** Similar books but thinner markets. Pitcher props behave differently from batter props. Fewer data points for calibration.
- **NRL/AFL:** AU-only sports. Sharp book coverage is thin (mostly OpticOdds consensus). Theories here need lower confidence thresholds or different sharp weights entirely.

### Market-Level Differences (Within NBA)
- **Points:** High volume, tight lines, well-understood. Multiplicative devig works well. Most calibration data.
- **Assists / Rebounds:** Lower volume, wider vig. Power devig may outperform multiplicative because longshot bias is more pronounced.
- **3-Pointers / Blocks / Steals:** Very low base rates (2–3 per game). Vig distribution is asymmetric. These are the hardest to devig accurately.
- **Combo markets (Pts+Rebs, etc.):** Often zero sharp book data. Consensus-only. These need fundamentally different treatment — lower confidence expectations, but potentially higher EV finds.

### The Calibration Frontier

Long-term profitability depends on getting this right. The questions the brain should help answer:
1. **Which devig method works best for which market type?** (Not yet fully calibrated)
2. **Which sharp books are actually sharp for which prop types?** (BetRivers seems sharp across the board, but is it equally sharp for assists vs points?)
3. **What min_confidence is right for consensus-only markets?** (Too high = miss real edge. Too low = track noise.)
4. **How do sport-specific vig structures affect interpolation accuracy?** (NRL/AFL may need different betas than NBA)

These are the questions that future theory iterations should systematically answer through A/B testing and backtesting. Every calibration finding should be recorded in this wiki so it compounds across sessions.

---

## Active Theories (Apr 2026)

### AltLine-V1 (NBA)
First alt-line theory, live since 2026-04-08. Params:
- `max_line_gap`: 5.0
- `line_gap_penalty`: 0.03
- 219 picks tracked on first day (Apr 8)

Alt-line picks occur when the soft book offers a different line than sharp books (e.g., sharp at 25.5, soft at 23.5). The interpolation engine adjusts the devigged probability across the line gap. The `line_gap_penalty` reduces confidence proportionally to the distance.

**Monitoring needed:** Compare alt-line CLV and hit rate to main-line picks at equivalent EV thresholds.

---

## Related Pages
- [[devig-engine]] — What theories configure
- [[calibration]] — How theories are optimized
- [[patterns/theory-lifecycle]] — Full lifecycle pattern
- [[resolver]] — How theory performance is measured
