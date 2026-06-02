---
title: "bet365 MLB Market ID Stamping Gap"
aliases: [mlb-market-id-gap, mlb-mi-field-missing, mlb-wizard-mi-stamping, mlb-stable-id-coverage]
tags: [value-betting, bet365, mlb, scraping, data-quality, bug]
sources:
  - "daily/lcash/2026-05-30.md"
created: 2026-05-30
updated: 2026-05-30
---

# bet365 MLB Market ID Stamping Gap

The bet365 MLB wizard parser (`ws_mlb_v4.py`) was missing the `MI` (Market ID) field stamping code path that the NBA wizard parser (`ws_nba.py`) already has. The NBA parser tracks a `current_mi` state variable that reads `MI` from `MA` (Market Area) segments and passes it to each `ScrapedOdds()` constructor. The MLB parser never read the `MI` field, resulting in **0% stable-ID coverage** for all MLB markets — every MLB market had an empty `market_id` field. The fix is approximately 6 lines of code mirroring the NBA pattern.

## Key Points

- `ws_mlb_v4.py` never reads the `MI` field from `MA` segments — NBA's `ws_nba.py` does this with a `current_mi` state variable that MLB lacks
- **0% stable-ID coverage** for all MLB markets vs NBA's existing MI-stamped markets
- Fix is ~6 LOC: (1) add `current_mi: str = ""` state variable, (2) reset on new EV section, (3) extract MI from MA segments, (4) pass `market_id=current_mi` to both `ScrapedOdds()` constructors
- Companion SQL fix for phantom >100% EVs: `max_ev_if_sharps_gte` SQL cap set to `{"sharps_gte": 1, "max_ev": 50}` on MLB 4-Book Power theory — blocks 186-476% phantom picks while letting real 3-20% EV through
- The `max_ev_if_sharps_gte` filter already existed in `tracker.py:1403-1408` — the SQL change requires no code deploy, takes effect on next theory reload
- Discovered during a `/VB-V3-Healthcheck` full sweep that audited per-sport scraper coverage

## Details

### The MI Field Gap

The bet365 BB wizard response contains `MA` (Market Area) segments that carry an `MI` (Market ID) field — a stable identifier for each market group within a fixture. The NBA parser (`ws_nba.py`) correctly tracks this field via a state machine pattern: when the parser enters a new `MA` segment and finds an `MI` field, it stores the value in `current_mi`. All subsequent `ScrapedOdds()` objects created within that MA inherit `market_id=current_mi`.

The MLB parser (`ws_mlb_v4.py`) was written without this state tracking. The `MI` field exists in MLB wizard responses but is never read or passed to `ScrapedOdds()`. This means every MLB market has `market_id=""` or `None`, preventing any downstream consumer from using stable market IDs for deduplication, change detection, or cross-session market tracking.

### The Fix

Four targeted changes mirror the NBA pattern:

1. **State variable**: Add `current_mi: str = ""` alongside existing `current_fi` state variable
2. **Reset on new EV section**: When entering a new EV section (market group), reset `current_mi = ""` to prevent bleed between sections
3. **Extract from MA**: When processing an `MA` segment, check for `MI` field: `mi = f.get("MI", ""); if mi: current_mi = mi`
4. **Pass to constructors**: Both `ScrapedOdds()` call sites receive `market_id=current_mi`

No behavioral change beyond populating a previously-empty field. Downstream consumers (diff cache, DataStore, tracker) that check `market_id` will start receiving values where they previously received empty strings.

### Companion: Phantom >100% EV Cap

The same healthcheck session revealed 453 one-sided EV >100% picks in 24 hours — the known "anytime hit → 3+ hits" extrapolation phantom pattern where one-sided devig on counting-stat milestones produces massively inflated EV values. Rather than a code change, a zero-deploy SQL fix was applied using the existing `max_ev_if_sharps_gte` filter in `tracker.py:1403-1408`:

```sql
UPDATE public.nba_optimization_runs
SET weights = jsonb_set(
    weights,
    '{max_ev_if_sharps_gte}',
    '{"sharps_gte": 1, "max_ev": 50}'::jsonb
)
WHERE name = 'MLB 4-Book Power';
```

With `sharps_gte: 1` (always true since all picks have at least 1 sharp), this caps maximum accepted EV at 50% — blocking all 186-476% phantom picks while allowing legitimate 3-20% EV through. The filter is theory-specific (only MLB 4-Book Power) and takes effect on the next 5-minute theory cache refresh with no code deployment required.

### Discovery Context

Both issues were surfaced during a comprehensive `/VB-V3-Healthcheck` full sweep on 2026-05-30. The healthcheck skill audits per-sport scraper coverage, market counts, staleness metrics, and anomaly detection. The MLB `market_id` gap was identified when the stable-ID coverage metric showed 0% for MLB vs the expected ~80%+ for NBA. The phantom EV cohort was flagged by the one-sided EV anomaly detector (threshold: >20 picks with >100% EV in 24 hours).

## Related Concepts

- [[concepts/bet365-mlb-wizard-first-regression-fix]] - The MLB wizard endpoint that the MI field should be extracted from; the wizard-first architecture is the data source for this fix
- [[concepts/bet365-nba-bb-wizard-v3-rewrite]] - The NBA wizard parser that already has the `current_mi` state tracking — the pattern to mirror
- [[concepts/co-milestone-one-sided-pairing-imbalance]] - The one-sided milestone market structure that produces the phantom >100% EVs capped by the SQL fix
- [[concepts/value-betting-theory-system]] - The theory system's `weights` JSONB column that carries the `max_ev_if_sharps_gte` configuration — enables zero-deploy behavioral changes
- [[concepts/self-evolving-operational-skill]] - The `/VB-V3-Healthcheck` skill that surfaced both issues during routine health auditing

## Sources

- [[daily/lcash/2026-05-30.md]] - V3 healthcheck found MLB market_id 0% coverage vs NBA; `ws_mlb_v4.py` never reads MI field; ~6 LOC fix mirroring NBA's `current_mi` pattern; companion SQL cap `max_ev_if_sharps_gte: {sharps_gte: 1, max_ev: 50}` on MLB 4-Book Power blocks 186-476% phantom EVs; 453 one-sided >100% EV picks in 24h; BetIT MLB showing 0 markets flagged for investigation (Session 09:44, 09:54)
