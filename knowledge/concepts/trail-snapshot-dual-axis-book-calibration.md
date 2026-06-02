---
title: "Trail-Snapshot Dual-Axis Book Calibration Methodology"
aliases: [dual-axis-calibration, brier-plus-calibration-gap, per-book-per-prop-sharpness, trail-snapshot-sharpness, firming-direction-analysis]
tags: [value-betting, methodology, analytics, calibration, sharp-books, trail-data]
sources:
  - "daily/lcash/2026-06-02.md"
created: 2026-06-02
updated: 2026-06-02
---

# Trail-Snapshot Dual-Axis Book Calibration Methodology

On 2026-06-02, lcash developed a dual-axis methodology for assessing per-book, per-prop sportsbook sharpness using raw trail snapshot data at the 30-minute pre-game mark. The key finding is that **Brier score alone lies**: Coolbet had the best overall Brier (0.211) but a -9.6pp calibration gap, while TAB had a worse Brier but near-perfect calibration. Accurate sharpness assessment requires both Brier (probability accuracy) AND calibration gap (systematic over/under-pricing direction) AND firming direction (whether the book's line drifts toward or against our picks over time). The methodology processes 424,413 trail rows across 229,040 (pick × book) observations to produce a per-(sport × prop × book × devig method) scoring matrix with bootstrap confidence intervals.

## Key Points

- **Brier score alone is insufficient** — low Brier ≠ calibrated (Coolbet best Brier at 0.211 but -9.6pp calibration gap; TAB worse Brier but near-perfect calibration)
- **Dual-axis required**: Calibration gap (systematic over/under-pricing in pp) + firming direction (does the book drift toward or against our picks?) — neither alone captures sharpness
- **Trail `books` JSONB stores RAW quoted odds per book** at snapshot time — devig is applied at evaluation, not storage; this makes per-book comparisons genuinely fair regardless of which theory triggered the pick
- **MLB Hits has a -36pp calibration gap universally** — either selection bias in triggered picks or a scrape/parse bug; betting should stop until diagnosed
- **MLB Strikeouts (pitcher) has a +13pp edge** — all books underprice strikeouts; deserves increased stake sizing
- **TAB is calibrated AND drifts against picks** — a potential contrarian signal worth investigating (the book that best calibrates is also the one whose line moves away from our position)
- **Pickle-before-report pattern**: Save intermediate data (`/tmp/sharp_trail_rows.pkl`) BEFORE the formatting phase — a 23-minute HTTP fetch crashed on a format string bug, losing all data

## Details

### The Methodology

The calibration analysis uses trail snapshot data captured at the 25-35 minute pre-game mark (the stake-window identified in [[concepts/closing-time-vs-stake-window-sharpness]] as the causal measurement point). For each resolved pick, the trail's `books` JSONB field contains raw quoted odds from every sportsbook that had data at snapshot time. These raw odds are NOT devigged — they represent each book's actual market price at that moment. The devig method (multiplicative, power, additive) is applied at evaluation time, meaning the same raw odds can be scored under multiple devig assumptions.

The scoring matrix evaluates each cell of `(sport × prop_type × book_id × devig_method)` using three metrics:

1. **Brier score** — measures probability accuracy: how well does this book's devigged implied probability predict actual outcomes? Lower is better. Computed as `mean((implied_prob - outcome)²)`.

2. **Calibration gap** — measures systematic directional bias: does this book systematically overprice or underprice this prop type? Computed as `mean(implied_prob) - mean(outcome)` in percentage points. A gap of +5pp means the book overprices (thinks events are 5pp more likely than they actually are); -5pp means it underprices.

3. **Firming direction** — measures whether the book's line moves toward or against our triggered picks between detection and game start. A book that firms toward our position is validating the pick; one that drifts away suggests we're on the wrong side of the market.

### Why Brier Alone Lies

The Brier score rewards both calibration (correct probability estimates) and resolution (separating outcomes). A book can achieve a low Brier score by being well-resolved (correctly assigning high probabilities to events that happen) while having a consistent directional bias (systematically overpricing everything by 5pp). The calibration gap captures this bias explicitly.

Coolbet exemplified this on 2026-06-02: best overall Brier at 0.211, but a -9.6pp calibration gap means it systematically underprices events. Using Coolbet as a sharp reference for devigging would systematically inflate EV calculations because its "true probability" estimates are biased low — making soft book prices appear more valuable than they are.

TAB showed the opposite profile: worse Brier (lower resolution — less good at separating outcomes) but near-perfect calibration (no systematic directional bias). For devigging purposes, calibration matters more than resolution because the devig output directly feeds EV computation — a calibrated but low-resolution book produces noisy but unbiased EV estimates, while a well-resolved but miscalibrated book produces precise but systematically wrong EV estimates.

### Sport × Prop Findings

Two extreme sport × prop findings emerged from the initial analysis:

**MLB Hits: -36pp calibration gap universally.** Every book underprices Hits by approximately 36 percentage points relative to actual outcomes on triggered picks. This is either (a) a selection bias artifact — the scanner's trigger logic systematically selects Hits picks that are miscalibrated, or (b) a scrape/parse bug producing wrong Hits odds. The magnitude (-36pp) is large enough that betting on MLB Hits should stop until the root cause is diagnosed.

**MLB Strikeouts (pitcher): +13pp edge.** All books overestimate the probability of pitcher strikeout outcomes by approximately 13 percentage points. This suggests a genuine, persistent market inefficiency — pitchers achieve strikeout thresholds less often than books price, creating systematic value on Under picks. This finding warrants increased stake sizing if confirmed with sufficient sample days.

### Selection Bias Caveat

Trail data only covers markets where the scanner triggered a pick — not the full market universe. The calibration findings are conditional on "picks we bet," not universal truths about book pricing. A -36pp gap on MLB Hits could mean "the scanner specifically selects Hits picks that books misprice" rather than "all Hits markets are mispriced." Unconditional sharpness claims require ~3 more weeks of data (n_day ≥ 20) for statistical significance at the day-as-unit level established in [[concepts/superwin-pick-non-independence-methodology]].

### The Pickle-Before-Report Pattern

The analysis script required ~23 minutes of HTTP fetches to pull trail data from Supabase. The initial run crashed during the report formatting phase (a format string bug in the findings markdown generation). Because the intermediate data wasn't saved, the entire 23-minute fetch had to be repeated. The fix: always serialize intermediate data to a pickle file (`/tmp/sharp_trail_rows.pkl`) immediately after the fetch phase completes, before any formatting or analysis. This ensures that a crash in downstream processing never requires re-fetching.

## Related Concepts

- [[concepts/closing-time-vs-stake-window-sharpness]] - The parent methodology article establishing stake-window (30-min) as the correct measurement point; this article extends it to per-book, per-prop dual-axis scoring
- [[concepts/pinnacle-prop-type-sharpness-variance]] - Established that Pinnacle's sharpness varies by prop type; this methodology extends the principle to ALL books across ALL prop types simultaneously
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV uses closing-line references; this calibration methodology provides the per-book accuracy data needed to correctly weight sharps in CLV computation
- [[concepts/value-betting-theory-system]] - Theory weights should be informed by per-book, per-prop calibration; the dual-axis matrix provides the data for weight optimization
- [[concepts/sharp-snapshot-soft-book-contamination]] - Bet365 and AU soft books contaminating sharp_snapshot were discovered during this calibration analysis

## Sources

- [[daily/lcash/2026-06-02.md]] - 424,413 trail rows, 229,040 (pick × book) observations; Coolbet best Brier 0.211 but -9.6pp cal gap vs TAB near-perfect calibration; MLB Hits -36pp universally; MLB Strikeouts +13pp edge; TAB contrarian signal; pickle-before-report pattern after 23-min fetch lost to format string crash; per-(sport × prop × book × devig method) Brier + bootstrap CI matrix kicked off (Sessions 16:41, 17:11)
