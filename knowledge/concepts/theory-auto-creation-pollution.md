---
title: "Theory Auto-Creation Pollution"
aliases: [theory-pollution, rogue-theories, null-theory-names, auto-discovery-theory-leak, theory-hygiene]
tags: [value-betting, architecture, bug, supabase, operations, theory-system]
sources:
  - "daily/lcash/2026-05-02.md"
  - "daily/lcash/2026-05-03.md"
created: 2026-05-02
updated: 2026-05-03
---

# Theory Auto-Creation Pollution

The value betting scanner's `_auto_create_theories()` function creates Supabase theory rows for every league discovered via SSE auto-discovery. On 2026-05-02, this produced **647 broken theories** — 441 for non-basketball/baseball sports (inaccessible via the OpticOdds API key) and 206 with `NULL` theory names — that blocked the EV evaluation pipeline. Broken theories consumed tracker evaluation cycles, cluttered the database, and silently prevented `triggered_ev` from being populated on picks. The theories also recreated themselves on every server restart, requiring not just deletion but a code fix to the auto-creation whitelist.

## Key Points

- 647 broken theories accumulated: 441 non-basketball/baseball sports (API key doesn't cover them) + 206 with NULL `theory_name` (creation bug)
- Auto-discovery runs on startup, scanning 521 sports when only basketball + baseball are accessible — creating theories for inaccessible leagues wastes compute and pollutes the database
- Broken theories with NULL names prevented the tracker from assigning `triggered_ev` to picks — picks existed in Supabase but with NULL EV values
- Deleting bad theories isn't sufficient — they recreate on next restart unless the auto-creation logic is scoped to valid sports
- Fix required three actions: (1) delete 441 invalid theories, (2) restore core NBA/MLB theories from known working set, (3) scope `auto_discover_leagues` to basketball + baseball only
- Rogue non-BB league theories (china_cba, japan_b1_league, kbo, npb, vtb) also auto-recreated on restart; excluded from ACTIVE_SPORTS at lines 1103-1105 in main.py
- `max_hours_before_start` on NBA theories was set to default 3h, silently blocking games 16+ hours away — expanded to 48h

## Details

### The Pollution Mechanism

The SSE auto-discovery function (`_sse_startup()` → `_auto_create_theories()`) enumerates all leagues available from OpticOdds and creates a theory row in Supabase for each new league. This was designed for scaling: as OpticOdds adds leagues, the scanner automatically creates evaluation configurations without manual intervention. However, the function creates theories indiscriminately — it does not check whether the API key can access the sport, whether the league has sharp book coverage, or whether the theory name is valid.

The result is a database that accumulates junk theories over time. Each server restart triggers a fresh auto-discovery pass. If the invalid theories were deleted but the creation logic wasn't fixed, they would reappear on the next restart. This is a "whack-a-mole" anti-pattern: the symptom (junk data) can be treated repeatedly but never cured without fixing the source (indiscriminate auto-creation).

### Impact on Pick Generation

The tracker loads ALL active theories from Supabase regardless of sport scope. When evaluating a market, the tracker iterates through loaded theories and attempts to compute EV for each. Theories with NULL `theory_name` caused the evaluation loop to fail silently — the theory couldn't be matched to a devig configuration, so `triggered_ev` was never assigned. The pick was still created (it met the basic +EV criteria) but with NULL in the EV column, making it impossible to assess the edge size.

This created a confusing diagnostic picture: picks existed in Supabase, the tracker was cycling, but `triggered_ev` was uniformly NULL. The natural hypothesis was a pipeline bug in EV computation, when the actual root cause was broken theory metadata preventing the computation from being reached.

### Cascading Discovery: max_hours_before_start

While debugging the theory pollution, lcash also discovered that NBA theory `max_hours_before_start` was set to the default 3 hours. With NBA games scheduled 16+ hours in the future, all NBA markets were silently excluded from evaluation as "too early." This is the same time-window filtering issue documented in [[concepts/pick-trail-time-window-separation]], but for a different reason — there, TAB threshold markets needed 24h; here, standard NBA games needed coverage during off-hours.

The fix expanded `max_hours_before_start` to 48 hours for NBA theories, ensuring games are evaluated up to 2 days before tip-off.

### Null max_line_gap Theory Configuration

A related theory configuration issue was discovered in the same day: the "Calibrated-Live" theory had `max_line_gap=null`, which caused the tracker to require exact line matches between sharp and soft books. Since exact matches rarely occur (different books price at slightly different lines), this effectively rejected all pick evaluations for the theory. The fix was setting `max_line_gap=4.0` via Supabase to re-enable interpolation.

### Recurrence: Pinnacle MLB max_line_gap=NULL (2026-05-03)

On 2026-05-03, the identical `max_line_gap=NULL` bug recurred on the `Pinnacle MLB` theory. The tracker showed `last_picks=0` despite 3,684 MLB markets and 6 completed tracker cycles — the canonical symptom pattern established on 2026-05-02. The root cause was the same: bet365's lines (e.g., 0.5) didn't match sharp book lines (e.g., 1.5), and with `max_line_gap=NULL` the tracker required exact matches, silently rejecting all markets.

The fix was a Supabase patch: `max_line_gap: 4.0` on the Pinnacle MLB theory, following the established pattern. This marks the **third documented occurrence** of `max_line_gap=NULL` causing zero picks (Calibrated-Live on 2026-05-02, NBA theories on 2026-05-02, Pinnacle MLB on 2026-05-03), confirming it as a recurring misconfiguration hazard whenever new theories are created. The canonical diagnostic: `tracker.last_picks=0` with `cycles>0` and `markets>0` and no errors → check theory `max_line_gap` immediately.

### Prevention

Three layers of prevention were deployed:

1. **Scope auto-discovery** — `auto_discover_leagues` now only creates theories for basketball and baseball (the two sports the API key covers), reducing the discovery universe from 521 sports to 2
2. **Whitelist ACTIVE_SPORTS** — lines 1103-1105 in `main.py` exclude non-BB league keys from ACTIVE_SPORTS to prevent rogue theories from accumulating
3. **League filter on creation** — the filter prevents NEW bad leagues from being created, but does not retroactively clean historical pollution; explicit bulk DELETE was required for the existing 647 broken theories

A fourth prevention — validating theory_name is NOT NULL at creation time — was not implemented but would catch the NULL-name creation bug at the source.

## Related Concepts

- [[concepts/value-betting-theory-system]] - The theory system whose auto-creation mechanism produces the pollution; theories are powerful because they're code-free, but this flexibility allows invalid configurations to accumulate
- [[concepts/sse-startup-theory-creation-hang]] - The SSE startup bottleneck (266 sequential Supabase GETs) compounds with theory pollution: more theories = more GETs per startup = longer hangs
- [[concepts/opticodds-api-key-sport-scoping]] - The API key covering only basketball + baseball is the root reason why non-BB theories are useless; auto-creation doesn't check key scope
- [[concepts/pick-trail-time-window-separation]] - The `max_hours_before_start` parameter separation between pick creation and trail recording; the 3h→48h fix for NBA is the same pattern applied to a different context
- [[concepts/configuration-drift-manual-launch]] - Theory pollution is a database-level analog of batch file drift: configuration state that diverges from intended state without anyone noticing

## Sources

- [[daily/lcash/2026-05-02.md]] - 647 broken theories discovered (441 non-BB sports + 206 NULL names); auto-discovery creating theories for 521 sports when only 2 accessible; broken theories blocked triggered_ev assignment; deletion + theory restoration + auto-create scoping fix deployed; 198 stale picks referencing deleted theories cleaned (Session 16:49). NBA max_hours_before_start default 3h blocking games 16+ hours away; expanded to 48h; rogue non-BB league theories auto-recreating on restart; excluded from ACTIVE_SPORTS at lines 1103-1105 (Session 17:16). Calibrated-Live theory had max_line_gap=null silently rejecting all picks; fixed to 4.0 (Session 12:26)
