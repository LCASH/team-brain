---
title: "OpticOdds CLV Backfill Audit"
aliases: [opticodds-clv, clv-backfill, pinnacle-clv-cross-validation, optic-close-pinnacle, clv-audit]
tags: [value-betting, analytics, clv, opticodds, data-quality, backfill, pinnacle]
sources:
  - "daily/lcash/2026-05-12.md"
  - "daily/lcash/2026-05-14.md"
created: 2026-05-12
updated: 2026-05-14
---

# OpticOdds CLV Backfill Audit

OpticOdds exposes CLV data via the `/fixtures/odds/historical` endpoint, where each entry contains `olv` (opening line value) and `clv` (closing line value) objects with `price` and `points` fields. Cross-validation of OpticOdds Pinnacle CLV against the scanner's devigged-blend CLV on 580 LAL@OKC picks revealed an 8.07 percentage point mean absolute gap with some sign-flips — expected since the scanner's blend gives Pinnacle only ~23% weight while OpticOdds CLV is raw Pinnacle-only. Match rate was initially only 4% (40 of 1,000 picks) but improved to ~90%+ after nickname-based fuzzy matching recovered 349 fixture name mismatches. MLB was completely unsupported until 18 prop type mappings were added on 2026-05-14. Pinnacle's structural ceiling limits exact-line CLV to ~71% of NBA picks (29% are alt-line with no Pinnacle counterpart). The system systematically under-estimates Pinnacle's closing movement by -4.55pp (mean signed divergence).

## Key Points

- OpticOdds CLV available via `/fixtures/odds/historical` — each entry has `olv` and `clv` objects with `price` and `points`; `/grader/odds` is a paid-tier auto-grader (403 on current key) but unnecessary since the resolver already handles grading
- OpticOdds CLV is raw Pinnacle-only (not devigged blend) — always compare shape of disagreement, not magnitude; 8.07pp mean absolute gap vs scanner's blend CLV is expected since blend gives Pinnacle ~23% weight
- **Fixture matching improved from 4% to ~90%+** via nickname-based fuzzy matching (last word of team name) — recovered 349 fixture name mismatches down to 4 unmatched; abbreviated formats ("ATL Hawks @ MIA Heat") were the main culprit
- **MLB prop mappings (18 types) added** — MLB was completely unsupported before; `PROP_TO_OPTIC_MARKET["mlb"]` was an empty dict silently skipping all MLB picks
- **Pinnacle structural ceiling**: quotes ONE main line per player per prop — 29% of NBA alt-line picks are structurally un-CLV-able against Pinnacle at exact line
- Counter-intuitive CLV signal at n=100: when Pinnacle moves *with us* (>+2% OO CLV), win rate is **47%**; when neutral/disagrees, win rate is **59%** — needs n>200+ to be conclusive
- Mean signed divergence is **-4.55pp** — the scanner systematically under-estimates Pinnacle's closing movement; newly recovered abbreviated-name picks have larger gaps (possibly older/sparser trail data)
- Two migrations: 033 adds four tracker audit columns; 034 adds six OpticOdds CLV columns

## Details

### API Endpoint Discovery

The OpticOdds API exposes two CLV-related endpoints. The primary endpoint `/fixtures/odds/historical` returns timestamped odds snapshots for a given fixture and market, with each entry containing `olv` (opening line value) and `clv` (closing line value) objects. Each object has `price` (American odds format) and `points` (the line value). This is the endpoint used for backfill — it provides Pinnacle's raw closing line without any devigging applied.

The secondary endpoint `/grader/odds` is an auto-grading service that evaluates whether a bet had positive CLV at close. However, this endpoint returns 403 on the current API key tier. It is not needed for the backfill audit since the scanner's resolver already handles pick grading (win/loss/push determination), and the CLV computation from historical odds snapshots is straightforward.

### Cross-Validation Methodology

The audit cross-validated OpticOdds Pinnacle CLV against the scanner's devigged-blend CLV on 580 picks from the LAL@OKC fixture. The scanner's blend CLV incorporates odds from multiple sharp books (Pinnacle, DraftKings, FanDuel, BetMGM, etc.) weighted by a proprietary scheme where Pinnacle receives approximately 23% weight. OpticOdds CLV is raw Pinnacle closing price only — no devigging, no blending.

The 8.07 percentage point mean absolute gap between the two CLV measures is expected and structurally driven. When the scanner's blend and Pinnacle disagree on direction, it indicates that other sharp books moved differently than Pinnacle. The important diagnostic is the *shape* of disagreement (systematic bias vs random noise) rather than the magnitude.

The low 4% match rate is the more actionable finding. Three failure modes account for the 96% of unmatched picks: fixture name mismatches between OpticOdds and the scanner's naming conventions (349 picks — the largest category, addressable via [[concepts/fixture-name-canonicalization]]), markets that exist in the scanner but have no Pinnacle history in OpticOdds (510 picks — structural limitation of Pinnacle's player prop coverage), and alt-line differences where the scanner and OpticOdds disagree on which line to compare (101 picks).

### Early Backfill Results

The first 40 successfully matched picks show a counterintuitive CLV-to-outcome pattern: when Pinnacle's closing line moved *with* the scanner's pick direction by more than +2% (confirming the scanner found real value), win rate was only 36%. When Pinnacle's closing line was flat (no movement), win rate was 60%. This is a small sample size (n=40) and should not drive any conclusions — the pattern needs n>200 before statistical reliability. It may reflect selection bias in which picks happen to match across the fixture name gap, or it may be a genuine signal about Pinnacle-confirming vs Pinnacle-neutral picks.

### Database Schema Changes

Migration 034 adds six new columns to the picks table for OpticOdds CLV persistence:
- `optic_close_pinnacle_price`: Pinnacle's closing American odds from OpticOdds
- `optic_close_pinnacle_points`: Pinnacle's closing line value from OpticOdds
- `optic_clv_pct`: Computed CLV percentage (scanner odds vs Pinnacle close)
- `optic_clv_direction`: Categorical — "with", "against", or "flat"
- `optic_lookup_at`: Timestamp of when the OpticOdds lookup was performed
- `optic_lookup_status`: Status of the lookup — "matched", "fixture_miss", "market_miss", "alt_line_diff"

Migration 033 (applied in the same session) adds four tracker audit columns that were silently dropped from an earlier deployment: `pick_filter_reason`, `model_take`, `model_take_reason`, `extra_sharp_data`. These columns support the tracker's decision audit trail but were lost because `nba_tracked_picks` has two independent writers — the tracker and `news_agent/pick_writer.py` — each with its own column list, representing architectural debt where schema changes must be synchronized across both writers.

### PATCH Error Logging Fix

A related fix addressed the PATCH error logging in the CLV backfill process. Previously, all errors were swallowed into a single `patch_fail += 1` counter with no cause differentiation. The fix buckets errors by cause (network timeout, 404 not found, 409 conflict, 500 server error) to enable targeted debugging of backfill failures.

### Nickname-Based Fuzzy Fixture Matching (2026-05-14)

On 2026-05-14, lcash overhauled the fixture matching algorithm from strict substring matching to **nickname-based fuzzy matching** using the last word of each team name. The match rate jumped from 4% (40/1,000) to approximately 90%+ — recovering 349 previously unmatched fixtures down to only 4 remaining misses.

The primary failure mode was abbreviated team name formats: the scanner's `fixture_name` field uses formats like "ATL Hawks @ MIA Heat" or "Minnesota Timberwolves vs Oklahoma City Thunder," while OpticOdds historical endpoints use their own naming conventions. Extracting the last word of each team name ("Hawks", "Heat", "Timberwolves", "Thunder") and matching on that nickname proved robust across all observed format variations.

The 4 remaining unmatched fixtures are edge cases requiring manual canonical mapping (teams with non-unique last names or unusual formatting). The improvement makes the backfill pipeline practically viable — the previous 4% match rate meant 96% of picks could never receive OpticOdds CLV data regardless of how well the rest of the pipeline worked.

### MLB Prop Type Support (2026-05-14)

MLB was completely unsupported in the backfill script because `PROP_TO_OPTIC_MARKET["mlb"]` was an empty dictionary. All 18 MLB prop type mappings (hits, bases, strikeouts, home runs, earned runs, RBIs, runs, doubles, singles, triples, stolen bases, walks, pitcher outs, etc.) were added, enabling MLB picks to receive OpticOdds CLV data for the first time.

### Pinnacle Structural Ceiling and Systematic Under-Estimation

Two structural findings emerged from the expanded cross-validation:

**Pinnacle one-main-line limitation:** Pinnacle quotes exactly one main line per player per prop — it does not offer alt lines. This means 29% of NBA picks (those triggered at alt lines like Points Over 19.5 when Pinnacle's main is 25.5) can never have exact-line CLV computed against Pinnacle. The structural ceiling for exact-line CLV coverage is approximately 71% for NBA and similarly constrained for MLB. An alt-line CLV policy decision remains open: either use Pinnacle's main line as a proxy with a flag indicating the approximation, or accept the ~71% coverage ceiling.

**Systematic under-estimation:** The mean signed divergence between the scanner's blend CLV and OpticOdds raw Pinnacle CLV is -4.55pp — the scanner consistently under-estimates how much Pinnacle moved. This is expected given the blend's multi-book weighting (Pinnacle receives ~23% weight), meaning the blend is dampened relative to Pinnacle-only movement. Newly recovered abbreviated-name-format picks from the fuzzy matching improvement show larger-than-average gaps, possibly because these older picks have sparser trail data contributing to less precise closing-odds estimation.

### Updated Counter-Intuitive CLV Signal (n=100)

At n=100 (expanded from the initial n=40), the counter-intuitive pattern persists but with updated numbers: when Pinnacle moves *with* the scanner's pick direction (>+2% OO CLV), win rate is 47%. When Pinnacle is neutral or disagrees, win rate is 59%. Two hypotheses remain: (1) late entry after value has evaporated (Pinnacle agreement = market already moved), (2) reverse sharp signal where Pinnacle reacted to public action rather than fundamental information. The sample remains too small for strategy-level conclusions — n>200+ is the target before adjusting theory weights based on CLV agreement direction.

### Production Integration Status (2026-05-14)

A comprehensive tracker audit on 2026-05-14 (see [[concepts/tracker-pipeline-7-phase-audit]]) confirmed that the OpticOdds historical integration has **never run in production**: 0 of 200 sampled resolved picks had `optic_lookup_at` populated. The script's overall filter accuracy is approximately 20% — three blockers: strict line equality (alt-line picks unmatchable), fixture string matching (partially solved by nickname fuzzy matching), and data retention gaps (754 picks with zero Pinnacle historical entries from OpticOdds' data retention limits). Scheduling the backfill script as a nightly cron remains a pending action item.

### Two-Writer Architectural Debt (Confirmed)

The two-writer problem (tracker and `news_agent/pick_writer.py` both writing to `nba_tracked_picks` with independent column lists) was confirmed again on 2026-05-14. The `sharp_snapshot` schema used by the tracker is `{book_id: {odds, under_odds, interp_prob, weight}}` — the replay logic must use `Σ(weight × interp_prob) / Σ(weight)` to reconstruct `true_prob`. The news agent writer uses a different schema. This debt means schema changes must be manually synchronized across both writers, with no shared validator.

## Related Concepts

- [[concepts/sharp-clv-theory-ranking]] - The scanner's own CLV ranking system that uses devigged blend CLV; the OpticOdds backfill provides a second CLV measure (raw Pinnacle) for cross-validation of theory performance
- [[concepts/opticodds-critical-dependency]] - OpticOdds as the single provider of sharp book data; the CLV backfill adds a new dependency surface (historical endpoint) beyond the existing real-time SSE feed
- [[concepts/tracker-pipeline-7-phase-audit]] - The 7-phase audit that confirmed OpticOdds integration has never run in production and validated the backfill pipeline fixes
- [[concepts/fixture-name-canonicalization]] - The fixture name normalization that the nickname-based fuzzy matching complements; both address the same class of team name format inconsistency
- [[concepts/pinnacle-mlb-player-prop-coverage-gap]] - Pinnacle's structural absence from MLB props compounds with the one-main-line limitation to constrain CLV coverage across sports

## Sources

- [[daily/lcash/2026-05-12.md]] - OpticOdds CLV via `/fixtures/odds/historical` with `olv`/`clv` objects; `/grader/odds` paid-tier 403; raw Pinnacle-only CLV (not devigged blend); 8.07pp mean absolute gap on 580 LAL@OKC picks; 4% match rate (40/1000) due to fixture name mismatches (349), unmapped markets (510), alt-line diffs (101); first 40 picks show 36% win rate when Pinnacle confirms vs 60% when flat; migration 034 adds 6 OpticOdds columns; migration 033 adds 4 silently-dropped tracker audit columns; two writers into nba_tracked_picks = architectural debt; PATCH error logging bucketed by cause (Sessions 14:22, 16:30)
- [[daily/lcash/2026-05-14.md]] - Fixture matching improved from strict substring to nickname-based fuzzy (349→4 unmatched, 99% recovery); MLB prop mappings (18 types) added — MLB completely unsupported before; Pinnacle structural ceiling: one main line per player per prop, 29% of NBA alt-line picks un-CLV-able; counter-intuitive signal updated at n=100: CLV>+2% → 47% WR vs neutral/disagrees → 59%; mean signed divergence -4.55pp; OpticOdds integration confirmed never run in production (0/200 picks, Phase 4 of 7-phase audit); `sharp_snapshot` schema `{bid: {odds, under_odds, interp_prob, weight}}`; two-writer debt confirmed (Sessions 09:43, 10:06, 11:22)
