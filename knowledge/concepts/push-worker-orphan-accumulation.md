---
title: "Push Worker Orphan Accumulation"
aliases: [orphan-push-workers, push-worker-buildup, orphaned-workers, silent-worker-orphans]
tags: [value-betting, operations, reliability, monitoring, anti-pattern]
sources:
  - "daily/lcash/2026-04-28.md"
created: 2026-04-28
updated: 2026-04-28
---

# Push Worker Orphan Accumulation

On 2026-04-28, 12 orphaned push worker processes were discovered running simultaneously on the mini PC, overwhelming the VPS with redundant push traffic. The dashboard showed no picks despite scrapers being active — the symptom appeared to be a scraper failure but the root cause was push worker orphans flooding the VPS. Each orphaned push worker independently pushed odds data to the VPS, creating resource contention and connection flooding that degraded VPS responsiveness below the threshold for successful data flow.

## Key Points

- **12 orphaned push workers** running simultaneously — each independently pushing odds to the VPS
- Dashboard showed no data, making the problem look like a scraper failure — but scrapers were healthy; the VPS was overwhelmed by 12× redundant push traffic
- Orphans accumulated from repeated process kills/restarts during debugging sessions — each kill spawned a new push worker without properly terminating the old one
- Killing all 12 orphans and restarting 1 clean instance immediately restored dashboard data flow
- The symptom (no picks on dashboard) is indistinguishable from scraper failure without checking push worker process count — a dangerous diagnostic red herring
- Push worker orphan count should be monitored/alerted as part of system health

## Details

### The Failure Mode

The value betting scanner's architecture uses a push worker process to aggregate odds from sport servers on the mini PC and push them to the VPS via HTTP. The push worker runs as a background process, typically launched by the sport server's startup script. When the sport server is killed and restarted (during debugging, deploys, or watchdog restarts), the old push worker may not be terminated — it continues running as an orphan.

Each orphan independently polls the sport servers and pushes data to the VPS at its configured interval (every few seconds). With 12 orphans, the VPS receives 12× the expected push volume. This overwhelms the VPS's HTTP handler, causing request queuing, connection timeouts, and eventually failed ingests. The VPS appears to be down or unresponsive, but it's actually drowning in legitimate but redundant traffic.

### Diagnostic Red Herring

The most dangerous aspect of this failure is its presentation. The dashboard shows no data → the operator investigates scrapers → scrapers appear to be running and producing odds → the operator concludes there's a VPS issue or a pipeline bug. The actual cause (too many push workers) is not visible from either the dashboard or scraper health checks. Only checking the process list on the mini PC (`tasklist | findstr python`) reveals the 12 orphaned workers.

This follows the scanner's established pattern of invisible operational failures (see [[connections/operational-compound-failures]]): the symptom points in the wrong direction, and the root cause is only discoverable through process-level inspection that isn't part of standard health checks.

### Accumulation Pattern

Push worker orphans accumulate through a specific sequence:

1. Operator kills sport server process (for deploy, debugging, or restart)
2. The kill terminates the sport server but not its child push worker (different process group on Windows)
3. Operator restarts sport server → new push worker spawned
4. Repeat steps 1-3 during an active debugging session
5. After N kill/restart cycles, N+1 push workers are running (N orphans + 1 current)

On 2026-04-28, the debugging session involved multiple kill/restart cycles for both NBA and MLB servers, producing 12 orphans before the problem was identified. During intensive debugging days, this pattern can create dozens of orphans within hours.

### Prevention

Three approaches to prevent orphan accumulation:

1. **Process group kill**: On Windows, use `taskkill /T` (tree kill) when stopping sport servers to terminate all child processes including push workers
2. **Push worker singleton**: The push worker checks for existing instances on startup and kills them before running — ensures only one instance exists regardless of how many times the server is restarted
3. **Push worker count monitoring**: Alert when more than 1 push worker process is running — catches accumulation early

## Related Concepts

- [[concepts/watchdog-environment-stripping]] - The watchdog launches new processes without killing old ones, contributing to orphan accumulation; similar pattern of process lifecycle mismanagement
- [[concepts/silent-worker-authentication-failure]] - Same diagnostic challenge: the system appears healthy at a glance (processes running, scrapers active) but a hidden process-level issue prevents data flow
- [[concepts/value-betting-operational-assessment]] - Weakness #2 (no monitoring) — push worker count is not monitored; weakness #7 (bus factor) — only manual process inspection catches this
- [[connections/operational-compound-failures]] - Orphan accumulation + no monitoring + misleading symptoms create the classic compound failure pattern
- [[concepts/vps-sse-cascade-silent-crash]] - VPS overwhelm from push worker flooding is similar to the SSE cascade crash — both are cases where the VPS is killed by traffic volume rather than code bugs

## Sources

- [[daily/lcash/2026-04-28.md]] - 12 orphaned push workers discovered on mini PC; dashboard showed no picks despite active scrapers; killing all orphans + restarting 1 clean instance restored data flow; orphans accumulated from repeated kill/restart cycles during debugging; push worker count monitoring recommended (Session 09:18)
