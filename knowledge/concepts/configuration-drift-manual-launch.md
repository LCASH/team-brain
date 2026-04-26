---
title: "Configuration Drift from Manual Launch"
aliases: [batch-file-drift, manual-launch-regression, env-var-drift]
tags: [deployment, operations, gotcha, windows, value-betting]
sources:
  - "daily/lcash/2026-04-12.md"
  - "daily/lcash/2026-04-15.md"
  - "daily/lcash/2026-04-19.md"
  - "daily/lcash/2026-04-26.md"
created: 2026-04-12
updated: 2026-04-26
---

# Configuration Drift from Manual Launch

A deployment anti-pattern where a service is initially launched manually with environment variables or flags set on the command line, but the committed startup script (e.g., a batch file) never includes those settings. The service runs correctly until it is restarted via the script, at which point the missing configuration causes a silent regression — fewer features enabled, missing integrations, or degraded functionality.

## Key Points

- The `start_nba.bat` batch file on the mini PC was committed on Apr 8 without `ENABLE_BET365_GAME_SCRAPER`, `ENABLE_DIRECT_SCRAPERS`, or `ENABLE_BLACKSTREAM` flags
- The NBA server had been running with all 9 tasks because it was launched manually with those env vars — not from the batch file
- When the process was killed and restarted via `start_nba.bat` during OpticOdds key rotation, only 4 of 9 tasks launched — a silent regression
- The drift was invisible until the restart: `git log` showed the flags were never in the file, confirming they were never "removed" — they were never committed
- Soft book count dropped from 7/8 to 3/8 until the batch file was fixed and the process restarted
- A second drift layer was discovered after fixing enable flags: API keys (`DIRECT_SCRAPERS_API_KEY`, `BLACKSTREAM_API_KEY`) were in `.env` but not in the batch file, which doesn't load `.env` — workers launched but silently failed to authenticate

## Details

### The Pattern

Configuration drift from manual launch follows a predictable lifecycle: (1) a developer starts a service manually with extra flags or environment variables during initial setup or debugging, (2) the service runs correctly, reinforcing the assumption that the configuration is correct, (3) time passes and the manual launch context is forgotten, (4) a restart event occurs (key rotation, process crash, server reboot) and the service is started from the committed script, (5) the service comes up in a degraded state because the script lacks the manually-applied configuration.

This pattern is particularly insidious because the degradation may be partial rather than total. In the value betting scanner case, the NBA server launched successfully with 4 out of 9 tasks — it appeared healthy at a glance. Only a detailed health check comparing expected vs. actual task counts revealed the regression. If the missing tasks had been less visible (e.g., a background data enrichment process), the drift could have gone unnoticed for days.

### The Specific Incident

On 2026-04-12, during OpticOdds API key rotation, lcash killed the running NBA server process on the mini PC and restarted it using `start_nba.bat`. The server came up with only 4 tasks (opticodds_poller, push_loop, disk_cleanup, and the betstamp_scraper) instead of the expected 9. Investigation via `git log` confirmed `start_nba.bat` was last committed on Apr 8 and had never contained the three `ENABLE_*` flags. The previous process had been launched manually (likely from the command line with `set ENABLE_BET365_GAME_SCRAPER=true` etc.) on Apr 10.

The first fix was to add the three enable flags to `start_nba.bat` and restart. However, this exposed a second drift layer: the `direct_scrapers` and `blackstream` workers launched (their task names appeared in the process list) but produced zero log output and zero market data. Investigation revealed that their API keys (`DIRECT_SCRAPERS_API_KEY` and `BLACKSTREAM_API_KEY`) were defined in the `.env` file but not in the batch file's explicit `set` statements. Windows batch files do not natively load `.env` files — each variable must be manually duplicated as a `set KEY=VALUE` line. Adding both API keys and restarting a third time finally brought all 9 tasks online, recovering soft book coverage from 3/8 to 7/8.

This two-phase debugging experience illustrates how configuration drift can be layered: fixing one category of missing config (enable flags) reveals a second category (API keys), each invisible until the previous layer is resolved. See [[concepts/silent-worker-authentication-failure]] for the specific anti-pattern of workers failing without log output.

### Third Drift Vector: Watchdog Restart (2026-04-15)

Even after fixing `start_nba.bat` to include all enable flags and API keys, a third drift vector was discovered on 2026-04-15. The Windows watchdog process — which automatically restarts the NBA server if it crashes — relaunches with a bare `cmd /c python -m server.main` command instead of invoking `start_nba.bat`. This means every automatic restart silently strips all environment variables, producing the same degraded 4-of-9-task state that the batch file fix was supposed to prevent.

This is particularly dangerous because it is automated: a deploy that kills the process, an out-of-memory crash, or any other unexpected exit triggers the watchdog, which quietly relaunches without configuration. The operator sees "server is running" but it's running without bet365_game, direct_scrapers, or betstamp. Diagnosis was further complicated by stale log files from the dead process (`nba_out.log` showed healthy bet365_game output from the previous run, while the live process logged to `server.log`).

The three drift vectors are now: (1) manual launch with ad-hoc env vars (original issue), (2) batch file missing flags/keys (fixed Apr 12), and (3) watchdog bypassing the batch file entirely (discovered Apr 15). The long-term fix is to ensure the watchdog invokes `start_nba.bat` rather than bare Python. See [[concepts/watchdog-environment-stripping]] for the full analysis.

### Prevention

The root prevention is ensuring that all production launch configuration lives in committed, version-controlled startup scripts — never in manual command-line invocations. When adding a new feature flag or environment variable during development, the startup script should be updated in the same change. Critically, all launch paths — manual, scheduled task, and watchdog — must go through the same startup script. A secondary defense is health check automation that compares expected task counts against actual running tasks, catching drift at restart time rather than waiting for a user to notice degraded output.

### Fourth Drift Vector: VPS Systemd Config Layering (2026-04-19)

On 2026-04-19, lcash discovered a Linux-specific configuration drift vector on the VPS. When adding NHL to `ACTIVE_SPORTS`, updating the `.env` file alone was insufficient — the VPS service uses `systemctl`, which reads environment variables from the systemd unit file's `Environment=` directive, NOT from `.env`.

Three layers of environment configuration can override each other, with later layers taking precedence:

1. **Code defaults** — hardcoded values in the Python source (lowest priority)
2. **`.env` file** — loaded by `python-dotenv` at runtime
3. **systemd `Environment=` directive** — set in the service unit file (highest priority on VPS)

The systemd directive takes precedence because it injects variables into the process environment before Python starts, and `python-dotenv` does not override existing environment variables by default. When `ACTIVE_SPORTS` was set in the systemd unit file (without NHL), updating `.env` to include NHL had no effect — the systemd value was already present in `os.environ`, so `dotenv` skipped it.

The fix required updating all three layers: (1) code default to include NHL, (2) `.env` on VPS, (3) systemd service `Environment=` line, followed by `systemctl daemon-reload && systemctl restart`. This is the Linux equivalent of the Windows batch file problem — both are cases where the actual launch mechanism bypasses the developer's expected configuration source.

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - The key rotation event that triggered the restart and exposed the drift
- [[concepts/betstamp-bet365-scraper-migration]] - The NBA scraper ecosystem where this drift occurred
- [[concepts/silent-worker-authentication-failure]] - The second drift layer: workers launching but silently failing without API keys
- [[connections/operational-compound-failures]] - How this drift compounds with silent failures and missing monitoring
- [[concepts/watchdog-environment-stripping]] - The third drift vector: watchdog bypassing the batch file on automatic restarts

## Sources

- [[daily/lcash/2026-04-12.md]] - `start_nba.bat` missing ENABLE_* flags since Apr 8 commit; manual launch on Apr 10 masked the gap; restart during key rotation exposed regression (4/9 tasks, 3/8 soft books); fixed by adding flags to batch file (Session 21:15). Second layer: API keys in `.env` but not in batch file; workers launched but silently failed; required third restart to fully resolve (Session 21:51)
- [[daily/lcash/2026-04-15.md]] - Third drift vector: watchdog restarts with bare `cmd /c python -m server.main` stripping all env vars; bet365_game went dark; stale `nba_out.log` from dead process misdirected diagnosis; fixed via full kill + `schtasks /Run /TN NBA_Server` (Session 23:17)
- [[daily/lcash/2026-04-19.md]] - Fourth drift vector (Linux/VPS): systemd `Environment=` directive overrides `.env` file. Three-layer precedence: code defaults < `.env` file < systemd `Environment=`. Adding NHL to ACTIVE_SPORTS required updating all three layers; `systemctl restart` reads the systemd unit file env vars, NOT `.env` — fixing `.env` alone was insufficient (Session 07:57)
- [[daily/lcash/2026-04-26.md]] - Fifth recurrence: TAB scraper not running because `ENABLE_DIRECT_SCRAPERS=1` env var was missing from `start_nba.bat`; direct scrapers require both sport config AND the env var (line 1445 in main.py); also `curl_cffi` missing on scanner-ms; same pattern: feature enabled in code but batch file doesn't pass the flag (Session 11:03)
