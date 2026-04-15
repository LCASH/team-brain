---
title: "bet365 Headless Browser Detection"
aliases: [headless-detection, headed-mode-requirement, headless-fingerprinting]
tags: [bet365, anti-scraping, browser-automation, headless, deployment]
sources:
  - "daily/lcash/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# bet365 Headless Browser Detection

bet365 detects `--headless=new` Chrome and serves degraded/inert SPA content — the page loads, JavaScript runs, and WebSocket constructor wrappers inject successfully, but zero WebSocket traffic arrives from the server. This is a separate defense layer from Cloudflare's network-level bot detection: even when Cloudflare is bypassed (e.g., via residential proxy), the SPA itself detects headless mode and withholds data. Headed (visible) Chrome on a desktop session bypasses this detection completely.

## Key Points

- bet365 serves empty/inert SPA content to `--headless=new` Chrome — page loads, JS executes, WS wrapper injects, but zero WS frames arrive from the server
- This is distinct from Cloudflare blocking: Cloudflare operates at the network/IP level, while this detection operates at the browser fingerprint level within the SPA
- Headed mode on a desktop session (even rendering into an invisible window) bypasses the detection — a real-user fingerprint is sufficient
- Profile wiping via `shutil.rmtree` on every Chrome start is fine — session warming is not required; headed mode alone is sufficient
- The existing NBA/MLB game scrapers (`bet365_game.py`) already run in headed mode intentionally, confirming this is a known requirement in the codebase

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

## Related Concepts

- [[connections/anti-scraping-driven-architecture]] - Headless detection is a distinct defense layer from Cloudflare, SPA navigation state, and WS authentication
- [[concepts/bet365-racing-adapter-architecture]] - The adapter being ported to Dell that exposed this detection
- [[concepts/cdp-browser-data-interception]] - CDP attachment works in both modes, but data only flows in headed mode
- [[concepts/configuration-drift-manual-launch]] - Windows deployment complications (zombie processes, encoding) compound with deployment gotchas
- [[concepts/silent-worker-authentication-failure]] - Headless detection produces a similar "zero output" failure mode — no error, just no data

## Sources

- [[daily/lcash/2026-04-15.md]] - Dell server port: 4 Chrome configs compared, headless serves empty SPA, headed mode bypasses completely, profile wiping fine, zombie Chrome on Windows, Python stdout buffering, cp1252 encoding, racecoupon HTTP preferred over CSS click runner map (Session 14:55)
