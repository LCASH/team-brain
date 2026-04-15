---
title: "Watchdog Environment Variable Stripping"
aliases: [watchdog-restart, watchdog-env-stripping, bare-restart, watchdog-drift]
tags: [deployment, operations, anti-pattern, windows, value-betting]
sources:
  - "daily/lcash/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# Watchdog Environment Variable Stripping

The Windows watchdog for the value betting scanner relaunches crashed processes with a bare `cmd /c python -m server.main` command instead of going through `start_nba.bat`, silently stripping all environment variables that the batch file sets (`ENABLE_BET365_GAME`, `ENABLE_DIRECT_SCRAPERS`, `ENABLE_BETSTAMP`, API keys). This is a third drift vector beyond manual launch and batch file omission: even when the batch file is correct, the watchdog bypasses it entirely on automatic restarts.

## Key Points

- The watchdog relaunches with bare `cmd /c python -m server.main` — no env vars, no `start_nba.bat` — so `ENABLE_BET365_GAME_SCRAPER`, `ENABLE_DIRECT_SCRAPERS`, and `ENABLE_BETSTAMP` all vanish silently
- The bet365_game scraper went dark on the mini PC because the watchdog restarted the process without the enable flags, not because of a code or scraper failure
- Diagnosis was misdirected for multiple steps because `nba_out.log` contained healthy bet365_game output from an **older dead process**, while the current process logged to `server.log` which showed only OpticOdds tasks
- 15 orphaned Chrome processes from `bet365_game_profile` were holding port and profile directory hostage, requiring full process tree kill before a clean restart
- The fix required `schtasks /Run /TN NBA_Server` (which executes `start_nba.bat`) rather than relying on the watchdog — but the watchdog itself needs to be fixed to use the batch file

## Details

### Discovery

On 2026-04-15, lcash investigated why the bet365_game scraper was dark on the mini PC. The initial hypothesis was that a deploy had killed the process, which was partially correct. However, the investigation was complicated by a log file misdirection: `nba_out.log` showed healthy bet365_game output (scraped odds, status updates, `set_bookie_status()` calls), suggesting the scraper was running fine. This was output from a **previous process** that had since died — the log file was stale.

The current live process was writing to `server.log` (revealed by inspecting the parent command: `cmd /c ... > server.log`), which showed only OpticOdds poller and push worker tasks — no bet365_game, no direct_scrapers, no betstamp. The process was running via the watchdog's bare restart command, which did not include the `ENABLE_*` environment variables.

### Three Launch Paths

The value betting scanner's NBA server now has three distinct launch paths, each with different environment variable sets:

1. **Manual launch** (command line) — developer sets env vars ad-hoc; may include everything or forget some
2. **Batch file launch** (`start_nba.bat` via `schtasks`) — includes all `ENABLE_*` flags and API keys (after the fixes from 2026-04-12)
3. **Watchdog restart** (automatic) — uses bare `cmd /c python -m server.main` with zero env vars

Path 3 is the most dangerous because it is automated — the watchdog fires without human intervention when a process crashes or is killed. A deploy that kills the NBA server process triggers the watchdog, which relaunches without enable flags, silently degrading the system. The operator sees "NBA server is running" (the process exists) but doesn't realize it's running in a stripped-down mode.

### The Naming Zoo

The investigation also documented the confusing naming landscape for the bet365 game scraper pipeline:

| Layer | Name |
|-------|------|
| Health check key | `bet365_game` |
| Python class | `GameBet365Scraper` |
| Dashboard label | "Bet365 2.0" |
| Windows scheduled task | `NBA_Server` |
| Book ID | `366` |

All five names refer to the same pipeline at different abstraction layers. This naming inconsistency slows debugging because log messages, health endpoints, task manager entries, and dashboard labels all use different identifiers for the same component.

### Log File Misdirection

A key debugging lesson: when multiple processes write to different log files, always verify which log file the **current PID** is writing to before drawing conclusions. The investigation was misdirected for several steps because `nba_out.log` showed healthy bet365_game activity — but this was from a dead process. The live process's parent command (`cmd /c ... > server.log`) revealed the true log target. `set_bookie_status()` calls visible in stale logs do not reflect in the health endpoint because the current process never executed that code path.

### Resolution

The fix was a full process tree kill followed by a scheduled task restart:
1. Killed all orphaned `python -m server.main` processes
2. Killed 15 orphaned Chrome processes from `bet365_game_profile` to free the CDP port and profile directory
3. Ran `schtasks /Run /TN NBA_Server` to restart via the batch file (with all env vars)

The long-term fix is to modify the watchdog to either invoke `start_nba.bat` directly or pass the required environment variables in its restart command. Without this fix, every process crash or deploy-triggered kill will produce a silently degraded restart.

## Related Concepts

- [[concepts/configuration-drift-manual-launch]] - The first two drift vectors (manual launch and batch file omission); the watchdog is a third, automated drift vector
- [[concepts/silent-worker-authentication-failure]] - Workers launched by the watchdog without API keys exhibit the same zero-output failure mode
- [[connections/operational-compound-failures]] - The watchdog adds a new automated entry point to the config drift → silent failure → no monitoring chain
- [[concepts/value-betting-operational-assessment]] - Weakness #3 (config drift) and #7 (bus factor) both amplified by watchdog behavior
- [[concepts/bet365-headless-detection]] - Zombie Chrome processes from the same pipeline compound with watchdog restarts on Windows

## Sources

- [[daily/lcash/2026-04-15.md]] - bet365_game went dark: watchdog restarted with bare `cmd /c python -m server.main` stripping all env vars; `nba_out.log` showed stale output from dead process while live process logged to `server.log`; 15 orphaned Chrome processes; naming zoo documented (bet365_game / GameBet365Scraper / "Bet365 2.0" / NBA_Server / book_id 366); fixed via full kill + `schtasks /Run /TN NBA_Server`; watchdog needs fixing to use batch file (Session 23:17)
