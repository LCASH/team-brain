---
title: "OpticOdds CLV Backfill Audit"
aliases: [opticodds-clv, clv-backfill, pinnacle-clv-cross-validation, optic-close-pinnacle, clv-audit]
tags: [value-betting, analytics, clv, opticodds, data-quality, backfill, pinnacle]
sources:
  - "daily/lcash/2026-05-12.md"
created: 2026-05-12
updated: 2026-05-12
---

# OpticOdds CLV Backfill Audit

OpticOdds exposes CLV data via the `/fixtures/odds/historical` endpoint, where each entry contains `olv` (opening line value) and `clv` (closing line value) objects with `price` and `points` fields. Cross-validation of OpticOdds Pinnacle CLV against the scanner's devigged-blend CLV on 580 LAL@OKC picks revealed an 8.07 percentage point mean absolute gap with some sign-flips — expected since the scanner's blend gives Pinnacle only ~23% weight while OpticOdds CLV is raw Pinnacle-only. Match rate was only 4% (40 of 1,000 picks) due to fixture name mismatches (349), unmapped markets with no Pinnacle history (510), and alt-line differences (101). Six new database columns were added via migration 034 to persist OpticOdds CLV data alongside the scanner's own blend CLV.

## Key Points

- OpticOdds CLV available via `/fixtures/odds/historical` — each entry has `olv` and `clv` objects with `price` and `points`; `/grader/odds` is a paid-tier auto-grader (403 on current key) but unnecessary since the resolver already handles grading
- OpticOdds CLV is raw Pinnacle-only (not devigged blend) — always compare shape of disagreement, not magnitude; 8.07pp mean absolute gap vs scanner's blend CLV is expected since blend gives Pinnacle ~23% weight
- Match rate only 4% (40/1,000): fixture name mismatches (349), unmapped markets / no Pinnacle history (510), alt-line differences (101) — fixture canonicalization is the primary bottleneck
- First 40 backfilled picks show counterintuitive pattern: when Pinnacle moves *with us* (>+2%), win rate is only 36% vs 60% when flat — needs n>200 before drawing conclusions
- Two migrations: 033 adds four tracker audit columns (pick_filter_reason, model_take, model_take_reason, extra_sharp_data) silently dropped; 034 adds six OpticOdds CLV columns

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

## Related Concepts

- [[concepts/sharp-clv-theory-ranking]] - The scanner's own CLV ranking system that uses devigged blend CLV; the OpticOdds backfill provides a second CLV measure (raw Pinnacle) for cross-validation of theory performance
- [[concepts/opticodds-critical-dependency]] - OpticOdds as the single provider of sharp book data; the CLV backfill adds a new dependency surface (historical endpoint) beyond the existing real-time SSE feed

## Sources

- [[daily/lcash/2026-05-12.md]] - OpticOdds CLV via `/fixtures/odds/historical` with `olv`/`clv` objects; `/grader/odds` paid-tier 403; raw Pinnacle-only CLV (not devigged blend); 8.07pp mean absolute gap on 580 LAL@OKC picks; 4% match rate (40/1000) due to fixture name mismatches (349), unmapped markets (510), alt-line diffs (101); first 40 picks show 36% win rate when Pinnacle confirms vs 60% when flat; migration 034 adds 6 OpticOdds columns; migration 033 adds 4 silently-dropped tracker audit columns; two writers into nba_tracked_picks = architectural debt; PATCH error logging bucketed by cause (Sessions 14:22, 16:30)
