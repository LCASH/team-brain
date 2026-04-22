---
title: "VPS SSE Cascade Silent Crash"
aliases: [sse-cascade-crash, sse-400-cascade, vps-silent-death, vps-crash-recovery]
tags: [value-betting, operations, sse, reliability, crash, monitoring]
sources:
  - "daily/lcash/2026-04-22.md"
created: 2026-04-22
updated: 2026-04-22
---

# VPS SSE Cascade Silent Crash

The VPS value betting server silently died from SSE 400 error cascades, remaining dead for 10+ hours with no alerting. The process crashed at 23:08, and the tracker went from 560 picks/day (yesterday) and 689 picks/day (day before) to 0 picks. The failure was only discovered through manual investigation the next morning when lcash noticed the dashboard was showing no data.

## Key Points

- SSE 400 errors cascaded across all sports and silently killed the VPS server process — no crash alert, no health check, no auto-restart
- The VPS was dead for 10+ hours (23:08 crash → ~09:21 next-day discovery) with zero picks generated during that window
- After manual restart: 11,615 markets loaded, tracker began cycling, 802 trail updates catching up, first new pick inserted within ~4 cycles
- Cold start after VPS crash: theories have a 5-minute cache TTL that starts empty on restart, so the first tracker cycle finds zero theories — not a bug, just cold-start latency
- The `/status` endpoint showed "0 theories" which was a display bug — theories ARE loaded internally after the TTL refresh, but the status endpoint doesn't reflect this correctly
- The mini PC NBA server had been running 21 days without restart (since April 1), demonstrating long-term stability on the scraping side — the VPS relay was the weak link

## Details

### The Failure Mode

The VPS server receives odds data from the mini PC via push and streams it to dashboard clients via Server-Sent Events (SSE). When the SSE layer encounters HTTP 400 errors — likely from malformed client connections, reconnection storms, or payload issues — the errors cascaded across all sport streams. Rather than isolating the error to the affected stream and continuing, the cascade killed the entire server process.

This is a fundamentally different failure mode from the SSE startup hang documented in [[concepts/sse-startup-theory-creation-hang]] (where the server starts but never launches streams) or the deploy syntax validation gap in [[concepts/deploy-syntax-validation-gap]] (where bad code prevents startup). Here, the server was running normally and then crashed from a runtime error cascade — a category of failure that requires both error isolation (to prevent cascades) and process supervision (to auto-restart after crashes).

### Discovery and Recovery

lcash discovered the failure at ~09:21 the next morning when investigating why zero picks were being generated. The diagnostic steps:

1. Checked the VPS server status — process was dead
2. Confirmed mini PC was healthy (NBA server running 21 days continuously)
3. Restarted VPS service manually
4. Observed cold-start behavior: 0 theories on first cycle (5-min cache TTL), then normal cycling after refresh
5. Verified recovery: 11,615 markets loaded, 802 trail updates processing, first pick within minutes

The 10-hour gap represents a complete data loss window. The mini PC continued scraping and writing picks directly to Supabase (see [[concepts/value-betting-operational-assessment]], weakness #6 asymmetric impact), but VPS relay tracker picks, trail writes, and dashboard availability were all lost.

### Architecture Implications

The SSE cascade crash reveals a gap between the VPS's two roles:

1. **Data relay + tracker** — receives push data from mini PC, evaluates EV, writes picks and trails to Supabase
2. **Dashboard server** — serves the web dashboard and SSE streams to browser clients

These roles should ideally be isolated so that client-facing SSE issues don't take down the backend data processing. A cascade from SSE (client-serving layer) killing the tracker (data-processing layer) means that unreliable client connections can produce data loss — a dangerous coupling.

### The `data.json` Red Herring

During investigation, lcash checked `data.json` on the VPS and found it was 14 days old. This initially appeared to be a staleness issue, but turned out to be irrelevant — the dashboard now reads from SSE `/api/v1/stream` with `/api/v1/odds` fallback, not from `data.json`. The stale file is legacy and should be removed to avoid future confusion.

### Dashboard True Odds vs Soft Book Odds Confusion

During the same investigation, the user was confused by the dashboard showing 2.45/2.00 vs bet365 showing 1.95/1.83. This was explained as the dashboard showing devigged true odds (the estimated fair price) vs the soft book's actual odds — these are separate columns, and the gap between them IS the edge. This is not a bug but a UX issue where the distinction between true odds and soft book odds is not clearly communicated.

## Related Concepts

- [[concepts/value-betting-operational-assessment]] - Weakness #2 (no monitoring) and #6 (no redundancy) both confirmed; VPS dead for 10+ hours with no alerting
- [[concepts/sse-startup-theory-creation-hang]] - A different SSE failure mode: startup hang vs runtime cascade crash
- [[concepts/deploy-syntax-validation-gap]] - A different VPS death cause: bad code vs runtime error cascade
- [[connections/operational-compound-failures]] - The VPS crash is another instance of the silent failure → no monitoring → extended invisible degradation chain
- [[concepts/sse-display-tracking-market-separation]] - The SSE architecture whose client-facing layer cascaded into the data-processing layer

## Sources

- [[daily/lcash/2026-04-22.md]] - VPS crashed at 23:08 from SSE 400 error cascade across all sports; dead 10+ hours; tracker went from 560/689 picks/day to 0; cold start: 5-min theory cache TTL empty on restart; 11,615 markets loaded after restart; 802 trail updates catching up; mini PC NBA server running 21 days; `/status` shows 0 theories (display bug); data.json 14 days old but irrelevant (dashboard reads SSE); true odds vs soft book odds confusion explained (Sessions 09:21, 09:42)
