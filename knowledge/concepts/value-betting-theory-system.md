---
title: "Value Betting Theory System"
aliases: [theory-system, nba-optimization-runs, data-driven-theories]
tags: [value-betting, architecture, supabase, configuration]
sources:
  - "daily/lcash/2026-04-13.md"
  - "daily/lcash/2026-04-14.md"
  - "daily/lcash/2026-04-15.md"
created: 2026-04-13
updated: 2026-04-15
---

# Value Betting Theory System

The value betting scanner's theory system is fully data-driven: theories are rows in the `nba_optimization_runs` Supabase table, cached every 5 minutes by the tracker. New betting theories — with custom sharp weights, devigging methods, EV thresholds, prop filters, and soft book filters — can be created entirely through database inserts with zero backend code changes.

## Key Points

- Theories are rows in `nba_optimization_runs` Supabase table, not code — no deployment needed to add or modify theories
- The tracker caches theories every 5 minutes, so changes propagate automatically without restart
- Configurable parameters per theory: sharp weights, devig method, EV threshold, prop filters (`prop_filter`), soft book filters (`soft_books`), max line gap (`max_line_gap`), line gap penalty (`line_gap_penalty`), max line (`max_line`), and excluded props (`excluded_props`)
- Only genuinely new devig algorithms or new filter types require backend code changes
- Dashboard `loadTheories()` must explicitly map every Supabase column to JS objects — missing fields are silently dropped, causing fallback to global defaults

## Details

### Architecture

The theory system decouples betting strategy configuration from code deployment. Each theory row in Supabase defines a complete set of parameters for evaluating expected value: which sharp books to weight and how, which devigging method to use (e.g., multiplicative, power, additive), what EV threshold triggers a pick, which prop types to include or exclude, and which soft books to evaluate against. The tracker loads these rows into memory every 5 minutes and applies each theory independently to every market, generating picks that are tagged with their originating theory.

This architecture means the team can experiment with new betting strategies — different EV thresholds, different sharp weighting schemes, different prop type filters — by simply inserting or updating rows in Supabase. The feedback loop from theory creation to live picks is at most 5 minutes, with no code changes, no deployments, and no restarts required.

### The `soft_books` Client-Side Bug

A dashboard bug illustrates the coupling between the theory system and its consumers. The `loadTheories()` function in the dashboard JavaScript was mapping Supabase theory rows to JS objects using destructuring that did not include `soft_books`, `prop_filter`, `max_line_gap`, `line_gap_penalty`, `max_line`, or `excluded_props`. These fields were silently dropped, causing `computeEVForTheory()` to fall back to the global `SOFT_IDS` (all Australian soft books) instead of the theory's configured soft book list. This made the Pinnacle theory pill show Ladbrokes/PointsBet instead of the intended Kalshi/Polymarket prediction markets. The fix required explicitly mapping every theory column in the client-side code.

**Fix deployed (2026-04-15):** All six missing fields are now explicitly mapped in `loadTheories()`. Verified: Pinnacle pill correctly filters to prediction markets (Kalshi 168, Polymarket 348 markets visible). This also exposed a deeper architectural issue: the dashboard's "+EV Picks" tab computes EV live in the browser against all soft books (ignoring theory restrictions), while the server tracker respects per-theory `soft_books`. This means client-side and server-side EV can diverge — see [[concepts/dashboard-client-server-ev-divergence]] for full analysis.

This is a general JavaScript anti-pattern: when mapping database rows to objects, any new column added to the source table must be explicitly included in the mapping. Silent field-dropping produces no error — the object simply lacks the field, and downstream code falls back to defaults without warning.

### Scope of Code-Free Configuration

The following can be changed without code: adding a new theory with custom parameters, changing an existing theory's EV threshold or sharp weights or prop filters, enabling/disabling theories via an active flag, and targeting specific soft books per theory.

The following requires code changes: new devigging algorithms (new math, not just parameter changes), new filter types (e.g., a filter dimension not yet supported in the schema), and changes to how the tracker applies theories to markets.

### Theory Proliferation and Audit (2026-04-14)

An audit of the `nba_optimization_runs` table on 2026-04-14 revealed 6 active AFL theories — not the 2 that were assumed to exist. Three targeted Goals markets and three targeted Disposals. Of the six, four used the `one_sided_consensus` devig method, which structurally skips all Under selections (see [[concepts/one-sided-consensus-structural-bias]]). Combined with alphabetical theory ordering for `triggered_by` attribution, broken theories hijacked pick attribution from correct ones.

The audit resulted in deactivating 5 of 6 theories: 3 Goals theories (calibration proved -28.9% best case across 6,180 combinations), `AFL Disposals` (wrong devig method), and `AFL Disposals OLV` (legacy near-duplicate of `AFL Disposals 5-Book` differing by one book: BetRivers 802 vs TAB 908). A new `AFL Disposals Net Cast` theory was inserted with liberal parameters (min_ev=1, multiplicative/poisson, books 900/901/903/908/911) for forward data capture and offline variant replay.

This experience highlights a gap in the theory system: no monitoring or audit mechanism exists to flag theory proliferation, detect structurally broken methods, or validate that theories are calibrated against actual outcomes.

### theory_evs Column Extension

A `theory_evs JSONB` column was planned for `nba_tracked_picks` to store each theory's computed EV at trigger time. This addresses a limitation of the `triggered_by` field, which records only the first alphabetical theory that fires for a given pick ID. See [[concepts/pick-dedup-multi-theory-limitation]] for the full design.

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - Sharp odds from OpticOdds feed the devigging step that theories configure
- [[concepts/alt-line-mismatch-poisoned-picks]] - Theory parameters like `max_line_gap` directly control whether alt-line mismatches produce poisoned picks
- [[concepts/value-betting-operational-assessment]] - The system assessment context in which theories were reviewed
- [[concepts/one-sided-consensus-structural-bias]] - The `one_sided_consensus` method's structural Over-only bias, discovered during AFL theory audit
- [[concepts/pick-dedup-multi-theory-limitation]] - Pick dedup architecture that limits multi-theory A/B testing
- [[concepts/afl-circular-devig-trap]] - How theories configured with non-sharp books produce circular devig
- [[concepts/dashboard-client-server-ev-divergence]] - Client-side EV computation diverges from server-side when theory fields are missing

## Sources

- [[daily/lcash/2026-04-13.md]] - Confirmed theories require NO backend code changes; configurable via Supabase rows with sharp weights, devig method, EV threshold, prop filters, soft book filters; cached every 5 min; only new devig algorithms or filter types need code (Sessions 08:50, 09:32). Dashboard `loadTheories()` bug dropping `soft_books` and other fields confirmed in session context.
- [[daily/lcash/2026-04-14.md]] - Theory audit: 6 active AFL theories found (not 2); 4 used `one_sided_consensus` (Over-only); 5 deactivated; net cast theory inserted; theory_evs JSONB column planned for multi-theory EV persistence (Sessions 14:31, 16:02)
- [[daily/lcash/2026-04-15.md]] - `loadTheories()` bug fix deployed: all 6 missing fields now mapped; Pinnacle pill verified showing Kalshi/Polymarket instead of AU soft books; client-side vs server-side EV divergence identified (Session 22:03/16:20+)
