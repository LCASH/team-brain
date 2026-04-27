---
title: "SSE Startup Theory Creation Hang"
aliases: [sse-startup-hang, theory-creation-bottleneck, sequential-supabase-gets, sse-stream-launch-block, auto-create-theories-bottleneck]
tags: [value-betting, operations, sse, supabase, scaling, bug]
sources:
  - "daily/lcash/2026-04-20.md"
  - "daily/lcash/2026-04-24.md"
  - "daily/lcash/2026-04-27.md"
created: 2026-04-20
updated: 2026-04-27
---

# SSE Startup Theory Creation Hang

The value betting scanner's `_sse_startup()` function performs auto-discovery of leagues and creates Supabase theories for each new league via sequential GET requests — approximately 299 individual database calls. This sequential theory creation phase can silently hang, blocking the SSE stream launch and fixture cache initialization phases that follow it. The system shows the SSE task as "alive" but zero streams are actually running, producing no data for the tracker.

## Key Points

- `_sse_startup()` auto-discovers ~299 leagues and creates Supabase theory rows via sequential GETs (~0.2s each = ~60s total, but can hang indefinitely)
- The hang occurs AFTER theory creation completes but BEFORE SSE streams or fixture cache launch — the function silently stops progressing with no error logged
- System health checks show the SSE startup task as "alive" — the failure is invisible without inspecting whether streams are actually running
- The fix on 2026-04-20 was a full VPS service restart, which brought 18/18 SSE streams online cleanly
- On 2026-04-18, the same bottleneck was identified: 0.2s × 462 theories = ~90s of serial Supabase GETs (see [[concepts/fixture-cache-silent-market-dropout]])
- Multiple restart attempts were needed before streams came online cleanly, suggesting the hang may be non-deterministic

## Details

### The Failure Mode

The SSE startup sequence has three phases that execute in order:

1. **Auto-discovery + theory creation** — calls `/leagues/active` to discover all available leagues, then checks/creates a Supabase theory row for each new league via individual GET requests
2. **Fixture cache initialization** — fetches active fixtures for all sports to build the fixture-to-team mapping cache
3. **SSE stream launch** — opens ~18 persistent SSE connections to OpticOdds for real-time odds streaming

When phase 1 hangs, phases 2 and 3 never execute. The system has auto-discovered leagues and created theories, but no streams are running to receive odds data, and no fixture cache exists to map incoming data to fixtures. The tracker has no data to evaluate, and the dashboard shows stale or empty state.

The failure is particularly insidious because the SSE startup task itself shows as "alive" in process monitoring. The task is running — it's just stuck after phase 1 with no progress indicator or timeout. An operator checking process health sees "SSE: alive" and assumes streams are running.

### Discovery on 2026-04-20

On 2026-04-20, lcash investigated why the VPS was not producing picks and discovered the tracker had been killed by a syntax error (see [[concepts/deploy-syntax-validation-gap]]) and the SSE startup had hung after theory creation. After fixing the syntax error and restarting the service, the SSE startup completed successfully: auto-discovery found 299 leagues, created 2 new Pinnacle theories, and launched 18/18 SSE streams with the fixture cache alive.

However, reaching this clean state required multiple restart attempts. The first restart may have triggered the same hang before streams came online. This suggests the hang is non-deterministic — possibly related to Supabase connection pool exhaustion after 299 sequential requests, or a race condition in the startup sequence.

### Scaling Context

The sequential theory creation pattern was previously identified as a scaling concern in [[concepts/fixture-cache-silent-market-dropout]]: 0.2s × 462 theories = ~90s of serial Supabase GET requests on first deployment. On subsequent starts, the check is instant because theories are cached. But the first deployment after adding new leagues (or after a database migration) is painful.

The SSE startup hang is a more severe manifestation: not just slow, but potentially indefinitely stuck. The serial request pattern creates two risks: (1) total latency scales linearly with league count, and (2) any single request that hangs (network timeout, Supabase rate limit, connection pool exhaustion) blocks all subsequent initialization.

### Recommended Fixes

1. **Batch theory checking** — replace 299 individual GETs with a single query (`SELECT name FROM theories WHERE name IN (...)`) to check existence, followed by a single bulk insert for missing theories
2. **Timeout on `_sse_startup()`** — add a global timeout so the system can detect and recover from hangs rather than waiting indefinitely
3. **Parallelization** — if individual GETs must be retained, run them concurrently with `asyncio.gather()` bounded by a semaphore to respect rate limits
4. **Phase separation** — decouple theory creation from stream launch so that a theory creation failure doesn't block streaming

### SSE_SPORTS Filtering and API Key Discovery (2026-04-24)

On 2026-04-24, lcash discovered that the SSE startup's auto-discovery was creating theories for 432 leagues — all against an API key that only covers NBA basketball. The 22 non-basketball SSE streams all failed with 400 "not enabled for your API key." This means the 5+ minute startup delay was entirely wasted compute for inaccessible sports.

An `SSE_SPORTS` environment variable was added to `server/main.py` to filter which sports get SSE streams. It was set to all sports (not just basketball) so that when the API key is upgraded, streams auto-activate without code changes. Failed connections silently retry with no harm. See [[concepts/opticodds-api-key-sport-scoping]] for the full API key audit.

Additionally, the auto-resolver and SSE startup running simultaneously after a VPS restart can flood the OpticOdds API, causing SSE streams to get stuck. A 5-minute startup delay was added to the auto-resolver to stagger the load.

### Recurrence: 266 Sequential Calls Killing SSE Pipeline (2026-04-27)

On 2026-04-27, the `_auto_create_theories` bottleneck resurfaced across two separate debugging sessions. In Session 17:03, lcash identified that the VPS's `_auto_create_theories` function was making 266 sequential Supabase calls — one per league — and this either timed out or hit rate limits, silently killing the entire SSE pipeline. No SSE streams came online, leaving all international leagues (KBO, NPB, Euroleague, Spain ACB, Argentina LNB) without data despite being correctly configured.

In Session 22:19, the same issue was confirmed as the root cause of VPS SSE failure: `_auto_create_theories` consumed all available Supabase connection capacity, causing the SSE stream launch phase to never execute. The VPS SSE was confirmed broken while VPS health checks showed the SSE task as "alive" — the same invisible failure pattern from previous occurrences.

This marks the third documented occurrence of this bottleneck (after 2026-04-20 and 2026-04-24), now with a specific call count (266 sequential GETs) rather than the estimated 299-432 from prior observations. The pattern is consistent: every VPS restart triggers auto-discovery, which triggers sequential theory creation, which either hangs or rate-limits, which blocks SSE streams.

The recommended fix — batch Supabase calls, add error handling, or skip existing theories — remains undeployed. A secondary mitigation was noted: checking for ANY existing theory (not just `is_active=true`) before creating would prevent duplicate creation on restart, reducing the call count. The fix was deferred to a fresh session due to the complexity of modifying the startup pipeline safely.

## Related Concepts

- [[concepts/fixture-cache-silent-market-dropout]] - Identified the same serial Supabase GET bottleneck (0.2s × 462 = ~90s); the SSE hang is the failure mode when this bottleneck becomes indefinite
- [[concepts/niche-league-tracker-pipeline-bottlenecks]] - Three compound bottlenecks (ACTIVE_SPORTS, freshness, SSE filter) produced zero output similarly; SSE startup hang adds a fourth potential bottleneck upstream of all three
- [[concepts/value-betting-operational-assessment]] - Weakness #2 (no monitoring): the SSE hang was invisible because the task showed "alive" — health checks need to verify stream count, not just task status
- [[concepts/opticodds-sse-streaming-scaling]] - The SSE streaming architecture that depends on `_sse_startup()` completing successfully
- [[concepts/opticodds-api-key-sport-scoping]] - API key scope discovery that explained why 22/22 non-basketball SSE streams fail; SSE_SPORTS env var added as mitigation

## Sources

- [[daily/lcash/2026-04-20.md]] - SSE startup hung after theory creation, blocking stream launch and fixture cache; 299 leagues auto-discovered, 2 new theories created; 18/18 streams came online after restart; multiple restart attempts needed; task showed "alive" despite zero streams running (Sessions 14:57, 16:29, 18:47)
- [[daily/lcash/2026-04-24.md]] - SSE startup creating theories for 432 leagues against NBA-only API key; 22 non-basketball streams all 400 errors; `SSE_SPORTS` env var added; auto-resolver 5-min delay to prevent API flood on restart (Sessions 14:40, 15:47, 16:35)
- [[daily/lcash/2026-04-27.md]] - Third recurrence: `_auto_create_theories` makes 266 sequential Supabase calls, either times out or hits rate limits, killing entire SSE pipeline; confirmed across two debugging sessions (17:03, 22:19); VPS SSE task shows "alive" but zero streams running; fix (batch calls, skip existing theories) deferred to fresh session (Sessions 17:03, 22:19)
