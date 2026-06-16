---
title: "LinkedIn AdsPower Inbox Bot"
aliases: [linkedin-bot, adspower-linkedin, linkedin-inbox-automation, linkedin-outreach-bot]
tags: [knowted, linkedin, scraping, adspower, ai-agent, anti-detection, outreach]
sources:
  - "daily/lcash/2026-06-12.md"
  - "daily/lcash/2026-06-16.md"
created: 2026-06-12
updated: 2026-06-16
---

# LinkedIn AdsPower Inbox Bot

On 2026-06-12, lcash built a LinkedIn inbox automation bot using AdsPower for anti-detection browser fingerprinting. The system switched from Playwright's vanilla Chromium to an AdsPower profile (k19yb91n) connected over CDP after LinkedIn's bot detection flagged the vanilla fingerprint. The bot includes an AI-powered /api/ai-draft endpoint with motion-aware drafting (sales leader, entrepreneur, investor, 1:1 warm, auto-pick) powered by the Claude API, with voice configuration maintained in a single-file source of truth (voice_context.py).

## Key Points

- **AdsPower over vanilla Playwright**: LinkedIn bot detection nuked the vanilla Chromium fingerprint; AdsPower profile k19yb91n over CDP (localhost:8888, local API at http://local.adspower.net:50325/api/v1/browser/start?user_id=k19yb91n) provides persistent anti-detection fingerprinting
- **Cookie management pitfall**: clear_cookies() before re-injecting wipes AdsPower's existing LinkedIn session and forces re-validation; cleaner approach is to only inject cookies if linkedin_cookies.json is newer or no li_at cookie present
- **Rate limits for safety**: <=4 scans/day, <=25 unreads/scan, <=10 replies/session, <=50 daily messages, restrict to local working hours; account flagging requires 24-72 hours of clean manual behavior to cool off
- **Bot-detection signals**: navigator.webdriver, missing chrome.runtime, empty navigator.plugins, permissions.query hang are all detectable; humanize with bezier mouse curves, per-char typing with typo simulation, gaussian jitter on sleeps
- **Project location**: ~/Documents/Claude Bot/ (last touched 11 Feb 2026); missing li_a cookie (Sales Nav enterprise token) is not needed -- regular /messaging/ works via li_at + li_ep_auth_context

## Details

### Anti-Detection Architecture

The core technical decision was abandoning Playwright's built-in Chromium in favor of connecting to an AdsPower-managed browser profile over the Chrome DevTools Protocol. AdsPower maintains a persistent browser fingerprint (canvas hash, WebGL renderer, audio context, font enumeration, screen resolution, timezone, language, and dozens of other signals) that remains consistent across sessions. This is critical for LinkedIn, which builds behavioral fingerprints over time and flags inconsistencies.

Even with AdsPower handling the browser fingerprint, additional anti-detection hardening is necessary at the interaction level. The bot implements bezier curve mouse movements rather than instant teleportation, per-character typing with occasional typo simulation and correction, and gaussian-distributed random jitter on all sleep intervals. These patterns mimic human motor behavior and prevent detection via interaction timing analysis. Key bot-detection signals that must be masked include the navigator.webdriver property, missing chrome.runtime object, empty navigator.plugins array, and permissions.query hanging behavior.

The stop() function was patched to disconnect from the AdsPower browser rather than close it entirely. Closing the browser would destroy the AdsPower session state, while disconnecting leaves the profile running for potential manual inspection or reconnection.

### Rate Limiting and Account Safety

LinkedIn's detection is primarily volume and frequency driven rather than purely fingerprint-based. The bot enforces conservative limits: no more than 4 inbox scans per day, no more than 25 unreads processed per scan, no more than 10 replies per session, and no more than 50 total messages per day. Activity is restricted to local working hours to match expected human behavior patterns.

If an account gets flagged, recovery requires 24 to 72 hours of clean manual behavior -- logging in normally, browsing profiles manually, engaging with the feed naturally. This cooldown period allows LinkedIn's risk scoring to decay back to baseline.

### AI-Powered Drafting

The /api/ai-draft endpoint provides context-aware message drafting using the Claude API. It implements motion-aware persona selection: sales leader, entrepreneur, investor, 1:1 warm, or auto-pick based on the conversation context. All drafting draws from a single voice_context.py file that serves as the source of truth for tone, vocabulary, and communication style. This ensures consistency across all automated responses regardless of which persona is active.

The missing li_a cookie (a Sales Navigator enterprise token) was investigated but determined unnecessary. The regular LinkedIn messaging endpoint at /messaging/ works with the standard li_at authentication cookie plus the li_ep_auth_context cookie, which are sufficient for inbox reading and reply functionality.

## Related Concepts

- [[concepts/bet365-headless-detection]] - Parallel anti-detection challenges in a different domain (sports betting) with similar fingerprint-masking requirements
- [[concepts/twitter-x-api-scraping-constraints]] - Another social platform's anti-scraping measures and workarounds
- [[concepts/adspower-wayland-gui-session-recovery]] - AdsPower GUI/session management issues on Linux that affect the same toolchain
- [[concepts/knowted-sales-prospecting-tool-stack]] - The broader outreach tool stack that this LinkedIn bot fits into

### Anti-Detection Overhaul and Auto-Start Pattern (2026-06-16)

On 2026-06-16, lcash performed a comprehensive anti-detection overhaul after LinkedIn flagged the account due to bot-like interaction patterns. The overhaul addressed timing at every interaction point: `fill()` and `click()` were replaced with per-character typing with typo simulation, bezier curve mouse movements, and gaussian-distributed random jitter on all sleep intervals. Even with AdsPower's browser fingerprint masking, Playwright's instant actions were fingerprintable at the interaction level.

A structural improvement was also deployed: **auto-start across all endpoints**. Previously, users had to call `/api/start` before any scan/reply operations. The refactored architecture lazily boots the bot on the first user-facing call (`scan-unread`, `scan-recent`, `reply`, `ai-draft`), eliminating the separate start step. This means any endpoint call from the UI "just works" without worrying about bot initialization state.

Key anti-detection additions:
- **Bezier mouse curves**: Playwright's instant `mouse.move()` replaced with natural arc trajectories
- **Per-character typing**: Each character typed with individual delay + occasional typo simulation + backspace correction
- **Gaussian jitter**: All `sleep()` calls use gaussian-distributed random values around the target duration rather than fixed milliseconds
- **Scroll realism**: Random scroll amounts with momentum simulation rather than instant `scrollIntoView()`
- **Context-level patching**: `navigator.webdriver`, `chrome.runtime`, `navigator.plugins`, and `permissions.query` all patched at the Playwright browser context level even when using AdsPower

The `__cf_bm` cookie (Cloudflare bot management) rotates every ~30 minutes; stale cookies from hours-old pastes will fail silently — always harvest fresh from the live session.

## Sources

- [[daily/lcash/2026-06-12.md]] - AdsPower profile k19yb91n over CDP, Playwright vanilla fingerprint nuked, cookie management pitfalls, /api/ai-draft with motion-aware personas, voice_context.py single-file config, rate limits (4 scans/25 unreads/10 replies/50 messages), bot-detection signals (navigator.webdriver et al.), humanization techniques (bezier/typing/jitter), li_a vs li_at cookie analysis, project at ~/Documents/Claude Bot/ (Session times)
- [[daily/lcash/2026-06-16.md]] - Anti-detection overhaul: fill()/click() replaced with per-char typing + bezier mouse; auto-start pattern across all endpoints (lazy boot on first call); gaussian jitter on all sleeps; scroll realism; context-level patching of webdriver/runtime/plugins/permissions; __cf_bm 30-min rotation; account flagging requires 24-72h manual cooloff (Session 20:45)
