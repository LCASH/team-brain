---
title: "Dashboard Background Task Persistence Gap"
aliases: [dashboard-data-json-staleness, background-task-restart-gap, dashboard-update-loop, vps-restart-task-loss]
tags: [value-betting, dashboard, operations, architecture, bug]
sources:
  - "daily/lcash/2026-05-03.md"
created: 2026-05-03
updated: 2026-05-03
---

# Dashboard Background Task Persistence Gap

The VPS dashboard relied on `dashboard/data.json` to display picks, but this file was 25 days stale (last updated April 8) because no background task was continuously syncing live picks from Supabase to the file. When the VPS restarted, background tasks registered via `@app.on_event("startup")` or other lifecycle hooks were not automatically re-registered — the server started but the tasks that feed the dashboard were missing. The fix was a `_dashboard_update_loop()` background task that queries Supabase every 30 seconds and writes to `data.json`.

## Key Points

- `dashboard/data.json` was **25 days stale** (last updated April 8) — the dashboard showed no MLB picks despite 877+ picks in Supabase with valid EV data
- VPS restarts do NOT automatically restart background tasks — they need explicit startup logic; the server process starts but supplementary data-writing tasks are lost
- Fix: `_dashboard_update_loop()` task queries Supabase picks every 30 seconds and writes to `data.json` with the `ev_picks` key format the dashboard expects
- The initial fix attempt failed silently because the Supabase query referenced a non-existent `theory_name` column — the query succeeded but returned no matching rows
- Dashboard has two loading paths: stored picks from Supabase (via `data.json`) OR computed picks from live matched markets (via SSE) — the `data.json` path was broken
- Sport filtering was also broken: NBA picks appeared in MLB queries, suggesting mixed sport data in the picks table or missing sport filter in the query

## Details

### The Staleness Discovery

On 2026-05-03 (Session 12:12), lcash investigated why MLB picks were not appearing on the dashboard despite active pick generation confirmed in Supabase. The root cause was that `dashboard/data.json` — the file the dashboard reads for pick display — was last written on April 8, twenty-five days earlier. The VPS had been restarted multiple times since then, but no background task was re-registered to keep the file current.

This is a specific instance of a general pattern: VPS restarts lose in-memory state and registered tasks. The FastAPI server restarts cleanly (binds to port, responds to HTTP, processes push payloads), but supplementary tasks — like periodically writing Supabase query results to a file — must be explicitly re-registered on startup. Without explicit startup logic, the task simply doesn't exist after a restart.

### Two Dashboard Data Paths

The dashboard loads pick data through two independent paths:

1. **Live computation path (SSE)**: The SSE stream delivers real-time matched market data. The dashboard's `computeEVForTheory()` runs client-side JavaScript to compute EV from these live markets. This path works for NBA/MLB when SSE data is flowing.

2. **Stored picks path (`data.json`)**: For historical picks, non-SSE sports, and display of tracked/resolved picks, the dashboard reads from `data.json`. This file must be periodically refreshed with current Supabase data.

When path 2 is stale but path 1 is working, the dashboard may appear partially functional — live picks compute correctly, but historical picks and certain views show nothing. The 25-day-stale `data.json` meant the stored picks path was completely broken for any pick created after April 8.

### Silent Query Failure

The initial `_dashboard_update_loop()` fix failed silently because the Supabase query included a `theory_name` column that doesn't exist in the picks table. Supabase returned an empty result set (no error, just no rows) because the query was syntactically valid but referenced a non-existent column in the SELECT clause. This is a specific instance of the "plausible wrong output" pattern: the query succeeded at the protocol level but produced zero results, which looks like "no picks exist" rather than "query is malformed."

After fixing the column reference and reformatting the output to use the `ev_picks` key that the dashboard JavaScript expects, picks began appearing within 30 seconds.

### Games Tab Feature

In the same session (17:35), a Games tab dashboard feature was implemented with market grouping by game, soft/sharp book highlighting, and cross-bookmaker player prop comparison. The feature was deployed to the VPS but showed empty because the mini PC aggregator had stopped responding (port 8899 failure), leaving zero market data on the VPS. The feature itself is working — the data pipeline failure is upstream.

### EV Display Artifacts

During debugging (Session 16:47), picks in `data.json` showed 990%+ EV values that appeared to be data corruption. Investigation confirmed these were display artifacts from the initial malformed query — actual Supabase picks have correct 1-3% EV values. The `ev_picks` key format expected by the dashboard differs from the raw picks structure the initial writer was outputting, causing the dashboard to read wrong fields as EV values.

## Related Concepts

- [[concepts/dashboard-client-server-ev-divergence]] - The broader chronicle of dashboard data display issues; this staleness gap is a new variant: not wrong computation but missing data entirely
- [[concepts/vps-sse-cascade-silent-crash]] - VPS crashes lose all in-memory state; the background task persistence gap is the specific consequence for dashboard data
- [[concepts/value-betting-operational-assessment]] - Weakness #6 (no redundancy/auto-recovery) — VPS has no mechanism to verify that supplementary tasks are running after restart
- [[concepts/unified-odds-aggregator-pipeline]] - The aggregator provides real-time market data (path 1); `data.json` provides historical picks (path 2); both paths must work for complete dashboard functionality
- [[connections/operational-compound-failures]] - Stale data.json (25 days) + no alerting + misleading partial functionality compounds diagnosis difficulty

## Sources

- [[daily/lcash/2026-05-03.md]] - `dashboard/data.json` 25 days stale (last updated April 8); VPS restarts don't restart background tasks; `_dashboard_update_loop()` added querying Supabase every 30s; initial query failed silently on non-existent `theory_name` column; output reformatted to `ev_picks` key; 990%+ EV display artifacts from wrong key format (Session 12:12). Sport filtering broken: NBA picks in MLB queries (Session 16:47). Games tab feature deployed but empty due to mini PC aggregator failure on port 8899 (Session 17:35)
