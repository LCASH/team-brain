---
title: "Game Scraper Chrome Crash Auto-Recovery"
aliases: [chrome-crash-recovery, epipe-broken-pipe, zero-ms-scrape-diagnostic, game-scraper-auto-recovery, stale-cached-odds]
tags: [value-betting, scraping, bet365, chrome, reliability, operations]
sources:
  - "daily/lcash/2026-04-19.md"
created: 2026-04-19
updated: 2026-04-19
---

# Game Scraper Chrome Crash Auto-Recovery

The Bet365 game scraper (NBA and MLB) was silently serving stale cached odds for hours after Chrome pipe breaks, with the scraper reporting "streaming" status and "1s" data age. The root cause was a chain: page timeouts → Chrome EPIPE broken pipe → Windows file locks on the Chrome profile directory → scraper stuck returning cached data indefinitely. The `0.0ms` scrape time is the diagnostic smoking gun — real Chrome page refresh takes 500ms+. Auto-recovery was added: after 5 consecutive refresh failures (~25s), the scraper triggers a full `stop() → start()` cycle.

## Key Points

- `0.0ms` scrape time is a smoking gun for stale data — real Chrome `page.goto()` takes 500ms+; zero means returning cached data without actually hitting Chrome
- The scraper reported `status=streaming` and `age=1s` while actual data was 3.7 hours old — health metrics measured process liveness, not data freshness
- Root cause chain: Bet365 page timeout → Chrome EPIPE (broken pipe) → Windows file locks prevent profile cleanup (`Access is denied`) → `refresh()` silently swallows failures → all subsequent `page.goto()` calls fail forever
- Auto-recovery: after 5 consecutive `refresh()` failures (~25 seconds of dead Chrome), trigger full `stop() → start()` cycle to spawn a fresh Chrome instance
- Both NBA and MLB game scrapers had the identical vulnerability — same code pattern, same fix applied to both
- Soft trail data confirmed the staleness: all trails had only 1 entry each (the initial capture), with batch-like timestamps (all at 00:27:42) indicating a single snapshot followed by hours of stale cache
- Crash-loop severity quantified: game scraper had 14 restarts in a single day, direct scraper ~50 — Chrome instability is systemic, not a one-off
- Two additional file locking root causes beyond profile directory: (1) `Path.replace()` on `.bet365_game_live.json` fails when server has it open, (2) Chrome `ActorSafetyLists/` subdirectory resists `shutil.rmtree`
- Fix: unique Chrome profile per session (implemented) + file write retry loop with short delay for the JSON data file

## Details

### The Failure Chain

The Bet365 game scraper uses Playwright/Chrome to navigate game pages and extract player prop odds via HTTP response interception. The scraper's `refresh()` method calls `page.goto()` to reload the current game page, which triggers fresh HTTP responses captured via CDP. Under normal operation, each refresh takes 500ms-2s depending on page load time.

The failure begins when a bet365 page load times out (15 seconds). This can happen due to bet365 server-side latency, network hiccups, or SPA routing issues. The timeout causes a broken pipe (`EPIPE`) in Chrome's internal communication channel. Once the pipe is broken, Chrome's page context becomes unresponsive — every subsequent `page.goto()` call fails immediately.

On Windows, the Chrome process's profile directory (`bet365_game_profile`) remains locked by the zombie Chrome process. Even if the scraper attempts to restart Chrome, it cannot delete or reuse the profile directory because Windows file locks prevent cleanup (`[WinError 5] Access is denied`). The scraper falls back to returning whatever data it last successfully captured — stale cached odds from hours ago.

Critically, the `refresh()` method caught timeout errors, logged a warning, and continued operating — it never detected that Chrome was fundamentally dead. Every subsequent call to `page.goto()` failed silently (caught by the same error handler), and the scraper continued returning its cached data as if it were fresh.

### The 0.0ms Diagnostic

The most reliable diagnostic for this failure mode is the scrape time metric. A real Chrome page refresh involves network roundtrip, page parsing, and JavaScript execution — minimum 500ms even on fast connections. When the scrape time shows `0.0ms`, it means the scraper returned immediately without touching Chrome at all — it served cached data from memory. This metric was available in logs but not surfaced in health checks, which only reported process status ("streaming") and a misleading data age ("1s" — based on when the cache was last read, not when the data was last captured from bet365).

### The Auto-Recovery Fix

The fix adds a consecutive failure counter to the `refresh()` method. Each failed `page.goto()` call increments the counter; each successful call resets it to zero. When the counter reaches 5 (approximately 25 seconds of continuous failure with a 5-second polling interval), the scraper triggers a full `stop() → start()` cycle:

1. **stop()**: Kill the Chrome process, clean up the CDP session, release file handles
2. **start()**: Launch a fresh Chrome instance with a new profile directory, navigate to bet365, establish a new CDP session

This transforms what was previously an indefinite stall (requiring manual SSH intervention to restart) into automatic recovery within ~30 seconds of Chrome dying. The 5-failure threshold prevents premature restarts on transient page load errors (a single timeout is normal and recoverable).

### Shared Vulnerability Pattern

Both the NBA game scraper (`bet365_game_worker.py` in scanner-new) and the MLB game scraper (in scanner-ms) shared the same vulnerable `refresh()` code pattern. When the bug was identified in the NBA scraper, the fix was applied to both simultaneously. This is a recurring maintenance pattern in the scanner: scrapers for different sports share code structures, so a bug in one is likely present in all — always check sister scrapers when fixing one.

### Trail Data Evidence

The staleness was confirmed through trail data analysis. Soft trails for Bet365 2.0 picks showed only 1 entry each — the initial capture at pick creation time — with no subsequent odds movement recorded. All timestamps were batch-like (e.g., all at 00:27:42), indicating a single data snapshot followed by hours of stale cache serving. Healthy trail data would show multiple entries at 5-15 second intervals as odds move pre-game.

The user correctly challenged the initial "between slates" explanation for sparse trails — Bet365 has pre-game player props hours before tipoff, so odds should be refreshing regardless of whether games are active. This pushed the investigation from "expected behavior" to "something is broken," ultimately revealing the Chrome crash.

### Windows File Lock Complication

The Windows file lock issue (`[WinError 5] Access is denied`) on the Chrome profile directory is a secondary complication. When Chrome crashes but its process lingers as a zombie, the profile directory remains locked — specifically, the `ActorSafetyLists/` subdirectory within the Chrome profile resists `shutil.rmtree`, blocking the next Chrome launch. The current auto-recovery's `stop()` must forcefully terminate the Chrome process tree before cleanup can proceed.

The fix (deployed in Session 20:38) uses **unique Chrome profile directories per session** (e.g., `bet365_game_profile_{timestamp}`) so each restart gets a fresh directory without needing to clean up the old one. This eliminates the locked-file conflict entirely — the old directory can be cleaned up later when the zombie Chrome process eventually releases it.

### Subprocess JSON File Locking

A second file locking issue was identified beyond the Chrome profile directory. The Bet365 game scraper architecture uses a **decoupled subprocess model**: a separate Chrome-driving subprocess writes scraped odds to a JSON file (`.bet365_game_live.json`), and the main server process reads that file to serve odds data. This decoupling is intentional — it isolates Chrome crashes from the server process.

However, the file handoff creates a Windows-specific locking issue. The subprocess uses `Path.replace()` (atomic rename) to update the JSON file, but Windows `replace()` fails with `[WinError 5] Access is denied` when the server process has the target file open for reading. Unlike Unix (where atomic rename succeeds regardless of readers), Windows file locks prevent the rename.

The fix adds a **file write retry loop** with a short delay: if `replace()` fails due to a file lock, the subprocess retries after a brief pause (e.g., 100ms). This handles the window where the server is mid-read. The retry loop is bounded to prevent indefinite blocking.

### Crash-Loop Severity

The 2026-04-19 investigation revealed that the Chrome instability was far more severe than initially diagnosed. The game scraper had **14 restarts** in a single day, while the direct scraper had approximately **50 restarts**. This quantifies the crash-loop: Chrome was dying and restarting frequently, not just occasionally. Each restart cycle produces a window of stale data (until the new Chrome instance warms up and begins scraping), creating repeated gaps in odds freshness that compound over the day.

The crash-loop also leaves orphaned Chrome processes — Session 20:38 found that 15 orphaned Chrome processes were still running from previous crashes, holding port and profile directory resources hostage. These orphans accumulate because the `stop()` cleanup in the auto-recovery didn't always successfully terminate the entire process tree on Windows. The unique-profile-per-session fix reduces the impact of orphans (they don't block new sessions), but orphan cleanup is still needed to prevent resource exhaustion over extended operation.

### Windows Process Persistence

A deployment lesson from the same session: `start /b` processes (launched via background command) die when the SSH session disconnects on Windows. This means deploying a fix via SSH and launching the scraper with `start /b python ...` creates a process that dies as soon as the operator disconnects. The correct persistence mechanism is `schtasks` — Windows scheduled tasks survive SSH disconnection and system reboots. When restarting a server on Windows, the old process must be explicitly killed first, or the new one fails with "port already in use."

## Related Concepts

- [[concepts/worker-status-observability]] - The game scraper reported "streaming" status with 3.7h old data — a more severe version of the hardcoded status problem: the scraper wasn't lying about its state, it genuinely believed it was streaming
- [[connections/browser-automation-reliability-cost]] - Chrome crash recovery is a direct manifestation of the browser-mediated architecture's reliability cost: the browser is an intermediary that can fail in ways the Python orchestrator can't detect
- [[concepts/bet365-headless-detection]] - Zombie Chrome processes from the game scraper compound with deployment issues on Windows (15 orphaned processes discovered during previous investigations)
- [[concepts/configuration-drift-manual-launch]] - The mini PC deploy to push auto-recovery code follows the same Windows deployment patterns (batch file, schtasks)
- [[concepts/silent-worker-authentication-failure]] - Same failure signature: process alive, zero useful output, zero errors — but this case is worse because it produces stale data (plausible wrong output) rather than no data

## Sources

- [[daily/lcash/2026-04-19.md]] - Bet365 2.0 data 3.7h stale; `0.0ms` scrape time diagnostic; root cause: page timeout → EPIPE → Windows file lock → cached data forever; `refresh()` silently swallowed failures; auto-recovery: 5 consecutive failures → full stop/start cycle; applied to both NBA and MLB scrapers; trail evidence: 1 entry per pick, batch timestamps; user correctly rejected "between slates" explanation (Sessions 14:57, 20:07). Crash-loop quantified: 14 game scraper restarts, ~50 direct scraper restarts in one day; two additional file locking issues: `.bet365_game_live.json` `Path.replace()` fails when server reads, Chrome `ActorSafetyLists/` resists rmtree; fixes: unique Chrome profile per session (implemented), file write retry loop; subprocess JSON architecture documented; `start /b` dies on SSH disconnect, schtasks is correct persistence; 15 orphaned Chrome processes found (Session 20:38)
