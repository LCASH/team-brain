---
title: "Unified Odds Aggregator Pipeline"
aliases: [odds-aggregator, mini-pc-aggregator, port-8899-aggregator, single-aggregation-point]
tags: [value-betting, architecture, pipeline, operations, mini-pc]
sources:
  - "daily/lcash/2026-05-03.md"
created: 2026-05-03
updated: 2026-05-03
---

# Unified Odds Aggregator Pipeline

On 2026-05-03, a unified odds aggregator was deployed on the mini PC (port 8899) to replace the previous per-sport push worker model. The aggregator collects odds from all 4 sport servers (NBA 8800, NRL 8801, AFL 8802, MLB 8803), merges them into a single payload, and pushes to the VPS. This creates a single aggregation point — cleaner than separate pushes for each sport — and enables centralized health monitoring via a `pulse` counter. The deployment exposed a uvicorn background task silent failure pattern where `@app.on_event("startup")` tasks failed without visible error signals.

## Key Points

- Single aggregator on port 8899 replaces separate per-sport push workers — polls all 4 sport servers every 5 seconds and pushes a unified multi-sport payload to the VPS
- `pulse` counter in the health endpoint was the diagnostic breakthrough: showed polling WAS executing (counter incremented) but no markets were being fetched from sport servers
- Uvicorn `@app.on_event("startup")` background tasks can fail silently — health/monitoring endpoints are essential for debugging task lifecycle issues
- VPS `/push/odds` handler already supported multi-sport payloads via `mdata.get("sport") or sport` fallback pattern — no VPS changes needed
- Initially showed `market_count: 0` despite sport servers running; root cause was bet365 auth expiry in the NBA scraper requiring server restart
- After auth restoration and sport server restart: 1,677+ markets flowing through aggregator to VPS, all soft books (Bet365, Sportsbet, TAB, PointsBet) confirmed

## Details

### Architecture

The previous push architecture had separate push workers for each sport, each independently collecting odds from their sport server and pushing to the VPS. This created multiple points of failure: any individual push worker could die without affecting the others, but also without anyone noticing. The push worker orphan accumulation documented in [[concepts/push-worker-orphan-accumulation]] was a direct consequence — 12 orphaned workers from repeated kill/restart cycles.

The unified aggregator simplifies this to a single process that:

1. Polls all 4 sport servers via HTTP every 5 seconds (`GET /api/v1/odds` from each)
2. Merges the responses into a unified payload with sport identification
3. Pushes the merged payload to the VPS via `POST /push/odds`
4. Exposes a health endpoint with `pulse` counter, `market_count`, and `last_push_time`

The VPS required zero changes because its `/push/odds` handler already used `mdata.get("sport") or sport` to extract sport identification from incoming payloads — a forward-compatible design from the multi-sport push support added earlier.

### Uvicorn Background Task Silent Failure

The aggregator was implemented as a FastAPI application with a background polling task started via `@app.on_event("startup")`. The initial deployment showed the server running and responding to health checks, but `market_count: 0`. The `pulse` counter was incrementing, proving the background task was executing its polling loop. However, the HTTP requests to sport servers were silently failing — either connection refused (sport server not running) or returning empty responses (bet365 auth expired).

This is a general uvicorn diagnostic pattern: when `@app.on_event("startup")` tasks fail or produce no data, the server appears healthy (responds to HTTP, increments counters) but performs no useful work. The `pulse` counter distinguishes "task not running" (counter frozen) from "task running but getting empty responses" (counter incrementing, market count zero) — a critical diagnostic distinction.

### PowerShell Remote Execution

SSH path issues on the mini PC made it difficult to reliably start the aggregator via SSH shell commands. The fix was to use PowerShell for remote execution, which handles Windows-specific path resolution and process management more reliably than bash-over-SSH on Windows. This follows the pattern documented in [[concepts/windows-ssh-chrome-gui-constraint]] where SSH-launched processes have different session and environment characteristics than desktop-launched ones.

### Relationship to Push Worker Orphans

The unified aggregator structurally eliminates the push worker orphan accumulation problem. With separate per-sport push workers, each `kill/restart` cycle of a sport server could orphan its push worker. With a single aggregator process that polls all servers, there is only one process to manage — killing and restarting it doesn't leave orphans because there's nothing to orphan against.

However, the aggregator introduces a new single point of failure: if port 8899 goes down, all sport data stops flowing to the VPS. The trade-off is operational simplicity (one process to monitor) versus blast radius (one failure affects all sports).

### Mini PC Aggregator Failure (Session 17:35)

Later on the same day, the aggregator on port 8899 stopped responding — the VPS health check showed servers running but zero market data flowing. This confirmed the mini PC component failure pattern: aggregator can stop without obvious remote-accessible logs. The MLB_Server schtask status also needed verification, suggesting the aggregator may have been killed by a sport server restart or resource contention.

## Related Concepts

- [[concepts/push-worker-orphan-accumulation]] - The 12 orphaned push workers that the unified aggregator structurally prevents by consolidating to a single process
- [[concepts/dual-tracker-redundancy-architecture]] - The VPS relay tracker that receives push payloads from this aggregator; the aggregator feeds the VPS leg of the dual-tracker system
- [[concepts/value-betting-operational-assessment]] - Weakness #2 (no monitoring): the aggregator's health endpoint and pulse counter partially address this by providing HTTP-accessible status without SSH
- [[concepts/vps-monitoring-log-noise-elimination]] - The `/api/v1/mini-pc` VPS endpoint that could proxy-check the aggregator's health for dashboard display
- [[concepts/configuration-drift-manual-launch]] - PowerShell used for remote execution because SSH path issues; another deployment environment friction point

## Sources

- [[daily/lcash/2026-05-03.md]] - Aggregator deployed on port 8899; initially `market_count: 0` despite servers running — `pulse` counter showed polling active but no data from bet365 (auth expired); rewrote with explicit error logging + PowerShell; VPS `/push/odds` handler unchanged (already supported multi-sport); 1,677+ markets after auth restoration (Session 11:56). Aggregator stopped responding later same day — mini PC port 8899 not responding to VPS health checks; zero market data flowing (Session 17:35)
