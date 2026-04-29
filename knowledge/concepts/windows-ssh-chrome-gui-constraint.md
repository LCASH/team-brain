---
title: "Windows SSH Chrome GUI Rendering Constraint"
aliases: [chrome-black-screen, ssh-gui-limitation, attach-first-pattern, windows-chrome-rendering, remote-chrome-management]
tags: [value-betting, operations, windows, chrome, deployment, constraint]
sources:
  - "daily/lcash/2026-04-29.md"
created: 2026-04-29
updated: 2026-04-29
---

# Windows SSH Chrome GUI Rendering Constraint

Windows blocks GPU-accelerated GUI rendering for processes spawned via SSH sessions or background services (scheduled tasks, watchdogs). Chrome launched from these contexts opens successfully — it binds to the debugging port, responds to CDP commands, and executes JavaScript — but renders a black screen visually. This means Chrome must be launched manually from the mini PC's desktop for bet365 scraping (which requires headed mode with visual rendering for anti-bot bypass). The scraper architecture must handle "Chrome already running" by attaching to the existing instance rather than killing and relaunching.

## Key Points

- Chrome launched from SSH/background processes binds to debug port and responds to CDP, but renders **black screen** visually — process running ≠ window visible
- Windows restricts GPU rendering to processes launched from the interactive desktop session — SSH shells and `schtasks` run in Session 0 (non-interactive)
- Scrapers must implement **attach-first** logic: check if Chrome is already running on the target port, attach to it if so, only launch new Chrome if none exists
- The NBA scraper's `start()` method was killing the user's manually-launched (visible, logged-in) Chrome and spawning its own invisible one — needed fix to attach first
- bet365 login detection cannot rely on URL checks (URL unchanged logged in/out) or button visibility checks (DOM may not render in black-screen mode) — login state must be verified via cookie presence or API response content
- `--disable-blink-features=AutomationControlled` triggers a harmless warning banner in Chrome that can be dismissed manually

## Details

### The Session 0 Rendering Limitation

Windows uses "session isolation" for security. The interactive desktop runs in Session 1 (or higher), while services and SSH connections run in Session 0 — a non-interactive session without a desktop compositor. Processes in Session 0 cannot access the GPU or the desktop's display system. When Chrome launches in Session 0, it starts correctly (process runs, ports bind, CDP works) but the Chromium rendering pipeline has no display target, producing a blank/black window if observed via RDP.

This is distinct from the headless Chrome issue documented in [[concepts/bet365-headless-detection]]. Headless Chrome (`--headless=new`) is blocked by bet365's SPA-level detection — it serves empty data. A Session 0 Chrome is "headed" (no `--headless` flag) but visually non-functional. bet365's anti-bot system likely still detects it as abnormal because the rendering pipeline isn't producing real pixel output, though this specific interaction wasn't tested.

### The Attach-First Pattern

The scraper's `start()` method previously followed a "kill-and-launch" pattern: terminate any existing Chrome on the target port, launch a fresh instance, connect via CDP. This worked when the scraper managed Chrome's full lifecycle. It broke when Chrome needed to be launched manually from the desktop:

1. User launches Chrome from desktop → visible, GPU-rendered, logged into bet365
2. Scraper starts (via SSH or schtask) → kills the user's Chrome → launches its own (invisible) Chrome
3. Invisible Chrome can't render bet365's anti-bot challenges → scraping fails

The fix inverts the priority: check if Chrome is already running on the target port (CDP HTTP at `http://localhost:{port}/json`), and if so, attach to it. Only launch new Chrome if no instance is found. This preserves the user's manually-launched, visually-functional Chrome while allowing the scraper to control it via CDP.

The MLB scraper already had this attach-first logic; the NBA scraper needed it added on 2026-04-29.

### Login Detection Challenges

bet365's login state cannot be reliably detected via:
- **URL checks**: bet365 uses the same URL for logged-in and logged-out states
- **"Log In" button visibility**: The DOM may report the button as "not visible" when Chrome is rendering as a black screen (no layout computation), or the button selector may not match the current SPA state

Alternative detection methods under consideration:
- **Cookie presence**: Check for the `aaat` session cookie via CDP `Network.getCookies`
- **Account-specific DOM elements**: Check for user-specific elements (balance display, account menu) that only render when logged in
- **API response content**: Make a test request to a bet365 endpoint that returns different content for authenticated vs anonymous sessions

### Operational Implications

The Windows SSH GUI constraint creates a daily operational workflow:
1. **Morning**: RDP or physically access the mini PC desktop
2. Launch Chrome windows (NBA on port 9223, MLB on port 9224)
3. Log into bet365 in each window (solve CAPTCHA manually)
4. Start scrapers via SSH — they attach to the existing Chrome instances
5. **Ongoing**: Scrapers can be restarted via SSH without touching Chrome (the persistent Chrome stays running)

If Chrome crashes during operation, the scraper's auto-recovery can kill and relaunch Chrome, but the relaunched Chrome will be invisible (launched from the scraper's Session 0 context). This means Chrome crashes during unattended operation require manual desktop intervention to restore visual rendering. See [[concepts/game-scraper-chrome-crash-recovery]] for the auto-recovery mechanism.

### 53+ Duplicate Tab Issue

When the scraper opens game pages before login is confirmed, it creates tabs that fail to load prop data (because the session is unauthenticated). On the next rediscovery cycle, it opens new tabs for the same games, accumulating duplicates. This compounds the tab leak issue documented in [[concepts/chrome-tab-leak-accumulation]]. The fix is to verify login state before opening game pages.

## Related Concepts

- [[concepts/bet365-headless-detection]] - bet365 detects headless Chrome at the SPA level; the Windows SSH constraint is a different issue (headed but visually non-functional) but compounds with it — both require manual desktop Chrome launch
- [[concepts/bet365-auto-login-session-recovery]] - CAPTCHA blocks automated re-login; manual desktop login is required after session expiry, further reinforcing the need for physical/RDP access
- [[concepts/game-scraper-chrome-crash-recovery]] - Chrome crash auto-recovery (fresh Chrome pattern) launches invisible Chrome from the scraper's Session 0 context — visual rendering lost until manual intervention
- [[concepts/cdp-stale-connection-poisoning]] - The attach-first pattern prevents killing manually-launched Chrome, but stale CDP connections from dead scrapers can still poison the attached session
- [[concepts/configuration-drift-manual-launch]] - The manual Chrome launch requirement is another operational step that can be missed on restart, similar to env var drift
- [[connections/browser-automation-reliability-cost]] - Adds a seventh reliability dimension: Chrome process must be launched from the correct Windows session for visual rendering

## Sources

- [[daily/lcash/2026-04-29.md]] - Chrome launched from SSH renders black screen on Windows; only desktop-launched Chrome gets GPU rendering; scrapers must attach to existing Chrome, not kill-and-relaunch (Session 08:19). NBA scraper's start() was killing user's Chrome; MLB already had attach-first; bet365 login detection unreliable via URL or button visibility (Sessions 08:19, 08:51). CAPTCHA blocks automated login; both accounts use Janklu565/Arilue2!; `--disable-blink-features=AutomationControlled` shows harmless warning banner (Session 08:51). Can't launch GUI Chrome apps via SSH on Windows — critical constraint for remote management; 53+ duplicate tabs from opening pages before login confirmed (Session 08:19)
