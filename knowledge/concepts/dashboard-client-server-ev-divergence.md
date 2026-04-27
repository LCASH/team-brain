---
title: "Dashboard Client-Server EV Divergence"
aliases: [client-side-ev, server-side-ev, ev-computation-mismatch, loadtheories-bug-fix, theory-name-exclusion]
tags: [value-betting, dashboard, bug, architecture]
sources:
  - "daily/lcash/2026-04-15.md"
  - "daily/lcash/2026-04-16.md"
  - "daily/lcash/2026-04-17.md"
  - "daily/lcash/2026-04-18.md"
  - "daily/lcash/2026-04-19.md"
  - "daily/lcash/2026-04-22.md"
  - "daily/lcash/2026-04-27.md"
created: 2026-04-15
updated: 2026-04-27
---

# Dashboard Client-Server EV Divergence

The value betting dashboard's "+EV Picks" tab computes EV live in the browser against all soft books (ignoring per-theory restrictions), while the server-side tracker respects each theory's `soft_books` filter when persisting picks. This architectural disconnect means the dashboard can show different EV values and different soft book comparisons than what the tracker used to trigger the pick. The root cause was a `loadTheories()` JavaScript mapping bug that silently dropped six theory fields, and the fix was deployed on 2026-04-15.

## Key Points

- Dashboard `computeEVForTheory()` falls back to global `SOFT_IDS` (all Australian soft books) when the theory's `soft_books` field is missing from the JS object
- Server-side tracker correctly applies per-theory `soft_books` when evaluating and persisting picks
- The Pinnacle theory appeared to work (showing EV against Ladbrokes, PointsBet AU) but should have been showing EV against prediction markets (Kalshi, Polymarket)
- Root cause: `loadTheories()` JS destructuring silently dropped `soft_books`, `prop_filter`, `max_line_gap`, `line_gap_penalty`, `max_line`, and `excluded_props` when mapping Supabase rows to JS objects
- Fix deployed 2026-04-15 as part of Pinnacle commit `9a0b19d` (5 files, +177/-28 lines): all theory columns now explicitly mapped in `loadTheories()`
- A recurring pattern: theory name-based exclusion for virtual pills (Pinnacle/Crypto Edge) was applied to the EV computation engine instead of only to the display layer, zeroing out NHL picks entirely and reducing MLB picks

## Details

### The Mismatch

The value betting scanner has two independent EV computation paths:

1. **Server-side (tracker)**: The tracker loads theory configurations every 5 minutes from Supabase, including `soft_books` (which soft bookmakers to evaluate against). When a theory's EV threshold is met for a specific soft book, the pick is persisted with `triggered_by` set to the theory name. This path correctly respects all theory parameters.

2. **Client-side (dashboard)**: The "+EV Picks" tab receives odds data via SSE and computes EV live in the browser using `computeEVForTheory()`. This function should use the theory's `soft_books` list to determine which soft books to show EV for. However, when the `soft_books` field is missing from the theory object (due to the `loadTheories()` mapping bug), it falls back to the global `SOFT_IDS` constant, which includes all Australian soft books.

The practical impact was that the Pinnacle theory — configured to evaluate prediction markets (Kalshi, Polymarket) against Pinnacle's sharp line — appeared on the dashboard with EV values computed against Ladbrokes, PointsBet AU, and other Australian retail books. The numbers looked plausible (they were real EV computations), but they were against the wrong set of soft books, defeating the purpose of the Pinnacle theory configuration.

### The loadTheories() Bug and Fix

The root cause is a JavaScript anti-pattern: when mapping database rows to objects using destructuring, any column not explicitly included in the mapping is silently discarded. The `loadTheories()` function was mapping theory rows from Supabase but did not include `soft_books`, `prop_filter`, `max_line_gap`, `line_gap_penalty`, `max_line`, or `excluded_props` in its destructuring. These fields were all silently dropped.

This is particularly dangerous because there is no error signal. The theory objects are constructed successfully, downstream functions receive them without complaint, and the fallback behavior (using global defaults) produces plausible-looking results. Only a human comparing the dashboard output against the theory configuration would notice the mismatch — in this case, lcash noticed that the Pinnacle pill was showing Australian soft books instead of prediction markets.

The fix was to explicitly map every theory column in the `loadTheories()` function. This is a maintenance burden: any future column added to the `nba_optimization_runs` table must also be added to the client-side mapping, or it will be silently ignored.

### Verification: Pinnacle Pipeline

After deploying the fix, the Pinnacle pipeline was verified end-to-end. Data was flowing: Polymarket (348 markets), Kalshi (168), Pinnacle (402) all visible on VPS. Zero Pinnacle picks were firing, but this was correct behavior — all NBA games were outside the 3-hour pre-tipoff window (today's games already tipped off, tomorrow's >24h out). No code change was needed; the pipeline would produce picks when games entered the actionable window.

### Deploy-Kills-All-Workers

A related operational discovery during the same session: deploying changes to the mini PC killed all running workers (push worker, AFL, MLB, NRL servers, betstamp worker) but only restarted the primary service (NBA server). This required manually restarting all ancillary services. The NRL scheduled task had also been disabled and needed re-enabling via `schtasks /Change /TN NRL_Server /Enable`. This is a deployment variant of the configuration drift pattern — the deploy process doesn't match the full production service set.

### Multiple Render Paths Anti-Pattern (2026-04-16)

A follow-on manifestation of the client-server divergence was discovered on 2026-04-16 when debugging the Pinnacle virtual pill. The dashboard's `renderStats()` and `renderEV()` functions both independently called `computeEVPicks()` — meaning there were two separate render paths invoking the same EV computation. Fixing the computation logic in one path (e.g., making `renderEV()` skip live computation for the Pinnacle pill) left the bug visible through the other path (`renderStats()` still calling the unfixed `computeEVPicks()`).

This is a generalization of the `loadTheories()` bug: when multiple code paths consume the same data or invoke the same computation, a fix to one path is insufficient. All entry points must be identified and patched simultaneously. The danger is that testing one path and seeing correct results creates false confidence that the fix is complete.

Additionally, a "Supabase Error" message displayed on the Pinnacle pill was traced to an error misattribution bug: a broad `try/catch` block wrapped both the Supabase data fetch AND the render logic. When the 3-way devig code path crashed during rendering (a JS error, not a network error), the catch block attributed it as a Supabase failure. The fix was to separate error boundaries — wrapping fetch and render in independent try/catch blocks so that render crashes are correctly identified rather than misattributed to the data layer.

## Related Concepts

- [[concepts/value-betting-theory-system]] - The theory system whose client-side consumption was broken by the loadTheories() bug
- [[concepts/one-sided-consensus-structural-bias]] - A different theory configuration bug with similarly invisible effects
- [[concepts/value-betting-operational-assessment]] - Weakness #2 (no monitoring) applies: the mismatch was discovered manually
- [[concepts/configuration-drift-manual-launch]] - Deploy-kills-all-workers is a deployment variant of the config drift pattern
- [[connections/operational-compound-failures]] - The silent field-dropping + no monitoring chain echoes the compound failure pattern
- [[concepts/pinnacle-prediction-market-pipeline]] - The Pinnacle pipeline whose verification exposed this bug; commit `9a0b19d` includes both the bug fix and prediction market book IDs
- [[concepts/crypto-edge-non-pinnacle-strategy]] - The Crypto Edge theories whose name-based exclusion compounded with Pinnacle exclusion to zero out NHL picks
- [[concepts/sse-display-tracking-market-separation]] - The display/tracking separation pattern; the theory exclusion bug is a related display-layer filtering issue
- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - Parallel pattern: sharp freshness cutoff (30s→120s) mirrors the VPS sharp data age threshold (60s→120s)

### Dashboard HTML Loss on VPS Restart (2026-04-17)

On 2026-04-17, lcash discovered that the dashboard HTML is lost on VPS restart because it is stored in-memory only. After any VPS restart, the dashboard must be re-pushed from the mini PC. The deploy script handles this automatically, but can fail if the VPS isn't fully booted when the push executes. This is a deployment fragility — the dashboard's rendered state is not persisted to disk, creating a dependency on the deploy script's timing relative to VPS boot sequence.

### Merge Conflict Artifacts (2026-04-17)

During a git rebase to sync local Pinnacle work with 10 remote commits, merge conflict resolution in `dashboard/index.html` left orphaned code blocks: a `books is not defined` JS error from duplicate filter bar code (inline HTML referencing variables not in scope) and an undefined `contentEl` variable (another merge artifact requiring `document.getElementById('td-content')`). This reinforces a general lesson: after resolving merge conflicts, always check for dangling references from the deleted branch — conflict markers show what was replaced, but don't flag code that referenced the deleted content from elsewhere in the file.

### Large Payload Browser Timeout (2026-04-17)

The Data tab loaded 60 days of resolved picks (21K picks, 11MB, 25 seconds) causing browser timeouts. Supabase returned the data successfully across 22 paginated pages (22 × 1000 rows), but browser-side JavaScript choked parsing the aggregated result. The fix reduced the default range to 7 days (~3 second load). This is a general pattern: large API responses that succeed at the network layer can fail at the browser parsing layer — server-side aggregation or tighter default ranges are needed when datasets grow beyond ~5MB.

### Theory Name Exclusion Overreach (2026-04-18)

On 2026-04-18, lcash discovered that multiple sport pills (MLB, AFL, NHL) were showing zero +EV picks despite SSE data flowing correctly (7,330 MLB markets, 611 AFL, 96 NHL — all at 17s freshness with both sharp and soft data). The root cause was an overly aggressive theory name exclusion filter in the dashboard's theory loading logic.

The dashboard excluded any theory with "Pinnacle" or "Crypto Edge" in the name from regular sport pills — intended to prevent duplicate picks between the virtual Pinnacle/Crypto Edge pills and the per-sport pills. However, for NHL, BOTH active theories ("NHL Pinnacle" and "NHL Crypto Edge") matched the exclusion, so **zero theories were loaded**, producing zero EV computations and zero picks. For MLB, "MLB Pinnacle" was excluded, reducing the available theories and lowering pick volume.

This exposed a critical architectural distinction: **display filtering vs. computation filtering**. Excluding theories from the picks *display* (to avoid showing the same pick on both the Pinnacle pill and the NHL pill) is legitimate and necessary. Excluding theories from the EV *computation engine's* theory loading prevents picks from ever being computed in the first place — a fundamentally different effect. The exclusion was applied at the wrong layer: it should only filter the display query (`triggeredByMatch` for stored picks), not the theory loading that drives `computeEVForTheory()`.

The rejected alternative was renaming theories (e.g., "NHL Pinnacle" → "NHL-P") to avoid matching the exclusion pattern. This would have broken the Pinnacle pill's `triggeredByMatch: 'Pinnacle'` filter, which relies on the theory name containing "Pinnacle" to select stored picks for the virtual pill. The correct fix was to remove theory name exclusion from the EV computation engine entirely, applying it only at the display layer.

A related finding in the same session: the VPS sharp data age threshold was raised from 60s to 120s. The mini PC's OpticOdds poller runs every ~60 seconds, so data arriving at the VPS was ~57s old — just below the previous 60s threshold. Slight timing variance caused some cycles to arrive at 61-63s and be silently discarded as stale. The 120s threshold accommodates the polling interval with comfortable margin.

Additionally, NRL showed zero markets across the SSE stream — either the NRL season is between rounds or the mini PC's NRL server (port 8801) is down. The VPS serves ALL sports on port 8802 via a single SSE stream; `switchSport` only changes client-side filtering, not the SSE connection. This single-stream architecture means sport pill bugs are always client-side filtering issues, never data availability issues — a useful diagnostic principle.

### True-Odds Display Inconsistency Across Soft Books (2026-04-19)

On 2026-04-19, lcash spotted the same bet (LOUD vs MIBR esports moneyline) showing different true odds on two soft books under the same Pinnacle theory: 4.44 on Kalshi vs 5.33 on Polymarket. Both are evaluated against Pinnacle's sharp line, so the true probability should be identical — yet the dashboard displayed different values.

The root cause is the dashboard's per-theory per-soft-book EV computation: `computeEVForTheory()` runs independently for each soft book row, devigging against whatever sharp data is freshest at the moment of that specific render cycle. If sharp data freshness varies between successive calls (e.g., Pinnacle's odds for this market were updated between the Kalshi and Polymarket render passes), different sharp book lines can be selected, producing different devigged true probabilities for the same underlying market.

Critically, trail data is completely unaffected by this display inconsistency. Trails store raw odds, and the server-side resolver devigs consistently using a single snapshot. The separation between the dashboard's ephemeral JavaScript computation (subject to render-cycle timing) and the server-side trail/resolver pipeline (persistent, consistent) is an architectural strength — the display may flicker, but the data of record is correct.

If this inconsistency becomes frequent, a fix would cache the devigged true probability per market (keyed by fixture + prop type + side + line) so all soft book rows reference the same computed value within a render cycle.

### Pick Flashing, Stale Odds, and `captured_at` Override (2026-04-22)

On 2026-04-22, lcash investigated multiple stacking dashboard bugs that manifested as picks "flashing" in and out while displaying stale odds. Five independent causes were identified: (1) SSE snapshot clearing on reconnect, (2) `reconcile_sport()` aggressive market removal, (3) stored Supabase picks carrying frozen `book_odds`, (4) market key format inconsistency (underscores in stored keys vs spaces in live keys), and (5) `captured_at` being overwritten with `time.time()` at VPS ingest (`state.py:2115`).

The `captured_at` override was the most critical bug: it made every market appear 5 seconds old, so the 5-min staleness filter never triggered, hiding the fact that OpticOdds sharp data was 111 minutes stale. The dashboard also lacked a **sharp book** staleness check — it only filters on soft book age, meaning picks computed from 2-hour-old sharp data display with confident EV%.

The market key format mismatch (`harrison_barnes_threes_under` in Supabase vs `harrison barnes_threes_under` in live API) caused the stored-vs-live dedup filter to fail, allowing both frozen and live versions of the same pick to appear simultaneously. This is the same class of format inconsistency documented in [[concepts/game-line-display-normalization]] (prop_type spaces vs underscores).

See [[concepts/dashboard-pick-flashing-stale-odds]] for the full multi-bug analysis and fixes (SSE merge instead of clear, reconcile_sport 60s grace period, 15-min isGameLive buffer, stored pick removal for SSE sports, captured_at override removal).

### Six-Dimension Dual-Codebase Computation Drift (2026-04-27)

On 2026-04-27, lcash performed a systematic audit between `dashboard/index.html` and `server/tracker.py`, tracing `findPair`, devig methods, Poisson interpolation, line-gap penalty, EV cap, odds-freshness, cross-validation, and `is_over` handling. Six specific dimensions where the implementations had drifted apart were identified and fixed:

1. **Poisson interpolation**: Dashboard fell back to logit for line gaps >1.0; backend always uses Poisson for count props. Logit inflates EV for count props with large gaps.
2. **Line-gap penalty**: Dashboard used "prob-shrink toward 0.5" which disproportionately inflates low-probability events; backend uses weight decay inside `computeTrueProb` — mathematically different.
3. **EV cap**: Dashboard had a hard 50% cap; backend has none. Dashboard hid extreme EVs that the backend tracked.
4. **Soft odds freshness**: Dashboard accepted odds up to 600s; backend rejected at 300s. Dashboard showed picks the backend already discarded as stale.
5. **Cross-validation check**: Dashboard was missing the sharp-vs-soft devig >5pp divergence filter that the backend uses to skip unreliable picks.
6. **`is_over` case sensitivity**: Dashboard checked `m.side === 'Over'` (case-sensitive); backend uses `.lower()` comparison. Non-standard case formats were misidentified.

This represents a new class of divergence beyond field-dropping (`loadTheories()`) and filtering confusion (theory name exclusion): the *same algorithm* implemented with *different assumptions* in two languages. See [[connections/dual-codebase-ev-computation-drift]] for the full analysis.

In the same session, the trail chart was also found to be using fundamentally different true-odds calculations than the table: the chart did raw devig without interpolation, while the table used `interpolateForProp()`. Under picks also had the devig arguments swapped (trail stores `odds` = this side, `u` = opposite, but `devigMultiplicative()` always expects Over first). Both were fixed. See [[concepts/per-theory-true-odds-display]] for the per-theory visualization redesign that emerged from this debugging.

Additionally, the MLB game scraper was discovered to be using `BET365_2_BOOK_ID = 365` (old betstamp ID) instead of 366 (Bet365 2.0), making all MLB game scraper data invisible on the dashboard because the dashboard filters for book 366.

## Sources

- [[daily/lcash/2026-04-15.md]] - Pinnacle theory showing AU soft books instead of prediction markets; `loadTheories()` dropping 6 fields via JS destructuring; client-side EV ≠ server-side EV divergence; fix deployed; zero Pinnacle picks correct (games outside 3h window); deploy killed all workers requiring manual restart; NRL scheduled task re-enable needed (Session 22:03/16:20+)
- [[daily/lcash/2026-04-16.md]] - Multiple render paths (`renderStats()` + `renderEV()`) both calling `computeEVPicks()` independently — fixing one left bug visible through the other; "Supabase Error" was actually a JS render crash misattributed by broad catch block wrapping fetch+render; error boundary separation deployed (Session 22:35)
- [[daily/lcash/2026-04-17.md]] - Dashboard HTML lost on VPS restart (in-memory only, re-push required); merge conflict artifacts leaving orphaned JS code (`books is not defined`, undefined `contentEl`); 21K picks / 11MB / 25s timeout → 7-day default range; deploy git sync guard blocks on uncommitted changes (Sessions 11:06, 16:09, 21:11)
- [[daily/lcash/2026-04-18.md]] - Theory name exclusion too aggressive: NHL had both theories excluded → 0 picks; MLB "MLB Pinnacle" excluded → fewer computations; critical distinction between display filtering and computation filtering; fix: exclude only from display query, not EV engine theory loading; sharp data age threshold 60s→120s for mini PC polling interval; VPS single-stream architecture confirmed (all sports on port 8802) (Session 21:50)
- [[daily/lcash/2026-04-19.md]] - True-odds display inconsistency: same bet (LOUD vs MIBR moneyline) showing different true odds (4.44 vs 5.33) on Kalshi vs Polymarket under the same Pinnacle theory; cause: sharp data freshness varies between render cycles → different sharp books selected for same market → different devigged true probability displayed; confirmed trail data unaffected (trails store raw odds, resolver devigs server-side consistently); separation between ephemeral dashboard JS computation and persistent server-side pipeline is an architectural strength (Session 07:26)
- [[daily/lcash/2026-04-22.md]] - Pick flashing from 5 stacking bugs: SSE snapshot clear-on-reconnect, reconcile_sport aggressive removal, frozen stored pick odds (Harrison Barnes 2.45 vs live 1.833), market key format mismatch (underscores vs spaces), `captured_at: time.time()` override at state.py:2115 masking 111-min sharp staleness; dashboard lacks sharp book staleness check (Sessions 09:42, 10:31, 11:06)
- [[daily/lcash/2026-04-27.md]] - Six-dimension dual-codebase drift audit: Poisson interpolation fallback removed, line-gap penalty changed from prob-shrink to weight-decay, EV cap removed, freshness tightened 600→300s, cross-validation check added, is_over case-insensitive; trail chart interpolation + Under devig arg swap fixed; MLB BET365_2_BOOK_ID was 365 instead of 366 making data invisible (Sessions 08:10, 08:45, 09:23, 11:34)
