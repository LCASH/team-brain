---
title: "AdsPower Wayland GUI Session Recovery"
aliases: [wayland-recovery, adspower-phantom-active, gui-session-env-harvest, adspower-linux-chrome-launch, display-env-vars]
tags: [value-betting, adspower, linux, chrome, operations, reliability, deployment]
sources:
  - "daily/lcash/2026-05-18.md"
created: 2026-05-18
updated: 2026-05-18
---

# AdsPower Wayland GUI Session Recovery

On 2026-05-18, lcash discovered that AdsPower's `browser/start` API on Linux (Eve VPS) can return a successful response with a port number while no Chrome process actually spawns. The root cause is that AdsPower's daemon cannot spawn Chrome via API alone without inherited GUI session environment variables (Wayland/X11 display context). The fix is to harvest `DISPLAY=:0`, `XAUTHORITY` (mutter xauth path), and `DBUS_SESSION_BUS_ADDRESS` from an active `gnome-shell` process, then call `browser/stop` followed by `browser/start` under that environment. This pattern enables individual profile re-launches without restarting the entire AdsPower daemon (which would kill other running profiles like MLB).

## Key Points

- AdsPower API `browser/start` can return HTTP 200 with a valid port number, but **no Chrome process actually launches** — the API response is a phantom success
- Root cause: AdsPower daemon on Linux needs Wayland/X11 display environment variables (`DISPLAY`, `XAUTHORITY`, `DBUS_SESSION_BUS_ADDRESS`) inherited from the GUI session to spawn Chrome
- **Always verify Chrome launch** with `pgrep` or CDP `/json` endpoint before trusting the API response — API "Active" status is unreliable
- Recovery pattern: harvest GUI env from active `gnome-shell` process via `/proc/{pid}/environ`, then `browser/stop` + `browser/start` under that env
- This pattern allows **per-profile re-launch** (e.g., restart NBA Chrome without killing MLB) — unlike restarting the AdsPower daemon which affects all profiles
- The phantom-active state can persist indefinitely — no timeout or self-correction; the profile appears "Active" in AdsPower's internal state while nothing is running

## Details

### The Phantom-Active State

AdsPower manages Chrome profiles with persistent state tracking. When `browser/start` is called for a profile, AdsPower marks it as "Active" and records the allocated CDP debugging port. On Linux systems running Wayland (e.g., Ubuntu with GNOME), Chrome requires display server environment variables to initialize its GPU process and window management. When these variables are absent — as happens when AdsPower is called from an SSH session, a systemd service, or a cron job — Chrome fails to spawn but AdsPower's internal state has already been updated to "Active."

The result is a phantom state: AdsPower reports the profile as active on port N, but no Chrome process is bound to that port. Any CDP connection attempt to `http://localhost:N/json` receives `ECONNREFUSED`. The scraper's startup logic — which trusts the API response — proceeds to attempt login, discovery, and scraping operations that all silently fail against a non-existent browser.

This was discovered on 2026-05-18 when the NBA Chrome (profile `k19yb91n` on Eve VPS) had been running since May 8 (10 days). After a v3 restart on May 15, the startup code detected Chrome was "already running" via AdsPower's status API and skipped login verification. The session cookies had expired, but no data flowed because the "running" Chrome was actually a phantom. When a manual restart was attempted, the `browser/start` API returned success with a port, but `pgrep` confirmed zero Chrome processes.

### The Environment Harvest Pattern

The fix harvests GUI session environment variables from a running desktop process:

1. Find the active `gnome-shell` PID (the desktop compositor)
2. Read `/proc/{pid}/environ` to extract `DISPLAY`, `XAUTHORITY`, and `DBUS_SESSION_BUS_ADDRESS`
3. Export these variables into the current shell environment
4. Call `browser/stop` for the target profile (clears AdsPower's phantom "Active" state)
5. Call `browser/start` under the enriched environment
6. Verify Chrome actually launched via `pgrep` or CDP `/json` before proceeding

This pattern works because the gnome-shell process has the correct Wayland display context. By inheriting its environment, AdsPower's Chrome launch inherits the display server connection, allowing GPU initialization and window rendering.

### Per-Profile vs Daemon Restart

Restarting the entire AdsPower daemon (`adspower --restart`) would also resolve the phantom state, but this kills ALL running profiles — including MLB Chrome which may be healthy and actively scraping. The env-harvest pattern enables surgical recovery: only the affected profile (NBA) is restarted while MLB continues uninterrupted.

This is operationally significant for the v3 scanner where NBA and MLB run on separate AdsPower profiles. A daemon restart during active MLB scraping would cause a data gap of 5+ minutes (Chrome relaunch + bet365 login + discovery + market enumeration).

### Interaction with v3 Startup Logic

The phantom-active state compounds with the v3 startup's login verification gap (see [[concepts/v3-startup-login-verification-gap]]): v3 detects Chrome as "already running" via the AdsPower API, presumes the session is logged in, and skips authentication checks. If Chrome is phantom-active, v3 silently produces zero data for the affected sport — no error, no log entry, just an orchestrator sitting idle.

The combined fix requires both: (1) verify Chrome is actually running after AdsPower API reports success, and (2) verify login state even when Chrome is genuinely running.

## Related Concepts

- [[concepts/v3-startup-login-verification-gap]] - v3 presumes Chrome running = logged in; compounds with phantom-active state to produce zero data silently
- [[concepts/bet365-headless-detection]] - AdsPower is required (not vanilla Chrome) because bet365 detects navigator.webdriver; phantom-active means even AdsPower can fail to provide the required anti-detect browser
- [[concepts/windows-ssh-chrome-gui-constraint]] - The Windows equivalent: Chrome from SSH renders black screen. Linux has a different failure mode — Chrome doesn't spawn at all, but the API says it did
- [[concepts/cdp-stale-connection-poisoning]] - A related "phantom state" bug: dead workers leave ghost CDP sessions. This bug is the inverse: no Chrome exists but AdsPower claims it does
- [[connections/stale-process-state-phantom-liveness]] - The broader pattern of processes/APIs reporting healthy state that doesn't reflect reality

## Sources

- [[daily/lcash/2026-05-18.md]] - AdsPower API returned success for browser/start but no Chrome spawned (ECONNREFUSED); root cause: missing Wayland display env vars; fix: harvest DISPLAY/XAUTHORITY/DBUS from gnome-shell process; per-profile restart without killing MLB; NBA had been phantom-active since May 15 restart (Session 09:30)
