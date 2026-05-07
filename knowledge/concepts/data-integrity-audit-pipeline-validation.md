---
title: "Data Integrity Audit and Pipeline Validation Placement"
aliases: [data-integrity-audit, unicode-normalization-pipeline, soft-book-id-validation-bug, defensive-code-placement, pipeline-validation-ordering]
tags: [value-betting, data-quality, bug, resolver, architecture, unicode]
sources:
  - "daily/lcash/2026-05-02.md"
created: 2026-05-02
updated: 2026-05-02
---

# Data Integrity Audit and Pipeline Validation Placement

On 2026-05-02, a comprehensive data integrity audit identified and fixed 8 issues across 5 critical files in the value betting scanner (resolver, interpolate, tracker, prop config, sport_config). The most impactful finding was that a defensive validation check for `soft_book_id` — placed too early in the pick generation pipeline — broke ALL pick generation by checking for a field that hadn't been populated yet. The audit also introduced Unicode NFD decomposition for player name matching, fixing silent failures with diacritics (Jokic) and curly apostrophes (O'Sharpe). The key lesson: defensive code must be placed after the data it validates has been populated, not before.

## Key Points

- **8 issues fixed across 5 files**, ranked by severity: 3 HIGH (silent failures), 2 MEDIUM (edge cases), 3 LOW (cleanup/dead code)
- **soft_book_id validation placed too early** broke ALL pick generation — the check was in `compute_ev_picks()` output processing, before the tracker's loop populated `soft_book_id` from iteration context; reverted in commit `10fae2d`
- **Unicode NFD decomposition**: player names with diacritics (Jokic, Doncic) now correctly normalize via `unicodedata.normalize('NFD')` + stripping combining marks (category "Mn") + transliteration for accented characters
- **Curly apostrophes** in player names ('O'Sharpe) were silently failing — standard `replace("'", "")` doesn't catch curly quote variants
- **Naive datetime TypeError**: resolver had `datetime.utcnow()` (naive) compared against timezone-aware timestamps, causing intermittent `TypeError` in date filtering
- **Duplicate PROP_TO_STAT dict** removed — was defined in both prop_config and sport_config; consolidated to single source of truth in sport_config
- Previous last-name-only matching bug motivated the full audit; all fixes are defensive/silent-failure prevention

## Details

### The soft_book_id Validation Catastrophe

The most severe issue was a defensive check intended to catch missing `soft_book_id` values. The check was added to prevent downstream bugs where picks without a soft book reference could corrupt analytics. However, it was placed in the wrong location: inside the output processing of `compute_ev_picks()`, which runs before the tracker's evaluation loop populates `soft_book_id` from its iteration context (the loop iterates over soft books, setting the ID for each).

The result was that every pick from `compute_ev_picks()` failed the validation check — `soft_book_id` was always missing at that stage because it hadn't been assigned yet. The tracker logged "0 inserts, 0 updates" on every cycle, producing zero picks despite 178 live markets (50 NBA, 124 MLB). The failure was completely silent: no error was raised, the check simply prevented picks from proceeding.

The fix was immediate reversion (commit `10fae2d`). The `soft_book_id` field is guaranteed present from the loop context — it's part of the iteration variable, not the EV engine output. The validation was not relocated because the field's presence is architecturally guaranteed: the tracker iterates `for book_id in soft_books:` and every pick generated within that loop inherits the book_id.

This is a general anti-pattern: **defensive validation that checks for the presence of data before the data has been populated transforms a zero-risk field into a total pipeline blocker.** The check would have been correct if placed after the loop assigns the book_id, but the original placement checked the field before it existed.

### Unicode Normalization

Player name matching is critical for the resolver (grading picks against outcomes), trail recording (matching trail entries to picks), and cross-book deduplication. Three unicode issues were identified:

**1. Diacritics (HIGH severity):** Players like Nikola Jokic (officially Jokić) and Luka Doncic (Dončić) have names with combining diacritical marks in some data sources but not others. OpticOdds may return "Jokić" while the tracker stored "Jokic". The fix applies NFD (Normalization Form D) decomposition, which separates base characters from combining marks, then strips characters in Unicode category "Mn" (Mark, Nonspacing). This converts "Jokić" → "Jokic" reliably.

**2. Accented character transliteration (HIGH severity):** Previous code was deleting accented characters entirely instead of transliterating them. "René" became "Rn" instead of "Rene". The fix uses proper transliteration that maps accented characters to their unaccented equivalents.

**3. Curly apostrophes (MEDIUM severity):** Player names with apostrophes (O'Shaughnessy, D'Angelo) sometimes arrive with curly/smart quotes (' U+2019) instead of straight apostrophes (' U+0027). Standard `replace("'", "")` only catches the straight variant. The fix normalizes all apostrophe variants before stripping.

### Naive Datetime Guard

The resolver's date filtering logic compared `datetime.utcnow()` (which returns a naive datetime without timezone info) against timezone-aware timestamps from Supabase. Python raises `TypeError` on direct comparison of naive and aware datetimes. This produced intermittent failures depending on whether the comparison operands happened to have matching timezone awareness — a non-deterministic bug that's difficult to reproduce.

The fix ensures all datetime objects are timezone-aware, consistent with the pattern established in [[concepts/odds-staleness-pipeline-diagnosis]] where `datetime.utcnow()` was already identified as a latent timezone bug.

### Full Issue Inventory

| ID | Severity | File | Issue | Fix |
|----|----------|------|-------|-----|
| H1 | HIGH | resolver.py | Unhandled stat derivation errors silently skipping picks | try/except with logging |
| H2 | HIGH | resolver.py | Unicode diacritics in player names (Jokić) | NFD decomposition |
| H3 | HIGH | interpolate.py | Accented chars deleted instead of transliterated | Proper transliteration |
| M1 | MEDIUM | resolver.py | Naive datetimes causing intermittent TypeError | Timezone-aware guards |
| M2 | MEDIUM | tracker.py | Inconsistent player name stripping between REST/SSE paths | `.strip()` on both paths |
| L1 | LOW | sport_config.py | Duplicate PROP_TO_STAT dict | Consolidated to single source |
| L2 | LOW | prop_config.py | Dead code (orphaned prop definitions) | Removed |
| L3 | LOW | tracker.py | Silent soft_book_id default to 365 | **Raised error → REVERTED** |
| L4 | LOW | various | Inconsistent import paths | Cleaned up |

### The Backend-vs-Frontend Blind Spot

After deploying all 8 fixes, the dashboard still showed 0 markets. Investigation revealed the fixes were solving the wrong problem: the backend had 174 markets with sharp books, but zero soft books (Bet365/book_id 365) were present. Without soft book data, the EV engine has nothing to compare sharp lines against — all the data integrity fixes were correct but irrelevant without the upstream data source.

This illustrates a diagnostic ordering principle: **verify end-to-end data flow (source → pipeline → display) before auditing code correctness.** The audit was valuable for long-term reliability, but the immediate blocker was operational (Bet365 scraper not sending data to VPS), not code-level.

## Related Concepts

- [[concepts/odds-staleness-pipeline-diagnosis]] - The `datetime.utcnow()` naive timezone bug was first documented here; the resolver fix is the same pattern applied to a different file
- [[concepts/pick-id-float-int-hashing-bug]] - Another silent type-handling bug that broke trail collection; the unicode normalization fixes address the name-matching equivalent
- [[connections/silent-type-coercion-data-corruption]] - The soft_book_id validation catastrophe is a new variant: not type coercion but validation placement producing the same "plausible zero output" failure mode
- [[concepts/tracker-optimistic-id-poisoning]] - The staged IDs pattern (commit only after confirmed operation) is conceptually related to validation placement: both are about ordering defensive code relative to the operation it protects
- [[concepts/bet365-session-login-detection-gap]] - The "0 markets despite fixes" discovery reinforces this concept: upstream data source availability is the first diagnostic, not downstream code correctness

## Sources

- [[daily/lcash/2026-05-02.md]] - 8 data integrity issues identified and deployed (H1-H3 silent failures, M1-M2 edge cases, L1-L4 cleanup); Unicode NFD decomposition for diacritics + transliteration tested with "Jokić" → "jokic"; soft_book_id validation broke ALL picks — field checked before populated from loop context, reverted commit 10fae2d; tracker resumed generating picks immediately after revert; 178 live markets (50 NBA, 124 MLB) available but 0 soft books present on VPS — backend fixes correct but irrelevant without upstream Bet365 data (Sessions 22:32, 22:38, 23:02)
