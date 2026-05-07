---
title: "VPS Monitoring and Log Noise Elimination"
aliases: [monitoring-design, log-noise-reduction, discord-alerting, mini-pc-endpoint, 3-phase-monitoring]
tags: [value-betting, operations, monitoring, observability, alerting, architecture]
sources:
  - "daily/lcash/2026-05-02.md"
created: 2026-05-02
updated: 2026-05-02
---

# VPS Monitoring and Log Noise Elimination

On 2026-05-02, a comprehensive monitoring system was designed and partially deployed for the value betting scanner after a 2-day NBA outage went undetected. The approach prioritized signal quality over alerting volume, following a 3-phase implementation: Phase 1 eliminates log noise that hides real signals, Phase 2 adds structured health metrics (rate tracking, rolling windows), and Phase 3 builds a dashboard health grid with smart alerts. Three immediate reliability fixes were deployed: a `/api/v1/mini-pc` endpoint on the VPS (eliminating SSH for health checks), Discord webhook alerting on task death, and automatic ev_periods closure when games go live.

## Key Points

- **2-day NBA outage went undetected** because the watchdog had been silently disabled; batch files not in repo prevented visibility into mini PC state
- **Discord webhook alerting deployed**: instant notifications on background task death via `ALERT_WEBHOOK_URL` in `.env`; eliminated the "processes die and nobody notices" failure class
- **`/api/v1/mini-pc` endpoint** on VPS: provides health status of mini PC components via HTTP, eliminating the need for SSH to check system state
- **Log noise was actively hiding real signals**: NHL dead sport, unavailable books (underdog_predictions, crypto_com), 521 auto-discovered sports generated constant error messages; demoted to DEBUG level
- **Market count oscillation (1500→7880) is normal**: event-driven behavior between SSE-only state and mini PC push arrivals — not a bug or data loss
- **3-phase monitoring plan**: (1) kill noise, (2) structured metrics (picks/5min, trails/5min, markets/cycle), (3) dashboard health grid + smart alerts
- **Batch files checked into repo** as version-controlled source of truth — prevents outages from configuration drift where batch files only existed on mini PC
- **ev_periods state leak fixed**: open periods never closed when games went live, creating permanent state accumulation

## Details

### The 2-Day Outage Trigger

On 2026-05-02, lcash discovered the NBA server had been down for approximately 2 days. The root cause was traced to `start_nba.bat` missing OpenBLAS thread limit settings — a batch file configuration issue identical in pattern to the recurring drift documented in [[concepts/configuration-drift-manual-launch]]. The outage went undetected because:

1. **Watchdog was silently disabled** — the scheduled task existed but wasn't running, providing zero auto-restart capability
2. **No alerting system** — no Discord webhook, no email, no SMS; failures were only discovered through manual SSH investigation
3. **Batch files not in repo** — the batch files only existed on the mini PC, making their state invisible to code review or deployment verification
4. **SSH complexity** — no saved Tailscale/VPS connection documentation, making manual health checks high-friction

### The Four Immediate Fixes

Rather than pursuing an architecture rewrite, four targeted fixes were deployed:

**Fix 1 — `/api/v1/mini-pc` endpoint**: Added to the VPS server, this endpoint aggregates health status from the mini PC's sport servers via HTTP. Operators can now check mini PC health from any browser without SSH. The endpoint reports per-component status (NBA tracker cycles, MLB scraper state, push worker age, etc.) with `all_ok` flipping to `false` when the tracker is dead for >5 minutes.

**Fix 2 — Discord webhook alerting**: Integrated via `ALERT_WEBHOOK_URL` environment variable. The `_send_discord_alert()` function fires when any background task dies. After deployment, task death notifications are immediate — eliminating the window between failure and detection that previously lasted hours or days.

**Fix 3 — ev_periods closure**: The post-game EV tracking system (`ev_periods`) had a state leak: when a game transitioned from pre-game to live, open periods were never closed. The leak was permanent — old periods accumulated indefinitely. The fix automatically closes open periods when the game goes live.

**Fix 4 — Batch files in repo**: All batch files (`start_nba.bat`, `start_nrl.bat`, `start_afl.bat`, `start_push.bat`) were checked into the repository as the version-controlled source of truth. This prevents the class of drift bugs where batch files on the mini PC diverge from expected state.

### Log Noise Analysis

A systematic log analysis revealed three categories of noise obscuring real signals:

**Category 1 — Dead sports**: NHL season was over, generating constant "No active NHL fixtures" messages. These are informationally correct but operationally useless during the off-season.

**Category 2 — Unavailable books**: `underdog_predictions`, `crypto_com`, and other book names produce consistent errors because they're no longer valid OpticOdds sportsbook identifiers. The SSE streams still attempt to fetch them, generating error lines every cycle.

**Category 3 — Over-scoped auto-discovery**: The `auto_discover_leagues` function was scanning 521 sports when only basketball and baseball are accessible via the API key. Each inaccessible sport generated discovery output with zero actionable data.

The fixes: (1) demote dead-sport and unavailable-book messages to DEBUG level, (2) truncate startup log messages from 500-league dumps to count-only summaries, (3) scope auto-discovery to basketball + baseball (see [[concepts/theory-auto-creation-pollution]]).

After noise elimination, real signals became visible: the tracker was actually healthy (1-73 new picks every 5-30 seconds), Pinnacle GL streams were disconnecting intermittently, and 2 orphaned MLB worker processes were running simultaneously.

### Market Count Oscillation

The apparent "market count instability" — oscillating between 1,500 and 7,880 — was diagnosed as normal event-driven behavior, not a reliability issue. The oscillation occurs between two states:

- **SSE-only (1,500 markets)**: When the mini PC hasn't pushed recently, the VPS has only SSE-sourced data
- **SSE + mini PC push (7,880 markets)**: When a push arrives, mini PC scraper data (Bet365, OpticOdds REST) merges with SSE data

The oscillation frequency matches the push cycle timing. This is architecturally correct behavior, not a bug — the market count reflects the union of available data at each moment.

### 3-Phase Monitoring Plan

**Phase 1 (deployed)**: Kill log noise. Gate NHL/esports/WTA resolvers, silence expected book errors, kill orphaned workers. Achieves: readable logs where real signals are visible.

**Phase 2 (planned)**: Add rolling-window rate tracking to the health endpoint. Metrics: picks/5min, trail_entries/5min, markets/cycle, SSE stream count, bet365 data age. Enables: quantitative health assessment without log parsing.

**Phase 3 (planned)**: Dashboard health grid + smart alerts. Shows: per-component status grid (tracker: HEALTHY, bet365: STALE, SSE: 18/18). Alerts fire only on sustained anomalies (zero picks for 15 minutes, SSE stream death), not on single-cycle blips. Prevents: alert fatigue from transient conditions.

### Discord Alert Coverage Gap

A critical gap was discovered in the alerting system on the same day: `_send_discord_alert()` only fires for background task crashes, not for login failures. The NBA scraper was found dead for 5 days (last log April 27) and the MLB scraper crashed on May 2 — neither triggered a Discord notification because: (1) `ALERT_WEBHOOK_URL` was missing from `.env`, and (2) even with the webhook configured, login failures aren't wired to the alert function. See [[concepts/bet365-session-login-detection-gap]] for the login detection gap that compounds with this alerting gap.

## Related Concepts

- [[concepts/value-betting-operational-assessment]] - The 7-weakness assessment that identified monitoring (weakness #2) as the highest-impact gap; the 3-phase monitoring plan directly addresses this
- [[concepts/configuration-drift-manual-launch]] - Batch files not in repo is the same drift pattern; checking them into version control closes this drift vector
- [[connections/operational-compound-failures]] - The 2-day outage follows the established compound failure chain: drift (missing OpenBLAS settings) + no alerting (disabled watchdog) + SSH friction
- [[concepts/bet365-session-login-detection-gap]] - Discord alerting covers task death but not login failures — a gap that leaves soft book scrapers silently dead
- [[concepts/worker-status-observability]] - The 4-state worker status system needs to be surfaced through the monitoring endpoint, not just logged
- [[concepts/watchdog-environment-stripping]] - The watchdog being silently disabled was a contributing factor to the 2-day outage; even when working, the watchdog strips env vars on restart

## Sources

- [[daily/lcash/2026-05-02.md]] - 2-day NBA outage from missing OpenBLAS in batch file; watchdog silently disabled; 4 targeted fixes (mini-pc endpoint, Discord alerts, ev_periods, batch files in repo) deployed; system confirmed healthy at 6,583 markets and 10 tasks after fixes (Sessions 13:29, 14:23). Log noise analysis: 3 categories of noise (dead sports, unavailable books, over-scoped auto-discovery) hiding real signals; market oscillation 1500→7880 is normal event-driven behavior; 2 orphaned MLB workers found; 521 sports scoped to 2; 3-phase monitoring plan designed (Sessions 16:08, 16:20). Discord alerting gap: NBA scraper dead 5 days, MLB crashed — neither alerted because ALERT_WEBHOOK_URL missing from .env AND login failures not wired to alert function (Session 23:14)
