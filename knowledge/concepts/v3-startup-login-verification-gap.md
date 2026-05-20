---
title: "V3 Startup Login Verification Gap"
aliases: [v3-login-gap, chrome-running-not-logged-in, startup-session-assumption, presumed-logged-in-bug]
tags: [value-betting, v3, bet365, chrome, reliability, bug, architecture]
sources:
  - "daily/lcash/2026-05-18.md"
created: 2026-05-18
updated: 2026-05-18
---

# V3 Startup Login Verification Gap

The V3 scanner's `startup.py` (line ~258) assumes that if Chrome is already running on the target CDP port, the bet365 session is logged in and healthy. On 2026-05-18, this assumption caused **zero NBA market production for 3+ days**: NBA Chrome had been running since May 8 (10 days), v3 was restarted on May 15, saw Chrome "already running," skipped login verification, and the orchestrator sat silent with zero log entries because the session cookies had expired.

## Key Points

- `startup.py:258` checks if Chrome is running; if yes, **skips login verification entirely** — presumes the session is healthy
- NBA Chrome ran 10 days (since May 8) → cookies expired → v3 restarted May 15 → detected "already running" → skipped login → discovery returned nothing → orchestrator idle with **zero log entries**
- The failure is completely silent: no error logs, no health endpoint degradation, no alerting — the orchestrator simply produces nothing
- This is distinct from the login detection gap in [[concepts/bet365-session-login-detection-gap]] which is about detecting expiry during active scraping — this bug prevents detection at **startup time**
- Fix requires adding an `_is_logged_in` check to the "presumed logged in" code path — verify session state even when Chrome is already running
- MLB Chrome (same May 8 launch) may expire similarly within days — the bug is time-bombed across all sport scrapers

## Details

### The Failure Chain

The v3 startup sequence for each sport scraper follows these steps:

1. Check if AdsPower Chrome is running on the target CDP port
2. **If running**: Skip Chrome launch + login → proceed directly to discovery
3. **If not running**: Launch Chrome via AdsPower API → perform login flow → proceed to discovery

Step 2 contains the dangerous assumption: "Chrome running" implies "Chrome authenticated." This was a reasonable shortcut when Chrome sessions lasted indefinitely, but bet365 cookies expire after approximately 10 days (the `aaat` cookie expiry documented in [[concepts/bet365-auto-login-session-recovery]]). After expiry, Chrome is still running and responsive to CDP commands, but all bet365 API calls return empty or redirect to the login page.

The May 18 incident followed this exact chain: Chrome launched May 8, cookies expired around May 18, v3 was restarted on May 15 (before expiry, but the cookies were already aging). On restart, v3 saw Chrome running, skipped login, and began discovery. Discovery with an expired session returned empty results (no games found). The orchestrator entered its polling loop with zero games to monitor — producing zero markets, zero picks, and zero log entries.

### Why Zero Log Entries

The silent failure is particularly dangerous because the orchestrator's logging is conditional on having games to process. With zero games discovered, the main loop has nothing to iterate over and nothing to log. The health endpoint may show the scraper as "running" (the process is alive) without reflecting that it has zero data. This follows the established "process liveness ≠ data flow" pattern documented across the scanner's operational history.

### The Tab Teardown Red Herring

During diagnosis, lcash observed that Chrome showed only the bet365 homepage with no game tabs open — which appeared to confirm the scraper wasn't working. However, this is actually **normal v3 behavior**: `TAB_TEARDOWN_AFTER_START_MIN=5` means game tabs are opened and closed per refresh cycle, not kept permanently open. Seeing only the homepage in Chrome tabs does not indicate failure. This made the diagnosis harder because the visual state of Chrome was consistent with both "healthy between refresh cycles" and "broken with expired session."

### Recommended Fix

The fix adds an `_is_logged_in(page)` check that runs after Chrome is detected as already running, before proceeding to discovery. This check could:

1. Navigate to a known bet365 endpoint and check for login page redirect
2. Check for the presence of the `aaat` session cookie via CDP `Network.getCookies`
3. Attempt a lightweight API call and verify non-empty response

If the check fails, the scraper should trigger the full login flow (including CAPTCHA handling if needed) before proceeding. This transforms the startup from "trust Chrome state" to "verify Chrome state."

### Broader Applicability

All v3 sport scrapers share the same startup code path and the same vulnerability. MLB Chrome was also launched on May 8 and will face the same cookie expiry timeline. The fix must be applied to the shared startup code, not per-sport.

## Related Concepts

- [[concepts/bet365-session-login-detection-gap]] - The login detection gap during active scraping (empty response ambiguity); this article covers the startup-time variant where login is never checked at all
- [[concepts/adspower-wayland-gui-session-recovery]] - AdsPower phantom-active state compounds with this gap: Chrome appears running (phantom) AND logged in (assumed), doubly wrong
- [[concepts/bet365-auto-login-session-recovery]] - The auto-login mechanism that would be triggered if login verification detected expiry; CAPTCHA remains a hard blocker
- [[concepts/worker-status-observability]] - The scraper reports "running" while producing zero data — the same false-healthy pattern from prior incidents
- [[concepts/v3-scanner-centralized-architecture]] - The v3 architecture whose startup sequence contains this gap
- [[connections/stale-process-state-phantom-liveness]] - The broader pattern of process state not reflecting actual operational reality

## Sources

- [[daily/lcash/2026-05-18.md]] - NBA Chrome running since May 8 (10 days); v3 restarted May 15, saw Chrome "already running," skipped login verification; discovery returned nothing; orchestrator sat silent with zero log entries; zero NBA market production for 3+ days; tab teardown is normal behavior not a failure indicator; MLB Chrome same May 8 launch may expire similarly (Session 09:30)
