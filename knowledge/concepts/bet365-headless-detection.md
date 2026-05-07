---
title: "bet365 Headless Browser Detection"
aliases: [headless-detection, headed-mode-requirement, headless-fingerprinting, vanilla-chrome-detection, navigator-webdriver-detection]
tags: [bet365, anti-scraping, browser-automation, headless, deployment]
sources:
  - "daily/lcash/2026-04-15.md"
  - "daily/lcash/2026-05-07.md"
created: 2026-04-15
updated: 2026-05-07
---

# bet365 Headless Browser Detection

bet365 detects `--headless=new` Chrome and serves degraded/inert SPA content — the page loads, JavaScript runs, and WebSocket constructor wrappers inject successfully, but zero WebSocket traffic arrives from the server. This is a separate defense layer from Cloudflare's network-level bot detection: even when Cloudflare is bypassed (e.g., via residential proxy), the SPA itself detects headless mode and withholds data. Headed (visible) Chrome on a desktop session bypasses this detection completely.

## Key Points

- bet365 serves empty/inert SPA content to `--headless=new` Chrome — page loads, JS executes, WS wrapper injects, but zero WS frames arrive from the server
- This is distinct from Cloudflare blocking: Cloudflare operates at the network/IP level, while this detection operates at the browser fingerprint level within the SPA
- Headed mode on a desktop session (even rendering into an invisible window) bypasses the detection — a real-user fingerprint is sufficient
- Profile wiping via `shutil.rmtree` on every Chrome start is fine — session warming is not required; headed mode alone is sufficient
- The existing NBA/MLB game scrapers (`bet365_game.py`) already run in headed mode intentionally, confirming this is a known requirement in the codebase
- On 2026-05-07, bet365 was confirmed to detect **vanilla Chrome** with `navigator.webdriver=true` even in headed mode — AdsPower anti-detect browser is now required, not just headed Chrome
- Body size difference is a diagnostic signal: 114KB (vanilla Chrome, partial bot detection) vs 131KB (AdsPower, full content)

## Details

### Discovery

During the 2026-04-15 Dell server port of the bet365 racing WS adapter, lcash investigated why Chrome captured 0 WebSocket frames despite the page loading successfully. Four Chrome configurations were compared:

1. **Raw HTTP (curl/requests)** — blocked by Cloudflare (expected)
2. **Headless CDP** (`--headless=new`) — page loads, SPA initializes, constructor wrapper injects, but zero WS traffic arrives
3. **Playwright bundled Chromium** — same result as headless CDP
4. **Existing NBA worker's Chrome configuration** — works, uses headed mode

The critical insight came from examining how the existing NBA game scraper launches Chrome: it uses headed (visible) mode, not headless. When the racing adapter was switched to headed mode, WS traffic immediately appeared. The Dell server has an active desktop session, so headed Chrome renders into a real window with genuine user-agent characteristics.

### Detection Mechanism

The detection mechanism likely examines a combination of browser properties that differ between headless and headed modes: `navigator.webdriver` property, presence of `window.chrome.runtime` and related APIs, rendered viewport dimensions and pixel ratios, WebGL renderer strings, and canvas fingerprint characteristics.

The SPA appears to gate its WebSocket connection initialization on a headless check result. Rather than blocking the page load entirely (which would be visible during debugging), it allows the SPA to function superficially — JavaScript runs, DOM renders, even the WS constructor wrapper injects — but the server-side WS infrastructure never sends data to what it identifies as a headless client. This makes the detection subtle: everything appears to work except that no data flows.

### Windows Deployment Complications

The Dell server port also revealed several Windows-specific operational issues that compound with the headed-mode requirement:

- **Zombie Chrome processes**: Old Chrome instances hold the CDP debugging port and user-data-dir hostage. New CDP connections silently attach to the zombie instead of spawning a fresh browser. Must kill the entire process tree and re-wipe the profile directory before relaunching.
- **Python stdout buffering**: When stdout is redirected to a file on Windows, output buffers indefinitely. If the process crashes, all buffered output is lost. Fix: use `python -u` (unbuffered mode) or set `PYTHONUNBUFFERED=1`.
- **cp1252 encoding**: Unicode characters (e.g., `✓`) crash Python on Windows because the default console encoding is cp1252, not UTF-8. Fix: `sys.stdout.reconfigure(encoding='utf-8')`.

### Runner Map Alternative

The Dell port also discovered that the CSS selector approach for building the runner map (clicking `.rcr-7b` race tabs) fails on fresh Chrome profiles — the obfuscated CSS class names may differ between browser versions or profiles. The preferred alternative is using the `racecoupon` HTTP endpoint via `page.evaluate("fetch(...)")` to inherit the browser's session cookies and sync_term. This reuses the existing `_parse_racecoupon_response` parser (~30 lines) instead of fragile CSS selector logic.

### Vanilla Chrome Detection Escalation (2026-05-07)

On 2026-05-07, lcash discovered that bet365's anti-bot detection had escalated beyond headless-vs-headed to also detect **vanilla Chrome with `--remote-debugging-port`**. The mini PC production environment runs standard Chrome (not AdsPower), and the `betbuilderpregamecontentapi/wizard` endpoint — the most heavily protected — started returning partial or empty content. Local testing on AdsPower (which masks `navigator.webdriver` and spoofs fingerprints) returned full 131KB responses, while the mini PC's vanilla Chrome received only 114KB (partial content, bot detection applied).

This represents a significant escalation: previously, headed Chrome with `--disable-blink-features=AutomationControlled` was sufficient to bypass detection. bet365 appears to have shipped stricter anti-bot checks that now examine additional browser properties exposed by CDP debugging connections. The `navigator.webdriver` property is `true` by default when Chrome is launched with `--remote-debugging-port`, and bet365's detection now checks this property.

Three remediation paths were identified:
1. **Install AdsPower on mini PC** — the proper long-term fix, providing full fingerprint spoofing
2. **Puppeteer-stealth-style evasion init scripts** — ~50 lines of JS injected via `Page.addScriptToEvaluateOnNewDocument` to mask `navigator.webdriver`, `chrome.runtime`, and other CDP artifacts
3. **Both** — defense in depth

This discovery also highlighted an **environment parity risk**: all local testing used AdsPower (which masks CDP artifacts), but production used vanilla Chrome. The anti-bot escalation was invisible during development because the testing environment had stronger anti-detection capabilities than production. Going forward, production must use the same anti-detect browser as development, or tests must explicitly validate against vanilla Chrome.

V3 rollback was attempted when V4 failed on mini PC, but V3 also failed — confirming this is an environmental issue (bet365 anti-bot change), not a code regression.

## Related Concepts

- [[connections/anti-scraping-driven-architecture]] - Headless detection is a distinct defense layer from Cloudflare, SPA navigation state, and WS authentication
- [[concepts/bet365-racing-adapter-architecture]] - The adapter being ported to Dell that exposed this detection
- [[concepts/cdp-browser-data-interception]] - CDP attachment works in both modes, but data only flows in headed mode
- [[concepts/configuration-drift-manual-launch]] - Windows deployment complications (zombie processes, encoding) compound with deployment gotchas
- [[concepts/silent-worker-authentication-failure]] - Headless detection produces a similar "zero output" failure mode — no error, just no data

- [[concepts/v3-scanner-centralized-architecture]] - V3 deployment blocked on mini PC by vanilla Chrome detection; environment parity risk between AdsPower (dev) and vanilla Chrome (prod)
- [[concepts/windows-ssh-chrome-gui-constraint]] - Vanilla Chrome from SSH renders black screen + now also detected by anti-bot — double constraint requiring desktop-launched AdsPower

## Sources

- [[daily/lcash/2026-04-15.md]] - Dell server port: 4 Chrome configs compared, headless serves empty SPA, headed mode bypasses completely, profile wiping fine, zombie Chrome on Windows, Python stdout buffering, cp1252 encoding, racecoupon HTTP preferred over CSS click runner map (Session 14:55)
- [[daily/lcash/2026-05-07.md]] - Vanilla Chrome with `--remote-debugging-port` now detected: 114KB (partial) vs 131KB (full) body; `navigator.webdriver=true` on vanilla Chrome; AdsPower required for production; V3/V4 both fail on mini PC's vanilla Chrome; environment parity risk: local AdsPower testing doesn't validate production vanilla Chrome (Session 22:29)
