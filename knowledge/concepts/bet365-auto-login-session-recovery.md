---
title: "bet365 Auto-Login Session Recovery"
aliases: [auto-login, session-recovery, bet365-login-automation, cookie-expiry-recovery, cdp-login-script]
tags: [bet365, scraping, operations, browser-automation, reliability, value-betting]
sources:
  - "daily/lcash/2026-04-23.md"
  - "daily/lcash/2026-04-24.md"
created: 2026-04-23
updated: 2026-04-24
---

# bet365 Auto-Login Session Recovery

bet365 sessions expire overnight despite the `aaat` cookie having a ~10-day expiry window, requiring manual RDP into the mini PC to log back in via Chrome. On 2026-04-23, lcash built an automated login script by watching a manual login flow via CDP, enabling self-healing session recovery. The script handles autofill interference (saved browser passwords must be cleared before typing), uses human-like delays to avoid bot detection, and falls back to raw CDP via httpx when Playwright has protocol errors with the Chrome instance.

## Key Points

- bet365 `aaat` cookie expires ~10 days out, but sessions can die overnight anyway — cookie injection alone is not a reliable session maintenance strategy
- Automated login flow: click "Log In" span → clear autofilled username → type username → clear autofilled password → type password → click "Log In" submit button
- Must clear autofilled credentials before typing — Chrome's saved password manager pre-fills fields, and typing over them appends rather than replaces
- Human-like delays between actions are needed to avoid triggering bet365's bot detection on the login form
- Playwright had protocol errors with the existing Chrome instance; raw CDP via httpx worked as a fallback for monitoring and interaction
- The auto-login complements the three-layer session expiry detection system (see [[concepts/bet365-size-gate-stale-odds]]) — detection surfaces WHEN the session is expired, auto-login FIXES it

## Details

### The Session Expiry Problem

The value betting scanner's bet365 game scrapers (NBA on port 9223, MLB on port 9224) depend on an authenticated Chrome session to access player prop data. The three-layer session expiry detection system deployed on 2026-04-23 (see [[concepts/bet365-size-gate-stale-odds]]) surfaces session expiry via the health endpoint and dashboard. However, the recovery procedure was manual: RDP into the mini PC, open Chrome on the appropriate debugging port, and log in to bet365 by hand.

This manual recovery is fragile for two reasons: (1) it requires a human to notice the `SESSION EXPIRED` status and act on it, and (2) it requires RDP access, which may not be available if the operator is away from their desk or on a different network. Combined with the discovery that bet365 sessions die overnight despite long-lived cookies, this creates a daily maintenance burden.

### Building the Auto-Login Script

The auto-login script was built by observing a manual login flow via CDP (Chrome DevTools Protocol). Rather than reverse-engineering bet365's login API (which would require handling CSRF tokens, Cloudflare challenges, and session establishment), the script drives the same browser that the scraper is already attached to — logging in "as the user" through the existing Chrome instance.

The login flow has five steps:

1. **Click the "Log In" element** — bet365's login form is triggered by clicking a span element with the login label
2. **Clear the username field** — Chrome's saved password manager autofills the username. Simply typing into the field appends to the autofill value. The script must select-all and clear the field before entering the username
3. **Type the username** — with human-like inter-keystroke delays (~50-100ms between characters)
4. **Clear and type the password** — same autofill clearing pattern as the username
5. **Click the submit button** — the "Log In" button submits the form

Each step includes delays to simulate human interaction patterns. bet365's login form likely has client-side behavioral analysis (timing between fields, keystroke patterns) that could flag automated logins. The delays are calibrated to appear natural without being so slow that the login times out.

### CDP Fallback

During development, Playwright had protocol errors when trying to interact with the already-running Chrome instance on the mini PC. The Chrome instance was launched by the scraper via `--remote-debugging-port` and had been running for an extended period. Playwright's connection to a long-lived Chrome session can encounter stale page contexts and protocol desynchronization.

The fallback was raw CDP via `httpx` — making direct HTTP requests to Chrome's debugging endpoint (e.g., `http://localhost:9223/json`) to enumerate pages, then using the WebSocket debugging URL to send CDP commands directly. This lower-level approach bypasses Playwright's session management and works reliably against long-lived Chrome instances.

### Session-Per-Cookie Constraint

An earlier attempt to share bet365 cookies between the NBA Chrome (port 9223) and MLB Chrome (port 9224) failed. Injecting the same cookies into both instances resulted in only the NBA Chrome accepting the session — the MLB Chrome connection was reset. This suggests bet365 enforces one active session per cookie set, meaning each Chrome instance needs its own independent login. The auto-login script must run against each Chrome port independently.

### Integration with Session Expiry Detection

The auto-login script is designed to be triggered by the session expiry detection system. When the scraper detects a redirect to bet365's login page (layer 1 of the detection system), or when the health endpoint shows `SESSION EXPIRED` status, the auto-login can be invoked to automatically recover without human intervention. This creates a self-healing loop: scraper detects expiry → auto-login restores session → scraper resumes normal operation.

The full self-healing architecture is:
1. **Detection**: Scraper checks for URL redirects to login page (per-request)
2. **Signaling**: Worker writes `session_expired` flag; server surfaces on health endpoint
3. **Recovery**: Auto-login script authenticates via CDP → session restored
4. **Resumption**: Scraper auto-attaches to the restored Chrome session

### Deployment Status

As of 2026-04-23, the auto-login script was built and tested against the NBA Chrome instance on the mini PC. Deployment to both NBA (port 9223) and MLB (port 9224) scrapers, and wiring the auto-login trigger into the session expiry detection flow, is pending.

## Related Concepts

- [[concepts/bet365-size-gate-stale-odds]] - The session expiry detection system (three layers) that surfaces when auto-login is needed; auto-login is the recovery mechanism for the state that detection identifies
- [[concepts/bet365-headless-detection]] - bet365 detects headless Chrome and serves empty data; auto-login must run against headed Chrome instances on the mini PC's desktop session
- [[concepts/game-scraper-chrome-crash-recovery]] - Chrome crash auto-recovery handles a different failure mode (EPIPE/dead Chrome); auto-login handles session expiry (live Chrome, expired auth)
- [[connections/browser-automation-reliability-cost]] - Session expiry and auto-login add a fifth reliability dimension to the browser-mediated architecture: authentication lifecycle management
- [[concepts/cdp-browser-data-interception]] - Raw CDP via httpx used as fallback when Playwright has protocol errors with long-lived Chrome instances
- [[concepts/configuration-drift-manual-launch]] - Auto-login reduces the operational bus factor by eliminating the need for manual RDP login after overnight session expiry
- [[concepts/bet365-shared-chrome-single-session]] - bet365 enforces single-session-per-account; auto-login now targets only port 9223 (shared Chrome) instead of two separate ports

## Sources

- [[daily/lcash/2026-04-23.md]] - Bet365 NBA scraper NOT logged in despite yesterday's cookies; cookie `aaat` ~10-day expiry but sessions die overnight; built automated login script watching manual flow via CDP; must clear autofilled fields before typing; Playwright protocol errors → raw CDP via httpx fallback; login flow: click Log In → clear+type username → clear+type password → click submit; human-like delays for bot detection avoidance; deployment to both NBA/MLB scrapers pending (Session 21:36)
- [[daily/lcash/2026-04-24.md]] - bet365 single-session-per-account discovered: NBA Chrome login failing because MLB Chrome already logged in; consolidated to shared Chrome on port 9223; auto-login now targets only one port; port 9224 killed (Session 09:10)
