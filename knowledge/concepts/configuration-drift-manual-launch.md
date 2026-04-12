---
title: "Configuration Drift from Manual Launch"
aliases: [batch-file-drift, manual-launch-regression, env-var-drift]
tags: [deployment, operations, gotcha, windows, value-betting]
sources:
  - "daily/lcash/2026-04-12.md"
created: 2026-04-12
updated: 2026-04-12
---

# Configuration Drift from Manual Launch

A deployment anti-pattern where a service is initially launched manually with environment variables or flags set on the command line, but the committed startup script (e.g., a batch file) never includes those settings. The service runs correctly until it is restarted via the script, at which point the missing configuration causes a silent regression — fewer features enabled, missing integrations, or degraded functionality.

## Key Points

- The `start_nba.bat` batch file on the mini PC was committed on Apr 8 without `ENABLE_BET365_GAME_SCRAPER`, `ENABLE_DIRECT_SCRAPERS`, or `ENABLE_BLACKSTREAM` flags
- The NBA server had been running with all 9 tasks because it was launched manually with those env vars — not from the batch file
- When the process was killed and restarted via `start_nba.bat` during OpticOdds key rotation, only 4 of 9 tasks launched — a silent regression
- The drift was invisible until the restart: `git log` showed the flags were never in the file, confirming they were never "removed" — they were never committed
- Soft book count dropped from 7/8 to 3/8 until the batch file was fixed and the process restarted

## Details

### The Pattern

Configuration drift from manual launch follows a predictable lifecycle: (1) a developer starts a service manually with extra flags or environment variables during initial setup or debugging, (2) the service runs correctly, reinforcing the assumption that the configuration is correct, (3) time passes and the manual launch context is forgotten, (4) a restart event occurs (key rotation, process crash, server reboot) and the service is started from the committed script, (5) the service comes up in a degraded state because the script lacks the manually-applied configuration.

This pattern is particularly insidious because the degradation may be partial rather than total. In the value betting scanner case, the NBA server launched successfully with 4 out of 9 tasks — it appeared healthy at a glance. Only a detailed health check comparing expected vs. actual task counts revealed the regression. If the missing tasks had been less visible (e.g., a background data enrichment process), the drift could have gone unnoticed for days.

### The Specific Incident

On 2026-04-12, during OpticOdds API key rotation, lcash killed the running NBA server process on the mini PC and restarted it using `start_nba.bat`. The server came up with only 4 tasks (opticodds_poller, push_loop, disk_cleanup, and the betstamp_scraper) instead of the expected 9. Investigation via `git log` confirmed `start_nba.bat` was last committed on Apr 8 and had never contained the three `ENABLE_*` flags. The previous process had been launched manually (likely from the command line with `set ENABLE_BET365_GAME_SCRAPER=true` etc.) on Apr 10.

The fix was straightforward: add the three enable flags to `start_nba.bat` and restart. Post-fix, all 9 tasks launched and soft book coverage recovered from 3/8 to 7/8 (with the 8th expected to warm up from the Betstamp scraper).

### Prevention

The root prevention is ensuring that all production launch configuration lives in committed, version-controlled startup scripts — never in manual command-line invocations. When adding a new feature flag or environment variable during development, the startup script should be updated in the same change. A secondary defense is health check automation that compares expected task counts against actual running tasks, catching drift at restart time rather than waiting for a user to notice degraded output.

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - The key rotation event that triggered the restart and exposed the drift
- [[concepts/betstamp-bet365-scraper-migration]] - The NBA scraper ecosystem where this drift occurred

## Sources

- [[daily/lcash/2026-04-12.md]] - `start_nba.bat` missing ENABLE_* flags since Apr 8 commit; manual launch on Apr 10 masked the gap; restart during key rotation exposed regression (4/9 tasks, 3/8 soft books); fixed by adding flags to batch file (Session 21:15)
