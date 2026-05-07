---
title: "bet365 Session Login Detection Gap"
aliases: [login-detection-gap, logged-out-session-detection, bet365-auth-detection, empty-response-ambiguity]
tags: [value-betting, bet365, scraping, reliability, architecture, bug]
sources:
  - "daily/lcash/2026-05-01.md"
  - "daily/lcash/2026-05-02.md"
  - "daily/lcash/2026-05-03.md"
created: 2026-05-01
updated: 2026-05-03
---

# bet365 Session Login Detection Gap

The bet365 MLB and NBA v3 scrapers have no mechanism to detect when the Chrome session is logged out. A logged-out browser session returns empty API responses that are structurally indistinguishable from rate-limiting or "no data available" responses — the scraper interprets both as transient failures, preserves stale cached data, and reports no error. On 2026-05-01, the MLB scraper's `.bet365_mlb_game_live.json` was stuck at `{"status":"stale","count":0}` for 34 minutes while all Chrome tabs sat on the bet365 login wall.

## Key Points

- Logged-out bet365 session returns empty body or login HTML — same shape as rate-limit response or "no props posted yet" — zero distinguishing signal
- The scraper's staleness logic (`age > REFRESH_INTERVAL`) decides "stale" purely by time, not by session state — a logged-out browser looks identical to a rate-limited one
- **Structural bug pattern**: logged-out → empty body → `count == 0` silently skipped → `consecutive_failures` increments but old data preserved → no alert raised → stale data served indefinitely
- `.bet365_mlb_game_live.json` stuck at `{"status":"stale","count":0}` for 34 minutes with zero indication that login was the root cause
- Both MLB v3 (`bet365_mlb_v3.py`) and NBA v3 have the identical gap — neither checks authentication state
- Proposed fix: `Runtime.evaluate` per scrape cycle checking for a logged-in DOM marker (balance/account icon) or logged-out marker (login button); on detection → set `session_logged_out` flag, surface in `/api/v1/health`, stop scraping

## Details

### The Ambiguity Problem

When the bet365 session expires (cookies expire, account kicks, or manual logout), the browser doesn't crash or throw an error. It silently redirects API requests to the login page or returns empty responses. From the scraper's perspective, the HTTP response from the intercepted API call has the same structural characteristics as several benign conditions:

| Condition | API Response | Scraper Interpretation |
|-----------|-------------|----------------------|
| **Logged out** | Empty body / login HTML redirect | "No data this cycle" → retry |
| **Rate-limited** | Empty or throttled body | "No data this cycle" → retry |
| **No props posted** | Empty body (game >6h out) | "No data this cycle" → retry |
| **bet365 CDN stale** | Same cached body as last fetch | "No change" → skip |

All four conditions produce `count == 0` in the scraper's response parser. The scraper's recovery logic — increment `consecutive_failures`, preserve the last known good data, retry next cycle — is correct for conditions 2-4 but catastrophically wrong for condition 1. A logged-out session will never spontaneously fix itself by retrying — every subsequent cycle produces the same empty response, and `consecutive_failures` climbs indefinitely without triggering any alert.

### The Stale Data Cascade

The scrapers use a decoupled architecture where a Chrome-driving subprocess writes odds to a JSON file, and the main server process reads that file. When the subprocess gets empty responses (because the session is logged out), it skips the file write — preserving whatever odds were last successfully captured. The main server reads the stale file and serves the stale odds to the VPS push pipeline.

From the dashboard, the scraper appears to be "streaming" with data that has a specific age. The age grows slowly because the JSON file's modification timestamp doesn't update, but the health check only alerts on total process death — not on data age exceeding a threshold. The operator sees "bet365: streaming" while the data is 34 minutes (or hours) old.

### Discovery

On 2026-05-01, lcash investigated why the MLB scraper was producing stale data. The `.bet365_mlb_game_live.json` file showed `{"status":"stale","count":0}` — updated 34 minutes ago. Initial diagnosis pointed toward rate limiting or CDN staleness. Only after checking the Chrome tabs via CDP (finding all tabs on the login wall) was the root cause identified as session expiry.

The diagnostic challenge was compounded by the UTC+10 timezone trap: Supabase queries for "today's" picks initially returned nothing because UTC was still on the previous calendar date. This led to a false alarm about the tracker being dead when it was actually healthy.

### Proposed Login Detection

The fix adds a per-cycle authentication probe using CDP `Runtime.evaluate` to check the Chrome DOM for login state indicators:

1. **Logged-in indicators**: Account balance display, user menu icon, or any element that only renders when authenticated
2. **Logged-out indicators**: "Log In" button, username/password input fields, or URL containing login path components

When the probe detects a logged-out state:
1. Set `session_logged_out = True` on the worker state
2. Surface the flag in `/api/v1/health` as `"session": "LOGGED_OUT"`
3. Stop scraping (don't accumulate `consecutive_failures` against a known-dead session)
4. Optionally trigger auto-login (see [[concepts/bet365-auto-login-session-recovery]]) — though CAPTCHA may block automated recovery

The probe must be lightweight — a single `document.querySelector()` call checking for the presence of a known element — and must not interfere with the scraping cycle's page state.

### Relationship to Existing Detection

The three-layer session expiry detection deployed on 2026-04-23 (see [[concepts/bet365-size-gate-stale-odds]]) operates at a different level: it checks for URL redirects during `page.goto()` navigation. The login detection gap is in the **response content** layer — the v3 scrapers use raw CDP response interception where URL redirects may not be visible in the same way as Playwright-managed navigation. The two detection mechanisms are complementary: URL redirect detection catches expiry during navigation, DOM probe detection catches expiry between navigations.

### Discord Alerting Gap for Login Failures (2026-05-02)

On 2026-05-02, lcash discovered that the NBA scraper had been dead for **5 days** (last log entry April 27) and the MLB scraper had crashed on May 2 — neither triggered a Discord notification. Investigation revealed two compounding gaps:

1. **Missing webhook configuration**: `ALERT_WEBHOOK_URL` was not set in the mini PC's `.env`, so the Discord alerting system deployed the same day was non-functional for the scraper processes.
2. **Alerting scope too narrow**: Even with the webhook configured, `_send_discord_alert()` only fires for background task crashes (detected by the asyncio task exception handler). Login failures — where the scraper process is alive but Chrome is on the login wall — are not wired to the alert function. Login detection code exists in both v3 scrapers (lines 58-60) but it only logs the failure; it does not call the Discord alert endpoint.

This compounds the original login detection gap: not only do the scrapers fail to detect logged-out sessions proactively (the `count=0` ambiguity), but even when the process dies from prolonged login failure, no human is notified. The operator must manually SSH into the mini PC and check process state — exactly the operational burden the Discord alerting was designed to eliminate.

The fix requires wiring login detection into the Discord alert system for both NBA and MLB scrapers, so that a logged-out Chrome session produces an immediate notification rather than silently accumulating stale data.

### Discord Alerting Deployed for Login Failures (2026-05-03)

On 2026-05-03, `ALERT_WEBHOOK_URL` was added to the mini PC's `.env` and login failure detection was wired to Discord alerts in both `bet365_nba_v3.py` and `bet365_mlb_v3.py`. This closes the gap identified on 2026-05-02. After deployment, both task death and session expiry produce immediate Discord notifications — the 6-day scraper outage (dead since April 27) is the longest undetected death in the system's history and directly motivated this fix.

Additionally, the Celtics vs 76ers game (May 2, 23:30 UTC) was missed because the bet365 session expired at 23:22 UTC — 8 minutes before tipoff. The scraper's rediscovery only runs every 30 minutes (or every 5 minutes if a game is within 60 minutes of tipoff), so a short auth expiry gap near game time means the game is permanently missed with no graceful recovery.

## Related Concepts

- [[concepts/bet365-auto-login-session-recovery]] - The auto-login mechanism that would be triggered when login detection identifies a logged-out state; CAPTCHA remains a hard blocker for fully automated recovery
- [[concepts/bet365-size-gate-stale-odds]] - The earlier three-layer session expiry detection (URL redirect → worker flag → health endpoint); the login detection gap is a fourth layer needed for v3 raw CDP scrapers
- [[concepts/game-scraper-chrome-crash-recovery]] - Chrome crash recovery handles a different failure mode (dead Chrome returning cached data); login detection handles live Chrome with expired auth
- [[concepts/worker-status-observability]] - The scraper reports "streaming" while serving stale data from an expired session — same false-healthy status pattern as the 3.7h stale data incident
- [[connections/silent-type-coercion-data-corruption]] - Empty response from logged-out session is another "plausible wrong output" — `count=0` is a valid state, making the failure invisible without content-level validation
- [[concepts/windows-ssh-chrome-gui-constraint]] - Manual login requires desktop access; login detection surfaces the need faster but recovery still requires physical/RDP intervention
- [[concepts/vps-monitoring-log-noise-elimination]] - Discord alerting deployed on 2026-05-02 but only covers task death, not login failures — a gap identified during the monitoring overhaul

## Sources

- [[daily/lcash/2026-05-01.md]] - MLB scraper `.bet365_mlb_game_live.json` stuck at `{"status":"stale","count":0}` for 34 minutes; all Chrome tabs on bet365 login wall; logged-out response indistinguishable from rate-limiting; proposed fix: Runtime.evaluate DOM probe per cycle for login/logout markers; both MLB v3 and NBA v3 have identical gap; UTC+10 timezone trap caused false alarm about tracker being dead (Session 11:39)
- [[daily/lcash/2026-05-03.md]] - Discord alerting deployed: `ALERT_WEBHOOK_URL` added to `.env`, login failure detection wired in both v3 scrapers; 6-day scraper outage confirmed (dead since Apr 27); Celtics vs 76ers missed — session expired 23:22 UTC, 8 min before 23:30 tipoff; rediscovery 30min/5min insufficient for near-game expiry (Sessions 08:10, 11:32)
- [[daily/lcash/2026-05-02.md]] - NBA scraper dead 5 days (last log April 27), MLB crashed May 2 — neither triggered Discord notification; `ALERT_WEBHOOK_URL` missing from `.env`; `_send_discord_alert()` only fires for task crashes, not login failures; login detection code exists (lines 58-60 in both v3 files) but doesn't call alert function; VPS had 0 soft book markets when should have had Bet365 + AU books active (Session 23:14)
